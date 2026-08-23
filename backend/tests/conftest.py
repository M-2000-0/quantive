import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.database as database_module
from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite://"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


def _clear_rate_limits():
    for middleware in [app.middleware_stack]:
        pass
    try:
        from app.security.middleware import RateLimitMiddleware
        for attr_name in dir(app):
            attr = getattr(app, attr_name, None)
            if isinstance(attr, RateLimitMiddleware):
                attr._requests.clear()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    old_session = database_module.SessionLocal
    database_module.SessionLocal = TestingSessionLocal
    _clear_rate_limits()
    yield
    database_module.SessionLocal = old_session
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_client(client):
    resp = client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "testpass123",
        "name": "Test User",
        "org_name": "Test Org",
    })
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest.fixture
def sample_portfolio_data():
    return {
        "name": "Test Portfolio",
        "description": "A test portfolio",
        "instruments": [
            {
                "name": "Bond A",
                "instrument_type": "treasury_bond",
                "currency": "USD",
                "principal_outstanding": 1000000000,
                "coupon_rate": 0.045,
                "maturity_date": "2030-01-01",
                "issue_date": "2020-01-01",
                "spread_bps": 50,
            },
            {
                "name": "Bond B",
                "instrument_type": "eurobond",
                "currency": "EUR",
                "principal_outstanding": 500000000,
                "coupon_rate": 0.035,
                "maturity_date": "2028-06-15",
                "issue_date": "2018-06-15",
                "spread_bps": 120,
            },
            {
                "name": "T-Bill C",
                "instrument_type": "t_bill",
                "currency": "USD",
                "principal_outstanding": 2000000000,
                "coupon_rate": 0.025,
                "maturity_date": "2025-12-31",
                "issue_date": "2024-12-31",
                "spread_bps": 10,
            },
        ],
    }
