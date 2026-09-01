"""
Shared pytest fixtures.

Uses an in-memory SQLite database (never the real dev MySQL database) —
StaticPool keeps one connection alive so every session in a test sees the
same data. Tables are created fresh and dropped for every test function,
so tests never see each other's leftover data.

Background services (Dhan feed, alert/order schedulers) are patched to
no-ops before app.main is even imported, so no test ever opens a real
Dhan WebSocket connection or starts a real background loop.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

_patch_targets = [
    "app.services.dhan_feed.start",
    "app.services.dhan_feed.stop",
    "app.alerts.scheduler.start",
    "app.alerts.scheduler.stop",
    "app.services.order_scheduler.start",
    "app.services.order_scheduler.stop",
]
_active_patches = [patch(target) for target in _patch_targets]
for _p in _active_patches:
    _p.start()

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app import models as _models  # noqa: E402,F401  (import registers every model on Base.metadata)

TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def test_user(db_session):
    from app.models.user import User
    from app.utils.security import hash_password

    user = User(
        email="testuser@example.com",
        full_name="Test User",
        hashed_password=hash_password("TestPass123"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def auth_headers(client, test_user):
    response = client.post(
        "/auth/login", data={"username": test_user.email, "password": "TestPass123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def seeded_stock(db_session):
    from app.models.stock import Stock

    stock = Stock(
        symbol="TCS",
        name="Tata Consultancy Services",
        exchange_segment="NSE_EQ",
        security_id="11536",
    )
    db_session.add(stock)
    db_session.commit()
    db_session.refresh(stock)
    return stock
