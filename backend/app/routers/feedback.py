"""Feedback Service — the entry point to the closed loop."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..engine import learning
from ..models import FeedbackEvent, Product, get_or_create_interaction
from ..schemas import REJECTION_REASONS, FeedbackIn, FeedbackOut
from .creators import get_creator_or_404

router = APIRouter(tags=["feedback"])

ACKNOWLEDGEMENT = {
    "promote": "Logged. More like this will rank higher for you.",
    "save": "Saved. Noted as a softer positive signal.",
    "skip": "Noted. Your next list will reflect this.",
    "click": "Logged.",
    "impression": "Logged.",
}


def record_event(
    db: Session,
    *,
    creator_id: str,
    product_id: str,
    action: str,
    reason: str | None = None,
    served_score: float | None = None,
) -> FeedbackEvent:
    """Write one creator action and keep the interactions aggregate in step.

    Shared by the feedback endpoint and by offer responses, so an accepted or
    declined brand offer teaches the ranker exactly what a tap on a card does.
    """
    event = FeedbackEvent(
        creator_id=creator_id,
        product_id=product_id,
        action=action,
        reason=reason,
        served_score=served_score,
    )
    db.add(event)
    interaction = get_or_create_interaction(db, creator_id, product_id)
    if action == "click":
        interaction.clicks += 1
    elif action == "save":
        interaction.saves += 1
    elif action == "promote":
        interaction.promotes += 1
    elif action == "impression":
        interaction.impressions += 1
    db.commit()
    db.refresh(event)
    return event


@router.post("/feedback", response_model=FeedbackOut, status_code=201)
def submit_feedback(payload: FeedbackIn, db: Session = Depends(get_db)):
    creator = get_creator_or_404(db, payload.creator_id)
    product = db.get(Product, payload.product_id)
    if product is None:
        raise HTTPException(status_code=404, detail=f"product {payload.product_id} not found")

    if payload.action == "skip" and payload.reason and payload.reason not in REJECTION_REASONS:
        raise HTTPException(
            status_code=422,
            detail=f"reason must be one of {list(REJECTION_REASONS)}",
        )

    event = record_event(
        db,
        creator_id=payload.creator_id,
        product_id=payload.product_id,
        action=payload.action,
        reason=payload.reason,
        served_score=payload.served_score,
    )

    # Show the creator what their tap actually changed.
    events = list(
        db.scalars(
            select(FeedbackEvent).where(FeedbackEvent.creator_id == payload.creator_id)
        ).all()
    )
    products_by_id = {p.product_id: p for p in db.scalars(select(Product)).all()}
    adjustments = learning.build_adjustments(events, products_by_id)

    return FeedbackOut(
        status="recorded",
        event_id=event.id,
        creator_id=payload.creator_id,
        product_id=payload.product_id,
        action=payload.action,
        reason=payload.reason,
        learning_notes=adjustments.explain(),
        message=ACKNOWLEDGEMENT.get(payload.action, "Logged."),
    )


@router.get("/feedback/{creator_id}")
def feedback_history(creator_id: str, db: Session = Depends(get_db)):
    get_creator_or_404(db, creator_id)
    events = list(
        db.scalars(
            select(FeedbackEvent)
            .where(FeedbackEvent.creator_id == creator_id)
            .order_by(FeedbackEvent.created_at.desc())
        ).all()
    )
    products_by_id = {p.product_id: p for p in db.scalars(select(Product)).all()}
    adjustments = learning.build_adjustments(events, products_by_id)
    return {
        "creator_id": creator_id,
        "event_count": len(events),
        "events": [
            {
                "id": e.id,
                "product_id": e.product_id,
                "title": products_by_id[e.product_id].title
                if e.product_id in products_by_id
                else e.product_id,
                "action": e.action,
                "reason": e.reason,
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ],
        "learning_notes": adjustments.explain(),
    }
