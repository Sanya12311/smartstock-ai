"""
One-off script to create all database tables from the SQLAlchemy models —
useful for a fresh dev DB with no history yet. Since Phase 28, schema
changes to an existing database should go through Alembic instead
(`alembic revision --autogenerate -m "..."` then `alembic upgrade head`)
so they're tracked and reversible rather than requiring a manual
drop/recreate. See migrations/ and the README.

Usage (with the virtual environment activated):
    python create_tables.py
    alembic stamp head   # so Alembic knows this DB is already at the latest schema
"""

from app.database import Base, engine
from app.models import (  # noqa: F401  (import registers the models with Base)
    Alert,
    BrokerAccount,
    ChatMessage,
    ChatSession,
    Notification,
    Order,
    PaperAccount,
    PaperHolding,
    PaperOrder,
    PortfolioHolding,
    Stock,
    User,
)


def main() -> None:
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully:", list(Base.metadata.tables.keys()))


if __name__ == "__main__":
    main()
