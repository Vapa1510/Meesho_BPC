"""Brand (seller) side: portfolio, product matching, offers.

The creator side asks "which products fit me". This side asks "which creators
fit my product", and closes the loop: an offer a brand sends lands in the
creator's inbox, and the answer becomes ordinary feedback for the ranker.
"""
from __future__ import annotations

import datetime as dt
import uuid
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..engine import learning, matching, pipeline, rewards
from ..engine.eligibility import category_return_medians, filter_eligible, RULES
from ..engine.retrieval import product_vector
from ..imagery import PACKS, image_for, pick_shape, render_svg
from ..models import Creator, FeedbackEvent, Pitch, Product
from ..schemas import (
    REJECTION_REASONS,
    SIGNAL_LABELS,
    BrandOut,
    BrandOverviewOut,
    CreatorMatchOut,
    FeedbackSummary,
    PitchIn,
    PitchOut,
    PitchRespondIn,
    ProductDiagnosis,
    ProductIn,
    ProductMatchesOut,
    ProductOut,
    SignalOut,
)
from .creators import get_creator_or_404
from .feedback import record_event
from .products import to_out as product_out

router = APIRouter(tags=["brands"])


def _pitch_out(pitch: Pitch, product: Product, creator: Creator) -> PitchOut:
    return PitchOut(
        id=pitch.id,
        product=product_out(product),
        creator_id=creator.creator_id,
        creator_name=creator.name,
        brand=pitch.brand,
        message=pitch.message,
        fit_score=pitch.fit_score,
        status=pitch.status,
        reason=pitch.reason,
        created_at=pitch.created_at.isoformat(),
        responded_at=pitch.responded_at.isoformat() if pitch.responded_at else None,
        incentive=pitch.incentive,
        incentive_label=rewards.INCENTIVES.get(pitch.incentive or ""),
    )


# ----------------------------------------------------------------- brands
@router.get("/brands", response_model=list[BrandOut])
def list_brands(db: Session = Depends(get_db)):
    rows = db.execute(
        select(
            Product.brand,
            func.count(Product.product_id),
            func.avg(Product.rating),
            func.sum(Product.nmv_30d),
        )
        .group_by(Product.brand)
        .order_by(func.sum(Product.nmv_30d).desc())
    ).all()
    sent = Counter(b for (b,) in db.execute(select(Pitch.brand)).all())
    accepted = Counter(b for (b,) in db.execute(select(Pitch.brand).where(Pitch.status == "accepted")).all())
    out = []
    for brand, count, rating, nmv in rows:
        # Only named sellers with a real portfolio get a workspace.
        first = db.scalar(select(Product).where(Product.brand == brand).order_by(Product.rating.desc()))
        out.append(
            BrandOut(
                brand=brand,
                products=count,
                avg_rating=round(rating or 0, 2),
                nmv_30d=int(nmv or 0),
                offers_sent=sent.get(brand, 0),
                offers_accepted=accepted.get(brand, 0),
                image=image_for(first) if first else "",
            )
        )
    # Named sellers first, then the long tail of marketplace sellers.
    from ..seed import BRAND_BY_ID

    named = set(BRAND_BY_ID.values())
    out.sort(key=lambda b: (b.brand not in named, -b.nmv_30d))
    return out


@router.get("/brands/{brand}", response_model=BrandOverviewOut)
def brand_overview(brand: str, db: Session = Depends(get_db)):
    products = list(
        db.scalars(select(Product).where(Product.brand == brand).order_by(Product.nmv_30d.desc())).all()
    )
    if not products:
        raise HTTPException(status_code=404, detail=f"brand {brand} not found")
    pitches = list(db.scalars(select(Pitch).where(Pitch.brand == brand)).all())
    counts = Counter(p.status for p in pitches)
    answered = counts["accepted"] + counts["declined"]
    return BrandOverviewOut(
        brand=brand,
        products=[product_out(p) for p in products],
        offers_sent=len(pitches),
        offers_pending=counts["pending"],
        offers_accepted=counts["accepted"],
        offers_declined=counts["declined"],
        acceptance_rate=round(counts["accepted"] / answered, 3) if answered else None,
        nmv_30d=sum(p.nmv_30d for p in products),
    )


