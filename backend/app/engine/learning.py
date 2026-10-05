"""The closed loop: creator feedback changes the next ranking.

This is deliberately not a model. It is a bounded, inspectable adjustment layer
that starts working on the very first rejection — which is what makes the MVP
feel alive before there is enough data to train anything. The same feedback
events it reads are the training rows a learned ranker will later use, so
nothing collected here is thrown away when the model arrives.

Every adjustment is capped, decays with time, and can be printed for a creator
as "why did this move".
"""
from __future__ import annotations

import datetime as dt
import math
from collections import defaultdict
from dataclasses import dataclass, field

from ..models import Creator, FeedbackEvent, Product

# How far feedback is allowed to move a score. Without a ceiling, three angry
# taps could bury a whole category for good.
MIN_MULTIPLIER = 0.62
MAX_MULTIPLIER = 1.15

# Each rejection reason moves a different lever. Positive numbers are penalties.
REASON_EFFECTS: dict[str, dict[str, float]] = {
    "too_expensive":      {"price_above_median": 0.16, "category": 0.02},
    "not_my_niche":       {"category": 0.20},
    "already_promoted":   {"product": 1.00},            # suppress that item only
    "audience_wont_care": {"category": 0.10, "audience_weak": 0.12},
    "dont_trust_product": {"low_quality": 0.18, "seller": 0.10},
    "not_trending":       {"low_trend": 0.16},
    "angle_unclear":      {},                            # content issue, not fit
}

# A delivered order is the strongest positive signal the loop gets (slide 5:
# Click -> Order -> NMV -> Learn); it lifts that category for this creator.
POSITIVE_EFFECTS = {"promote": 0.09, "save": 0.04, "click": 0.01, "order": 0.06}

HALF_LIFE_DAYS = 45.0


@dataclass
class CreatorAdjustments:
    """Everything learned about one creator, ready to apply to any product."""

    category_penalty: dict[str, float] = field(default_factory=dict)
    suppressed_products: set[str] = field(default_factory=set)
    price_sensitivity: float = 0.0      # >0 means "stop showing me expensive things"
    quality_sensitivity: float = 0.0
    trend_sensitivity: float = 0.0
    audience_sensitivity: float = 0.0
    category_boost: dict[str, float] = field(default_factory=dict)
    event_count: int = 0

    def explain(self) -> list[str]:
        notes = []
        for category, penalty in sorted(
            self.category_penalty.items(), key=lambda kv: -kv[1]
        ):
            if penalty >= 0.05:
                notes.append(f"{category} down-weighted {penalty:.0%} from recorded rejections")
        for category, boost in sorted(self.category_boost.items(), key=lambda kv: -kv[1]):
            if boost >= 0.04:
                notes.append(f"{category} up-weighted {boost:.0%} from promotes and saves")
        if self.price_sensitivity >= 0.05:
            notes.append("higher-priced products down-weighted")
        if self.quality_sensitivity >= 0.05:
            notes.append("lower-rated products down-weighted")
        if self.trend_sensitivity >= 0.05:
            notes.append("flat-trend products down-weighted")
        if self.suppressed_products:
            notes.append(f"{len(self.suppressed_products)} product(s) hidden as already promoted")
        return notes


def _decay(event_time: dt.datetime, now: dt.datetime) -> float:
    """Recent feedback counts more; a six-month-old skip barely counts."""
    if event_time.tzinfo is None:
        event_time = event_time.replace(tzinfo=dt.timezone.utc)
    age_days = max(0.0, (now - event_time).total_seconds() / 86400)
    return 0.5 ** (age_days / HALF_LIFE_DAYS)


