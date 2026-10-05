"""Today's generic discovery, as the pilot's comparison arm (slide 11).

Meesho's toolkit surfaces high-converting SKUs for everyone, not fit to one
creator's audience, niche and intent (slide 3). This module reproduces that
baseline so the prototype can serve it, interleave it with personalised picks
(weeks 5-6, source hidden) and log which feed every pick came from.
"""
from __future__ import annotations

import hashlib
import random

from ..models import Creator, Product
from .eligibility import _price_window, passes_quality


def generic_ranking(catalogue: list[Product], suppressed: set[str] | None = None) -> list[Product]:
    """Best sellers for everyone: universal rules only, ranked by orders x conversion."""
    suppressed = suppressed or set()
    pool = [
        p for p in catalogue
        if p.in_stock and p.serviceable and p.policy_compliant and passes_quality(p)
        and p.product_id not in suppressed
    ]
    pool.sort(key=lambda p: (p.orders_30d * p.conversion_rate, p.nmv_30d), reverse=True)
    return pool


def fallback_pool(creator: Creator, catalogue: list[Product], exclude: set[str]) -> list[Product]:
    """Generic picks that still respect the creator's price window and exclusions.

    Used only when fewer than K products pass every gate, so a creator never
    gets an empty or short feed (slide 12: 100% fallback coverage) and never a
    product far outside what her audience pays.
    """
    lo, hi = _price_window(creator)
    avoid = {c.lower() for c in (creator.avoid_categories or [])}
    return [
        p for p in generic_ranking(catalogue, exclude)
        if lo <= p.price <= hi and p.category.lower() not in avoid
    ]


def slate_rng(creator_id: str, salt: str) -> random.Random:
    """Deterministic per creator and slate, so a refresh shows the same order."""
    h = int(hashlib.sha256(f"{creator_id}:{salt}".encode()).hexdigest()[:12], 16)
    return random.Random(h)


def team_draft(
    personalised: list[Product],
    generic: list[Product],
    k: int,
    rng: random.Random,
) -> list[tuple[Product, str]]:
    """Team-draft interleaving: each round a coin decides which feed picks first.

    Every product is credited to the feed that picked it, so creator actions can
    be scored as a match-quality win rate (personalised vs generic).
    """
    out: list[tuple[Product, str]] = []
    seen: set[str] = set()
    pointers = {"personalised": 0, "generic": 0}
    lists = {"personalised": personalised, "generic": generic}

    def take(source: str) -> bool:
        lst = lists[source]
        while pointers[source] < len(lst):
            p = lst[pointers[source]]
            pointers[source] += 1
            if p.product_id not in seen:
                seen.add(p.product_id)
                out.append((p, source))
                return True
        return False

    while len(out) < k:
        order = ["personalised", "generic"] if rng.random() < 0.5 else ["generic", "personalised"]
        progressed = False
        for source in order:
            if len(out) >= k:
                break
            progressed = take(source) or progressed
        if not progressed:
            break
    return out
