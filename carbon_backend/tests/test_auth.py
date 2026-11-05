from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update

from app.models import AccessToken, User
from tests.conftest import PASSWORD


def test_signup_hashes_password_and_returns_201(client, db):
    response = client.post("/auth/signup", json={"email": "new@example.com", "full_name": "New", "password": "s3cret-pass"})

    assert response.status_code == 201
    assert response.json() == {"id": response.json()["id"], "email": "new@example.com", "full_name": "New", "role": "user"}
    stored = db.scalar(select(User).where(User.email == "new@example.com"))
    assert stored.hashed_password.startswith("$argon2")


def test_signup_rejects_duplicate_email_case_insensitively(client, user):
    response = client.post("/auth/signup", json={"email": "KHOA@example.com", "full_name": "X", "password": "s3cret-pass"})

    assert response.status_code == 409
    assert response.json() == {"detail": "Email already registered"}


def test_login_returns_working_bearer_token(client, user):
    response = client.post("/auth/login", json={"email": "khoa@example.com", "password": PASSWORD})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "khoa@example.com"


def test_login_rejects_wrong_password(client, user):
    response = client.post("/auth/login", json={"email": "khoa@example.com", "password": "nope"})

    assert response.status_code == 401


def test_email_lookup_does_not_treat_underscore_as_wildcard(client, db):
    from tests.conftest import make_user

    make_user(db, email="a_b@example.com")
    response = client.post("/auth/login", json={"email": "axb@example.com", "password": PASSWORD})

    assert response.status_code == 401


def test_me_requires_bearer_token(client):
    response = client.get("/auth/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_tokens_are_stored_hashed(client, db, user, headers):
    raw_token = headers["Authorization"].removeprefix("Bearer ")

    stored = db.scalars(select(AccessToken.token_hash)).all()
    assert raw_token not in stored
    assert len(stored) == 1 and len(stored[0]) == 64


def test_expired_token_is_rejected(client, db, headers):
    db.execute(update(AccessToken).values(expires_at=datetime.now(UTC) - timedelta(minutes=1)))
    db.commit()

    assert client.get("/auth/me", headers=headers).status_code == 401


def test_logout_revokes_token(client, headers):
    assert client.post("/auth/logout", headers=headers).status_code == 204
    assert client.get("/auth/me", headers=headers).status_code == 401
