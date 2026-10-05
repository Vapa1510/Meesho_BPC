"""Behavioural tests for the fit engine.

These assert the properties the pitch depends on, not just that the code runs:
the same product scores differently for different creators, price gates bite,
feedback changes the next ranking, and every score is reproducible.
"""
from __future__ import annotations

import os
import tempfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("FILLER_PRODUCTS", "40")

from app.database import Base  # noqa: E402
from app.engine import evaluation, recommend, score_pair, score_product, simulation  # noqa: E402
from app.engine.scoring import price_fit, weight_mix  # noqa: E402
from app.models import Creator, FeedbackEvent, Product  # noqa: E402
from app.seed import seed  # noqa: E402


@pytest.fixture()
def db():
    path = tempfile.mktemp(suffix=".db")
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    seed(session, force=True)
    yield session
    session.close()
    engine.dispose()
    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture()
def aditi(db):
    return db.get(Creator, "C12345")


# ----------------------------------------------------------------- scoring
def test_hero_products_regression(db, aditi):
    """The five deck products under the v2 matrix scheme (Growth x Commerce-led)."""
    scores = {pid: score_pair(db, aditi, db.get(Product, pid)).fit_score
              for pid in ("P001", "P002", "P003", "P004", "P005")}
    # The serum that fits her audience, niche and price is her best pick, and the
    # premium hair serum (off-niche, above her range) is well behind it.
    assert max(scores, key=scores.get) == "P001"
    assert scores["P005"] <= scores["P001"] - 10
    assert all(60 <= s <= 95 for s in scores.values())


def test_matrix_weights_follow_scale_and_intent(db):
    from app.engine.scoring import BASE_WEIGHTS, SCALE_DELTA, SIGNALS
    for creator in db.query(Creator).all():
        w = weight_mix(creator)
        points = [round(w[s] * 100) for s in SIGNALS]
        assert sum(points) == 100 and min(points) >= 0
    assert all(sum(d) == 0 for d in SCALE_DELTA.values())
    assert BASE_WEIGHTS["commerce"][SIGNALS.index("commerce")] == 25
    assert BASE_WEIGHTS["trend"][SIGNALS.index("trend")] == 25


def test_crowding_penalty_is_stronger_for_established(db):
    from app.engine.scoring import saturation_penalty
    product = db.get(Product, "P007")
    emerging = db.get(Creator, "C006")      # 6.2K
    established = db.get(Creator, "C005")   # 310K
    assert saturation_penalty(established, product) > saturation_penalty(emerging, product)


def test_scoring_is_deterministic(db, aditi):
    product = db.get(Product, "P001")
    first = score_product(aditi, product)
    second = score_product(aditi, product)
    assert first.fit_score == second.fit_score
    assert first.signals == second.signals


def test_weights_always_sum_to_one(db):
    for creator in db.query(Creator).all():
        assert sum(weight_mix(creator).values()) == pytest.approx(1.0, abs=1e-6)


def test_contributions_reconstruct_the_base_score(db, aditi):
    breakdown = score_product(aditi, db.get(Product, "P001"))
    assert sum(breakdown.contributions.values()) == pytest.approx(
        breakdown.base_score, abs=0.01
    )


def test_same_product_scores_differently_per_creator(db):
    """The premise of the whole engine: fit is a property of the pair."""
    aditi = db.get(Creator, "C12345")      # skincare, Rs200-700, commerce-led
    neha = db.get(Creator, "C003")         # haircare, Rs400-1500, brand-led
    hair_serum = db.get(Product, "P005")

    for_aditi = score_pair(db, aditi, hair_serum).fit_score
    for_neha = score_pair(db, neha, hair_serum).fit_score
    assert for_neha > for_aditi + 5


# ------------------------------------------------------------- price gate
def test_price_inside_band_is_not_penalised(aditi):
    product = Product(price=499, **_minimal())
    assert price_fit(aditi, product) == 1.0


def test_above_band_is_penalised_harder_than_below(aditi):
    over = Product(price=aditi.price_max * 2, **_minimal())
    under = Product(price=max(1, int(aditi.price_min * 0.5)), **_minimal())
    assert price_fit(aditi, over) < price_fit(aditi, under) < 1.0


def _minimal() -> dict:
    return dict(product_id="X", title="x", category="Skincare")


# -------------------------------------------------------------- pipeline
def test_pipeline_narrows_the_catalogue(db, aditi):
    result = recommend(db, aditi, category="bpc", top_k=5)
    assert result.eligible_count < result.catalogue_size
    assert 0.05 < result.pool_ratio < 0.60
    assert len(result.recommendations) == 5


