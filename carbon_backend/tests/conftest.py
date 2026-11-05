import os

# Must be set before the app (and its settings/engine) is imported; tests never touch the real database.
os.environ["DATABASE_URL"] = "sqlite://"

from collections.abc import Iterator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.enums import Role  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import EmissionFactor, User  # noqa: E402
from app.services import auth_service  # noqa: E402
from app.services.carbon_metrics import DEFAULT_EMISSION_FACTORS  # noqa: E402

PASSWORD = "correct-horse-battery"

# SQLite in memory by default; set TEST_DATABASE_URL to a throwaway Postgres DB to exercise row locks too.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "sqlite://")
if TEST_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
else:
    engine = create_engine(TEST_DATABASE_URL)
TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _override_get_db() -> Iterator[Session]:
    with TestingSession() as db:
        yield db


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:  # runs the lifespan, i.e. loads the routing graph once
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def db() -> Iterator[Session]:
    Base.metadata.create_all(bind=engine)
    with TestingSession() as session:
        session.add_all(EmissionFactor(mode=mode, factor=factor) for mode, factor in DEFAULT_EMISSION_FACTORS.items())
        session.commit()
        yield session
    Base.metadata.drop_all(bind=engine)


def make_user(db: Session, email: str = "khoa@example.com") -> User:
    user = User(email=email, full_name="Khoa", hashed_password=hash_password(PASSWORD), role=Role.user)
    db.add(user)
    db.commit()
    return user


def auth_headers(db: Session, user: User) -> dict[str, str]:
    token, _expires_at = auth_service.issue_access_token(db, user, get_settings())
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user(db: Session) -> User:
    return make_user(db)


@pytest.fixture
def headers(db: Session, user: User) -> dict[str, str]:
    return auth_headers(db, user)
