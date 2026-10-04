"""Orchestration: catalogue -> eligible -> candidates -> ranked Top-K.

This is the only module the API layer talks to. Swapping the MVP ranker for a
learned model means changing `_rank`, not the routers or the frontend.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import DEFAULT_TOP_K, MODEL_VERSION
from ..models import (
    Creator,
    FeedbackEvent,
    Interaction,
    Product,
    RecommendationLog,
    get_or_create_interaction,
)
from . import learning, reasons
from .eligibility import filter_eligible
from .retrieval import retrieve_candidates
from .scoring import ScoreBreakdown, score_product


@dataclass
class Recommendation:
    product: Product
    rank: int
    fit_score: int
    breakdown: ScoreBreakdown
    reason_codes: list[str]
    reasons: list[str]
    caveats: list[str]
    confidence: str
    content_angle: str
    similarity: float


@dataclass
class PipelineResult:
    recommendations: list[Recommendation]
    catalogue_size: int
    eligible_count: int
    candidate_count: int
    pool_ratio: float
    rejected_by_rule: dict[str, list[str]]
    model_version: str
    learning_notes: list[str] = field(default_factory=list)


def _creator_feedback(db: Session, creator_id: str) -> list[FeedbackEvent]:
    return list(
        db.scalars(
            select(FeedbackEvent).where(FeedbackEvent.creator_id == creator_id)
        ).all()
    )


def _interaction_count(db: Session, creator_id: str, product_id: str) -> int:
    row = db.scalar(
        select(Interaction).where(
            Interaction.creator_id == creator_id,
            Interaction.product_id == product_id,
        )
    )
    if row is None:
        return 0
    return row.impressions + row.clicks + row.saves + row.promotes + row.orders


def recommend(
    db: Session,
    creator: Creator,
    *,
    category: str | None = None,
    top_k: int = DEFAULT_TOP_K,
    apply_learning: bool = True,
    log: bool = True,
) -> PipelineResult:
    catalogue = list(db.scalars(select(Product)).all())
    products_by_id = {p.product_id: p for p in catalogue}

    # Learned adjustments come first: they decide what is still eligible.
    if apply_learning:
        events = _creator_feedback(db, creator.creator_id)
        adjustments = learning.build_adjustments(events, products_by_id)
    else:
        adjustments = learning.CreatorAdjustments()

    # Stage 1 — hard filters, including anything the creator has already run.
    stage1 = filter_eligible(
        creator, catalogue, category=category, suppressed=adjustments.suppressed_products
    )

    # Stage 2 — narrow to a candidate set by similarity.
    candidates = retrieve_candidates(creator, stage1.eligible)

    # Ranking.
    ranked = _rank(db, creator, candidates, adjustments, stage1.return_medians or {})[:top_k]

    results: list[Recommendation] = []
    for index, (product, similarity, breakdown) in enumerate(ranked, start=1):
        codes, positives, caveats = reasons.build_reasons(creator, product, breakdown)
        results.append(
            Recommendation(
                product=product,
                rank=index,
                fit_score=breakdown.fit_score,
                breakdown=breakdown,
                reason_codes=codes,
                reasons=positives,
                caveats=caveats,
                confidence=reasons.confidence(
                    creator, product, _interaction_count(db, creator.creator_id, product.product_id)
                ),
                content_angle=reasons.content_angle(creator, product),
                similarity=similarity,
            )
        )

    if log and results:
        _log_slate(db, creator, results)

    return PipelineResult(
        recommendations=results,
        catalogue_size=len(catalogue),
        eligible_count=len(stage1.eligible),
        candidate_count=len(candidates),
        pool_ratio=stage1.pool_ratio,
        rejected_by_rule={k: v for k, v in stage1.rejected.items() if v},
        model_version=MODEL_VERSION,
        learning_notes=adjustments.explain(),
    )


def _rank(
    db: Session,
    creator: Creator,
    candidates: list[tuple[Product, float]],
    adjustments: learning.CreatorAdjustments,
    return_medians: dict[str, float] | None = None,
) -> list[tuple[Product, float, ScoreBreakdown]]:
    """Score every candidate and sort.

    Replace the body of this function to swap in LightGBM / learning-to-rank:
    the inputs (creator, candidates, adjustments) and the output shape are the
    contract the rest of the system depends on.
    """
    scored: list[tuple[Product, float, ScoreBreakdown]] = []
    medians = return_medians or {}
    for product, similarity in candidates:
        rm = medians.get(product.category.lower())
        provisional = score_product(creator, product, return_median=rm)
        multiplier = learning.multiplier_for(
            creator, product, adjustments, provisional.signals
        )
        final = (
            provisional
            if multiplier == 1.0
            else score_product(creator, product, learning_multiplier=multiplier, return_median=rm)
        )
        scored.append((product, similarity, final))

    scored.sort(key=lambda row: (row[2].fit_score, row[1]), reverse=True)
    return scored


def _log_slate(db: Session, creator: Creator, results: list[Recommendation]) -> None:
    for rec in results:
        db.add(
            RecommendationLog(
                creator_id=creator.creator_id,
                product_id=rec.product.product_id,
                rank=rec.rank,
                fit_score=rec.fit_score,
                signals=rec.breakdown.signals,
                reason_codes=rec.reason_codes,
                model_version=MODEL_VERSION,
            )
        )
        interaction = get_or_create_interaction(db, creator.creator_id, rec.product.product_id)
        interaction.impressions += 1
    db.commit()


def score_pair(db: Session, creator: Creator, product: Product) -> Recommendation:
    """Score a single creator-product pair (used by POST /rank-products)."""
    events = _creator_feedback(db, creator.creator_id)
    catalogue = list(db.scalars(select(Product)).all())
    products_by_id = {p.product_id: p for p in catalogue}
    adjustments = learning.build_adjustments(events, products_by_id)
    from .eligibility import category_return_medians
    rm = category_return_medians(catalogue).get(product.category.lower())

    provisional = score_product(creator, product, return_median=rm)
    multiplier = learning.multiplier_for(creator, product, adjustments, provisional.signals)
    breakdown = (
        provisional
        if multiplier == 1.0
        else score_product(creator, product, learning_multiplier=multiplier, return_median=rm)
    )
    codes, positives, caveats = reasons.build_reasons(creator, product, breakdown)
    return Recommendation(
        product=product,
        rank=0,
        fit_score=breakdown.fit_score,
        breakdown=breakdown,
        reason_codes=codes,
        reasons=positives,
        caveats=caveats,
        confidence=reasons.confidence(
            creator, product, _interaction_count(db, creator.creator_id, product.product_id)
        ),
        content_angle=reasons.content_angle(creator, product),
        similarity=0.0,
    )
