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
        handle=creator.handle,
        synthetic=(creator.handle or "").startswith("sim."),
    )


def get_creator_or_404(db: Session, creator_id: str) -> Creator:
    creator = db.get(Creator, creator_id)
    if creator is None:
        raise HTTPException(status_code=404, detail=f"creator {creator_id} not found")
    return creator


@router.get("/creators", response_model=list[CreatorOut])
def list_creators(db: Session = Depends(get_db)):
    """Riya (the deck's persona) first, then the rest in seed order."""
    from ..seed import DEMO_CREATOR_ID

    creators = list(db.scalars(select(Creator)).all())
    creators.sort(key=lambda c: c.creator_id != DEMO_CREATOR_ID)
    return [to_out(c) for c in creators]


@router.get("/creator/{creator_id}", response_model=CreatorOut)
def get_creator(creator_id: str, db: Session = Depends(get_db)):
    return to_out(get_creator_or_404(db, creator_id))


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
    """Create (or update) a creator from a connected profile plus the indirect answers.

    The same handle always maps to the same creator, so onboarding Riya again
    updates Riya instead of adding a second Riya to every brand's list.
    """
    if not payload.consent:
        raise HTTPException(status_code=422, detail="consent is required to build a Creator DNA")
    fetched = ob.DEMO_PROFILES.get(payload.handle, {"followers": 0, "name": payload.name or "New Creator"})
    dna = ob.build_dna(payload.answers.model_dump(exclude_none=True), fetched, _products(db))

    creator = db.scalar(select(Creator).where(Creator.handle == payload.handle)) if payload.handle else None
    if creator is None:
        creator_id = ob.HANDLE_IDS.get(payload.handle) or f"C{uuid.uuid4().hex[:6].upper()}"
        creator = db.get(Creator, creator_id) or Creator(creator_id=creator_id)
        db.add(creator)
    ob.apply_dna(creator, dna, fetched, payload.handle, payload.name)
    db.commit()
    return to_out(creator)


INTENT_FOR_GOAL = {"reach": "trend", "revenue": "commerce", "brand": "brand"}


def correct_intent(creator: Creator, goal: str) -> bool:
    """Make `goal` the primary intent without throwing away the measured scores.

    The chosen intent swaps scores with the current primary, so the separation
    the onboarding measured is kept. Choosing the intent that is already primary
    changes nothing. Returns True when the scores changed.
    """
    target = INTENT_FOR_GOAL.get(goal)
    if target is None:
        raise HTTPException(status_code=422, detail="goal must be one of reach, revenue, brand")
    scores = {"trend": creator.intent_trend, "commerce": creator.intent_commerce, "brand": creator.intent_brand}
    current = primary_intent(creator)
    creator.goal = goal
    if current == target:
        return False
    scores[current], scores[target] = scores[target], scores[current]
    # Break an exact tie in favour of the creator's choice.
    if any(v >= scores[target] for k, v in scores.items() if k != target):
        scores[target] = min(100, max(scores.values()) + 1)
    creator.intent_trend, creator.intent_commerce, creator.intent_brand = (
        scores["trend"], scores["commerce"], scores["brand"],
    )
    return True


@router.patch("/creator/{creator_id}", response_model=CreatorOut)
def update_creator(
    creator_id: str, payload: CreatorUpdateIn, db: Session = Depends(get_db)
):
    """The creator correcting her DNA on the Profile page.

    Only the fields that are sent change. Feedback never rewrites the DNA;
    this endpoint is the creator doing it herself.
    """
    creator = get_creator_or_404(db, creator_id)
    sources = dict(creator.dna_sources or {})
    if payload.goal and correct_intent(creator, payload.goal):
        sources["intent"] = "Corrected on Profile"
    lo = payload.price_min if payload.price_min is not None else creator.price_min
    hi = payload.price_max if payload.price_max is not None else creator.price_max
    if lo > hi:
        raise HTTPException(status_code=422, detail="price_min must not exceed price_max")
    if (lo, hi) != (creator.price_min, creator.price_max):
        creator.price_min, creator.price_max = lo, hi
        if creator.preferred_price is not None and not (lo <= creator.preferred_price <= hi):
            creator.preferred_price = int((lo + hi) / 2)
        sources["price"] = "Corrected on Profile"
    if payload.avoid_categories is not None and payload.avoid_categories != (creator.avoid_categories or []):
        creator.avoid_categories = payload.avoid_categories
        sources["exclusions"] = "Corrected on Profile"
    creator.dna_sources = sources
    db.commit()
    return to_out(creator)
