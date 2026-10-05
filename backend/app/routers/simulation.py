"""Simulation Service — generate creators, run rounds, measure what was learned."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..config import MODEL_VERSION
from ..database import get_db
from ..engine import evaluation, simulation
from ..models import (
    Creator,
    EvaluationSnapshot,
    FeedbackEvent,
    Interaction,
    SimulatedProfile,
)
from .creators import to_out

from ..schemas import CreatorOut

# Starting intent scores for synthetic creators, by the goal they declare.
GOAL_INTENT_SEED = {
    "reach":   {"trend": 84, "commerce": 58, "brand": 52},
    "revenue": {"trend": 70, "commerce": 86, "brand": 50},
    "brand":   {"trend": 58, "commerce": 56, "brand": 82},
}

router = APIRouter(prefix="/simulation", tags=["simulation"])


class GenerateIn(BaseModel):
    seed: int | None = Field(default=None, description="Omit for a random creator")
    count: int = Field(default=1, ge=1, le=20)


class RunIn(BaseModel):
    creator_id: str
    rounds: int = Field(default=8, ge=1, le=40)
    top_k: int = Field(default=5, ge=1, le=20)
    mode: str = Field(default="personalised", pattern="^(personalised|interleaved)$")


class RoundOut(BaseModel):
    round_number: int
    served: list[dict]
    promotes: int
    saves: int
    skips: int
    nmv: int
    ndcg_at_k: float
    precision_at_k: float
    mean_served_utility: float
    utility_capture: float


class RunOut(BaseModel):
    creator_id: str
    rounds: list[RoundOut]
    first: RoundOut
    last: RoundOut
    ndcg_improvement: float
    utility_improvement: float
    total_nmv: int
    summary: str


def _creator_or_404(db: Session, creator_id: str) -> Creator:
    creator = db.get(Creator, creator_id)
    if creator is None:
        raise HTTPException(status_code=404, detail=f"creator {creator_id} not found")
    return creator


def _synthetic_or_409(db: Session, creator_id: str) -> Creator:
    """Simulations only touch synthetic creators, so the deck's creators keep their numbers."""
    creator = _creator_or_404(db, creator_id)
    if not (creator.handle or "").startswith("sim."):
        raise HTTPException(
            status_code=409,
            detail="Simulations run on synthetic creators only, so the deck's creators keep the numbers "
                   "shown on the slides. Generate a synthetic creator first.",
        )
    return creator


@router.post("/generate", response_model=list[CreatorOut], status_code=201)
def generate_creators(payload: GenerateIn, db: Session = Depends(get_db)):
    """Create one or more plausible creators, each with a hidden latent profile.

    The latent profile deliberately drifts from what the creator "states" at
    signup, so the engine starts out partly wrong and has something to learn.
    """
    created: list[Creator] = []
    for index in range(payload.count):
        seed = None if payload.seed is None else payload.seed + index
        spec = simulation.generate_creator_payload(seed)
        intent = GOAL_INTENT_SEED[spec["goal"]]
        followers = spec["followers"]
        new_id = f"C{uuid.uuid4().hex[:6].upper()}"
        creator = Creator(
            creator_id=new_id,
            # Marks a synthetic creator: kept out of brand matching and the
            # trust metrics, so the deck's numbers never move.
            handle=f"sim.{new_id.lower()}",
            name=spec["name"],
            tier_label=(
                "Established Creator" if followers >= 100_000
                else "Growth Creator" if followers >= 10_000
                else "Emerging Creator"
            ),
            followers=followers,
            niche=spec["niche"],
            sub_niches=spec["sub_niches"],
            bio=spec["bio"],
            audience_age_min=spec["audience_age_min"],
            audience_age_max=spec["audience_age_max"],
            audience_tiers=spec["audience_tiers"],
            price_min=spec["price_min"],
            price_max=spec["price_max"],
            goal=spec["goal"],
            intent_trend=intent["trend"],
            intent_commerce=intent["commerce"],
            intent_brand=intent["brand"],
            avoid_categories=spec["avoid_categories"],
            engagement_rate=spec["engagement_rate"],
        )
        db.add(creator)
        db.flush()
        simulation.ensure_latent(db, creator, seed)
        created.append(creator)

    db.commit()
    return [to_out(c) for c in created]