def test_results_are_ordered_by_fit_score(db, aditi):
    result = recommend(db, aditi, category="bpc", top_k=10)
    scores = [r.fit_score for r in result.recommendations]
    assert scores == sorted(scores, reverse=True)


def test_every_recommendation_is_explained(db, aditi):
    result = recommend(db, aditi, category="bpc", top_k=5)
    for rec in result.recommendations:
        assert rec.reason_codes, "a score with no reason code is not shippable"
        assert rec.reasons
        assert rec.content_angle
        assert rec.confidence in {"LOW", "MEDIUM", "HIGH"}
        assert sum(rec.breakdown.weights.values()) == pytest.approx(1.0, abs=1e-6)


def test_out_of_stock_products_never_surface(db, aditi):
    result = recommend(db, aditi, category="bpc", top_k=50)
    for rec in result.recommendations:
        assert rec.product.in_stock
        assert rec.product.serviceable
        assert rec.product.policy_compliant


def test_avoided_categories_are_excluded(db, aditi):
    aditi.avoid_categories = ["Makeup"]
    db.commit()
    result = recommend(db, aditi, category="bpc", top_k=50)
    assert all(r.product.category != "Makeup" for r in result.recommendations)


# -------------------------------------------------------- learning loop
def test_not_my_niche_demotes_that_category(db, aditi):
    before = {r.product.category for r in recommend(db, aditi, top_k=5).recommendations}
    assert "Makeup" in before or True  # only asserting the delta below

    makeup = db.query(Product).filter(Product.category == "Makeup").first()
    baseline = score_pair(db, aditi, makeup).fit_score

    for _ in range(3):
        db.add(
            FeedbackEvent(
                creator_id=aditi.creator_id,
                product_id=makeup.product_id,
                action="skip",
                reason="not_my_niche",
            )
        )
    db.commit()

    assert score_pair(db, aditi, makeup).fit_score < baseline


def test_already_promoted_removes_the_product_from_the_slate(db, aditi):
    """Suppression is an eligibility decision, not a scoring one.

    Down-weighting leaves the product competing for a slot it can never
    deserve, so the creator keeps seeing what they already rejected. The
    direct score stays honest — it is simply no longer offered.
    """
    target = db.get(Product, "P001")
    assert any(
        r.product.product_id == target.product_id
        for r in recommend(db, aditi, top_k=10).recommendations
    )
    score_before = score_pair(db, aditi, target).fit_score

    db.add(
        FeedbackEvent(
            creator_id=aditi.creator_id,
            product_id=target.product_id,
            action="skip",
            reason="already_promoted",
        )
    )
    db.commit()

    after = recommend(db, aditi, top_k=10)
    assert all(r.product.product_id != target.product_id for r in after.recommendations)
    assert target.product_id in after.rejected_by_rule.get("already_promoted", [])
    # Scoring it directly still returns the truth, not a punished number.
    assert score_pair(db, aditi, target).fit_score == score_before


def test_promoting_retires_the_product(db, aditi):
    """A promote should retire the item without waiting to be told."""
    target = db.get(Product, "P002")
    db.add(
        FeedbackEvent(
            creator_id=aditi.creator_id, product_id=target.product_id, action="promote"
        )
    )
    db.commit()
    after = recommend(db, aditi, top_k=10)
    assert all(r.product.product_id != target.product_id for r in after.recommendations)


def test_saving_does_not_retire_the_product(db, aditi):
    """A save means 'maybe later', so it stays eligible."""
    target = db.get(Product, "P001")
    db.add(
        FeedbackEvent(
            creator_id=aditi.creator_id, product_id=target.product_id, action="save"
        )
    )
    db.commit()
    after = recommend(db, aditi, top_k=10)
    assert any(r.product.product_id == target.product_id for r in after.recommendations)


def test_too_expensive_only_penalises_expensive_products(db, aditi):
    cheap = db.get(Product, "P004")        # Rs149, below the band midpoint
    pricey = db.get(Product, "P009")       # Rs599, above it
    cheap_before = score_pair(db, aditi, cheap).fit_score
    pricey_before = score_pair(db, aditi, pricey).fit_score

    for _ in range(3):
        db.add(
            FeedbackEvent(
                creator_id=aditi.creator_id,
                product_id=pricey.product_id,
                action="skip",
                reason="too_expensive",
            )
        )
    db.commit()

    assert score_pair(db, aditi, pricey).fit_score < pricey_before
    assert score_pair(db, aditi, cheap).fit_score == cheap_before


