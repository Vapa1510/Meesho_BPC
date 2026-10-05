"""Indirect onboarding: turns taps, ranks and picks into Creator DNA.

Many creators cannot say whether they are trend-, commerce- or brand-led, so
the engine never asks. It asks short, indirect questions, and it only asks what
the data it already has cannot tell it:

    Emerging  (<10K)      5-8 questions   little history, so ask more
    Growth    (10K-100K)  3-5 questions   content history fills the rest
    Established (>100K)   0-2 taps        auto-built profile, creator confirms

Each question feeds exactly one kind of signal:

    Q1 posts you'd love to make   -> Content signal (formats; niche only when history is thin)
    Q2 scenario                   -> Intent
    Q3 rank what matters          -> Intent
    Q4 pick 3 products            -> Product + Price signals (preferred price, observed range, positioning)
    Q5 six-month pride (adaptive) -> Intent, only when Q2+Q3 leave the top two too close
    Q6 who asks you for advice    -> Audience, only when analytics are missing
    Q7 never show me              -> Exclusions

Intent is a weighted score, not a vote count:

    I_k = sum_q  w_q * a_qk  /  sum_q w_q          (a_q sums to 1 over k)

with w(Q2)=0.4, w(Q3)=0.6, w(Q5)=0.5. Intent separation = I_primary - I_second.
Below 0.25 (an MVP heuristic, tuned in the pilot) the engine asks Q5.
A secondary intent is kept only if it is at least half the primary.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field

INTENTS = ("trend", "commerce", "brand")
SEPARATION_MVP_THRESHOLD = 0.25
SECONDARY_RATIO = 0.5
QUESTION_WEIGHT = {"q2": 0.4, "q3": 0.6, "q5": 0.5}
RANK_POINTS = (0.4, 0.3, 0.2, 0.1)

Q1_OPTIONS = {
    "skincare_routine": {"label": "Skincare routine", "topic": "Skincare", "format": "routine", "icon": "routine"},
    "makeup_tutorial": {"label": "Makeup tutorial", "topic": "Makeup", "format": "tutorial", "icon": "tutorial"},
    "haircare_tips": {"label": "Haircare tips", "topic": "Haircare", "format": "tips", "icon": "tips"},
    "product_review": {"label": "Product review", "topic": None, "format": "review", "icon": "review"},
    "grwm": {"label": "Get ready with me", "topic": "Makeup", "format": "grwm", "icon": "grwm"},
    "trend_reel": {"label": "Trend reel", "topic": None, "format": "reel", "icon": "reel"},
}
Q2_OPTIONS = {
    "definitely": {"label": "Definitely", "profile": (0.1, 0.8, 0.1)},
    "maybe": {"label": "Maybe", "profile": (0.4, 0.4, 0.2)},
    "skip": {"label": "No, I\u2019d skip it", "profile": (0.7, 0.1, 0.2)},
}
Q3_OPTIONS = {
    "sells": {"label": "Sells consistently", "intent": "commerce"},
    "niche": {"label": "Fits my niche", "intent": "brand"},
    "audience": {"label": "Audience asks for it", "intent": "commerce"},
    "trending": {"label": "It\u2019s trending", "intent": "trend"},
}
Q4_PRODUCTS = ("P004", "P018", "P003", "P007", "P001", "P005")
Q5_OPTIONS = {
    "viral": {"label": "A video that went viral", "profile": (0.8, 0.1, 0.1)},
    "income": {"label": "Steady monthly earnings", "profile": (0.1, 0.8, 0.1)},
    "style": {"label": "Brands know my style", "profile": (0.1, 0.1, 0.8)},
}
Q6_AGES = {"18-24": (18, 24), "25-34": (25, 34), "35+": (35, 45)}

QUESTIONS = {
    "q1": {"signal": "content", "text": "Which posts would you love to make? Tap up to 3.", "options": Q1_OPTIONS},
    "q2": {"signal": "intent", "text": "A product sells well every week but isn\u2019t trending anymore. Would you still promote it?", "options": Q2_OPTIONS},
    "q3": {"signal": "intent", "text": "What matters most when you pick a product? Drag to rank.", "options": Q3_OPTIONS},
    "q4": {"signal": "product_price", "text": "Pick 3 products you\u2019d happily show your followers.", "options": list(Q4_PRODUCTS)},
    "q5": {"signal": "intent", "text": "Six months from now, which would make you proudest?", "options": Q5_OPTIONS},
    "q6": {"signal": "audience", "text": "Who asks you for product advice most?", "options": list(Q6_AGES)},
    "q7": {"signal": "exclusions", "text": "Any category you never want to see?", "options": ["Skincare", "Makeup", "Haircare", "Personal Care"]},
}


def scale_for(followers: int) -> str:
    return "Established" if followers >= 100_000 else "Growth" if followers >= 10_000 else "Emerging"


def plan(followers: int, has_audience_analytics: bool = True) -> list[str]:
    """Which questions this creator is asked, before the adaptive Q5."""
    scale = scale_for(followers)
    if scale == "Established":
        return []                                   # confirm the auto-built profile
    if scale == "Growth":
        return ["q1", "q2", "q3", "q4"]
    qs = ["q1", "q2", "q3", "q4", "q7"]
    if not has_audience_analytics:
        qs.insert(4, "q6")
    return qs


# ------------------------------------------------------------------ intent
def intent_scores(answers: dict) -> dict[str, float]:
    """Weighted score: sum_q w_q * a_qk / sum_q w_q."""
    parts: list[tuple[float, tuple[float, float, float]]] = []
    if answers.get("q2") in Q2_OPTIONS:
        parts.append((QUESTION_WEIGHT["q2"], Q2_OPTIONS[answers["q2"]]["profile"]))
    ranking = [r for r in (answers.get("q3") or []) if r in Q3_OPTIONS]
    if ranking:
        prof = {k: 0.0 for k in INTENTS}
        for pts, opt in zip(RANK_POINTS, ranking):
            prof[Q3_OPTIONS[opt]["intent"]] += pts
        total = sum(prof.values()) or 1.0
        parts.append((QUESTION_WEIGHT["q3"], tuple(prof[k] / total for k in INTENTS)))
    if answers.get("q5") in Q5_OPTIONS:
        parts.append((QUESTION_WEIGHT["q5"], Q5_OPTIONS[answers["q5"]]["profile"]))
    if answers.get("behaviour"):                      # fetched past-promotion mix, if any
        b = answers["behaviour"]
        parts.append((1.0, tuple(b.get(k, 0.0) for k in INTENTS)))
    if not parts:
        return {"trend": 1 / 3, "commerce": 1 / 3, "brand": 1 / 3}
    wsum = sum(w for w, _ in parts)
    return {k: sum(w * p[i] for w, p in parts) / wsum for i, k in enumerate(INTENTS)}


def intent_summary(scores: dict[str, float]) -> dict:
    ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    (p, pv), (s, sv) = ordered[0], ordered[1]
    separation = pv - sv
    return {
        "scores": {k: round(v, 2) for k, v in scores.items()},
        "primary": p,
        "secondary": s if sv >= SECONDARY_RATIO * pv else None,
        "separation": round(separation, 2),
        "needs_follow_up": separation < SEPARATION_MVP_THRESHOLD,
        "threshold": SEPARATION_MVP_THRESHOLD,
    }


# ------------------------------------------------------------------ hashtags
HASHTAG_TOPICS = {
    "skincare": "Skincare", "skin": "Skincare", "serum": "Skincare", "sunscreen": "Skincare",
    "makeup": "Makeup", "lip": "Makeup", "lipstick": "Makeup", "kajal": "Makeup",
    "hair": "Haircare", "haircare": "Haircare",
    "bodycare": "Personal Care", "fragrance": "Personal Care", "grooming": "Personal Care",
}
HASHTAG_POSITIONS = {
    "budget": "budget", "affordable": "budget", "cheap": "budget",
    "premium": "premium", "luxury": "premium",
    "routine": "routine", "daily": "routine",
    "glowup": "trendy", "trending": "trendy", "viral": "trendy",
}


def hashtag_signals(hashtags: list[str]) -> tuple[dict[str, float], dict[str, float]]:
    """Topic and positioning hints read from a creator's hashtags."""
    topics: dict[str, float] = {}
    positions: dict[str, float] = {}
    for raw in hashtags:
        tag = str(raw).lower().lstrip("#")
        for key, topic in HASHTAG_TOPICS.items():
            if key in tag:
                topics[topic] = topics.get(topic, 0.0) + 1.0
                break
        for key, pos in HASHTAG_POSITIONS.items():
            if key in tag:
                positions[pos] = positions.get(pos, 0.0) + 1.0
    return topics, positions


