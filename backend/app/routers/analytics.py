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


# --------------------------------------------------------------------------
# Trust & quality metrics (slide 9) and scale gates (slide 12), measured live.
# --------------------------------------------------------------------------
FIT_REASONS = {"too_expensive", "not_my_niche", "audience_wont_care", "dont_trust_product", "not_trending"}


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))], 1)


@router.get("/analytics/trust")
def trust_metrics(db: Session = Depends(get_db)):
    """The deck's trust, quality and reliability metrics, from what has been served.

    Every number is computed from the prototype's own tables (sample data), not
    from Meesho traffic. Targets are the deck's; precision comes from simulated
    creators and is a mechanism check, not creator performance.
    """
    from ..engine.eligibility import filter_eligible
    from ..engine.pipeline import TOP_K_BY_SCALE
    from ..engine.scoring import scale_of
    from ..models import Product, SimulatedProfile
    from .recommendations import LATENCY_MS

    synthetic = {c for (c,) in db.execute(select(SimulatedProfile.creator_id)).all()}
    logs = [
        r for r in db.scalars(select(RecommendationLog).where(RecommendationLog.source != "generic")).all()
        if r.creator_id not in synthetic
    ]
    products = {p.product_id: p for p in db.scalars(select(Product)).all()}
    creators = {c.creator_id: c for c in db.scalars(select(Creator)).all()}

    latest: dict[tuple[str, str], RecommendationLog] = {}
    for r in logs:
        latest[(r.creator_id, r.product_id)] = r
    pairs = list(latest)
    n_pairs = len(pairs)

    explained = sum(1 for k in pairs if [c for c in (latest[k].reason_codes or []) if c != "broad_match"])
    skips = {
        (e.creator_id, e.product_id)
        for e in db.scalars(select(FeedbackEvent).where(FeedbackEvent.action == "skip")).all()
        if e.reason in FIT_REASONS
    }
    wrong = sum(1 for k in pairs if k in skips)
    stale = sum(
        1 for (_c, pid) in pairs
        if pid in products and not (products[pid].in_stock and products[pid].serviceable and products[pid].policy_compliant)
    )

    slates: dict[str, list[RecommendationLog]] = {}
    for r in logs:
        if r.slate_id and r.mode == "personalised":
            slates.setdefault(r.slate_id, []).append(r)
    diversity = []
    full = 0
    for rows in slates.values():
        top5 = sorted(rows, key=lambda r: r.rank)[:5]
        diversity.append(len({products[r.product_id].sub_category for r in top5 if r.product_id in products}))
        c = creators.get(rows[0].creator_id)
        if c is not None and len(rows) >= TOP_K_BY_SCALE[scale_of(c)]:
            full += 1

    eligible_any: set[str] = set()
    catalogue = list(products.values())
    for c in creators.values():
        if c.creator_id in synthetic:
            continue
        eligible_any |= {p.product_id for p in filter_eligible(c, catalogue).eligible}
    reached = {pid for (_c, pid) in pairs} & eligible_any

    sim = _ranking_quality(db)

    def share(a: int, b: int) -> float | None:
        return round(a / b, 3) if b else None

    rows = [
        {"metric": "Explained picks", "formula": "Explained picks ÷ picks shown",
         "value": share(explained, n_pairs), "target": "≥ 80%", "ok": None if not n_pairs else explained / n_pairs >= 0.8,
         "unit": "share", "evidence": "live (prototype data)"},
        {"metric": "Wrong picks", "formula": "Picks skipped for a fit reason ÷ picks shown",
         "value": share(wrong, n_pairs), "target": "< 10%", "ok": None if not n_pairs else wrong / n_pairs < 0.10,
         "unit": "share", "evidence": "live (prototype data)"},
        {"metric": "Freshness", "formula": "Stale or out-of-stock picks ÷ picks shown",
         "value": share(stale, n_pairs), "target": "< 5%", "ok": None if not n_pairs else stale / n_pairs < 0.05,
         "unit": "share", "evidence": "live (prototype data)"},
        {"metric": "Mix diversity", "formula": "Distinct product types in each Top-5 (average)",
         "value": round(sum(diversity) / len(diversity), 2) if diversity else None, "target": "≥ 3 (tracked, not enforced)",
         "ok": None if not diversity else sum(diversity) / len(diversity) >= 3, "unit": "count",
         "evidence": "live (prototype data)"},
        {"metric": "Catalogue reach", "formula": "Eligible products recommended ≥ once ÷ all eligible",
         "value": share(len(reached), len(eligible_any)), "target": "≥ 70%",
         "ok": None if not eligible_any else len(reached) / len(eligible_any) >= 0.70, "unit": "share",
         "evidence": "live (prototype data); grows as more creators are served"},
        {"metric": "Fallback coverage", "formula": "Slates served with a full Top-K ÷ slates served",
         "value": share(full, len(slates)), "target": "100%", "ok": None if not slates else full == len(slates),
         "unit": "share", "evidence": "live (prototype data)"},
        {"metric": "Response time (P95)", "formula": "95th percentile of /recommendations time",
         "value": _p95(LATENCY_MS), "target": "< 500 ms", "ok": None if not LATENCY_MS else _p95(LATENCY_MS) < 500,
         "unit": "ms", "evidence": "live, this server since its last restart"},
        {"metric": "Precision@5", "formula": "Picks above the simulated creator's promote threshold ÷ 5",
         "value": sim["precision_at_k"], "target": "≥ 70%", "ok": None if sim["precision_at_k"] is None else sim["precision_at_k"] >= 0.7,
         "unit": "share", "evidence": "simulated creators: a mechanism check, not creator performance"},
    ]
    return {
        "picks_shown": n_pairs,
        "slates_served": len(slates),
        "metrics": rows,
        "note": "Computed from the prototype's sample data. Targets are the deck's (slides 9 and 12); "
                "the pilot measures them on real creators.",
    }


