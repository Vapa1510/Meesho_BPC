"""Creator Service — profiles, onboarding, intent scores."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..engine import onboarding as ob
from ..engine.scoring import INTENT_LABEL, cell_label, primary_intent, scale_of
from ..models import Creator, Product
from ..schemas import CreatorOut, CreatorUpdateIn, IntentScores, OnboardingAnswers, OnboardingIn

router = APIRouter(tags=["creators"])

# Editing the primary intent on the profile page (the creator correcting what
# the engine understood). Observed behaviour moves these later.
GOAL_INTENT_SEED = {
    "reach":   {"trend": 84, "commerce": 58, "brand": 52},
    "revenue": {"trend": 70, "commerce": 86, "brand": 50},
    "brand":   {"trend": 58, "commerce": 56, "brand": 82},
}

NICHE_SUBS = {
    "Skincare": ["serum", "moisturiser", "sunscreen", "acne", "brightening", "routine"],
    "Makeup": ["lips", "eyes", "base", "kajal", "tint"],
    "Haircare": ["shampoo", "oil", "serum", "frizz"],
    "Personal Care": ["body", "fragrance", "grooming"],
}


def to_out(creator: Creator) -> CreatorOut:
    return CreatorOut(
        creator_id=creator.creator_id,
        name=creator.name,
        tier_label=creator.tier_label,
        followers=creator.followers,
        niche=creator.niche,
        sub_niches=creator.sub_niches or [],
        bio=creator.bio,
        audience_label=creator.audience_label,
        audience_age_min=creator.audience_age_min,
        audience_age_max=creator.audience_age_max,
        audience_tiers=creator.audience_tiers or [],
        price_min=creator.price_min,
        price_max=creator.price_max,
        goal=creator.goal,
        intent_scores=IntentScores(
            trend=creator.intent_trend,
            commerce=creator.intent_commerce,
            brand=creator.intent_brand,
        ),
        avoid_categories=creator.avoid_categories or [],
        engagement_rate=creator.engagement_rate,
        scale=scale_of(creator),
        cell=cell_label(creator),
        primary_intent=INTENT_LABEL[primary_intent(creator)],
        secondary_intent=creator.secondary_intent,
        intent_separation=creator.intent_separation,
        preferred_price=creator.preferred_price,
        niche_shares=creator.niche_shares,
        content_formats=creator.content_formats,
        positioning=creator.positioning,
        dna_sources=creator.dna_sources,
        questions_asked=creator.questions_asked,
    )


def get_creator_or_404(db: Session, creator_id: str) -> Creator:
    creator = db.get(Creator, creator_id)
    if creator is None:
        raise HTTPException(status_code=404, detail=f"creator {creator_id} not found")
    return creator


@router.get("/creators", response_model=list[CreatorOut])
def list_creators(db: Session = Depends(get_db)):
    return [to_out(c) for c in db.scalars(select(Creator)).all()]


@router.get("/creator/{creator_id}", response_model=CreatorOut)
def get_creator(creator_id: str, db: Session = Depends(get_db)):
    return to_out(get_creator_or_404(db, creator_id))


GOAL_FOR_INTENT = {"trend": "reach", "commerce": "revenue", "brand": "brand"}


def _products(db: Session) -> dict[str, Product]:
    return {p.product_id: p for p in db.scalars(select(Product)).all()}


@router.get("/onboarding/connect/{handle}")
def connect(handle: str):
    """What connecting a creator profile fetches, and which questions remain."""
    fetched = ob.DEMO_PROFILES.get(handle)
    if fetched is None:
        raise HTTPException(status_code=404, detail=f"no demo profile '{handle}'")
    questions = ob.plan(fetched["followers"], has_audience_analytics=bool(fetched.get("audience")))
    return {"handle": handle, "fetched": fetched, "scale": ob.scale_for(fetched["followers"]), "questions": questions}


@router.get("/onboarding/questions")
def questions(db: Session = Depends(get_db)):
    """The question bank, with the Q4 product cards filled in from the catalogue."""
    prods = _products(db)
    bank = {k: dict(v) for k, v in ob.QUESTIONS.items()}
    bank["q4"] = {**bank["q4"], "options": [
        {"product_id": pid, "title": prods[pid].title, "price": prods[pid].price, "category": prods[pid].category}
        for pid in ob.Q4_PRODUCTS if pid in prods
    ]}
    return bank


@router.post("/onboarding/preview")
def preview(payload: OnboardingIn, db: Session = Depends(get_db)):
    """Build the Creator DNA without saving it: used to decide on Q5 and to show the result."""
    fetched = ob.DEMO_PROFILES.get(payload.handle, {"followers": 0})
    dna = ob.build_dna(payload.answers.model_dump(exclude_none=True), fetched, _products(db))
    return {"dna": dna.__dict__, "fetched": fetched}


@router.post("/creator/onboard", response_model=CreatorOut, status_code=201)
def onboard(payload: OnboardingIn, db: Session = Depends(get_db)):
    """Create a creator from a connected profile plus the indirect answers."""
    if not payload.consent:
        raise HTTPException(status_code=422, detail="consent is required to build a Creator DNA")
    fetched = ob.DEMO_PROFILES.get(payload.handle, {"followers": 0, "name": payload.name or "New Creator"})
    dna = ob.build_dna(payload.answers.model_dump(exclude_none=True), fetched, _products(db))
    scores = dna.intent["scores"]
    tier = {"Established": "Established Creator", "Growth": "Growth Creator", "Emerging": "Emerging Creator"}[dna.scale]
    creator = Creator(
        creator_id=f"C{uuid.uuid4().hex[:6].upper()}",
        name=payload.name or fetched.get("name", "New Creator"),
        tier_label=tier,
        followers=int(fetched.get("followers", 0)),
        niche=dna.niche,
        sub_niches=NICHE_SUBS.get(dna.niche, []) + dna.content_formats,
        bio=" ".join(h.strip("#") for h in fetched.get("hashtags", [])) or f"{dna.niche.lower()} creator",
        audience_age_min=dna.audience_age_min,
        audience_age_max=dna.audience_age_max,
        audience_tiers=dna.audience_tiers,
        price_min=dna.price_min,
        price_max=dna.price_max,
        goal=GOAL_FOR_INTENT[dna.intent["primary"]],
        intent_trend=int(round(scores["trend"] * 100)),
        intent_commerce=int(round(scores["commerce"] * 100)),
        intent_brand=int(round(scores["brand"] * 100)),
        avoid_categories=dna.avoid_categories,
        preferred_price=dna.preferred_price,
        niche_shares=dna.niche_shares,
        content_formats=dna.content_formats,
        positioning=dna.positioning,
        secondary_intent=dna.intent["secondary"],
        intent_separation=dna.intent["separation"],
        dna_sources=dna.sources,
        questions_asked=dna.questions_asked,
        consented=True,
    )
    db.add(creator)
    db.commit()
    return to_out(creator)


@router.patch("/creator/{creator_id}", response_model=CreatorOut)
def update_creator(
    creator_id: str, payload: CreatorUpdateIn, db: Session = Depends(get_db)
):
    creator = get_creator_or_404(db, creator_id)
    if payload.goal:
        creator.goal = payload.goal
        seed = GOAL_INTENT_SEED.get(payload.goal)
        if seed:
            creator.intent_trend = seed["trend"]
            creator.intent_commerce = seed["commerce"]
            creator.intent_brand = seed["brand"]
    if payload.price_min is not None:
        creator.price_min = payload.price_min
    if payload.price_max is not None:
        creator.price_max = payload.price_max
    if payload.avoid_categories is not None:
        creator.avoid_categories = payload.avoid_categories
    db.commit()
    return to_out(creator)