# ------------------------------------------------------------------ DNA
@dataclass
class DNA:
    scale: str
    intent: dict
    niche: str
    niche_shares: dict
    content_formats: list
    preferred_price: int | None
    price_min: int
    price_max: int
    positioning: dict
    audience_age_min: int
    audience_age_max: int
    audience_tiers: list
    avoid_categories: list
    sources: dict = field(default_factory=dict)
    questions_asked: int = 0


def build_dna(answers: dict, fetched: dict, products_by_id: dict) -> DNA:
    """Combine what was fetched with what was asked. Nothing is guessed twice."""
    from .scoring import product_positioning

    followers = int(fetched.get("followers", 0))
    scale = scale_for(followers)
    sources: dict[str, str] = {}

    # Content signal (Q1): formats always; topics only fill a thin history.
    picks1 = [o for o in (answers.get("q1") or []) if o in Q1_OPTIONS][:3]
    formats = [Q1_OPTIONS[o]["format"] for o in picks1] or list(fetched.get("formats", []))
    history = dict(fetched.get("content_history") or {})
    topic_counts: dict[str, float] = {}
    for o in picks1:
        t = Q1_OPTIONS[o]["topic"]
        if t:
            topic_counts[t] = topic_counts.get(t, 0) + 1
    q1_weight = 0.5 if scale == "Emerging" or not history else 0.0
    shares: dict[str, float] = {}
    for k, v in history.items():
        shares[k] = shares.get(k, 0.0) + (1 - q1_weight) * v
    if topic_counts and q1_weight:
        tot = sum(topic_counts.values())
        for k, v in topic_counts.items():
            shares[k] = shares.get(k, 0.0) + q1_weight * v / tot
    if not shares:
        shares = {k: v / sum(topic_counts.values()) for k, v in topic_counts.items()} or {"Skincare": 1.0}
    total = sum(shares.values())
    shares = {k: round(v / total, 2) for k, v in sorted(shares.items(), key=lambda kv: -kv[1])}
    tag_topics, tag_positions = hashtag_signals(fetched.get("hashtags") or [])
    if not history and not topic_counts and tag_topics:
        # Nothing fetched or asked about topics: fall back to the hashtags.
        tot = sum(tag_topics.values())
        shares = {k: round(v / tot, 2) for k, v in sorted(tag_topics.items(), key=lambda kv: -kv[1])}
    niche = next((k for k in shares if k != "Other"), "Skincare")
    # Every value is tagged with where it came from, and the tag says only what
    # was actually used. Hashtags are a cross-check on the niche when history
    # exists, and the source when nothing else is available.
    hashtags_agree = bool(tag_topics) and max(tag_topics, key=tag_topics.get) == niche
    if history and q1_weight and topic_counts:
        sources["niche"] = "Fetched + asked: content history + Q1"
    elif history:
        sources["niche"] = "Fetched: content history + hashtags" if hashtags_agree else "Fetched: content history"
    elif topic_counts:
        sources["niche"] = "Asked: Q1"
    elif tag_topics:
        sources["niche"] = "Fetched: hashtags"
    else:
        sources["niche"] = "Default (ask later)"
    sources["content"] = "Asked: Q1" if picks1 else "Fetched: content history"

    # Product + Price signals (Q4).
    picks4 = [products_by_id[p] for p in (answers.get("q4") or []) if p in products_by_id][:3]
    if picks4:
        prices = sorted(p.price for p in picks4)
        preferred = int(statistics.median(prices))
        lo, hi = prices[0], prices[-1]
        pos: dict[str, float] = {}
        for p in picks4:
            for k, v in product_positioning(p).items():
                pos[k] = pos.get(k, 0.0) + v / len(picks4)
        sources["price"] = "Asked: Q4 picks"
        top_pos = max(pos, key=pos.get)
        sources["positioning"] = (
            "Asked: Q4 + hashtags" if top_pos in tag_positions else "Asked: Q4 picks"
        )
    else:
        lo, hi = fetched.get("price_range", (200, 700))
        preferred = int((lo + hi) / 2)
        pos = fetched.get("positioning") or (
            {k: round(v / sum(tag_positions.values()), 2) for k, v in tag_positions.items()}
            if tag_positions else {"mid": 1.0}
        )
        sources["price"] = "Fetched: order history"
        sources["positioning"] = (
            "Fetched: order history" if fetched.get("positioning")
            else "Fetched: hashtags" if tag_positions else "Default (ask later)"
        )

    # Audience: analytics first, Q6 only when missing.
    if fetched.get("audience"):
        a = fetched["audience"]
        age_min, age_max, tiers = a["age_min"], a["age_max"], a["tiers"]
        sources["audience"] = "Fetched: audience analytics"
    elif answers.get("q6") in Q6_AGES:
        age_min, age_max = Q6_AGES[answers["q6"]]
        tiers = answers.get("q6_tiers") or ["T2", "T3"]
        sources["audience"] = "Asked: Q6"
    else:
        age_min, age_max, tiers = 18, 30, ["T2", "T3"]
        sources["audience"] = "Default (ask later)"

    intent = intent_summary(intent_scores({**answers, "behaviour": fetched.get("behaviour")}))
    asked_intent = [q.upper() for q in ("q2", "q3", "q5") if answers.get(q)]
    if asked_intent:
        sources["intent"] = "Asked: " + " + ".join(asked_intent) + (" + fetched behaviour" if fetched.get("behaviour") else "")
    elif fetched.get("behaviour"):
        sources["intent"] = "Fetched: promotion behaviour"
    else:
        sources["intent"] = "Default (ask later)"
    sources["maturity"] = "Fetched: profile"

    asked = sum(1 for q in ("q1", "q2", "q3", "q4", "q5", "q6", "q7") if answers.get(q))
    return DNA(
        scale=scale, intent=intent, niche=niche, niche_shares=shares, content_formats=formats,
        preferred_price=preferred, price_min=int(lo), price_max=int(hi),
        positioning={k: round(v, 2) for k, v in pos.items()},
        audience_age_min=age_min, audience_age_max=age_max, audience_tiers=tiers,
        avoid_categories=list(answers.get("q7") or []), sources=sources, questions_asked=asked,
    )


