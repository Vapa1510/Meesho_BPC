"""Stage 1 of the pipeline: rule-based eligibility filters.

Cheap, hard, auditable. Nothing here is a score — a product either may be shown
to this creator or it may not. On the seed catalogue this leaves roughly the
20-30% pool the deck describes.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..config import MIN_RATING
from ..models import Creator, Product


@dataclass
class EligibilityResult:
    eligible: list[Product]
    rejected: dict[str, list[str]]   # rule -> product ids it removed
    pool_ratio: float
    return_medians: dict[str, float] | None = None   # category -> median return rate


RULES = (
    "category",
    "price_range",
    "stock_serviceable",
    "quality_threshold",
    "return_rate",
    "policy_compliant",
    "creator_excluded",
    "audience_fit",
    "already_promoted",
)

# A rating is only trusted once enough people have left one. Until then a new
# listing is judged on its seller's rating (the cold-start path).
MIN_REVIEWS_FOR_RATING = 50
MIN_AUDIENCE_FIT = 50.0


def category_return_medians(catalogue: list[Product]) -> dict[str, float]:
    by_cat: dict[str, list[float]] = {}
    for p in catalogue:
        by_cat.setdefault(p.category.lower(), []).append(p.return_rate)
    out = {}
    for cat, rates in by_cat.items():
        rates = sorted(rates)
        n = len(rates)
        out[cat] = rates[n // 2] if n % 2 else (rates[n // 2 - 1] + rates[n // 2]) / 2
    return out


def passes_quality(product: Product) -> bool:
    if product.review_count >= MIN_REVIEWS_FOR_RATING:
        return product.rating >= MIN_RATING
    return product.seller_rating >= MIN_RATING


def _price_window(creator: Creator) -> tuple[float, float]:
    """A soft window around the stated band.

    The band is what the audience usually pays, not a hard wall: allow 30% above
    and 45% below so near-miss products still reach the ranker, where the price
    gate can discount them honestly instead of hiding them.
    """
    return creator.price_min * 0.55, creator.price_max * 1.30


def filter_eligible(
    creator: Creator,
    catalogue: list[Product],
    category: str | None = None,
    suppressed: set[str] | None = None,
    return_medians: dict[str, float] | None = None,
) -> EligibilityResult:
    """Apply the hard rules.

    `suppressed` carries products the creator has told us they have already
    promoted. That is an eligibility question, not a scoring one: down-weighting
    such a product still leaves it competing for a slot it can never deserve,
    and the creator sees the same recommendation again after rejecting it.
    """
    from .scoring import audience_fit  # local import: scoring imports models only

    rejected: dict[str, list[str]] = {rule: [] for rule in RULES}
    eligible: list[Product] = []
    lo, hi = _price_window(creator)
    avoid = {c.lower() for c in (creator.avoid_categories or [])}
    medians = return_medians or category_return_medians(catalogue)

    for product in catalogue:
        if category and product.category.lower() != category.lower():
            # `category=bpc` means the whole beauty & personal care vertical, not
            # one sub-category, so it is not a rejection reason worth logging.
            if category.lower() != "bpc":
                rejected["category"].append(product.product_id)
                continue

        if not (lo <= product.price <= hi):
            rejected["price_range"].append(product.product_id)
            continue
        if not (product.in_stock and product.serviceable):
            rejected["stock_serviceable"].append(product.product_id)
            continue
        if not passes_quality(product):
            rejected["quality_threshold"].append(product.product_id)
            continue
        # Returns are only judged once there is a history to judge (cold start).
        if product.review_count >= MIN_REVIEWS_FOR_RATING and product.return_rate > medians.get(product.category.lower(), 1.0) + 1e-9:
            rejected["return_rate"].append(product.product_id)
            continue
        if not product.policy_compliant:
            rejected["policy_compliant"].append(product.product_id)
            continue
        if product.category.lower() in avoid:
            rejected["creator_excluded"].append(product.product_id)
            continue
        if audience_fit(creator, product) < MIN_AUDIENCE_FIT:
            rejected["audience_fit"].append(product.product_id)
            continue
        if suppressed and product.product_id in suppressed:
            rejected["already_promoted"].append(product.product_id)
            continue

        eligible.append(product)

    ratio = len(eligible) / len(catalogue) if catalogue else 0.0
    return EligibilityResult(eligible=eligible, rejected=rejected, pool_ratio=round(ratio, 3), return_medians=medians)