@router.post("/run", response_model=RunOut)
def run_simulation(payload: RunIn, db: Session = Depends(get_db)):
    """Run N rounds of serve → react → learn, measuring quality after each."""
    creator = _synthetic_or_409(db, payload.creator_id)
    latent = simulation.ensure_latent(db, creator)

    profile = db.get(SimulatedProfile, creator.creator_id)
    start = profile.rounds_run if profile else 0

    rounds: list[RoundOut] = []
    total_nmv = 0

    for offset in range(payload.rounds):
        number = start + offset + 1
        result = simulation.run_round(db, creator, latent, number, top_k=payload.top_k, mode=payload.mode)
        metrics = evaluation.evaluate_creator(db, creator, latent, k=payload.top_k)
        total_nmv += result.nmv

        db.add(
            EvaluationSnapshot(
                creator_id=creator.creator_id,
                round_number=number,
                ndcg_at_k=metrics.ndcg_at_k,
                precision_at_k=metrics.precision_at_k,
                mean_served_utility=metrics.mean_served_utility,
                utility_capture=metrics.utility_capture,
                promotes=result.promotes,
                saves=result.saves,
                skips=result.skips,
                nmv=result.nmv,
                model_version=MODEL_VERSION,
            )
        )
        rounds.append(
            RoundOut(
                round_number=number,
                served=result.served,
                promotes=result.promotes,
                saves=result.saves,
                skips=result.skips,
                nmv=result.nmv,
                ndcg_at_k=metrics.ndcg_at_k,
                precision_at_k=metrics.precision_at_k,
                mean_served_utility=metrics.mean_served_utility,
                utility_capture=metrics.utility_capture,
            )
        )

    if profile:
        profile.rounds_run = start + payload.rounds
    db.commit()

    first, last = rounds[0], rounds[-1]
    promoted_count = sum(r.promotes for r in rounds)
    ndcg_improvement = round(last.ndcg_at_k - first.ndcg_at_k, 4)
    utility_improvement = round(last.mean_served_utility - first.mean_served_utility, 4)

    # Round 1 is measured against a full catalogue; by the last round the best
    # matches have been promoted and retired. So a negative first-to-last delta
    # is usually catalogue consumption, not a worse model — saying "quality
    # fell" here would contradict the ablation, which isolates the loop itself.
    if ndcg_improvement > 0.01:
        summary = (
            f"NDCG@{payload.top_k} rose {ndcg_improvement:+.3f} across "
            f"{payload.rounds} rounds as the engine recovered more of "
            f"{creator.name.split()[0]}'s real preferences."
        )
    elif ndcg_improvement < -0.01:
        summary = (
            f"NDCG@{payload.top_k} ended {ndcg_improvement:+.3f} below round 1. "
            f"{creator.name.split()[0]} promoted {promoted_count} products over "
            f"{payload.rounds} rounds and each one retires, so the best remaining "
            "matches get steadily weaker. Use the ablation to see what the "
            "feedback loop itself is worth."
        )
    else:
        summary = (
            f"NDCG@{payload.top_k} held steady across {payload.rounds} rounds, "
            "with the engine keeping pace as the strongest matches were used up."
        )

    return RunOut(
        creator_id=creator.creator_id,
        rounds=rounds,
        first=first,
        last=last,
        ndcg_improvement=ndcg_improvement,
        utility_improvement=utility_improvement,
        total_nmv=total_nmv,
        summary=summary,
    )


@router.get("/history/{creator_id}")
def history(creator_id: str, db: Session = Depends(get_db)):
    """The learning curve for one creator."""
    _creator_or_404(db, creator_id)
    rows = list(
        db.scalars(
            select(EvaluationSnapshot)
            .where(EvaluationSnapshot.creator_id == creator_id)
            .order_by(EvaluationSnapshot.round_number)
        ).all()
    )
    profile = db.get(SimulatedProfile, creator_id)
    return {
        "creator_id": creator_id,
        "rounds_run": profile.rounds_run if profile else 0,
        "snapshots": [
            {
                "round": row.round_number,
                "ndcg_at_k": row.ndcg_at_k,
                "precision_at_k": row.precision_at_k,
                "mean_served_utility": row.mean_served_utility,
                "utility_capture": row.utility_capture,
                "promotes": row.promotes,
                "saves": row.saves,
                "skips": row.skips,
                "nmv": row.nmv,
            }
            for row in rows
        ],
    }


@router.get("/ablation/{creator_id}")
def ablation(
    creator_id: str,
    k: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """Same creator, same catalogue, feedback loop on versus off."""
    creator = _creator_or_404(db, creator_id)
    latent = simulation.load_latent(db, creator_id)
    if latent is None:
        raise HTTPException(
            status_code=409,
            detail="this creator has no simulated profile; run /simulation/run first",
        )
    return evaluation.ablate(db, creator, latent, k=k)


@router.get("/discovered/{creator_id}")
def discovered(creator_id: str, db: Session = Depends(get_db)):
    """What the engine learned, next to what is actually true.

    The honest scoreboard: stated profile, learned adjustment, latent truth.
    """
    creator = _creator_or_404(db, creator_id)
    latent = simulation.load_latent(db, creator_id)
    if latent is None:
        raise HTTPException(
            status_code=409,
            detail="this creator has no simulated profile; run /simulation/run first",
        )
    return evaluation.discovered_preferences(db, creator, latent)


@router.post("/reset/{creator_id}", status_code=200)
def reset(creator_id: str, db: Session = Depends(get_db)):
    """Wipe this creator's learned state so a demo can be run again cleanly."""
    _synthetic_or_409(db, creator_id)
    db.execute(delete(FeedbackEvent).where(FeedbackEvent.creator_id == creator_id))
    db.execute(delete(Interaction).where(Interaction.creator_id == creator_id))
    db.execute(
        delete(EvaluationSnapshot).where(EvaluationSnapshot.creator_id == creator_id)
    )
    profile = db.get(SimulatedProfile, creator_id)
    if profile:
        latent = simulation.LatentProfile.from_json(profile.latent)
        latent.promoted = set()
        profile.latent = latent.to_json()
        profile.rounds_run = 0
    db.commit()
    return {"status": "reset", "creator_id": creator_id}