# ------------------------------------------------------------------ demo profiles
# What "Connect your creator profile" returns in the prototype. In production this
# comes from Meesho's creator, content and order services.
DEMO_PROFILES = {
    "riya.glows": {
        "name": "Riya Kapoor", "followers": 25_000, "city": "Varanasi", "engagement_rate": 0.04,
        "audience": {"age_min": 18, "age_max": 30, "tiers": ["T2", "T3"]},
        "content_history": {"Skincare": 0.7, "Makeup": 0.2, "Other": 0.1},
        "hashtags": ["#skincareroutine", "#budgetskincare", "#glowup"],
        "posts": 64,
    },
    "naina.starts": {
        "name": "Naina Verma", "followers": 6_200, "city": "Gaya", "engagement_rate": 0.07,
        "audience": None, "content_history": {}, "hashtags": ["#makeuplook"], "posts": 9,
    },
    "zara.luxe": {
        "name": "Zara Khan", "followers": 210_000, "city": "Lucknow", "engagement_rate": 0.035,
        "audience": {"age_min": 22, "age_max": 34, "tiers": ["T1", "T2"]},
        "content_history": {"Makeup": 0.6, "Skincare": 0.3, "Other": 0.1},
        "hashtags": ["#luxurymakeup", "#premiumbeauty"], "posts": 410,
        "behaviour": {"trend": 0.2, "commerce": 0.25, "brand": 0.55},
        "price_range": (450, 1800), "positioning": {"premium": 0.6, "mid": 0.4},
    },
}


