"""ORM models.

The three core tables (creators / products / interactions) mirror the
Operational Data Store on slide 06. Two further tables support the closed loop
on slide 07: every served recommendation is logged, and every creator action is
captured as a feedback event that later nudges that creator's ranking.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class Creator(Base):
    __tablename__ = "creators"

    creator_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    tier_label: Mapped[str] = mapped_column(String(40), default="Growth Creator")
    followers: Mapped[int] = mapped_column(Integer, default=0)

    # What they make. niche is the primary category; sub_niches adds nuance.
    niche: Mapped[str] = mapped_column(String(40))
    sub_niches: Mapped[list] = mapped_column(JSON, default=list)
    bio: Mapped[str] = mapped_column(String(200), default="")

    # Who watches. Captured in onboarding, used by the audience-fit signal.
    audience_age_min: Mapped[int] = mapped_column(Integer, default=18)
    audience_age_max: Mapped[int] = mapped_column(Integer, default=24)
    audience_tiers: Mapped[list] = mapped_column(JSON, default=lambda: ["T1", "T2"])

    # What their audience will pay. Drives the price-fit gate.
    price_min: Mapped[int] = mapped_column(Integer, default=200)
    price_max: Mapped[int] = mapped_column(Integer, default=700)

    # Stated goal from onboarding: reach | revenue | brand.
    goal: Mapped[str] = mapped_column(String(16), default="revenue")

    # Intent scores (0-100). These set the ranker's weight mix for this creator,
    # so two creators with identical audiences can still rank products
    # differently. Seeded from onboarding, updated by observed behaviour.
    intent_trend: Mapped[int] = mapped_column(Integer, default=70)
    intent_commerce: Mapped[int] = mapped_column(Integer, default=70)
    intent_brand: Mapped[int] = mapped_column(Integer, default=50)

    # Categories the creator asked not to see.
    avoid_categories: Mapped[list] = mapped_column(JSON, default=list)

    # ---- Creator DNA built by the indirect onboarding (engine/onboarding.py)
    # Price signal from Q4 picks: preferred price (median pick) and the observed
    # range (price_min..price_max above).
    preferred_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Niche shares from content history + hashtags + Q1, e.g. {"Skincare": 0.7}.
    niche_shares: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Content signal from Q1: the formats they enjoy making (routine, review...).
    content_formats: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Positioning shares from Q4 picks + hashtags (budget / mid / premium / ...).
    positioning: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    secondary_intent: Mapped[str | None] = mapped_column(String(16), nullable=True)
    intent_separation: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Where each DNA parameter came from: "fetched" or "asked".
    dna_sources: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    questions_asked: Mapped[int | None] = mapped_column(Integer, nullable=True)
    consented: Mapped[bool] = mapped_column(default=True)

    engagement_rate: Mapped[float] = mapped_column(Float, default=0.04)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)

    interactions: Mapped[list["Interaction"]] = relationship(back_populates="creator")

    @property
    def audience_label(self) -> str:
        tiers = "/".join(t.replace("T", "Tier ") for t in self.audience_tiers)
        return f"{self.audience_age_min}–{self.audience_age_max} | {tiers}"


class Product(Base):
    __tablename__ = "products"

    product_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    title: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(40))          # Skincare, Makeup, ...
    sub_category: Mapped[str] = mapped_column(String(60), default="")
    price: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[list] = mapped_column(JSON, default=list)
    art_key: Mapped[str] = mapped_column(String(24), default="serum")  # image style
    # Who sells it, and an optional real photo. When image_url is empty the API
    # draws the product itself (see imagery.py), so every product has a picture.
    brand: Mapped[str] = mapped_column(String(80), default="Independent Seller")
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Trust signals.
    rating: Mapped[float] = mapped_column(Float, default=4.0)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    seller_rating: Mapped[float] = mapped_column(Float, default=4.0)
    return_rate: Mapped[float] = mapped_column(Float, default=0.08)

    # Commerce signals.
    orders_30d: Mapped[int] = mapped_column(Integer, default=0)
    conversion_rate: Mapped[float] = mapped_column(Float, default=0.02)
    nmv_30d: Mapped[int] = mapped_column(Integer, default=0)

    # Trend signals. trend_score is the normalised momentum (0-1) that the deck
    # shows as the Trend Momentum curve; stage marks where it sits on that curve.
    trend_score: Mapped[float] = mapped_column(Float, default=0.4)
    trend_stage: Mapped[str] = mapped_column(String(16), default="rising")
    creator_saturation: Mapped[float] = mapped_column(Float, default=0.3)

    # Who the product is actually for.
    target_age_min: Mapped[int] = mapped_column(Integer, default=18)
    target_age_max: Mapped[int] = mapped_column(Integer, default=34)
    target_tiers: Mapped[list] = mapped_column(JSON, default=lambda: ["T1", "T2", "T3"])

    in_stock: Mapped[bool] = mapped_column(default=True)
    serviceable: Mapped[bool] = mapped_column(default=True)
    policy_compliant: Mapped[bool] = mapped_column(default=True)

    # Populated when pgvector is enabled; otherwise retrieval falls back to a
    # lexical overlap score over tags + category.
    embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)


class Interaction(Base):
    """Aggregate row per (creator, product) — the deck's Interactions table."""

    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    creator_id: Mapped[str] = mapped_column(ForeignKey("creators.creator_id"))
    product_id: Mapped[str] = mapped_column(ForeignKey("products.product_id"))

    impressions: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    saves: Mapped[int] = mapped_column(Integer, default=0)
    promotes: Mapped[int] = mapped_column(Integer, default=0)
    orders: Mapped[int] = mapped_column(Integer, default=0)
    nmv: Mapped[int] = mapped_column(Integer, default=0)

    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    creator: Mapped[Creator] = relationship(back_populates="interactions")

    __table_args__ = (Index("ix_interaction_pair", "creator_id", "product_id", unique=True),)

    @classmethod
    def new(cls, creator_id: str, product_id: str) -> "Interaction":
        """Column defaults only apply at INSERT, so zero the counters here."""
        return cls(
            creator_id=creator_id,
            product_id=product_id,
            impressions=0,
            clicks=0,
            saves=0,
            promotes=0,
            orders=0,
            nmv=0,
        )


