"""Turn a score breakdown into something a creator can read and argue with.

Three outputs:
  reason_codes   machine-readable, stable, logged with every recommendation
  reasons        the same thing in the creator's own terms, for the app
  content_angle  a concrete first idea, so the recommendation is actionable
"""
from __future__ import annotations

import math

from ..models import Creator, Product
from .scoring import ScoreBreakdown, primary_intent, creator_positioning

# A signal earns its reason code once it clears this bar.
STRONG = 78.0
WEAK = 52.0

CODE_FOR_SIGNAL = {
    "audience": "audience_fit",
    "creator": "niche_fit",
    "intent": "intent_fit",
    "product": "product_quality",
    "commerce": "commerce_potential",
    "trend": "trend",
    "brand": "brand_fit",
}

POSITIVE_TEMPLATES = {
    "audience_fit": "Strong overlap with your {audience} audience",
    "niche_fit": "Fits the {niche} content you already make",
    "intent_fit": "Serves your {goal} goal",
    "brand_fit": "Fits the {positioning} look you already show",
    "product_quality": "Well-rated product ({rating}★, {reviews} reviews)",
    "commerce_potential": "Converts well — {conversion} on recent traffic",
    "trend": "{category} is {stage} right now",
    "price_fit": "₹{price} sits inside your ₹{lo}–₹{hi} range",
    "white_space": "Few creators in your niche have covered it yet",
}

NEGATIVE_TEMPLATES = {
    "audience_fit": "Built for a wider audience than yours",
    "niche_fit": "Outside the {niche} content you usually make",
    "product_quality": "Thin review history — harder to vouch for",
    "commerce_potential": "Converts slowly compared with your other options",
    "trend": "{category} demand is flat right now",
    "price_above": "₹{price} is above your ₹{lo}–₹{hi} range",
    "price_below": "₹{price} is below your usual range — lower earnings per order",
    "saturated": "Already promoted by many creators in your niche",
    "brand_fit": "Positioned differently from what you usually show",
}

GOAL_WORDS = {"trend": "reach", "commerce": "earning", "brand": "identity-building"}


def _fmt(template: str, creator: Creator, product: Product) -> str:
    return template.format(
        audience=creator.audience_label,
        niche=(creator.niche or "").lower(),
        goal=GOAL_WORDS[primary_intent(creator)],
        positioning=max(creator_positioning(creator), key=creator_positioning(creator).get),
        rating=product.rating,
        reviews=_short_count(product.review_count),
        conversion=f"{product.conversion_rate * 100:.1f}%",
        category=product.category.lower(),
        stage=product.trend_stage,
        price=product.price,
        lo=creator.price_min,
        hi=creator.price_max,
    )


def _short_count(n: int) -> str:
    if n >= 100_000:
        return f"{n / 100_000:.1f}L".replace(".0L", "L")
    if n >= 1_000:
        return f"{n / 1_000:.1f}K".replace(".0K", "K")
    return str(n)


def build_reasons(
    creator: Creator, product: Product, breakdown: ScoreBreakdown, max_codes: int = 3
) -> tuple[list[str], list[str], list[str]]:
    """Return (reason_codes, positive reasons, caveats)."""
    signals = breakdown.signals

    # Rank signals by what actually moved this score, not by raw value, so the
    # explanation matches the weighting this creator is being ranked under.
    ordered = sorted(
        breakdown.contributions.items(), key=lambda kv: kv[1], reverse=True
    )

    codes: list[str] = []
    positives: list[str] = []
    for name, _contribution in ordered:
        if signals[name] < STRONG:
            continue
        code = CODE_FOR_SIGNAL[name]
        codes.append(code)
        positives.append(_fmt(POSITIVE_TEMPLATES[code], creator, product))
        if len(codes) >= max_codes:
            break

    if breakdown.price_fit == 1.0 and len(codes) < max_codes:
        codes.append("price_fit")
        positives.append(_fmt(POSITIVE_TEMPLATES["price_fit"], creator, product))

    if product.creator_saturation <= 0.25 and len(codes) < max_codes:
        codes.append("white_space")
        positives.append(_fmt(POSITIVE_TEMPLATES["white_space"], creator, product))

    caveats: list[str] = []
    if product.price > creator.price_max:
        caveats.append(_fmt(NEGATIVE_TEMPLATES["price_above"], creator, product))
    elif product.price < creator.price_min:
        caveats.append(_fmt(NEGATIVE_TEMPLATES["price_below"], creator, product))
    if product.creator_saturation > 0.55:
        caveats.append(_fmt(NEGATIVE_TEMPLATES["saturated"], creator, product))
    for name in ("creator", "commerce", "product", "trend", "audience", "brand"):
        if signals[name] < WEAK:
            key = CODE_FOR_SIGNAL[name]
            if key in NEGATIVE_TEMPLATES:
                caveats.append(_fmt(NEGATIVE_TEMPLATES[key], creator, product))

    if not codes:
        codes.append("broad_match")
        positives.append("Matches on category, but nothing stands out")

    return codes, positives, caveats[:3]


def confidence(creator: Creator, product: Product, interaction_count: int) -> str:
    """How much evidence is behind this recommendation.

    Deliberately conservative: a cold-start creator never sees HIGH, because
    the honest answer early on is that the engine is still guessing.
    """
    evidence = 0.0
    evidence += min(1.0, math.log10(product.review_count + 1) / 3.5) * 0.4
    evidence += min(1.0, math.log10(product.orders_30d + 1) / 3.5) * 0.3
    evidence += min(1.0, interaction_count / 25) * 0.3

    if evidence >= 0.75:
        return "HIGH"
    if evidence >= 0.42:
        return "MEDIUM"
    return "LOW"


LEVEL_FOR_PRICE = ((600, "Beginner"), (1200, "Everyday"), (10**9, "Premium"))
FORMAT_FOR_CATEGORY = {
    "skincare": "routine",
    "makeup": "look",
    "haircare": "routine",
    "personal care": "routine",
}


ANGLE_STYLE = {"trend": "Trend hook", "commerce": "Proof angle", "brand": "Identity story"}
FORMAT_WORDS = {"routine": "routine", "tutorial": "tutorial", "tips": "tips", "review": "honest review",
                "grwm": "get-ready-with-me", "reel": "reel"}


def content_angle(creator: Creator, product: Product) -> str:
    """A concrete first idea, styled by intent and shaped by the formats from Q1."""
    level = next(word for ceiling, word in LEVEL_FOR_PRICE if product.price < ceiling)
    formats = [f for f in (getattr(creator, "content_formats", None) or []) if f in FORMAT_WORDS]
    fmt = FORMAT_WORDS[formats[0]] if formats else FORMAT_FOR_CATEGORY.get(product.category.lower(), "video")
    niche = product.category.lower()
    step = 100 if product.price < 1000 else 500
    rounded = int(math.ceil(product.price / step) * step)
    style = ANGLE_STYLE[primary_intent(creator)]

    if style == "Trend hook" or (product.trend_stage in ("rising", "peak") and product.creator_saturation < 0.20):
        return f"{style}: {level} {niche} {fmt} under \u20b9{rounded}, before everyone covers it"
    if style == "Identity story":
        return f"{style}: why this {niche} pick fits my {fmt}"
    return f"{style}: {level} {niche} {fmt} under \u20b9{rounded}"
