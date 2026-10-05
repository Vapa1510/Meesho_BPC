"""Profile corrections, orders and Fit Rewards, the interleaved pilot feed, trust metrics."""
from __future__ import annotations

import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.seed import seed

RIYA = "C013"


@pytest.fixture()
def client():
    path = tempfile.mktemp(suffix=".db")
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as s:
        seed(s, force=True, filler_count=140)

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


# ------------------------------------------------------- profile corrections
def test_saving_the_profile_unchanged_keeps_her_dna(client):
    before = client.get(f"/creator/{RIYA}").json()
    after = client.patch(f"/creator/{RIYA}", json={"goal": "revenue", "price_min": 299, "price_max": 499,
                                                    "avoid_categories": []}).json()
    assert after["intent_scores"] == before["intent_scores"] == {"trend": 10, "commerce": 68, "brand": 22}
    assert after["dna_sources"]["intent"] == before["dna_sources"]["intent"]


def test_correcting_intent_swaps_scores_instead_of_overwriting(client):
    after = client.patch(f"/creator/{RIYA}", json={"goal": "reach"}).json()
    assert after["intent_scores"] == {"trend": 68, "commerce": 10, "brand": 22}
    assert after["cell"] == "Growth × Trend-led"
    assert after["dna_sources"]["intent"] == "Corrected on Profile"


def test_correcting_price_moves_the_band_and_re_ranks(client):
    before = client.get(f"/recommendations/{RIYA}?category=bpc").json()["pipeline"]["eligible_count"]
    after_c = client.patch(f"/creator/{RIYA}", json={"price_min": 400, "price_max": 900}).json()
    assert (after_c["price_min"], after_c["price_max"]) == (400, 900)
    assert after_c["dna_sources"]["price"] == "Corrected on Profile"
    after = client.get(f"/recommendations/{RIYA}?category=bpc").json()["pipeline"]["eligible_count"]
    assert after != before


# ------------------------------------------------------- orders + Fit Rewards
def test_order_needs_a_promotion_to_attribute_to(client):
    r = client.post("/orders", json={"creator_id": RIYA, "product_id": "P007", "status": "delivered"})
    assert r.status_code == 422


def test_click_order_nmv_fit_rewards(client):
    client.get(f"/recommendations/{RIYA}?category=bpc")
    client.post("/feedback", json={"creator_id": RIYA, "product_id": "P007", "action": "promote", "served_score": 85})
    rew = client.get(f"/rewards/{RIYA}").json()
    assert rew["archetype"]["name"] == "Commerce Builder" and rew["delivered_fit_orders"] == 0

    o = client.post("/orders", json={"creator_id": RIYA, "product_id": "P007", "status": "delivered"}).json()
    assert o["fit_qualified"] and o["amount"] == 349
    rew = client.get(f"/rewards/{RIYA}").json()
    assert rew["delivered_fit_orders"] == 1 and rew["fit_nmv"] == 349
    assert {e["reward"] for e in rew["earned"]} == {"Starter bonus", "Conversion bonus"}

    # Net of returns: a return takes the order back out.
    client.post("/orders", json={"creator_id": RIYA, "product_id": "P007", "status": "returned"})
    rew = client.get(f"/rewards/{RIYA}").json()
    assert rew["delivered_fit_orders"] == 0 and rew["fit_nmv"] == 0 and rew["earned"] == []


def test_rewards_only_on_fit_qualified_picks(client):
    recs = client.get(f"/recommendations/{RIYA}?category=bpc").json()["recommendations"]
    for r in recs:
        assert bool(r["rewards"]) == (r["fit_score"] >= 80)


# ------------------------------------------------------- explanations
def test_every_pick_shows_drivers_and_passed_checks(client):
    for r in client.get(f"/recommendations/{RIYA}?category=bpc").json()["recommendations"]:
        assert len(r["top_drivers"]) == 3
        assert r["eligible"] and r["blocked_by"] is None
        assert {c["rule"] for c in r["checks"]} >= {"stock_serviceable", "quality_threshold", "return_rate",
                                                     "policy_compliant", "price_range"}
        assert all(c["passed"] for c in r["checks"])


def test_catalogue_scores_say_why_a_product_is_not_served(client):
    rows = client.post("/rank-products", json={"creator_id": RIYA, "product_ids": ["P005", "P007"]}).json()
    by_id = {r["product_id"]: r for r in rows}
    assert by_id["P007"]["eligible"] and not by_id["P005"]["eligible"]
    assert by_id["P005"]["blocked_by"] == "price_range" and rows[0]["product_id"] == "P007"


# ------------------------------------------------------- pilot: interleaving
def test_interleaved_slate_mixes_sources_and_logs_them(client):
    d = client.get(f"/recommendations/{RIYA}?category=bpc&mode=interleaved").json()
    sources = [r["source"] for r in d["recommendations"]]
    assert len(sources) == 8 and set(sources) == {"personalised", "generic"}
    pick = next(r for r in d["recommendations"] if r["source"] == "personalised")
    client.post("/feedback", json={"creator_id": RIYA, "product_id": pick["product_id"], "action": "promote"})
    pilot = client.get("/analytics/pilot").json()["real"]
    assert pilot["slates"] == 1 and pilot["personalised_wins"] == 1 and pilot["win_rate"] == 1.0


def test_synthetic_interleaving_is_reported_separately(client):
    c = client.post("/simulation/generate", json={"count": 1, "seed": 3}).json()[0]
    client.post("/simulation/run", json={"creator_id": c["creator_id"], "rounds": 2, "top_k": 6, "mode": "interleaved"})
    pilot = client.get("/analytics/pilot").json()
    assert pilot["synthetic"]["slates"] == 2 and pilot["real"]["slates"] == 0


def test_fallback_fills_a_short_feed_inside_the_price_window(client):
    d = client.get(f"/recommendations/{RIYA}?category=bpc&top_k=40").json()
    fallback = [r for r in d["recommendations"] if r["source"] == "fallback"]
    assert fallback, "25 eligible products cannot fill 40 slots, so fallback must step in"
    assert all(164 <= r["price"] <= 649 for r in fallback)      # Riya's price window


# ------------------------------------------------------- trust metrics
def test_trust_metrics_cover_the_deck_targets(client):
    from app.routers.recommendations import LATENCY_MS
    LATENCY_MS.clear()
    client.get(f"/recommendations/{RIYA}?category=bpc")
    t = client.get("/analytics/trust").json()
    names = {m["metric"] for m in t["metrics"]}
    assert names == {"Explained picks", "Wrong picks", "Freshness", "Mix diversity", "Catalogue reach",
                     "Fallback coverage", "Response time (P95)", "Precision@5"}
    m = {x["metric"]: x for x in t["metrics"]}
    assert m["Explained picks"]["value"] == 1.0 and m["Freshness"]["value"] == 0.0
    assert m["Fallback coverage"]["value"] == 1.0 and m["Response time (P95)"]["value"] < 500


def test_simulations_never_touch_the_deck_creators(client):
    r = client.post("/simulation/run", json={"creator_id": RIYA, "rounds": 1})
    assert r.status_code == 409
    assert client.post(f"/simulation/reset/{RIYA}").status_code == 409
    c = client.post("/simulation/generate", json={"count": 1, "seed": 5}).json()[0]
    assert c["synthetic"]
    names = {m["creator_id"] for m in client.get("/product/P009/matches").json()["matches"]}
    assert c["creator_id"] not in names and len(names) == 13
