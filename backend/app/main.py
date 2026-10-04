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
from .routers import analytics, brands, creators, feedback, products, recommendations, simulation
from .seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with SessionLocal() as db:
        seed(db)
    yield


app = FastAPI(
    title="Creator × Product Fit Engine",
    description=(
        "Matches BPC products to creators on audience, niche, intent, product "
        "quality, commerce and trend — and explains every score."
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
               feedback.router, analytics.router, simulation.router, brands.router):
    app.include_router(router)


@app.get("/health", tags=["meta"])
def health():
    return {
        "status": "ok",
        "model_version": MODEL_VERSION,
        "database": DATABASE_URL.split("://", 1)[0],
        "pgvector": USE_PGVECTOR,
    }
