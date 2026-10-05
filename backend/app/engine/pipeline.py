"""Orchestration: catalogue -> eligible -> candidates -> ranked Top-K.

This is the only module the API layer talks to. Swapping the MVP ranker for a
learned model means changing `_rank`, not the routers or the frontend.
"""
from __future__ import annotations

import uuid
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
from . import baseline, learning, reasons, rewards
from .eligibility import explain_checks, filter_eligible
from .retrieval import retrieve_candidates
from .scoring import ScoreBreakdown, scale_of, score_product

# Top-K by creator tier (slide 7): Starter-5 for Emerging, Top 8 for Growth,
# Top 4 for Established. One rule, used by the API and the app.
TOP_K_BY_SCALE = {"Emerging": 5, "Growth": 8, "Established": 4}
MODES = ("personalised", "interleaved", "generic")


def top_k_for(creator: Creator) -> int:
    return TOP_K_BY_SCALE[scale_of(creator)]


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
    source: str = "personalised"          # personalised | generic | fallback
    checks: list[dict] = field(default_factory=list)
    eligible: bool = True
    blocked_by: str | None = None
    rewards: list[str] = field(default_factory=list)


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
    top_k: int = 5
    mode: str = "personalised"
    slate_id: str = ""


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
    top_k: int | None = None,
    apply_learning: bool = True,
    log: bool = True,
    mode: str = "personalised",
) -> PipelineResult:
    """Serve one slate.

    mode="personalised"  the Fit Engine (default)
    mode="interleaved"   personalised and generic picks mixed by team draft,
                         source hidden from the creator, logged per pick
    mode="generic"       today's best sellers for everyone (the baseline arm)
    """
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    k = top_k or top_k_for(creator)
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
    medians = stage1.return_medians or {}

    # Stage 2 — narrow to a candidate set by similarity.
    candidates = retrieve_candidates(creator, stage1.eligible)

    # Ranking.
    ranked = _rank(db, creator, candidates, adjustments, medians)
    scored = {p.product_id: (p, sim, b) for p, sim, b in ranked}

    def scored_pair(product: Product) -> tuple[Product, float, ScoreBreakdown]:
        if product.product_id in scored:
            return scored[product.product_id]
        rm = medians.get(product.category.lower())
        base = score_product(creator, product, return_median=rm)
        mult = learning.multiplier_for(creator, product, adjustments, base.signals)
        b = base if mult == 1.0 else score_product(creator, product, learning_multiplier=mult, return_median=rm)
        return product, 0.0, b

    picks: list[tuple[Product, float, ScoreBreakdown, str]] = []
    if mode == "personalised":
        picks = [(p, sim, b, "personalised") for p, sim, b in ranked[:k]]
        if len(picks) < k:
            # Fallback: never a short feed, never outside her price window.
            taken = {p.product_id for p, *_ in picks} | adjustments.suppressed_products
            for product in baseline.fallback_pool(creator, catalogue, taken):
                if len(picks) >= k:
                    break
                p, sim, b = scored_pair(product)
                picks.append((p, sim, b, "fallback"))
    else:
        generic = baseline.generic_ranking(catalogue, adjustments.suppressed_products)
        if mode == "generic":
            picks = [(*scored_pair(p), "generic") for p in generic[:k]]
        else:
            personalised = [p for p, _sim, _b in ranked]
            rng = baseline.slate_rng(creator.creator_id, str(len(_creator_feedback(db, creator.creator_id))))
            for product, source in baseline.team_draft(personalised, generic, k, rng):
                picks.append((*scored_pair(product), source))

    has_fit_order = bool(rewards.delivered_fit_orders(db, creator.creator_id))
    eligible_ids = {p.product_id for p in stage1.eligible}
    results: list[Recommendation] = []
    for index, (product, similarity, breakdown, source) in enumerate(picks, start=1):
        codes, positives, caveats = reasons.build_reasons(creator, product, breakdown)
        checks, failed = explain_checks(creator, product, medians, adjustments.suppressed_products)
        if source == "fallback":
            caveats = ["Fallback pick: fewer products than usual passed every check"] + caveats[:2]
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
                source=source,
                checks=checks,
                eligible=product.product_id in eligible_ids,
                blocked_by=failed,
                rewards=rewards.pick_rewards(creator, product, breakdown.fit_score, has_fit_order),
            )
        )

    slate_id = uuid.uuid4().hex[:16]
    if log and results:
        _log_slate(db, creator, results, slate_id, mode)

    return PipelineResult(
        recommendations=results,
        catalogue_size=len(catalogue),
        eligible_count=len(stage1.eligible),
        candidate_count=len(candidates),
        pool_ratio=stage1.pool_ratio,
        rejected_by_rule={k_: v for k_, v in stage1.rejected.items() if v},
        model_version=MODEL_VERSION,
        learning_notes=adjustments.explain(),
        top_k=k,
        mode=mode,
        slate_id=slate_id,
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


def _log_slate(db: Session, creator: Creator, results: list[Recommendation], slate_id: str, mode: str) -> None:
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
                source=rec.source,
                slate_id=slate_id,
                mode=mode,
            )
        )
        interaction = get_or_create_interaction(db, creator.creator_id, rec.product.product_id)
        interaction.impressions += 1
    db.commit()


def score_pair(db: Session, creator: Creator, product: Product) -> Recommendation:
    """Score a single creator-product pair (used by POST /rank-products and offers)."""
    events = _creator_feedback(db, creator.creator_id)
    catalogue = list(db.scalars(select(Product)).all())
    products_by_id = {p.product_id: p for p in catalogue}
    adjustments = learning.build_adjustments(events, products_by_id)
    from .eligibility import category_return_medians
    medians = category_return_medians(catalogue)
    rm = medians.get(product.category.lower())

    provisional = score_product(creator, product, return_median=rm)
    multiplier = learning.multiplier_for(creator, product, adjustments, provisional.signals)
    breakdown = (
        provisional
        if multiplier == 1.0
        else score_product(creator, product, learning_multiplier=multiplier, return_median=rm)
    )
    codes, positives, caveats = reasons.build_reasons(creator, product, breakdown)
    checks, failed = explain_checks(creator, product, medians, adjustments.suppressed_products)
    has_fit_order = bool(rewards.delivered_fit_orders(db, creator.creator_id))
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
        checks=checks,
        eligible=failed is None,
        blocked_by=failed,
        rewards=rewards.pick_rewards(creator, product, breakdown.fit_score, has_fit_order) if failed is None else [],
    )
