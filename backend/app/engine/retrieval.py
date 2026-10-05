"""Stage 2 of the pipeline: narrow the eligible pool to a candidate set.

MVP: candidates are ordered by a deterministic hashed bag-of-words similarity
(plus same-category and momentum terms). It is explainable and needs no model
download. USE_PGVECTOR=1 only reads the stored product vectors instead of
recomputing them; it does not run a pgvector query. Production would swap
pseudo_embedding() for a learned encoder and an ANN index (pgvector); the
function signatures stay the same.
"""
from __future__ import annotations

import hashlib
import math

from ..config import CANDIDATE_LIMIT, EMBEDDING_DIM, USE_PGVECTOR
from ..models import Creator, Product


def _tokens(*parts: object) -> set[str]:
    out: set[str] = set()
    for part in parts:
        if part is None:
            continue
        if isinstance(part, (list, tuple, set)):
            for item in part:
                out |= _tokens(item)
        else:
            out |= {t for t in str(part).lower().replace("/", " ").split() if len(t) > 2}
    return out


def pseudo_embedding(*parts: object) -> list[float]:
    """A stable hashed bag-of-words vector.

    Stands in for a sentence-transformer embedding so the vector path can be
    exercised end to end without downloading a model. Swap this one function for
    a real encoder and the rest of the retrieval code is unchanged.
    """
    vec = [0.0] * EMBEDDING_DIM
    for token in _tokens(*parts):
        h = int(hashlib.md5(token.encode()).hexdigest(), 16)
        vec[h % EMBEDDING_DIM] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def creator_vector(creator: Creator) -> list[float]:
    return pseudo_embedding(creator.niche, creator.sub_niches, creator.bio)


def product_vector(product: Product) -> list[float]:
    return pseudo_embedding(
        product.category, product.sub_category, product.tags, product.title
    )


def semantic_similarity(creator: Creator, product: Product) -> float:
    """0-1 similarity used to order candidates before ranking."""
    if USE_PGVECTOR and product.embedding:
        return max(0.0, cosine(creator_vector(creator), product.embedding))
    return max(0.0, cosine(creator_vector(creator), product_vector(product)))


def retrieve_candidates(
    creator: Creator,
    eligible: list[Product],
    limit: int = CANDIDATE_LIMIT,
) -> list[tuple[Product, float]]:
    """Return (product, similarity) ordered by relevance, capped at `limit`.

    Similarity blends semantic closeness with two cheap structural signals so a
    brand-new product with thin text still surfaces on category and momentum.
    """
    scored: list[tuple[Product, float]] = []
    for product in eligible:
        semantic = semantic_similarity(creator, product)
        same_category = 1.0 if product.category.lower() == (creator.niche or "").lower() else 0.0
        momentum = product.trend_score
        blended = 0.55 * semantic + 0.30 * same_category + 0.15 * momentum
        scored.append((product, round(blended, 4)))

    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:limit]
