"""Fit Rewards: reward fit, not volume (slides 2, 4, 5, 12).

Rules, as the deck states them:

* Rewards apply only to fit-qualified picks: fit score >= 80.
* Brand-funded samples are offered only for picks with fit >= 80.
* A starter bonus unlocks on the creator's first delivered fit-pick order.
* Each intent archetype gets the reward that matches what it is after:
    Trend Scout (trend-led)       early access to rising products
    Commerce Builder (commerce)   conversion bonus + earnings dashboard
    Brand Builder (brand-led)     brand offers + verified-fit badge
* Rewards pay on delivered orders, net of returns; they are mostly non-cash or
  brand-funded. The prototype records which rewards were earned; it does not
  set amounts, because the deck does not and the brand or programme would.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Creator, OrderEvent, Product
from .scoring import primary_intent

FIT_QUALIFIED = 80

ARCHETYPE = {
    "trend": {
        "name": "Trend Scout",
        "quote": "Help me spot what I can use to get viral.",
        "needs": "Early signals + high trend fit",
        "reward": "Early access to rising products",
    },
    "commerce": {
        "name": "Commerce Builder",
        "quote": "Help me find products my audience will actually buy.",
        "needs": "Proof + personalised fit",
        "reward": "Conversion bonus + earnings dashboard",
    },
    "brand": {
        "name": "Brand Builder",
        "quote": "Help me promote products that strengthen my identity.",
        "needs": "Creator identity fit",
        "reward": "Brand offers + verified-fit badge",
    },
}

INCENTIVES = {
    "sample": "Brand-funded sample",
    "conversion_bonus": "Conversion bonus on delivered orders",
    "early_access": "Early access (rising product)",
}


def incentive_allowed(incentive: str, fit_score: int, product: Product) -> str | None:
    """None if the incentive may go on this offer, else the reason it may not."""
    if incentive not in INCENTIVES:
        return f"incentive must be one of {sorted(INCENTIVES)}"
    if fit_score < FIT_QUALIFIED:
        return f"Fit Rewards need a fit score of at least {FIT_QUALIFIED}; this pair scores {fit_score}"
    if incentive == "early_access" and product.trend_stage not in ("early", "rising"):
        return "early access is for products that are still early or rising"
    return None


def delivered_fit_orders(db: Session, creator_id: str) -> list[OrderEvent]:
    """Delivered, fit-qualified orders that have not been returned."""
    events = list(
        db.scalars(
            select(OrderEvent).where(OrderEvent.creator_id == creator_id).order_by(OrderEvent.created_at)
        ).all()
    )
    delivered: list[OrderEvent] = []
    for e in events:
        if e.status == "delivered" and e.fit_score >= FIT_QUALIFIED:
            delivered.append(e)
        elif e.status == "returned":
            # Net of returns: a return cancels the most recent matching delivery.
            for i in range(len(delivered) - 1, -1, -1):
                if delivered[i].product_id == e.product_id:
                    delivered.pop(i)
                    break
    return delivered


def pick_rewards(creator: Creator, product: Product, fit_score: int, has_fit_order: bool) -> list[str]:
    """What acting on this pick could earn, shown on the card."""
    if fit_score < FIT_QUALIFIED:
        return []
    out: list[str] = []
    if not has_fit_order:
        out.append("Starter bonus on your first delivered order")
    intent = primary_intent(creator)
    if intent == "trend":
        if product.trend_stage in ("early", "rising"):
            out.append("Early access: still rising")
    elif intent == "commerce":
        out.append("Conversion bonus on delivered orders")
    else:
        out.append("Counts toward your verified-fit badge")
    return out


@dataclass
class RewardsSummary:
    archetype: dict
    fit_threshold: int
    delivered_fit_orders: int
    returned_orders: int
    fit_nmv: int
    earned: list[dict] = field(default_factory=list)
    next_step: str = ""


def summary(db: Session, creator: Creator) -> RewardsSummary:
    intent = primary_intent(creator)
    arche = ARCHETYPE[intent]
    events = list(db.scalars(select(OrderEvent).where(OrderEvent.creator_id == creator.creator_id)).all())
    delivered = delivered_fit_orders(db, creator.creator_id)
    returned = sum(1 for e in events if e.status == "returned")
    earned: list[dict] = []
    if delivered:
        earned.append({"reward": "Starter bonus", "basis": "first delivered fit-pick order", "count": 1})
        if intent == "commerce":
            earned.append({"reward": "Conversion bonus", "basis": "delivered fit-pick orders, net of returns", "count": len(delivered)})
        elif intent == "trend":
            earned.append({"reward": "Early-access invites", "basis": "delivered fit-pick orders", "count": len(delivered)})
        else:
            earned.append({"reward": "Verified-fit badge progress", "basis": "delivered fit-pick orders", "count": len(delivered)})
    next_step = (
        f"Promote a pick with fit {FIT_QUALIFIED}+; your first delivered order unlocks the starter bonus."
        if not delivered else
        "Every further delivered fit-pick order adds to your rewards; returns are netted off."
    )
    return RewardsSummary(
        archetype={**arche, "intent": intent},
        fit_threshold=FIT_QUALIFIED,
        delivered_fit_orders=len(delivered),
        returned_orders=returned,
        fit_nmv=sum(e.amount for e in delivered),
        earned=earned,
        next_step=next_step,
    )
