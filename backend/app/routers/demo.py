"""Demo controls for the deployed prototype.

The QR codes in the deck open /creator and /creator/onboard. Judges share one
deployment, so this lets anyone put it back to the exact state the deck shows.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Product
from ..seed import DEMO_CREATOR_ID, seed

router = APIRouter(prefix="/demo", tags=["demo"])

DEMO_PATH = [
    {"step": 1, "slide": 7, "title": "Onboard Riya", "path": "/creator/onboard",
     "what": "Connect @riya.glows and answer 4 indirect questions."},
    {"step": 2, "slide": 7, "title": "Her Creator DNA", "path": "/creator/profile",
     "what": "Every value tagged fetched or asked; correct intent or price and the picks re-rank."},
    {"step": 3, "slide": 8, "title": "Fit Engine: her Top 8", "path": "/creator",
     "what": "164 listings → 25 pass the gates → ranked with reasons and a content angle."},
    {"step": 4, "slide": 8, "title": "Brand Match + feedback loop", "path": "/brand/product/P009",
     "what": "Skip Ceramide Moisturiser as 'Too expensive': 76 → 73, and the brand sees the reason."},
]


@router.get("")
def demo_info():
    return {"demo_creator_id": DEMO_CREATOR_ID, "path": DEMO_PATH}


@router.post("/reset")
def reset_demo(db: Session = Depends(get_db)):
    """Wipe everything a demo created and reload the deck's data."""
    # Keep the catalogue the same size it is now (164 listings when deployed).
    filler = sum(
        1 for (pid,) in db.execute(select(Product.product_id)).all()
        if pid.startswith("P") and pid[1:].isdigit() and int(pid[1:]) >= 100
    )
    counts = seed(db, force=True, filler_count=filler or None)
    return {"status": "reset", "demo_creator_id": DEMO_CREATOR_ID, **counts}
