"""Creator x Product Fit Engine — API entry point.

    uvicorn app.main:app --reload --port 8000

Interactive docs at /docs. The database is created and seeded on first start,
so there is nothing to run beforehand.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import CORS_ORIGINS, DATABASE_URL, MODEL_VERSION, USE_PGVECTOR
from .database import SessionLocal, init_db
from .routers import analytics, brands, creators, demo, feedback, orders, products, recommendations, simulation
from .seed import DEMO_CREATOR_ID, seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with SessionLocal() as db:
        seed(db)
    yield


app = FastAPI(
    title="Creator × Product Fit Engine",
    description=(
        "Matches BPC products to creators on seven signals (audience, niche, intent, "
        "product, commerce, trend, brand) and explains every score. Meesho DICE "
        "Season 3, Team Pro (IIT BHU). Sample data, not Meesho data."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (creators.router, products.router, recommendations.router,
               feedback.router, analytics.router, simulation.router, brands.router,
               orders.router, demo.router):
    app.include_router(router)


@app.get("/health", tags=["meta"])
def health():
    return {
        "status": "ok",
        "model_version": MODEL_VERSION,
        "database": DATABASE_URL.split("://", 1)[0],
        "pgvector": USE_PGVECTOR,
        # Said plainly so nobody mistakes the MVP for something it is not.
        "ranker": "explainable weighted rules (7 signals, 3x3 weights) + feedback adjustments",
        "retrieval": "deterministic hashed similarity (MVP); learned retrieval in production",
        "demo_creator_id": DEMO_CREATOR_ID,
    }