# --------------------------------------------------------------- products
@router.post("/products", response_model=ProductOut, status_code=201)
def create_product(payload: ProductIn, db: Session = Depends(get_db)):
    """List a new product. It starts cold: no reviews, no orders, early trend."""
    if payload.pack and payload.pack not in PACKS:
        raise HTTPException(status_code=422, detail=f"pack must be one of {sorted(PACKS)}")
    if payload.target_age_min > payload.target_age_max:
        raise HTTPException(status_code=422, detail="target_age_min must not exceed target_age_max")

    product = Product(
        product_id=f"S{uuid.uuid4().hex[:5].upper()}",
        title=payload.title.strip(),
        brand=payload.brand.strip(),
        category=payload.category,
        sub_category=payload.sub_category.strip().lower(),
        price=payload.price,
        description=payload.description.strip()
        or f"{payload.title.strip()} by {payload.brand.strip()}.",
        tags=[t.strip().lower() for t in payload.tags if t.strip()],
        art_key=f"pack:{payload.pack}" if payload.pack else "auto",
        image_url=payload.image_url or None,
        # Cold start. No reviews yet, so quality rests on the seller rating.
        rating=4.0,
        review_count=0,
        seller_rating=4.2,
        return_rate=0.08,
        orders_30d=0,
        conversion_rate=0.025,
        nmv_30d=0,
        trend_score=0.45,
        trend_stage="early",
        creator_saturation=0.15,
        target_age_min=payload.target_age_min,
        target_age_max=payload.target_age_max,
        target_tiers=payload.target_tiers,
    )
    product.embedding = product_vector(product)
    db.add(product)
    db.commit()
    return product_out(product)


@router.get("/product/{product_id}/image.svg", include_in_schema=False)
def product_image(product_id: str, db: Session = Depends(get_db)):
    from fastapi.responses import Response

    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="product not found")
    svg = render_svg(product.title, product.category, product.art_key, product.product_id)
    return Response(svg, media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=3600"})


@router.get("/imagery/preview.svg", include_in_schema=False)
def preview_image(
    title: str = Query(default="Product"),
    category: str = Query(default=""),
    pack: str = Query(default=""),
    seed: str = Query(default=""),
):
    """Live preview for the listing form, before a product exists."""
    from fastapi.responses import Response

    svg = render_svg(title, category, f"pack:{pack}" if pack else "", seed or title)
    return Response(svg, media_type="image/svg+xml", headers={"Cache-Control": "no-store"})


@router.get("/product/{product_id}/matches", response_model=ProductMatchesOut)
def product_matches(product_id: str, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail=f"product {product_id} not found")

    result = matching.match_creators(db, product)

    out = []
    for m in result.matches:
        b = m.breakdown
        signals = [
            SignalOut(
                name=name,
                label=SIGNAL_LABELS[name],
                score=b.signals[name],
                weight=b.weights[name],
                contribution=b.contributions[name],
            )
            for name in sorted(b.signals, key=lambda n: -b.contributions[n])
        ]
        c = m.creator
        out.append(
            CreatorMatchOut(
                creator_id=c.creator_id,
                name=c.name,
                niche=c.niche,
                tier_label=c.tier_label,
                followers=c.followers,
                goal=c.goal,
                price_min=c.price_min,
                price_max=c.price_max,
                fit_score=b.fit_score,
                eligible=m.eligible,
                blocked_by=matching.BLOCK_LABELS.get(m.blocked_by or "", m.blocked_by),
                signals=signals,
                reasons=m.reasons,
                caveats=m.caveats,
                est_reach=m.est_reach,
                est_orders=m.est_orders,
                est_nmv=m.est_nmv,
                offer_status=m.offer_status,
            )
        )

    events = list(db.scalars(select(FeedbackEvent).where(FeedbackEvent.product_id == product_id)).all())
    action_counts = Counter(e.action for e in events)
    reasons_count = Counter(e.reason for e in events if e.action == "skip" and e.reason)
    pitches = list(db.scalars(select(Pitch).where(Pitch.product_id == product_id)).all())
    pc = Counter(p.status for p in pitches)

    d = result.diagnosis
    return ProductMatchesOut(
        product=product_out(product),
        matches=out,
        diagnosis=ProductDiagnosis(
            creators_total=d.creators_total,
            reachable=d.reachable,
            strong_matches=d.strong_matches,
            blockers={matching.BLOCK_LABELS.get(k, k): v for k, v in d.blockers.items()},
            price_in_band=d.price_in_band,
            median_band_ceiling=d.median_band_ceiling,
            weakest=[SIGNAL_LABELS[n] for n in d.weakest],
            tips=d.tips,
        ),
        feedback=FeedbackSummary(
            promotes=action_counts["promote"],
            saves=action_counts["save"],
            skips=action_counts["skip"],
            skip_reasons=dict(reasons_count),
            offers_sent=len(pitches),
            offers_accepted=pc["accepted"],
            offers_declined=pc["declined"],
        ),
    )


# ----------------------------------------------------------------- offers
@router.post("/pitches", response_model=PitchOut, status_code=201)
def send_pitch(payload: PitchIn, db: Session = Depends(get_db)):
    product = db.get(Product, payload.product_id)
    if product is None:
        raise HTTPException(status_code=404, detail=f"product {payload.product_id} not found")
    creator = get_creator_or_404(db, payload.creator_id)

    existing = db.scalar(
        select(Pitch).where(Pitch.product_id == product.product_id, Pitch.creator_id == creator.creator_id)
    )
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"{creator.name} already has an offer for this product ({existing.status}).",
        )

    # The brand side's rules apply to the API, not only to the screen: an
    # unsolicited offer goes only to a creator who covers the category and
    # whom every hard gate lets through.
    catalogue = list(db.scalars(select(Product)).all())
    events = list(db.scalars(select(FeedbackEvent).where(FeedbackEvent.creator_id == creator.creator_id)).all())
    adj = learning.build_adjustments(events, {p.product_id: p for p in catalogue})
    if not matching.in_niche(creator, product):
        raise HTTPException(status_code=422, detail=f"{creator.name} is not reachable: {matching.BLOCK_LABELS['off_niche']}")
    stage1 = filter_eligible(
        creator, [product], suppressed=adj.suppressed_products,
        return_medians=category_return_medians(catalogue),
    )
    if not stage1.eligible:
        rule = next((r for r in RULES if stage1.rejected.get(r)), "category")
        raise HTTPException(status_code=422, detail=f"{creator.name} is not reachable: {matching.BLOCK_LABELS.get(rule, rule)}")

    fit = pipeline.score_pair(db, creator, product).fit_score
    incentive = (payload.incentive or "").strip() or None
    if incentive in ("none",):
        incentive = None
    if incentive:
        problem = rewards.incentive_allowed(incentive, fit, product)
        if problem:
            raise HTTPException(status_code=422, detail=problem)
    pitch = Pitch(
        product_id=product.product_id,
        creator_id=creator.creator_id,
        brand=product.brand,
        message=payload.message.strip()
        or f"{product.brand} would like you to feature {product.title}.",
        fit_score=fit,
        incentive=incentive,
    )
    db.add(pitch)
    db.commit()
    db.refresh(pitch)
    return _pitch_out(pitch, product, creator)


