"""The deck can no longer change, so the prototype must keep matching it.

Every number below is printed on a slide (slide numbers in comments). These
tests run the full 164-listing catalogue, exactly as deployed, and fail if any
code change moves a number a judge could check by scanning the QR codes.
"""
from __future__ import annotations

import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.engine.scoring import BASE_WEIGHTS, SATURATION_LAMBDA, SCALE_DELTA
from app.main import app
from app.seed import seed

RIYA = "C013"
DECK_ANSWERS = {
    "q1": ["skincare_routine", "product_review", "makeup_tutorial"],
    "q2": "definitely",
    "q3": ["sells", "niche", "audience", "trending"],
    "q4": ["P003", "P007", "P001"],
}


@pytest.fixture()
def client():
    path = tempfile.mktemp(suffix=".db")
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as s:
        seed(s, force=True, filler_count=140)          # the deployed catalogue: 164 listings

    def override():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()
    engine.dispose()
    try:
        os.unlink(path)
    except OSError:
        pass


def by_name(signals):
    return {s["name"]: s for s in signals}


def half_up(x: float) -> int:
    """How the app (JavaScript Math.round) and the slides round: 90.5 -> 91."""
    import math
    return int(math.floor(x + 0.5))


# ---------------------------------------------------------------- slide 7
def test_riya_is_seeded_with_her_deck_dna(client):
    c = client.get(f"/creator/{RIYA}").json()
    assert c["name"] == "Riya Kapoor" and c["followers"] == 25_000
    assert c["cell"] == "Growth × Commerce-led"
    assert c["intent_scores"] == {"trend": 10, "commerce": 68, "brand": 22}
    assert c["intent_separation"] == 0.46
    assert c["niche_shares"] == {"Skincare": 0.7, "Makeup": 0.2, "Other": 0.1}
    assert c["content_formats"] == ["routine", "review", "tutorial"]
    assert (c["preferred_price"], c["price_min"], c["price_max"]) == (349, 299, 499)
    assert c["positioning"] == {"budget": 0.47, "routine": 0.3, "mid": 0.15, "trendy": 0.08}
    assert (c["audience_age_min"], c["audience_age_max"], c["audience_tiers"]) == (18, 30, ["T2", "T3"])
    assert c["questions_asked"] == 4


def test_onboarding_riya_again_reproduces_the_seed_without_a_duplicate(client):
    before = client.get(f"/creator/{RIYA}").json()
    after = client.post("/creator/onboard", json={"handle": "riya.glows", "answers": DECK_ANSWERS, "consent": True}).json()
    assert after["creator_id"] == RIYA
    for key in ("intent_scores", "niche_shares", "positioning", "price_min", "price_max", "preferred_price", "cell"):
        assert after[key] == before[key]
    assert sum(1 for c in client.get("/creators").json() if c["name"] == "Riya Kapoor") == 1


def test_question_depth_and_top_k_by_tier(client):
    assert len(client.get("/onboarding/connect/naina.starts").json()["questions"]) == 6
    assert len(client.get("/onboarding/connect/riya.glows").json()["questions"]) == 4
    assert len(client.get("/onboarding/connect/zara.luxe").json()["questions"]) == 0
    assert client.get(f"/recommendations/{RIYA}?category=bpc").json()["top_k"] == 8     # Growth: Top 8
    assert client.get("/recommendations/C006?category=bpc").json()["top_k"] == 5        # Emerging: Starter-5
    assert client.get("/recommendations/C003?category=bpc").json()["top_k"] == 4        # Established: Top 4


def test_consent_is_required(client):
    r = client.post("/creator/onboard", json={"handle": "riya.glows", "answers": DECK_ANSWERS, "consent": False})
    assert r.status_code == 422


# ---------------------------------------------------------------- slide 8
def test_riyas_catalogue_removal(client):
    d = client.get(f"/recommendations/{RIYA}?category=bpc").json()
    p = d["pipeline"]
    removed = {k: len(v) for k, v in p["rejected_by_rule"].items()}
    assert p["catalogue_size"] == 164
    assert removed == {"price_range": 102, "stock_serviceable": 8, "quality_threshold": 13,
                       "return_rate": 10, "audience_fit": 6}
    assert p["eligible_count"] == 25
    assert len(d["recommendations"]) == 8


def test_riyas_number_one_pick(client):
    top = client.get(f"/recommendations/{RIYA}?category=bpc").json()["recommendations"][0]
    assert top["title"] == "Daily Sunscreen SPF 50" and top["price"] == 349 and top["fit_score"] == 85
    s = by_name(top["signals"])
    assert half_up(s["audience"]["score"]) == 96 and half_up(s["commerce"]["score"]) == 91
    assert half_up(s["product"]["score"]) == 95 and half_up(s["intent"]["score"]) == 85
    assert half_up(s["creator"]["score"]) == 94 and half_up(s["brand"]["score"]) == 70
    assert half_up(s["trend"]["score"]) == 63
    assert round(top["base_score"], 1) == 89.7 and round(top["penalty_saturation"], 1) == 4.6
    assert top["content_angle"] == "Proof angle: Beginner skincare routine under ₹400"
    assert top["fit_qualified"] and "Starter bonus on your first delivered order" in top["rewards"]


