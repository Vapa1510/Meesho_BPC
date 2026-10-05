"""Indirect onboarding: answers become Creator DNA, and only intent questions move intent."""
import os
import tempfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.engine import onboarding as ob
from app.seed import seed


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


def test_riya_intent_is_a_weighted_score():
    s = ob.intent_scores({"q2": "definitely", "q3": ["sells", "niche", "audience", "trending"]})
    assert round(s["trend"], 2) == 0.10 and round(s["commerce"], 2) == 0.68 and round(s["brand"], 2) == 0.22
    summary = ob.intent_summary(s)
    assert summary["primary"] == "commerce"
    assert summary["secondary"] is None                 # 0.22 < half of 0.68
    assert summary["separation"] == 0.46 and not summary["needs_follow_up"]


def test_close_call_triggers_the_follow_up_question():
    s = ob.intent_scores({"q2": "maybe", "q3": ["trending", "sells", "niche", "audience"]})
    assert ob.intent_summary(s)["needs_follow_up"]


def test_q1_and_q4_do_not_move_intent():
    base = ob.intent_scores({"q2": "definitely", "q3": ["sells", "niche", "audience", "trending"]})
    more = ob.intent_scores({"q1": ["trend_reel"], "q4": ["P003"], "q2": "definitely",
                             "q3": ["sells", "niche", "audience", "trending"]})
    assert base == more


def test_question_depth_by_scale():
    assert 5 <= len(ob.plan(6_200, has_audience_analytics=False)) <= 8
    assert 3 <= len(ob.plan(25_000)) <= 5
    assert len(ob.plan(210_000)) <= 2


def test_price_signal_from_product_picks(db):
    from app.models import Product
    products = {p.product_id: p for p in db.query(Product).all()}
    dna = ob.build_dna({"q1": ["skincare_routine", "product_review", "makeup_tutorial"],
                        "q2": "definitely", "q3": ["sells", "niche", "audience", "trending"],
                        "q4": ["P003", "P007", "P001"]}, ob.DEMO_PROFILES["riya.glows"], products)
    assert dna.preferred_price == 349 and (dna.price_min, dna.price_max) == (299, 499)
    assert dna.niche == "Skincare" and dna.niche_shares["Skincare"] == 0.7
    assert dna.content_formats == ["routine", "review", "tutorial"]
    # Growth creator with history: Q1 shapes formats, not niche; hashtags confirm the niche.
    assert dna.sources["niche"] == "Fetched: content history + hashtags"
    assert dna.sources["positioning"] == "Asked: Q4 + hashtags"
