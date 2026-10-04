"""The seven fit signals, the 3x3 marking scheme and the two penalties.

Design rules this file follows (they match the deck's Product DNA slide):

1.  Every signal is a pure function of (creator, product) and returns 0-100,
    so every number on screen can be traced to one formula.
2.  Weights come from the creator's cell in a 3x3 matrix: scale (Emerging,
    Growth, Established) x primary intent (Trend-, Commerce-, Brand-led).
        W(cell) = W_intent + Delta_scale        (each cell sums to 100)
    Scale never earns a higher score. It only changes how much each signal is
    trusted: thin history leans on proven products, rich history leans on the
    creator's own signals. Growth is the reference row.
3.  Crowding and return risk are penalties in points, not hidden inside a
    signal, so the creator sees exactly what was taken off and why.
4.  Price comfort is part of Product fit; products far outside what the
    audience pays never reach the ranker (eligibility.py).

    FitScore = sum_i W_i(cell) * s_i  -  lambda_S(scale) * saturation  -  return penalty

This is the MVP ranker: weighted rules, explainable, cold-start safe.
`engine/pipeline.py` keeps the interface the same so a learned model can
replace `score_product` without touching the API layer.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..models import Creator, Product

SIGNALS = ("audience", "creator", "intent", "product", "commerce", "trend", "brand")

# ---------------------------------------------------------------- 3x3 matrix
# Base weights by primary intent, in points, in SIGNALS order.
BASE_WEIGHTS = {
    "trend":    (20, 15, 15, 10, 10, 25, 5),
    "commerce": (25, 10, 15, 15, 25, 5, 5),
    "brand":    (20, 20, 15, 15, 10, 5, 15),
}
# Points moved between signals by scale. Each row sums to zero.
SCALE_DELTA = {
    "Emerging":    (0, -5, 0, 5, 5, 0, -5),
    "Growth":      (0, 0, 0, 0, 0, 0, 0),
    "Established": (3, 2, 0, -5, -5, 0, 5),
}
# Crowding penalty rate by scale: established creators want white space.
SATURATION_LAMBDA = {"Emerging": 4.0, "Growth": 8.0, "Established": 12.0}
RETURN_PENALTY_MAX = 10.0
DEFAULT_RETURN_MEDIAN = 0.08

INTENT_LABEL = {"trend": "Trend-led", "commerce": "Commerce-led", "brand": "Brand-led"}

TREND_STAGE_MULTIPLIER = {
    "early": 0.90,
    "rising": 1.06,
    "peak": 1.00,
    "saturating": 0.82,
    "declining": 0.70,
}


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


@dataclass
class ScoreBreakdown:
    """Everything the UI and the logs need to explain one score."""

    fit_score: int
    signals: dict[str, float]
    weights: dict[str, float]
    contributions: dict[str, float]
    price_fit: float                 # price comfort, 0-1 (already inside Product fit)
    base_score: float                # weighted sum before penalties
    learning_multiplier: float = 1.0
    penalty_saturation: float = 0.0
    penalty_returns: float = 0.0
    cell: str = ""
    notes: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------
# creator cell
# --------------------------------------------------------------------------
def scale_of(creator: Creator) -> str:
    if creator.followers >= 100_000:
        return "Established"
    if creator.followers >= 10_000:
        return "Growth"
    return "Emerging"


def primary_intent(creator: Creator) -> str:
    scores = {"trend": creator.intent_trend, "commerce": creator.intent_commerce, "brand": creator.intent_brand}
    return max(scores, key=lambda k: (scores[k], k == "commerce"))


def cell_label(creator: Creator) -> str:
    return f"{scale_of(creator)} \u00d7 {INTENT_LABEL[primary_intent(creator)]}"


def weight_mix(creator: Creator) -> dict[str, float]:
    """W(cell) = W_intent + Delta_scale, returned as fractions that sum to 1."""
    base = BASE_WEIGHTS[primary_intent(creator)]
    delta = SCALE_DELTA[scale_of(creator)]
    points = [b + d for b, d in zip(base, delta)]
    assert sum(points) == 100 and min(points) >= 0
    return {name: p / 100 for name, p in zip(SIGNALS, points)}


# --------------------------------------------------------------------------
# positioning (used by Brand fit)
# --------------------------------------------------------------------------
POSITIONING_TAGS = {
    "affordable": "budget", "everyday": "budget", "beginner-friendly": "budget",
    "premium": "premium", "retinol": "premium",
    "trending": "trendy", "party": "trendy", "glow": "trendy",
    "routine": "routine", "daily-use": "routine",
}


def price_tier(price: float) -> str:
    return "budget" if price < 300 else "premium" if price >= 700 else "mid"


def product_positioning(product: Product) -> dict[str, float]:
    counts: dict[str, float] = {price_tier(product.price): 1.0}
    for tag in product.tags or []:
        key = POSITIONING_TAGS.get(str(tag).lower())
        if key:
            counts[key] = counts.get(key, 0.0) + 1.0
    total = sum(counts.values())
    return {k: v / total for k, v in counts.items()}


def creator_positioning(creator: Creator) -> dict[str, float]:
    stored = getattr(creator, "positioning", None) or {}
    if stored:
        return stored
    preferred = getattr(creator, "preferred_price", None) or (creator.price_min + creator.price_max) / 2
    counts: dict[str, float] = {price_tier(preferred): 1.0}
    for tag in (creator.sub_niches or []) + (creator.bio or "").lower().split():
        key = POSITIONING_TAGS.get(str(tag).lower())
        if key:
            counts[key] = counts.get(key, 0.0) + 1.0
    total = sum(counts.values())
    return {k: v / total for k, v in counts.items()}


# --------------------------------------------------------------------------
# individual signals
# --------------------------------------------------------------------------
def audience_fit(creator: Creator, product: Product) -> float:
    """Does this product serve the people who actually watch this creator?"""
    c_lo, c_hi = creator.audience_age_min, creator.audience_age_max
    p_lo, p_hi = product.target_age_min, product.target_age_max

    overlap = max(0, min(c_hi, p_hi) - max(c_lo, p_lo) + 1)
    recall = overlap / max(1, c_hi - c_lo + 1)
    precision = overlap / max(1, p_hi - p_lo + 1)
    age_score = 0.75 * recall + 0.25 * precision

    c_tiers = set(creator.audience_tiers or [])
    p_tiers = set(product.target_tiers or [])
    tier_score = len(c_tiers & p_tiers) / len(c_tiers) if c_tiers else 0.5

    return 100 * (0.68 * age_score + 0.32 * tier_score)


def creator_fit(creator: Creator, product: Product) -> float:
    """Niche fit: does this product belong on this creator's feed at all?

    Uses the niche shares built from content history, hashtags and Q1 when
    they exist; falls back to the primary niche and sub-niches otherwise.
    """
    category = (product.category or "").lower()
    shares = {k.lower(): v for k, v in (getattr(creator, "niche_shares", None) or {}).items()}
    niche = (creator.niche or "").lower()
    subs = {s.lower() for s in (creator.sub_niches or [])}

    if shares:
        top = max(shares.values()) or 1.0
        base = 34.0 + 52.0 * (shares.get(category, 0.0) / top)
    elif category == niche:
        base = 86.0
    elif category in subs:
        base = 70.0
    elif subs & {t.lower() for t in (product.tags or [])}:
        base = 58.0
    else:
        base = 34.0

    creator_vocab = subs | {niche} | set((creator.bio or "").lower().split())
    product_vocab = {t.lower() for t in (product.tags or [])} | {(product.sub_category or "").lower()}
    bonus = min(12.0, len(creator_vocab & product_vocab) * 4.0)
    return min(100.0, base + bonus)


def intent_fit(creator: Creator, product: Product) -> float:
    """Her intent shares x the product's trend / commerce / brand role scores."""
    t = max(creator.intent_trend, 1)
    c = max(creator.intent_commerce, 1)
    b = max(creator.intent_brand, 1)
    total = t + c + b

    trend_component = _clamp(product.trend_score / 0.85) * 100
    commerce_component = _clamp(product.conversion_rate / 0.055) * 100
    brand_component = _clamp((product.rating - 3.2) / 1.3) * 100
    return (t * trend_component + c * commerce_component + b * brand_component) / total


