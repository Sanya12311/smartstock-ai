"""
One-off script to create all database tables from the SQLAlchemy models.
Run this after creating the MySQL database and setting DB_* values in .env.

Usage (with the virtual environment activated):
    python create_tables.py
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
