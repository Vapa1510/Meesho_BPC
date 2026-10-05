"""Recommendation Service — the two-stage pipeline behind one endpoint."""
from __future__ import annotations

import datetime as dt
import time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..engine import pipeline
from ..imagery import image_for
from ..models import Product
from ..engine.rewards import FIT_QUALIFIED
from ..schemas import (
    SIGNAL_LABELS,
    CheckOut,
    DriverOut,
    PipelineStats,
    RankRequest,
    RecommendationOut,
    RecommendationsOut,
    SignalOut,
)
from .creators import get_creator_or_404

router = APIRouter(tags=["recommendations"])

# Response times of the last 500 slates, for the P95 gate on slide 12.
LATENCY_MS: list[float] = []


def record_latency(ms: float) -> None:
    LATENCY_MS.append(ms)
    del LATENCY_MS[:-500]


def rec_to_out(rec: pipeline.Recommendation) -> RecommendationOut:
    breakdown = rec.breakdown
    signals = [
        SignalOut(
            name=name,
            label=SIGNAL_LABELS[name],
            score=breakdown.signals[name],
            weight=breakdown.weights[name],
            contribution=breakdown.contributions[name],
        )
        for name in sorted(breakdown.signals, key=lambda n: -breakdown.contributions[n])
    ]
    return RecommendationOut(
        product_id=rec.product.product_id,
        rank=rec.rank,
        fit_score=rec.fit_score,
        title=rec.product.title,
        price=rec.product.price,
        category=rec.product.category,
        art_key=rec.product.art_key,
        brand=rec.product.brand or "",
        image=image_for(rec.product),
        rating=rec.product.rating,
        trend_stage=rec.product.trend_stage,
        trend_score=rec.product.trend_score,
        reason_codes=rec.reason_codes,
        reasons=rec.reasons,
        caveats=rec.caveats,
        confidence=rec.confidence,
        content_angle=rec.content_angle,
        signals=signals,
        price_fit=breakdown.price_fit,
        penalty_saturation=breakdown.penalty_saturation,
        penalty_returns=breakdown.penalty_returns,
        cell=breakdown.cell,
        base_score=breakdown.base_score,
        learning_multiplier=breakdown.learning_multiplier,
        notes=breakdown.notes,
        top_drivers=[
            DriverOut(
                label=SIGNAL_LABELS[name],
                score=breakdown.signals[name],
                weight=breakdown.weights[name],
                points=breakdown.contributions[name],
            )
            for name in sorted(breakdown.contributions, key=lambda n: -breakdown.contributions[n])[:3]
        ],
        checks=[CheckOut(**c) for c in rec.checks],
        eligible=rec.eligible,
        blocked_by=rec.blocked_by,
        rewards=rec.rewards,
        fit_qualified=rec.fit_score >= FIT_QUALIFIED,
        source=rec.source,
    )


@router.get("/recommendations/{creator_id}", response_model=RecommendationsOut)
def get_recommendations(
    creator_id: str,
    category: str | None = Query(default=None, description="e.g. bpc, Skincare"),
    top_k: int | None = Query(default=None, ge=1, le=50, description="Default: by tier (5 / 8 / 4)"),
    mode: str = Query(default="personalised", pattern="^(personalised|interleaved|generic)$"),
    explain: bool = Query(default=True),
    db: Session = Depends(get_db),
):
    started = time.perf_counter()
    creator = get_creator_or_404(db, creator_id)
    result = pipeline.recommend(db, creator, category=category, top_k=top_k, mode=mode)

    out = [rec_to_out(r) for r in result.recommendations]
    if not explain:
        for item in out:
            item.signals = []
            item.reasons = []
    elapsed = round((time.perf_counter() - started) * 1000, 1)
    record_latency(elapsed)

    return RecommendationsOut(
        creator_id=creator_id,
        model_version=result.model_version,
        generated_at=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        recommendations=out,
        pipeline=PipelineStats(
            catalogue_size=result.catalogue_size,
            eligible_count=result.eligible_count,
            candidate_count=result.candidate_count,
            pool_ratio=result.pool_ratio,
            rejected_by_rule=result.rejected_by_rule,
        ),
        learning_notes=result.learning_notes,
        top_k=result.top_k,
        mode=result.mode,
        slate_id=result.slate_id,
        latency_ms=elapsed,
    )


@router.post("/rank-products", response_model=list[RecommendationOut])
def rank_products(payload: RankRequest, db: Session = Depends(get_db)):
    """Score and rank an explicit candidate set.

    Used for A/B comparisons and for scoring a shortlist a human supplies,
    bypassing stage 1 and stage 2.
    """
    creator = get_creator_or_404(db, payload.creator_id)
    products = list(
        db.scalars(select(Product).where(Product.product_id.in_(payload.product_ids))).all()
    )
    if not products:
        raise HTTPException(status_code=404, detail="none of the product_ids were found")

    scored = [pipeline.score_pair(db, creator, product) for product in products]
    # Products the feed would serve come first; the rest carry the rule that blocks them.
    scored.sort(key=lambda r: (r.eligible, r.fit_score), reverse=True)
    for index, rec in enumerate(scored, start=1):
        rec.rank = index
    return [rec_to_out(r) for r in scored]
