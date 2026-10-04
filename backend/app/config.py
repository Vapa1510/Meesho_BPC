"""Runtime configuration.

Everything is environment-driven so the same code runs on SQLite (zero setup,
for the demo) and on PostgreSQL + pgvector (the production target in the deck).
"""
import os

# SQLite by default so `uvicorn app.main:app` works with no database to install.
# Set DATABASE_URL=postgresql+psycopg://user:pass@host:5432/creator_fit_db to
# switch to Postgres; nothing else in the code changes.
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./creator_fit.db")

# pgvector is only used when it is actually available. When off, semantic
# similarity falls back to a deterministic lexical overlap score, so Stage 2 of
# the pipeline behaves the same way (just less precisely).
USE_PGVECTOR: bool = os.getenv("USE_PGVECTOR", "0") == "1"
EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", "128"))

# Stage 1 of the two-stage pipeline is a hard filter. Stage 2 narrows the
# eligible pool to a candidate set before the ranker scores it.
CANDIDATE_LIMIT: int = int(os.getenv("CANDIDATE_LIMIT", "200"))
DEFAULT_TOP_K: int = int(os.getenv("DEFAULT_TOP_K", "5"))

# Minimum quality bar a product must clear to be eligible at all.
MIN_RATING: float = float(os.getenv("MIN_RATING", "3.8"))

# Model identity, surfaced in API responses so a stored recommendation can
# always be traced back to the version that produced it.
MODEL_VERSION: str = os.getenv("MODEL_VERSION", "v2-matrix-rules")

CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,https://meesho-cfe.vercel.app",
).split(",")