def price_comfort(creator: Creator, product: Product) -> float:
    """1.0 inside the observed range; above it hurts more than below it."""
    lo, hi = creator.price_min, creator.price_max
    price = product.price
    if lo <= price <= hi:
        return 1.0
    if price < lo:
        return 1.0 - 0.25 * _clamp((lo - price) / max(lo, 1))
    return 1.0 - 0.55 * _clamp((price - hi) / max(hi, 1))


def product_fit(creator: Creator, product: Product) -> float:
    """0.6 x quality + 0.4 x price comfort."""
    rating_s = _clamp((product.rating - 3.0) / 1.5)
    volume_s = _clamp(math.log10(product.review_count + 1) / 4.0)
    seller_s = _clamp((product.seller_rating - 3.0) / 1.5)
    returns_s = _clamp(1 - product.return_rate / 0.25)
    quality = 0.34 * rating_s + 0.20 * volume_s + 0.20 * seller_s + 0.26 * returns_s
    return 100 * (0.6 * quality + 0.4 * price_comfort(creator, product))


def commerce_fit(creator: Creator, product: Product) -> float:
    """Does this product actually convert when someone sends traffic to it?"""
    conv_s = _clamp(product.conversion_rate / 0.058) * 100
    velocity_s = _clamp(math.log10(product.orders_30d + 1) / 4.3) * 100
    nmv_s = _clamp(math.log10(product.nmv_30d + 1) / 6.0) * 100
    return 0.46 * conv_s + 0.30 * velocity_s + 0.24 * nmv_s


