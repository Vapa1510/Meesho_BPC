"""Offline evaluation.

Ranking quality can only be measured against a ground truth. In production that
ground truth is observed behaviour; here it is the simulated creator's latent
utility, which the engine never sees. That makes NDCG and precision@k real
numbers rather than placeholders.

The ablation is the useful part: the same creator, the same catalogue, scored
once with the feedback loop on and once with it off. The gap is what the
closed loop is worth.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Creator, Product
from .eligibility import filter_eligible
from .pipeline import recommend
from .simulation import LatentProfile, latent_utility


@dataclass
class RankingMetrics:
    ndcg_at_k: float
    precision_at_k: float
    mean_served_utility: float
    best_possible_utility: float
    utility_capture: float      # mean served / best possible
    k: int


def _dcg(relevances: list[float]) -> float:
    return sum(rel / math.log2(index + 2) for index, rel in enumerate(relevances))


def ndcg(served: list[float], ideal: list[float]) -> float:
    ideal_dcg = _dcg(sorted(ideal, reverse=True)[: len(served)])
    if ideal_dcg == 0:
        return 0.0
    return round(_dcg(served) / ideal_dcg, 4)


def evaluate_creator(
    db: Session,
    creator: Creator,
    latent: LatentProfile,
    k: int = 5,
    apply_learning: bool = True,
) -> RankingMetrics:
    """Score the engine's current Top-K against what the creator actually wants."""
    catalogue = list(db.scalars(select(Product)).all())
    eligible = filter_eligible(
        creator, catalogue, category="bpc", suppressed=latent.promoted
    ).eligible

    # Ground truth: the utility of every product the engine could have shown.
    truth = {p.product_id: latent_utility(latent, p)[0] for p in eligible}
    if not truth:
        return RankingMetrics(0.0, 0.0, 0.0, 0.0, 0.0, k)

    result = recommend(
        db, creator, category="bpc", top_k=k, apply_learning=apply_learning, log=False
    )
    served = [truth.get(rec.product.product_id, 0.0) for rec in result.recommendations]
    if not served:
        return RankingMetrics(0.0, 0.0, 0.0, 0.0, 0.0, k)

    ideal = sorted(truth.values(), reverse=True)
    hits = sum(1 for utility in served if utility >= latent.promote_threshold)
    best = sum(ideal[:k]) / min(k, len(ideal))

    mean_served = sum(served) / len(served)
    return RankingMetrics(
        ndcg_at_k=ndcg(served, ideal),
        precision_at_k=round(hits / len(served), 4),
        mean_served_utility=round(mean_served, 4),
        best_possible_utility=round(best, 4),
        utility_capture=round(mean_served / best, 4) if best else 0.0,
        k=k,
    )


@dataclass
class Ablation:
    """Side-by-side: the loop on versus the loop off."""

    with_learning: dict
    without_learning: dict
    ndcg_delta: float
    utility_delta: float
    verdict: str


def ablate(db: Session, creator: Creator, latent: LatentProfile, k: int = 5) -> Ablation:
    on = evaluate_creator(db, creator, latent, k=k, apply_learning=True)
    off = evaluate_creator(db, creator, latent, k=k, apply_learning=False)

    ndcg_delta = round(on.ndcg_at_k - off.ndcg_at_k, 4)
    utility_delta = round(on.mean_served_utility - off.mean_served_utility, 4)

    if abs(ndcg_delta) < 0.005:
        verdict = "No measurable difference yet — not enough feedback collected."
    elif ndcg_delta > 0:
        verdict = (
            f"The feedback loop improves NDCG@{k} by {ndcg_delta:+.3f} "
            f"and mean served utility by {utility_delta:+.3f}."
        )
    else:
        verdict = (
            f"The feedback loop is currently costing {abs(ndcg_delta):.3f} NDCG@{k}. "
            "With few events this can happen: early feedback over-corrects."
        )
    return Ablation(
        with_learning=asdict(on),
        without_learning=asdict(off),
        ndcg_delta=ndcg_delta,
        utility_delta=utility_delta,
        verdict=verdict,
    )


def discovered_preferences(
    db: Session, creator: Creator, latent: LatentProfile
) -> dict:
    """How close the engine's learned view is to the creator's real one.

    Compares the stated profile and the learned adjustments against the latent
    truth, per category. This is the "what did it actually figure out" view.
    """
    from .learning import build_adjustments
    from ..models import FeedbackEvent

    events = list(
        db.scalars(
            select(FeedbackEvent).where(FeedbackEvent.creator_id == creator.creator_id)
        ).all()
    )
    products_by_id = {p.product_id: p for p in db.scalars(select(Product)).all()}
    adjustments = build_adjustments(events, products_by_id)

    rows = []
    for category in ("Skincare", "Makeup", "Haircare", "Personal Care"):
        stated = (
            1.0
            if category == creator.niche
            else 0.0
            if category in (creator.avoid_categories or [])
            else 0.5
        )
        learned = (
            1.0
            - adjustments.category_penalty.get(category, 0.0)
            + adjustments.category_boost.get(category, 0.0)
        )
        rows.append(
            {
                "category": category,
                "stated": round(stated, 3),
                "learned_multiplier": round(learned, 3),
                "true_affinity": latent.category_affinity.get(category, 0.0),
            }
        )

    return {
        "creator_id": creator.creator_id,
        "events_seen": len(events),
        "categories": rows,
        "stated_price_band": [creator.price_min, creator.price_max],
        "true_price_band": [latent.price_floor, latent.price_ceiling],
        "price_sensitivity_learned": round(adjustments.price_sensitivity, 3),
        "notes": adjustments.explain(),
    }