def test_brand_side_ceramide_moisturiser_and_the_skip(client):
    def matches():
        return {m["name"]: m for m in client.get("/product/P009/matches").json()["matches"]}

    m = matches()
    assert (m["Simran Kaur"]["fit_score"], m["Aditi Sharma"]["fit_score"],
            m["Riya Kapoor"]["fit_score"], m["Ananya Rao"]["fit_score"]) == (82, 78, 76, 66)
    assert sum(1 for x in m.values() if not x["eligible"]) == 9
    assert (m["Simran Kaur"]["est_reach"], m["Simran Kaur"]["est_orders"]) == (2052, 8)
    assert round(m["Simran Kaur"]["est_nmv"], -2) == 5000
    assert (m["Ananya Rao"]["est_orders"], round(m["Ananya Rao"]["est_nmv"], -2)) == (35, 20800)

    # The Vitamin C offer reaches Riya's inbox at 83, the same number as her feed.
    offer = client.post("/pitches", json={"product_id": "P001", "creator_id": RIYA,
                                          "message": "Would love for you to try our Vitamin C Serum."}).json()
    assert offer["brand"] == "Dewdrop Labs" and offer["fit_score"] == 83

    # Her skip of Ceramide Moisturiser: 76 -> 73, and the brand sees "Too expensive".
    r = client.post("/feedback", json={"creator_id": RIYA, "product_id": "P009", "action": "skip", "reason": "too_expensive"})
    assert r.status_code == 201
    m = matches()
    assert m["Riya Kapoor"]["fit_score"] == 73 and round(m["Riya Kapoor"]["est_nmv"], -2) == 2200
    assert client.get("/product/P009/matches").json()["feedback"]["skip_reasons"] == {"too_expensive": 1}


def test_skip_needs_a_reason(client):
    r = client.post("/feedback", json={"creator_id": RIYA, "product_id": "P009", "action": "skip"})
    assert r.status_code == 422


# ---------------------------------------------------------------- slide 18 (A5)
def test_riya_times_vitamin_c_serum(client):
    r = client.post("/rank-products", json={"creator_id": RIYA, "product_ids": ["P001"]}).json()[0]
    s = by_name(r["signals"])
    assert [s[k]["score"] for k in ("audience", "creator", "intent", "product", "commerce", "trend", "brand")] == \
        [68.3, 98.0, 87.9, 93.6, 91.8, 74.2, 85.0]
    assert [s[k]["contribution"] for k in ("audience", "creator", "intent", "product", "commerce", "trend", "brand")] == \
        [17.07, 9.8, 13.19, 14.04, 22.95, 3.71, 4.25]
    assert round(r["base_score"], 1) == 85.0 and r["penalty_saturation"] == 1.76 and r["penalty_returns"] == 0
    assert r["fit_score"] == 83


# ---------------------------------------------------------------- slides 6 + 16 (A3)
def test_nine_marking_schemes_match_a3(client):
    deck = {
        ("Emerging", "trend"): (20, 10, 15, 15, 15, 25, 0), ("Emerging", "commerce"): (25, 5, 15, 20, 30, 5, 0),
        ("Emerging", "brand"): (20, 15, 15, 20, 15, 5, 10), ("Growth", "trend"): (20, 15, 15, 10, 10, 25, 5),
        ("Growth", "commerce"): (25, 10, 15, 15, 25, 5, 5), ("Growth", "brand"): (20, 20, 15, 15, 10, 5, 15),
        ("Established", "trend"): (23, 17, 15, 5, 5, 25, 10), ("Established", "commerce"): (28, 12, 15, 10, 20, 5, 10),
        ("Established", "brand"): (23, 22, 15, 10, 5, 5, 20),
    }
    for (scale, intent), weights in deck.items():
        code = tuple(b + d for b, d in zip(BASE_WEIGHTS[intent], SCALE_DELTA[scale]))
        assert code == weights and sum(code) == 100
    assert SATURATION_LAMBDA == {"Emerging": 4.0, "Growth": 8.0, "Established": 12.0}


def test_learning_bounds_and_half_life():
    from app.engine import learning
    assert (learning.MIN_MULTIPLIER, learning.MAX_MULTIPLIER, learning.HALF_LIFE_DAYS) == (0.62, 1.15, 45.0)


# ---------------------------------------------------------------- slide 17 (A4 tables)
def test_a4_tables(client):
    aditi = client.get("/creator/C12345").json()
    assert (aditi["followers"], aditi["niche"], aditi["audience_age_min"], aditi["audience_age_max"]) == (28_000, "Skincare", 18, 24)
    assert aditi["intent_scores"] == {"trend": 78, "commerce": 86, "brand": 54}
    pooja = client.get("/creator/C006").json()
    assert (pooja["followers"], pooja["niche"], pooja["audience_age_min"], pooja["audience_age_max"]) == (6_200, "Makeup", 17, 23)
    assert pooja["intent_scores"] == {"trend": 86, "commerce": 66, "brand": 40}
    p1, p2 = client.get("/product/P001").json(), client.get("/product/P002").json()
    assert (p1["price"], p1["orders_30d"], p1["conversion_rate"], p1["trend_stage"]) == (499, 18_400, 0.048, "rising")
    assert (p2["price"], p2["orders_30d"], p2["conversion_rate"], p2["trend_stage"]) == (399, 11_200, 0.036, "rising")
    endpoints = set(client.get("/openapi.json").json()["paths"])
    assert {"/creator/{creator_id}", "/recommendations/{creator_id}", "/creator/onboard",
            "/feedback", "/product/{product_id}", "/rank-products"} <= endpoints


# ---------------------------------------------------------------- the QR codes
def test_demo_reset_returns_the_deck_state(client):
    client.post("/feedback", json={"creator_id": RIYA, "product_id": "P009", "action": "skip", "reason": "too_expensive"})
    client.patch(f"/creator/{RIYA}", json={"goal": "reach"})
    assert client.post("/demo/reset").json()["status"] == "reset"
    c = client.get(f"/creator/{RIYA}").json()
    assert c["intent_scores"] == {"trend": 10, "commerce": 68, "brand": 22}
    assert {m["name"]: m["fit_score"] for m in client.get("/product/P009/matches").json()["matches"]}["Riya Kapoor"] == 76