def trend_fit(creator: Creator, product: Product) -> float:
    """Momentum only. Crowding is a separate, visible penalty."""
    base = product.trend_score * 100 * TREND_STAGE_MULTIPLIER.get(product.trend_stage, 1.0)
    return _clamp(base / 100) * 100


def brand_fit(creator: Creator, product: Product) -> float:
    """Overlap of positioning: sum over tags of min(her share, product share)."""
    c = creator_positioning(creator)
    p = product_positioning(product)
    return 100 * sum(min(c.get(k, 0.0), v) for k, v in p.items())


SIGNAL_FUNCTIONS = {
    "audience": audience_fit,
    "creator": creator_fit,
    "intent": intent_fit,
    "product": product_fit,
    "commerce": commerce_fit,
    "trend": trend_fit,
    "brand": brand_fit,
}


# Kept for callers that still ask for the old name.
def price_fit(creator: Creator, product: Product) -> float:
    return price_comfort(creator, product)


# --------------------------------------------------------------------------
# penalties
# --------------------------------------------------------------------------
def saturation_penalty(creator: Creator, product: Product) -> float:
    return SATURATION_LAMBDA[scale_of(creator)] * _clamp(product.creator_saturation)


def return_penalty(product: Product, category_median: float | None = None) -> float:
    """0 up to 80% of the category median, rising to -10 at the median cap."""
    m = category_median or DEFAULT_RETURN_MEDIAN
    return RETURN_PENALTY_MAX * _clamp((product.return_rate - 0.8 * m) / (0.2 * m))


# --------------------------------------------------------------------------
# combination
# --------------------------------------------------------------------------
def score_product(
    creator: Creator,
    product: Product,
    learning_multiplier: float = 1.0,
    return_median: float | None = None,
) -> ScoreBreakdown:
    """Score one creator-product pair and return the full breakdown."""
    weights = weight_mix(creator)
    signals = {name: round(fn(creator, product), 1) for name, fn in SIGNAL_FUNCTIONS.items()}
    contributions = {name: round(signals[name] * weights[name], 2) for name in SIGNALS}

    base = sum(contributions.values())
    pen_sat = round(saturation_penalty(creator, product), 2)
    # New listings have no return history yet, so no return penalty (cold start).
    pen_ret = round(return_penalty(product, return_median), 2) if product.review_count >= 50 else 0.0
    final = max(0.0, base - pen_sat - pen_ret) * learning_multiplier

    comfort = price_comfort(creator, product)
    notes: list[str] = []
    if comfort < 1.0:
        side = "above" if product.price > creator.price_max else "below"
        notes.append(f"price {side} the creator's \u20b9{creator.price_min}\u2013\u20b9{creator.price_max} range")
    if pen_sat >= 4:
        notes.append(f"crowding penalty \u2212{pen_sat:.1f}")
    if pen_ret > 0:
        notes.append(f"return-risk penalty \u2212{pen_ret:.1f}")
    if learning_multiplier != 1.0:
        notes.append("adjusted by this creator's own past feedback")

    return ScoreBreakdown(
        fit_score=int(round(_clamp(final / 100) * 100)),
        signals=signals,
        weights=weights,
        contributions=contributions,
        price_fit=round(comfort, 3),
        base_score=round(base, 2),
        learning_multiplier=round(learning_multiplier, 3),
        penalty_saturation=pen_sat,
        penalty_returns=pen_ret,
        cell=cell_label(creator),
        notes=notes,
    )
