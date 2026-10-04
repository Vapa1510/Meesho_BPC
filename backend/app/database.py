"""SQLAlchemy engine / session wiring."""
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import DATABASE_URL

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from . import models  # noqa: F401  (registers the mappers)

    Base.metadata.create_all(bind=engine)
    _add_missing_columns()


def _add_missing_columns() -> None:
    """Add columns introduced after a database file was first created.

    create_all() never alters an existing table, so an older creator_fit.db
    would otherwise fail on the new product columns. Only additive changes.
    """
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    additions = {
        "products": {"brand": "VARCHAR(80)", "image_url": "TEXT"},
        "creators": {
            "preferred_price": "INTEGER", "niche_shares": "JSON", "content_formats": "JSON",
            "positioning": "JSON", "secondary_intent": "VARCHAR(16)", "intent_separation": "FLOAT",
            "dna_sources": "JSON", "questions_asked": "INTEGER", "consented": "BOOLEAN DEFAULT 1",
        },
    }
    with engine.begin() as conn:
        for table, columns in additions.items():
            if table not in inspector.get_table_names():
                continue
            existing = {c["name"] for c in inspector.get_columns(table)}
            for name, ddl in columns.items():
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
                    if name == "brand":
                        conn.execute(
                            text("UPDATE products SET brand = 'Independent Seller' WHERE brand IS NULL")
                        )
