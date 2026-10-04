"""Analytics Service — the monitoring metrics the deck lists, computed live."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    Creator,
    EvaluationSnapshot,
    FeedbackEvent,
    Interaction,
    RecommendationLog,
)

router = APIRouter(tags=["analytics"])


def _safe_div(a: float, b: float) -> float:
    return round(a / b, 4) if b else 0.0


@router.get("/analytics/metrics")
def metrics(db: Session = Depends(get_db)):
    """CTR, conversion, acceptance, NMV per creator — the four live ones.

    AUC / NDCG need a held-out set and a trained model, so they are reported as
    pending rather than invented.
    """
    impressions = db.scalar(select(func.sum(Interaction.impressions))) or 0
    clicks = db.scalar(select(func.sum(Interaction.clicks))) or 0
    orders = db.scalar(select(func.sum(Interaction.orders))) or 0
    nmv = db.scalar(select(func.sum(Interaction.nmv))) or 0
    creator_count = db.scalar(select(func.count(Creator.creator_id))) or 0

    actions = dict(
        db.execute(
            select(FeedbackEvent.action, func.count(FeedbackEvent.id)).group_by(
                FeedbackEvent.action
            )
        ).all()
    )
    decisive = actions.get("promote", 0) + actions.get("save", 0) + actions.get("skip", 0)
    accepted = actions.get("promote", 0) + actions.get("save", 0)

    reasons = dict(
        db.execute(
            select(FeedbackEvent.reason, func.count(FeedbackEvent.id))
            .where(FeedbackEvent.reason.is_not(None))
            .group_by(FeedbackEvent.reason)
        ).all()
    )

    served = db.scalar(select(func.count(RecommendationLog.id))) or 0
    mean_score = db.scalar(select(func.avg(RecommendationLog.fit_score))) or 0

    return {
        "ctr": _safe_div(clicks, impressions),
        "conversion_rate": _safe_div(orders, clicks),
        "recommendation_acceptance": _safe_div(accepted, decisive),
        "nmv_per_creator": round(_safe_div(nmv, creator_count), 2),
        "model_performance": _ranking_quality(db),
        "volumes": {
            "impressions": impressions,
            "clicks": clicks,
            "orders": orders,
            "nmv": nmv,
            "recommendations_served": served,
            "mean_served_fit_score": round(float(mean_score), 1),
            "feedback_events": sum(actions.values()),
        },
        "actions": actions,
        "rejection_reasons": reasons,
    }


def _ranking_quality(db: Session) -> dict:
    """Mean ranking quality across every simulated creator.

    Real numbers, because simulated creators carry a latent utility to measure
    against. Without any simulation run there is no ground truth, and the
    honest answer is to say so rather than to invent one.
    """
    rows = list(
        db.execute(
            select(
                EvaluationSnapshot.creator_id,
                func.max(EvaluationSnapshot.round_number),
            ).group_by(EvaluationSnapshot.creator_id)
        ).all()
    )
    if not rows:
        return {
            "ndcg_at_k": None,
            "precision_at_k": None,
            "utility_capture": None,
            "creators_evaluated": 0,
            "status": "no_simulation_run_yet",
        }

    latest = [
        db.scalar(
            select(EvaluationSnapshot).where(
                EvaluationSnapshot.creator_id == creator_id,
                EvaluationSnapshot.round_number == last_round,
            )
        )
        for creator_id, last_round in rows
    ]
    latest = [row for row in latest if row is not None]
    n = len(latest)
    return {
        "ndcg_at_k": round(sum(r.ndcg_at_k for r in latest) / n, 4),
        "precision_at_k": round(sum(r.precision_at_k for r in latest) / n, 4),
        "utility_capture": round(sum(r.utility_capture for r in latest) / n, 4),
        "creators_evaluated": n,
        "status": "measured_against_simulated_ground_truth",
    }


@router.get("/analytics/creator/{creator_id}")
def creator_metrics(creator_id: str, db: Session = Depends(get_db)):
    rows = list(
        db.scalars(select(Interaction).where(Interaction.creator_id == creator_id)).all()
    )
    impressions = sum(r.impressions for r in rows)
    clicks = sum(r.clicks for r in rows)
    return {
        "creator_id": creator_id,
        "products_touched": len(rows),
        "impressions": impressions,
        "clicks": clicks,
        "saves": sum(r.saves for r in rows),
        "promotes": sum(r.promotes for r in rows),
        "orders": sum(r.orders for r in rows),
        "nmv": sum(r.nmv for r in rows),
        "ctr": _safe_div(clicks, impressions),
    }