# The three demo profiles keep one creator id each, so onboarding the same
# handle twice updates that creator instead of creating a duplicate.
HANDLE_IDS = {"riya.glows": "C013", "naina.starts": "C014", "zara.luxe": "C015"}

# Riya's answers exactly as slides 7, 8 and 18 show them. The seed builds her
# Creator DNA from these through the same code path as the onboarding screen.
DECK_ANSWERS = {
    "riya.glows": {
        "q1": ["skincare_routine", "product_review", "makeup_tutorial"],
        "q2": "definitely",
        "q3": ["sells", "niche", "audience", "trending"],
        "q4": ["P003", "P007", "P001"],
    },
}

NICHE_SUBS = {
    "Skincare": ["serum", "moisturiser", "sunscreen", "acne", "brightening", "routine"],
    "Makeup": ["lips", "eyes", "base", "kajal", "tint"],
    "Haircare": ["shampoo", "oil", "serum", "frizz"],
    "Personal Care": ["body", "fragrance", "grooming"],
}
GOAL_FOR_INTENT = {"trend": "reach", "commerce": "revenue", "brand": "brand"}
TIER_LABEL = {"Established": "Established Creator", "Growth": "Growth Creator", "Emerging": "Emerging Creator"}


def apply_dna(creator, dna: DNA, fetched: dict, handle: str | None, name: str | None = None) -> None:
    """Write a Creator DNA onto a Creator row (new or existing)."""
    scores = dna.intent["scores"]
    subs: list[str] = []
    for s in NICHE_SUBS.get(dna.niche, []) + list(dna.content_formats):
        if s not in subs:
            subs.append(s)
    creator.handle = handle
    creator.name = name or fetched.get("name", "New Creator")
    creator.tier_label = TIER_LABEL[dna.scale]
    creator.followers = int(fetched.get("followers", 0))
    creator.niche = dna.niche
    creator.sub_niches = subs
    creator.bio = " ".join(h.strip("#") for h in fetched.get("hashtags", [])) or f"{dna.niche.lower()} creator"
    creator.audience_age_min = dna.audience_age_min
    creator.audience_age_max = dna.audience_age_max
    creator.audience_tiers = dna.audience_tiers
    creator.price_min = dna.price_min
    creator.price_max = dna.price_max
    creator.goal = GOAL_FOR_INTENT[dna.intent["primary"]]
    creator.intent_trend = int(round(scores["trend"] * 100))
    creator.intent_commerce = int(round(scores["commerce"] * 100))
    creator.intent_brand = int(round(scores["brand"] * 100))
    creator.avoid_categories = dna.avoid_categories
    creator.preferred_price = dna.preferred_price
    creator.niche_shares = dna.niche_shares
    creator.content_formats = dna.content_formats
    creator.positioning = dna.positioning
    creator.secondary_intent = dna.intent["secondary"]
    creator.intent_separation = dna.intent["separation"]
    creator.dna_sources = dna.sources
    creator.questions_asked = dna.questions_asked
    creator.engagement_rate = float(fetched.get("engagement_rate", 0.04))
    creator.consented = True