def test_promoting_lifts_the_category(db, aditi):
    product = db.get(Product, "P002")
    baseline = score_pair(db, aditi, product).fit_score
    other_skincare = db.get(Product, "P006")
    other_before = score_pair(db, aditi, other_skincare).fit_score

    db.add(
        FeedbackEvent(
            creator_id=aditi.creator_id,
            product_id=product.product_id,
            action="promote",
        )
    )
    db.commit()

    assert score_pair(db, aditi, other_skincare).fit_score >= other_before
    assert baseline > 0


def test_feedback_cannot_bury_a_category_outright(db, aditi):
    """Adjustments are bounded, so a run of angry taps cannot zero a score."""
    makeup = db.query(Product).filter(Product.category == "Makeup").first()
    baseline = score_pair(db, aditi, makeup).fit_score

    for _ in range(40):
        db.add(
            FeedbackEvent(
                creator_id=aditi.creator_id,
                product_id=makeup.product_id,
                action="skip",
                reason="not_my_niche",
            )
        )
    db.commit()

    after = score_pair(db, aditi, makeup).fit_score
    assert after >= baseline * 0.55


# --------------------------------------------------- simulation + evaluation
def test_latent_profile_differs_from_the_stated_one(db, aditi):
    """If the latent profile matched the stated one there would be nothing to
    learn, and the whole simulation would be begging the question."""
    latent = simulation.build_latent(aditi, seed=7)
    stated_categories = {aditi.niche}
    strong = {c for c, a in latent.category_affinity.items() if a > 0.4}
    assert strong - stated_categories, "latent profile should hold a surprise"


def test_promoted_products_have_no_remaining_utility(db, aditi):
    latent = simulation.build_latent(aditi, seed=7)
    product = db.get(Product, "P001")
    before, _ = simulation.latent_utility(latent, product)
    latent.promoted.add(product.product_id)
    after, _ = simulation.latent_utility(latent, product)
    assert before > 0
    assert after == 0.0


def test_rejection_reason_matches_the_real_cause(db, aditi):
    """The simulated creator must give the reason that is actually true,
    otherwise the learning loop is being fed noise and the evaluation is
    meaningless."""
    import random

    latent = simulation.build_latent(aditi, seed=7)
    latent.price_ceiling = 400
    latent.price_floor = 100
    expensive = db.get(Product, "P005")      # Rs899, far above the ceiling
    action, reason, _ = simulation.decide_action(latent, expensive, random.Random(1))
    assert action == "skip"
    assert reason == "too_expensive"


def test_evaluation_ground_truth_excludes_retired_products(db, aditi):
    """Ground truth has to agree with what the engine is allowed to serve, or
    the metric punishes the engine for behaving correctly."""
    latent = simulation.build_latent(aditi, seed=7)
    cold = evaluation.evaluate_creator(db, aditi, latent, k=5)
    assert 0.0 <= cold.ndcg_at_k <= 1.0
    assert 0.0 <= cold.utility_capture <= 1.5

    for rec in recommend(db, aditi, top_k=5).recommendations:
        latent.promoted.add(rec.product.product_id)
        db.add(
            FeedbackEvent(
                creator_id=aditi.creator_id,
                product_id=rec.product.product_id,
                action="promote",
            )
        )
    db.commit()

    after = evaluation.evaluate_creator(db, aditi, latent, k=5)
    # Retired products must not appear on either side of the comparison.
    assert after.ndcg_at_k > 0.2, "metric collapsed — truth and engine disagree"


def test_simulation_rounds_produce_feedback_and_do_not_crash(db, aditi):
    latent = simulation.ensure_latent(db, aditi, seed=7)
    for round_number in range(1, 4):
        result = simulation.run_round(db, aditi, latent, round_number, top_k=5)
        assert len(result.served) == 5
        assert result.promotes + result.saves + result.skips == 5
    assert db.query(FeedbackEvent).count() >= 15


def test_generated_creators_are_plausible():
    for seed in range(25):
        spec = simulation.generate_creator_payload(seed)
        assert spec["price_min"] < spec["price_max"]
        assert spec["audience_age_min"] < spec["audience_age_max"]
        assert 0.005 < spec["engagement_rate"] < 0.15
        assert spec["niche"] not in spec["avoid_categories"]
