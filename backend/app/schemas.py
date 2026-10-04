"""Pydantic request / response models — the API contract from slide 06."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Action = Literal["impression", "click", "save", "promote", "skip"]

REJECTION_REASONS = (
    "too_expensive",
    "not_my_niche",
    "already_promoted",
    "audience_wont_care",
    "dont_trust_product",
    "not_trending",
    "angle_unclear",
)


# ---------------------------------------------------------------- creators
class IntentScores(BaseModel):
    trend: int = Field(ge=0, le=100)
    commerce: int = Field(ge=0, le=100)
    brand: int = Field(ge=0, le=100)


class CreatorOut(BaseModel):
    creator_id: str
    name: str
    tier_label: str
    followers: int
    niche: str
    sub_niches: list[str]
    bio: str
    audience_label: str
    audience_age_min: int
    audience_age_max: int
    audience_tiers: list[str]
    price_min: int
    price_max: int
    goal: str
    intent_scores: IntentScores
    avoid_categories: list[str]
    engagement_rate: float
    scale: str = ""
    cell: str = ""
    primary_intent: str = ""
    secondary_intent: str | None = None
    intent_separation: float | None = None
    preferred_price: int | None = None
    niche_shares: dict | None = None
    content_formats: list | None = None
    positioning: dict | None = None
    dna_sources: dict | None = None
    questions_asked: int | None = None


class OnboardingAnswers(BaseModel):
    """Indirect answers. Every field is optional: only asked questions are sent."""

    q1: list[str] | None = None          # posts you'd love to make (content signal)
    q2: str | None = None                # scenario (intent)
    q3: list[str] | None = None          # ranking (intent)
    q4: list[str] | None = None          # 3 product ids (product + price signals)
    q5: str | None = None                # adaptive follow-up (intent)
    q6: str | None = None                # audience age band, only if analytics missing
    q6_tiers: list[str] | None = None
    q7: list[str] | None = None          # categories never to show


class OnboardingIn(BaseModel):
    """Connected profile handle + the indirect answers."""

    handle: str = "riya.glows"
    name: str | None = None
    answers: OnboardingAnswers = OnboardingAnswers()
    consent: bool = True


class CreatorUpdateIn(BaseModel):
    goal: str | None = None              # reach | revenue | brand (edits the primary intent)
    price_min: int | None = None
    price_max: int | None = None
    avoid_categories: list[str] | None = None


# ---------------------------------------------------------------- products
class ProductOut(BaseModel):
    product_id: str
    title: str
    category: str
    sub_category: str
    price: int
    description: str
    tags: list[str]
    art_key: str
    brand: str = ""
    image: str = ""
    is_new: bool = False
    rating: float
    review_count: int
    seller_rating: float
    return_rate: float
    orders_30d: int
    conversion_rate: float
    nmv_30d: int
    trend_score: float
    trend_stage: str
    creator_saturation: float
    in_stock: bool


# ---------------------------------------------------- recommendations
class SignalOut(BaseModel):
    name: str
    label: str
    score: float
    weight: float
    contribution: float


SIGNAL_LABELS = {
    "audience": "Audience fit",
    "creator": "Niche fit",
    "intent": "Intent fit",
    "product": "Product fit",
    "commerce": "Commerce fit",
    "trend": "Trend fit",
    "brand": "Brand fit",
}


class RecommendationOut(BaseModel):
    product_id: str
    rank: int
    fit_score: int
    title: str
    price: int
    category: str
    art_key: str
    brand: str = ""
    image: str = ""
    rating: float
    trend_stage: str
    trend_score: float
    reason_codes: list[str]
    reasons: list[str]
    caveats: list[str]
    confidence: str
    content_angle: str
    signals: list[SignalOut]
    price_fit: float
    base_score: float
    learning_multiplier: float
    notes: list[str]
    penalty_saturation: float = 0.0
    penalty_returns: float = 0.0
    cell: str = ""


class PipelineStats(BaseModel):
    catalogue_size: int
    eligible_count: int
    candidate_count: int
    pool_ratio: float
    rejected_by_rule: dict[str, list[str]]


class RecommendationsOut(BaseModel):
    creator_id: str
    model_version: str
    generated_at: str
    recommendations: list[RecommendationOut]
    pipeline: PipelineStats
    learning_notes: list[str]


class RankRequest(BaseModel):
    creator_id: str
    product_ids: list[str] = Field(min_length=1, max_length=500)


# ---------------------------------------------------------------- feedback
class FeedbackIn(BaseModel):
    creator_id: str
    product_id: str
    action: Action
    reason: str | None = None
    served_score: float | None = None


class FeedbackOut(BaseModel):
    status: str
    event_id: int
    creator_id: str
    product_id: str
    action: str
    reason: str | None
    learning_notes: list[str]
    message: str


# ------------------------------------------------------------ product side
class ProductIn(BaseModel):
    """A seller listing a new product."""

    title: str = Field(min_length=2, max_length=120)
    brand: str = Field(min_length=2, max_length=80)
    category: Literal["Skincare", "Makeup", "Haircare", "Personal Care"]
    sub_category: str = ""
    price: int = Field(ge=10, le=100_000)
    description: str = ""
    tags: list[str] = []
    pack: str = ""                       # image style; empty = infer from the title
    target_age_min: int = 18
    target_age_max: int = 34
    target_tiers: list[str] = ["T1", "T2", "T3"]
    image_url: str | None = Field(default=None, max_length=600_000)


class CreatorMatchOut(BaseModel):
    creator_id: str
    name: str
    niche: str
    tier_label: str
    followers: int
    goal: str
    price_min: int
    price_max: int
    fit_score: int
    eligible: bool
    blocked_by: str | None
    signals: list[SignalOut]
    reasons: list[str]
    caveats: list[str]
    est_reach: int
    est_orders: int
    est_nmv: int
    offer_status: str | None            # pending | accepted | declined | None


class ProductDiagnosis(BaseModel):
    creators_total: int
    reachable: int
    strong_matches: int
    blockers: dict[str, int]
    price_in_band: float                # share of creators whose band holds the price
    median_band_ceiling: int
    weakest: list[str]
    tips: list[str]


class FeedbackSummary(BaseModel):
    promotes: int
    saves: int
    skips: int
    skip_reasons: dict[str, int]
    offers_sent: int
    offers_accepted: int
    offers_declined: int


class ProductMatchesOut(BaseModel):
    product: ProductOut
    matches: list[CreatorMatchOut]
    diagnosis: ProductDiagnosis
    feedback: FeedbackSummary


class PitchIn(BaseModel):
    product_id: str
    creator_id: str
    message: str = Field(default="", max_length=400)


class PitchRespondIn(BaseModel):
    action: Literal["accept", "decline"]
    reason: str | None = None


class PitchOut(BaseModel):
    id: int
    product: ProductOut
    creator_id: str
    creator_name: str
    brand: str
    message: str
    fit_score: int
    status: str
    reason: str | None
    created_at: str
    responded_at: str | None


class BrandOut(BaseModel):
    brand: str
    products: int
    avg_rating: float
    nmv_30d: int
    offers_sent: int
    offers_accepted: int
    image: str


class BrandOverviewOut(BaseModel):
    brand: str
    products: list[ProductOut]
    offers_sent: int
    offers_pending: int
    offers_accepted: int
    offers_declined: int
    acceptance_rate: float | None
    nmv_30d: int
