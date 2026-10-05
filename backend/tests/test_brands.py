"""The product side: matching, offers, listings and imagery."""
from __future__ import annotations

import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("FILLER_PRODUCTS", "40")

from app.database import Base, get_db  # noqa: E402
from app.engine import matching  # noqa: E402
from app.imagery import PACKS, pick_shape, render_svg  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Creator, Product  # noqa: E402
from app.seed import seed  # noqa: E402


@pytest.fixture()
def env():
    path = tempfile.mktemp(suffix=".db")
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as s:
        seed(s, force=True)

    def override():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override
    yield TestClient(app), Session
    app.dependency_overrides.clear()
    engine.dispose()
    try:
        os.unlink(path)
    except OSError:
        pass


def test_same_pair_same_score_both_sides(env):
    """A brand and a creator must never see two different scores for one pair."""
    client, _ = env
    creator_side = client.post(
        "/rank-products", json={"creator_id": "C12345", "product_ids": ["P001"]}
    ).json()[0]["fit_score"]
    brand_side = next(
        m["fit_score"] for m in client.get("/product/P001/matches").json()["matches"]
        if m["creator_id"] == "C12345"
    )
    assert creator_side == brand_side


def test_off_niche_creators_are_not_reachable(env):
    client, _ = env
    matches = client.get("/product/P001/matches").json()["matches"]   # a skincare serum
    by_id = {m["creator_id"]: m for m in matches}
    assert by_id["C12345"]["eligible"]
    assert not by_id["C003"]["eligible"]                               # haircare creator
    assert "niche" in by_id["C003"]["blocked_by"]
    eligible_first = [m["eligible"] for m in matches]
    assert eligible_first == sorted(eligible_first, reverse=True)


def test_price_band_blocks_and_is_reported(env):
    client, _ = env
    created = client.post("/products", json={
        "title": "Gold Luxe Serum", "brand": "Test Brand", "category": "Skincare",
        "price": 6000, "tags": ["serum", "premium"],
    })
    assert created.status_code == 201
    data = client.get(f"/product/{created.json()['product_id']}/matches").json()
    assert data["diagnosis"]["price_in_band"] < 0.5
    assert any("price" in tip for tip in data["diagnosis"]["tips"])


def test_new_listing_is_cold_start_but_scorable(env):
    client, _ = env
    p = client.post("/products", json={
        "title": "Aloe Gel", "brand": "Test Brand", "category": "Skincare", "price": 299,
    }).json()
    assert p["is_new"] and p["image"].endswith("/image.svg")
    matches = client.get(f"/product/{p['product_id']}/matches").json()["matches"]
    assert any(m["eligible"] and m["fit_score"] > 0 for m in matches)


def test_offer_lifecycle_feeds_the_ranker(env):
    client, _ = env
    sent = client.post("/pitches", json={"product_id": "P001", "creator_id": "C004"})
    assert sent.status_code == 201
    assert client.post("/pitches", json={"product_id": "P001", "creator_id": "C004"}).status_code == 409

    pid = sent.json()["id"]
    assert client.post(f"/pitches/{pid}/respond", json={"action": "decline"}).status_code == 422

    top_before = [r["product_id"] for r in client.get("/recommendations/C004?top_k=20").json()["recommendations"]]
    assert "P001" in top_before

    ok = client.post(f"/pitches/{pid}/respond", json={"action": "accept"})
    assert ok.json()["status"] == "accepted"
    assert client.post(f"/pitches/{pid}/respond", json={"action": "accept"}).status_code == 409

    # Accepting is a promote, and a promote retires the product from that creator's slate.
    after = [r["product_id"] for r in client.get("/recommendations/C004?top_k=20").json()["recommendations"]]
    assert "P001" not in after
    assert client.get("/product/P001/matches").json()["feedback"]["offers_accepted"] == 1


def test_decline_reason_reaches_the_brand(env):
    client, _ = env
    pid = client.post("/pitches", json={"product_id": "P009", "creator_id": "C004"}).json()["id"]
    client.post(f"/pitches/{pid}/respond", json={"action": "decline", "reason": "too_expensive"})
    fb = client.get("/product/P009/matches").json()["feedback"]
    assert fb["skip_reasons"] == {"too_expensive": 1}
    assert fb["offers_declined"] == 1


def test_offers_only_reach_creators_the_brand_view_lists(env):
    """The API enforces the same reachability rules the brand screen shows."""
    client, _ = env
    off_niche = client.post("/pitches", json={"product_id": "P019", "creator_id": "C006"})   # serum to a makeup creator
    assert off_niche.status_code == 422 and "not reachable" in off_niche.json()["detail"]
    out_of_band = client.post("/pitches", json={"product_id": "P019", "creator_id": "C12345"})  # ₹2,499 to a ₹200-700 band
    assert out_of_band.status_code == 422


def test_fit_rewards_on_offers_need_fit_80(env):
    client, _ = env
    # Vitamin C Serum to Aditi scores 90: a brand-funded sample is allowed.
    ok = client.post("/pitches", json={"product_id": "P001", "creator_id": "C12345", "incentive": "sample"})
    assert ok.status_code == 201 and ok.json()["incentive"] == "sample"
    # Ceramide Moisturiser to Ananya scores 66: no Fit Rewards below 80.
    low = client.post("/pitches", json={"product_id": "P009", "creator_id": "C005", "incentive": "sample"})
    assert low.status_code == 422 and "80" in low.json()["detail"]


def test_every_product_has_a_working_image(env):
    client, Session = env
    with Session() as s:
        ids = [p.product_id for p in s.query(Product).limit(30)]
    for pid in ids:
        r = client.get(f"/product/{pid}/image.svg")
        assert r.status_code == 200 and r.text.startswith("<svg")
    assert pick_shape("Vitamin C Serum") == "dropper"
    assert pick_shape("Acne Patch Pack") == "patch"
    assert pick_shape("Mystery Item", "tint") == "lipstick"
    assert pick_shape("Anything", "pack:oil") == "oil"      # a seller-chosen pack wins
    assert pick_shape("Blurring Compact", "patch") == "compact"   # seed art_key never overrides the title
    assert all(render_svg("x", "Skincare", f"pack:{k}").startswith("<svg") for k in PACKS)


def test_projection_is_plain_arithmetic():
    c = Creator(creator_id="X", name="x", niche="Skincare", followers=10_000, engagement_rate=0.05)
    p = Product(product_id="Y", title="y", category="Skincare", price=500, conversion_rate=0.04)
    reach, orders, nmv = matching.project(c, p, 80)
    assert reach == 500
    assert orders == round(500 * matching.CLICK_SHARE * 1.0 * 0.04)
    assert nmv == orders * 500


def test_concurrent_slate_requests_do_not_collide(env):
    """Two simultaneous requests for one creator used to race on the interactions row."""
    import threading

    client, _ = env
    codes: list[int] = []

    def hit():
        codes.append(client.get("/recommendations/C002?category=bpc&top_k=9").status_code)

    threads = [threading.Thread(target=hit) for _ in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert codes == [200] * 8