@router.get("/pitches", response_model=list[PitchOut])
def list_pitches(
    creator_id: str | None = None,
    brand: str | None = None,
    product_id: str | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(Pitch).order_by(Pitch.created_at.desc())
    if creator_id:
        stmt = stmt.where(Pitch.creator_id == creator_id)
    if brand:
        stmt = stmt.where(Pitch.brand == brand)
    if product_id:
        stmt = stmt.where(Pitch.product_id == product_id)
    out = []
    for pitch in db.scalars(stmt).all():
        product = db.get(Product, pitch.product_id)
        creator = db.get(Creator, pitch.creator_id)
        if product and creator:
            out.append(_pitch_out(pitch, product, creator))
    return out


@router.post("/pitches/{pitch_id}/respond", response_model=PitchOut)
def respond_to_pitch(pitch_id: int, payload: PitchRespondIn, db: Session = Depends(get_db)):
    pitch = db.get(Pitch, pitch_id)
    if pitch is None:
        raise HTTPException(status_code=404, detail="offer not found")
    if pitch.status != "pending":
        raise HTTPException(status_code=409, detail=f"this offer was already {pitch.status}")

    if payload.action == "decline":
        if payload.reason not in REJECTION_REASONS:
            raise HTTPException(
                status_code=422,
                detail=f"a decline needs a reason, one of {list(REJECTION_REASONS)}",
            )
    product = db.get(Product, pitch.product_id)
    creator = db.get(Creator, pitch.creator_id)

    # The answer is ordinary feedback: it moves the creator's ranking the same
    # way a tap on a recommendation card does.
    record_event(
        db,
        creator_id=pitch.creator_id,
        product_id=pitch.product_id,
        action="promote" if payload.action == "accept" else "skip",
        reason=None if payload.action == "accept" else payload.reason,
        served_score=pitch.fit_score,
    )
    pitch.status = "accepted" if payload.action == "accept" else "declined"
    pitch.reason = payload.reason if payload.action == "decline" else None
    pitch.responded_at = dt.datetime.now(dt.timezone.utc)
    db.commit()
    return _pitch_out(pitch, product, creator)
