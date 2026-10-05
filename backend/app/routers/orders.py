"""Orders and Fit Rewards: the end of the loop (slide 5: Click -> Order -> NMV -> Fit Rewards).

In production, attributed orders arrive from Meesho's order service. Here the
demo posts them, so the loop can be shown end to end. NMV is net of
cancellations, returns and undelivered orders; it is not revenue or profit.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..engine import rewards
from ..models import FeedbackEvent, OrderEvent, Product, get_or_create_interaction
from ..schemas import OrderIn, OrderOut, RewardsOut
from .creators import get_creator_or_404

router = APIRouter(tags=["orders & rewards"])

NMV_NOTE = (
    "NMV is net of cancellations, returns and undelivered orders; it is not revenue or profit. "
    "Fit Rewards pay on delivered fit-pick orders (fit 80+), net of returns, and are mostly "
    "non-cash or brand-funded. Orders here are demo events; in production they come from "
    "Meesho's order service."
)


def _order_out(e: OrderEvent, products: dict[str, Product]) -> OrderOut:
    p = products.get(e.product_id)
    return OrderOut(
        id=e.id,
        creator_id=e.creator_id,
        product_id=e.product_id,
        title=p.title if p else e.product_id,
        status=e.status,
        amount=e.amount,
        fit_score=e.fit_score,
        fit_qualified=e.fit_score >= rewards.FIT_QUALIFIED,
        created_at=e.created_at.isoformat(),
    )


def _promote_event(db: Session, creator_id: str, product_id: str) -> FeedbackEvent | None:
    return db.scalar(
        select(FeedbackEvent)
        .where(
            FeedbackEvent.creator_id == creator_id,
            FeedbackEvent.product_id == product_id,
            FeedbackEvent.action == "promote",
        )
        .order_by(FeedbackEvent.id.desc())
        .limit(1)
    )


@router.post("/orders", response_model=OrderOut, status_code=201)
def record_order(payload: OrderIn, db: Session = Depends(get_db)):
    """Record an order attributed to a promotion, and keep NMV net of returns."""
    creator = get_creator_or_404(db, payload.creator_id)
    product = db.get(Product, payload.product_id)
    if product is None:
        raise HTTPException(status_code=404, detail=f"product {payload.product_id} not found")
    promote = _promote_event(db, creator.creator_id, product.product_id)
    if promote is None:
        raise HTTPException(
            status_code=422,
            detail="no promotion to attribute this order to: the creator has not promoted this product",
        )
    if payload.status == "returned":
        delivered = db.scalar(
            select(OrderEvent).where(
                OrderEvent.creator_id == creator.creator_id,
                OrderEvent.product_id == product.product_id,
                OrderEvent.status == "delivered",
            ).limit(1)
        )
        if delivered is None:
            raise HTTPException(status_code=422, detail="only a delivered order can be returned")

    fit = int(round(promote.served_score)) if promote.served_score is not None else 0
    event = OrderEvent(
        creator_id=creator.creator_id,
        product_id=product.product_id,
        status=payload.status,
        amount=product.price if payload.status in ("delivered", "returned") else 0,
        fit_score=fit,
    )
    db.add(event)

    interaction = get_or_create_interaction(db, creator.creator_id, product.product_id)
    if payload.status == "delivered":
        interaction.orders += 1
        interaction.nmv += product.price
        # A delivered order teaches the ranker too: it lifts this category for her.
        db.add(FeedbackEvent(creator_id=creator.creator_id, product_id=product.product_id,
                             action="order", served_score=promote.served_score, source=promote.source))
    elif payload.status == "returned":
        interaction.nmv = max(0, interaction.nmv - product.price)   # NMV is net of returns
    db.commit()
    db.refresh(event)
    return _order_out(event, {product.product_id: product})


@router.get("/rewards/{creator_id}", response_model=RewardsOut)
def creator_rewards(creator_id: str, db: Session = Depends(get_db)):
    """Fit Rewards for one creator: her archetype, what she has earned, what is next."""
    creator = get_creator_or_404(db, creator_id)
    s = rewards.summary(db, creator)
    products = {p.product_id: p for p in db.scalars(select(Product)).all()}
    promotes = list(
        db.scalars(
            select(FeedbackEvent)
            .where(FeedbackEvent.creator_id == creator_id, FeedbackEvent.action == "promote")
            .order_by(FeedbackEvent.id.desc())
        ).all()
    )
    orders = list(
        db.scalars(select(OrderEvent).where(OrderEvent.creator_id == creator_id).order_by(OrderEvent.id.desc())).all()
    )
    seen: set[str] = set()
    promoted: list[dict] = []
    for e in promotes:
        if e.product_id in seen or e.product_id not in products:
            continue
        seen.add(e.product_id)
        p = products[e.product_id]
        fit = int(round(e.served_score or 0))
        delivered = sum(1 for o in orders if o.product_id == p.product_id and o.status == "delivered")
        returned = sum(1 for o in orders if o.product_id == p.product_id and o.status == "returned")
        promoted.append({
            "product_id": p.product_id, "title": p.title, "price": p.price, "fit_score": fit,
            "fit_qualified": fit >= rewards.FIT_QUALIFIED, "delivered": delivered, "returned": returned,
        })
    return RewardsOut(
        creator_id=creator_id,
        archetype=s.archetype,
        fit_threshold=s.fit_threshold,
        delivered_fit_orders=s.delivered_fit_orders,
        returned_orders=s.returned_orders,
        fit_nmv=s.fit_nmv,
        earned=s.earned,
        next_step=s.next_step,
        promoted=promoted,
        orders=[_order_out(o, products) for o in orders],
        note=NMV_NOTE,
    )