@router.get("/analytics/pilot")
def pilot_metrics(db: Session = Depends(get_db)):
    """Interleaving win rate (slide 11, gate 1): do personalised picks beat generic ones?

    Each action is credited to the feed that served the pick in an interleaved
    slate. A slate is a personalised win when its personalised picks got more
    promotes and saves than its generic picks.
    """
    from ..models import SimulatedProfile

    synthetic = {c for (c,) in db.execute(select(SimulatedProfile.creator_id)).all()}
    logs = list(db.scalars(select(RecommendationLog).where(RecommendationLog.mode == "interleaved")).all())
    events = list(db.scalars(select(FeedbackEvent).where(FeedbackEvent.action.in_(("promote", "save", "skip")))).all())

    def summarise(keep) -> dict:
        rows = [r for r in logs if keep(r.creator_id)]
        shown = {"personalised": 0, "generic": 0}
        slate_of: dict[tuple[str, str], list[RecommendationLog]] = {}
        for r in rows:
            shown[r.source] = shown.get(r.source, 0) + 1
            slate_of.setdefault((r.creator_id, r.product_id), []).append(r)
        positives = {"personalised": 0, "generic": 0}
        by_slate: dict[str, dict[str, int]] = {}
        for e in events:
            served = [r for r in slate_of.get((e.creator_id, e.product_id), []) if r.created_at <= e.created_at]
            if not served:
                continue
            r = max(served, key=lambda x: x.id)
            if e.action in ("promote", "save"):
                positives[r.source] = positives.get(r.source, 0) + 1
                by_slate.setdefault(r.slate_id or "", {"personalised": 0, "generic": 0})
                by_slate[r.slate_id or ""][r.source] = by_slate[r.slate_id or ""].get(r.source, 0) + 1
        p_wins = sum(1 for v in by_slate.values() if v["personalised"] > v["generic"])
        g_wins = sum(1 for v in by_slate.values() if v["generic"] > v["personalised"])
        decided = p_wins + g_wins
        return {
            "slates": len({r.slate_id for r in rows}),
            "shown": shown,
            "positive_actions": positives,
            "pick_rate": {k: (round(positives[k] / shown[k], 3) if shown.get(k) else None) for k in ("personalised", "generic")},
            "personalised_wins": p_wins,
            "generic_wins": g_wins,
            "ties": len(by_slate) - decided,
            "win_rate": round(p_wins / decided, 3) if decided else None,
        }

    return {
        "real": summarise(lambda c: c not in synthetic),
        "synthetic": summarise(lambda c: c in synthetic),
        "gate": "Gate 1 (match quality): personalised picks beat generic ones in the interleaved test (win rate > 50%).",
        "note": "Synthetic results are a mechanism check on simulated creators, not business validation.",
    }
