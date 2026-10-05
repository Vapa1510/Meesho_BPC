"""The product side of the engine: which creators should this product go to?

The creator side ranks products for one creator. This does the transpose —
it scores one product against every creator — using the same signals, the same
price gate and the same learned adjustments, so a brand and a creator are never
looking at two different scores for the same pair.

Two things are added that only make sense from the brand's seat:

* Stage 1 is applied per creator, and the rule that blocked the pair is kept.
  "Not reachable: price above this audience's band" is the most useful thing a
  brand can be told about a product.
* A projection of reach, orders and NMV. It is arithmetic on public inputs
  (followers x engagement x click share x conversion), not a forecast, and the
  frontend labels it that way.
"""
from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Creator, FeedbackEvent, Pitch, Product
from . import learning, reasons
from .eligibility import RULES, filter_eligible
from .scoring import ScoreBreakdown, score_product
from .eligibility import category_return_medians

CLICK_SHARE = 0.10      # share of engaged followers who click a promoted product
STRONG_MATCH = 75

BLOCK_LABELS = {
    "off_niche": "outside this creator's niche",
    "price_range": "price is outside this audience's band",
    "stock_serviceable": "out of stock or not serviceable",
    "quality_threshold": "rating is below the quality bar",
    "policy_compliant": "listing is not policy compliant",
    "creator_excluded": "creator excludes this category",
    "already_promoted": "creator has already promoted it",
    "category": "category mismatch",
    "return_rate": "returns are above the category median",
    "audience_fit": "built for a different audience",
}

TIPS = {
    "audience": "Widen the target age range or tiers, or aim at creators whose audience sits inside them.",
    "creator": "Add specific tags and a sub-category so the product reads as part of a niche, not a generic listing.",
    "intent": "Position it around one clear goal (trend, conversion or brand) so it matches creators who share it.",
    "product": "Rating, review count and returns carry this signal; early reviews move it fastest.",
    "commerce": "Conversion history is thin. A few early offers will build the evidence this signal needs.",
    "trend": "Demand momentum is flat. Seasonal or ingredient-led angles tend to lift it.",
    "brand": "Positioning reads differently from these creators. Clear tags (budget, premium, routine) help the right ones find it.",
}


@dataclass
class Match:
    creator: Creator
    breakdown: ScoreBreakdown
    eligible: bool
    blocked_by: str | None
    reasons: list[str]
    caveats: list[str]
    est_reach: int
    est_orders: int
    est_nmv: int
    offer_status: str | None = None


@dataclass
class Diagnosis:
    creators_total: int
    reachable: int
    strong_matches: int
    blockers: dict[str, int]
    price_in_band: float
    median_band_ceiling: int
    weakest: list[str]
    tips: list[str]


@dataclass
class ProductMatches:
    matches: list[Match]
    diagnosis: Diagnosis
    extra: dict = field(default_factory=dict)


def in_niche(creator: Creator, product: Product) -> bool:
    category = (product.category or "").lower()
    subs = {x.lower() for x in (creator.sub_niches or [])}
    return (creator.niche or "").lower() == category or category in subs


def project(creator: Creator, product: Product, fit: int) -> tuple[int, int, int]:
    """(engaged reach, orders, NMV). Transparent on purpose."""
    reach = creator.followers * creator.engagement_rate
    clicks = reach * CLICK_SHARE * (fit / 80.0)
    orders = clicks * product.conversion_rate
    return int(round(reach)), int(round(orders)), int(round(orders * product.price))


def match_creators(db: Session, product: Product) -> ProductMatches:
    # Synthetic creators from the Engine lab are never offered to brands.
    creators = [c for c in db.scalars(select(Creator)).all() if not (c.handle or "").startswith("sim.")]
    products_by_id = {p.product_id: p for p in db.scalars(select(Product)).all()}

    events_by_creator: dict[str, list[FeedbackEvent]] = defaultdict(list)
    for event in db.scalars(select(FeedbackEvent)).all():
        events_by_creator[event.creator_id].append(event)

    offers = {
        (p.creator_id): p.status
        for p in db.scalars(select(Pitch).where(Pitch.product_id == product.product_id)).all()
    }

    medians = category_return_medians(list(products_by_id.values()))
    matches: list[Match] = []
    blockers: dict[str, int] = {}
    for creator in creators:
        adj = learning.build_adjustments(events_by_creator.get(creator.creator_id, []), products_by_id)
        stage1 = filter_eligible(creator, [product], suppressed=adj.suppressed_products, return_medians=medians)
        blocked_by = None
        if not in_niche(creator, product):
            # A brand targets creators who actually cover its category. The
            # creator side lets a creator browse across categories on their own
            # terms; an unsolicited offer should not.
            blocked_by = "off_niche"
        elif not stage1.eligible:
            blocked_by = next((r for r in RULES if stage1.rejected.get(r)), None)
            if blocked_by:
                blockers[blocked_by] = blockers.get(blocked_by, 0) + 1

        rm = medians.get(product.category.lower())
        base = score_product(creator, product, return_median=rm)
        mult = learning.multiplier_for(creator, product, adj, base.signals)
        breakdown = base if mult == 1.0 else score_product(creator, product, learning_multiplier=mult, return_median=rm)
        _codes, positives, caveats = reasons.build_reasons(creator, product, breakdown)
        reach, orders, nmv = project(creator, product, breakdown.fit_score)
        matches.append(
            Match(
                creator=creator,
                breakdown=breakdown,
                eligible=not blocked_by,
                blocked_by=blocked_by,
                reasons=positives,
                caveats=caveats,
                est_reach=reach,
                est_orders=orders,
                est_nmv=nmv,
                offer_status=offers.get(creator.creator_id),
            )
        )

    matches.sort(key=lambda m: (m.eligible, m.breakdown.fit_score), reverse=True)
    pool = [c for c in creators if in_niche(c, product)]
    return ProductMatches(matches=matches, diagnosis=_diagnose(product, pool, matches, blockers))


def _diagnose(product: Product, creators: list[Creator], matches: list[Match], blockers: dict[str, int]) -> Diagnosis:
    reachable = [m for m in matches if m.eligible]
    # `creators` here is the in-niche pool, so shares and medians describe the
    # people this product could realistically go to.
    strong = [m for m in reachable if m.breakdown.fit_score >= STRONG_MATCH]

    in_band = [
        c for c in creators if c.price_min * 0.55 <= product.price <= c.price_max * 1.30
    ]
    ceilings = [c.price_max for c in creators] or [0]

    weakest: list[str] = []
    tips: list[str] = []
    pool = reachable[:8] or matches[:8]
    if pool:
        avg = {
            name: statistics.fmean(m.breakdown.signals[name] for m in pool)
            for name in pool[0].breakdown.signals
        }
        weakest = [n for n, _ in sorted(avg.items(), key=lambda kv: kv[1])[:2]]
        tips = [TIPS[n] for n in weakest if avg[n] < 75]

    share = len(in_band) / len(creators) if creators else 0.0
    if share < 0.5:
        tips.insert(
            0,
            f"₹{product.price} sits inside only {len(in_band)} of {len(creators)} creators' "
            f"price bands; the typical ceiling is ₹{int(statistics.median(ceilings))}.",
        )
    if product.review_count == 0:
        tips.append("New listing: there are no reviews yet, so quality is scored on the seller rating alone.")

    return Diagnosis(
        creators_total=len(creators),
        reachable=len(reachable),
        strong_matches=len(strong),
        blockers=blockers,
        price_in_band=round(share, 3),
        median_band_ceiling=int(statistics.median(ceilings)),
        weakest=weakest,
        tips=tips[:4],
    )