def build_adjustments(
    events: list[FeedbackEvent],
    products_by_id: dict[str, Product],
) -> CreatorAdjustments:
    """Fold a creator's feedback history into one adjustment object."""
    adj = CreatorAdjustments(event_count=len(events))
    now = dt.datetime.now(dt.timezone.utc)

    category_penalty: dict[str, float] = defaultdict(float)
    category_boost: dict[str, float] = defaultdict(float)

    for event in events:
        product = products_by_id.get(event.product_id)
        if product is None:
            continue
        weight = _decay(event.created_at, now)
        category = product.category

        if event.action in POSITIVE_EFFECTS:
            category_boost[category] += POSITIVE_EFFECTS[event.action] * weight
            if event.action == "promote":
                # Promoting retires the product for this creator. Waiting to be
                # told "already promoted" wastes a slot in every slate until
                # they bother to say so — and asking a creator to reject a
                # product they just posted about is the wrong way round.
                # A save is different: that means "maybe later", so it stays.
                adj.suppressed_products.add(event.product_id)
            continue

        if event.action != "skip":
            continue

        effects = REASON_EFFECTS.get(event.reason or "", {"category": 0.08})
        for lever, size in effects.items():
            scaled = size * weight
            if lever == "category":
                category_penalty[category] += scaled
            elif lever == "product":
                adj.suppressed_products.add(event.product_id)
            elif lever == "price_above_median":
                adj.price_sensitivity += scaled
            elif lever in ("low_quality", "seller"):
                adj.quality_sensitivity += scaled
            elif lever == "low_trend":
                adj.trend_sensitivity += scaled
            elif lever == "audience_weak":
                adj.audience_sensitivity += scaled

    adj.category_penalty = {k: _saturate(v, 0.35) for k, v in category_penalty.items()}
    adj.category_boost = {k: _saturate(v, 0.15) for k, v in category_boost.items()}
    adj.price_sensitivity = _saturate(adj.price_sensitivity, 0.30)
    adj.quality_sensitivity = _saturate(adj.quality_sensitivity, 0.30)
    adj.trend_sensitivity = _saturate(adj.trend_sensitivity, 0.30)
    adj.audience_sensitivity = _saturate(adj.audience_sensitivity, 0.30)
    return adj


def _saturate(raw: float, ceiling: float) -> float:
    """Diminishing returns rather than a hard cap.

    A linear sum with `min()` lets three taps hit the maximum penalty, which
    feels punitive and throws away the difference between a creator who skipped
    a category three times and one who skipped it thirty times. This approaches
    the ceiling asymptotically: the first skip moves the score a little, the
    tenth barely moves it at all, and the ordering still carries information.
    """
    return round(ceiling * (1 - math.exp(-1.6 * raw)), 4)


def multiplier_for(
    creator: Creator,
    product: Product,
    adj: CreatorAdjustments,
    signals: dict[str, float] | None = None,
) -> float:
    """The bounded multiplier applied to this creator-product pair."""
    # Already-promoted products are removed in Stage 1 (see eligibility.py), so
    # there is nothing to discount here; scoring one directly still returns an
    # honest score rather than a punished one.
    multiplier = 1.0
    multiplier -= adj.category_penalty.get(product.category, 0.0)
    multiplier += adj.category_boost.get(product.category, 0.0)

    # Sensitivities only bite on products that actually have the complained-about
    # property, so "too expensive" never punishes a cheap product.
    midpoint = (creator.price_min + creator.price_max) / 2
    if product.price > midpoint:
        overshoot = min(1.0, (product.price - midpoint) / max(midpoint, 1))
        multiplier -= adj.price_sensitivity * overshoot
    if product.rating < 4.3:
        multiplier -= adj.quality_sensitivity * min(1.0, (4.3 - product.rating) / 1.0)
    if product.trend_score < 0.5:
        multiplier -= adj.trend_sensitivity * min(1.0, (0.5 - product.trend_score) / 0.5)
    if signals and signals.get("audience", 100) < 75:
        multiplier -= adj.audience_sensitivity * 0.5

    return max(MIN_MULTIPLIER, min(MAX_MULTIPLIER, multiplier))