def get_or_create_interaction(db, creator_id: str, product_id: str) -> "Interaction":
    """Fetch the (creator, product) row, creating it safely under concurrency.

    Two requests for the same creator can both find no row and both insert; the
    unique index then rejects one. The insert runs in a savepoint so the loser
    simply re-reads the winner's row instead of failing the whole request.
    """
    from sqlalchemy import select
    from sqlalchemy.exc import IntegrityError

    query = select(Interaction).where(
        Interaction.creator_id == creator_id, Interaction.product_id == product_id
    )
    row = db.scalar(query)
    if row is not None:
        return row
    try:
        with db.begin_nested():
            row = Interaction.new(creator_id, product_id)
            db.add(row)
            db.flush()
        return row
    except IntegrityError:
        return db.scalar(query)


class FeedbackEvent(Base):
    """One creator action. This is the raw signal the learning loop reads."""

    __tablename__ = "feedback_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    creator_id: Mapped[str] = mapped_column(ForeignKey("creators.creator_id"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.product_id"), index=True)

    action: Mapped[str] = mapped_column(String(16))      # promote | save | skip | click | impression
    reason: Mapped[str | None] = mapped_column(String(48), nullable=True)
    served_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)


class RecommendationLog(Base):
    """Every served slate, kept for offline evaluation and A/B comparison."""

    __tablename__ = "recommendation_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    creator_id: Mapped[str] = mapped_column(ForeignKey("creators.creator_id"), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.product_id"))
    rank: Mapped[int] = mapped_column(Integer)
    fit_score: Mapped[int] = mapped_column(Integer)
    signals: Mapped[dict] = mapped_column(JSON, default=dict)
    reason_codes: Mapped[list] = mapped_column(JSON, default=list)
    model_version: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)


class SimulatedProfile(Base):
    """The hidden preference profile of a simulated creator.

    Stored apart from `creators` and never joined into the ranking path, so the
    engine cannot read it even by accident. `engine/simulation.py` is the only
    module that touches this table.
    """

    __tablename__ = "simulated_profiles"

    creator_id: Mapped[str] = mapped_column(
        ForeignKey("creators.creator_id"), primary_key=True
    )
    latent: Mapped[dict] = mapped_column(JSON, default=dict)
    rounds_run: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class EvaluationSnapshot(Base):
    """Ranking quality after each simulated round, for the learning curve."""

    __tablename__ = "evaluation_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    creator_id: Mapped[str] = mapped_column(
        ForeignKey("creators.creator_id"), index=True
    )
    round_number: Mapped[int] = mapped_column(Integer)
    ndcg_at_k: Mapped[float] = mapped_column(Float)
    precision_at_k: Mapped[float] = mapped_column(Float)
    mean_served_utility: Mapped[float] = mapped_column(Float)
    utility_capture: Mapped[float] = mapped_column(Float)
    promotes: Mapped[int] = mapped_column(Integer, default=0)
    saves: Mapped[int] = mapped_column(Integer, default=0)
    skips: Mapped[int] = mapped_column(Integer, default=0)
    nmv: Mapped[int] = mapped_column(Integer, default=0)
    model_version: Mapped[str] = mapped_column(String(32), default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)


class Pitch(Base):
    """A brand's offer of one product to one creator.

    This is the product-side half of the loop. A brand sends the offer; the
    creator's answer is written back as ordinary feedback, so what a brand
    learns about its product and what the ranker learns about the creator come
    from the same events.
    """

    __tablename__ = "pitches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.product_id"), index=True)
    creator_id: Mapped[str] = mapped_column(ForeignKey("creators.creator_id"), index=True)
    brand: Mapped[str] = mapped_column(String(80), index=True)
    message: Mapped[str] = mapped_column(String(400), default="")
    fit_score: Mapped[int] = mapped_column(Integer, default=0)   # as shown to the brand
    status: Mapped[str] = mapped_column(String(12), default="pending")  # pending|accepted|declined
    reason: Mapped[str | None] = mapped_column(String(48), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_now)
    responded_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (Index("ix_pitch_pair", "creator_id", "product_id"),)
