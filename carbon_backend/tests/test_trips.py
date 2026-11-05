from datetime import date

import pytest
from sqlalchemy import select

from app.models import CreditWalletEntry
from tests.conftest import auth_headers, make_user


def log_trip(client, headers, **body):
    return client.post("/trips", headers=headers, json={"date": date.today().isoformat(), **body})


def test_trip_endpoints_require_authentication(client):
    assert client.get("/trips").status_code == 401
    assert client.get("/trips/stats").status_code == 401
    assert client.post("/trips", json={"distance_km": 1, "transport_modes": ["Walking"]}).status_code == 401


def test_create_trip_computes_credits_server_side(client, db, user, headers):
    # Walking: 0 kg/km vs the 0.5 kg/km baseline -> 10 km saves 5 kg -> 5 credits. Client "credits" is ignored.
    response = log_trip(client, headers, distance_km=10, transport_modes=["Walking"], credits=9999)

    assert response.status_code == 201
    body = response.json()
    assert body["credits"] == 5
    assert body["credits_earned"] == 5
    assert body["co2_saved_kg"] == 5.0
    assert body["co2_emitted_kg"] == 0.0
    assert body["user_id"] == user.id
    assert db.scalars(select(CreditWalletEntry.delta)).all() == [5]


def test_trips_on_the_same_day_are_merged(client, headers):
    log_trip(client, headers, distance_km=10, transport_modes=["Walking"])
    response = log_trip(client, headers, distance_km=4, transport_modes=["Bicycle", "Walking"])

    body = response.json()
    assert body["distance_km"] == 14
    assert body["transport_modes"] == ["Walking", "Bicycle"]
    assert body["credits"] == 5 + 2
    assert body["credits_earned"] == 2
    assert len(client.get("/trips", headers=headers).json()) == 1


def test_users_only_see_their_own_trips(client, db, headers):
    other = make_user(db, email="other@example.com")
    other_trip = log_trip(client, auth_headers(db, other), distance_km=3, transport_modes=["Walking"]).json()

    # A user_id query parameter no longer selects whose data is returned.
    assert client.get(f"/trips?user_id={other.id}", headers=headers).json() == []
    assert client.get(f"/trips/{other_trip['id']}", headers=headers).status_code == 404


@pytest.mark.parametrize(
    "body",
    [
        {"transport_modes": ["Walking"]},  # neither distance nor GPS points
        {"distance_km": 10_000, "transport_modes": ["Walking"]},  # above the sanity cap
        {"distance_km": 1, "transport_modes": []},
        {"distance_km": 1, "transport_modes": ["Teleport"]},  # no emission factor
    ],
)
def test_invalid_trips_are_rejected(client, headers, body):
    assert log_trip(client, headers, **body).status_code == 422


def test_trip_from_gps_points(client, headers):
    # ~111 m north every 30 s at walking speed, accurate fixes.
    points = [
        {"latitude": 10.77 + i * 0.001, "longitude": 106.70, "accuracy": 5, "timestamp": f"2026-01-01T08:00:{i * 10:02d}Z"}
        for i in range(4)
    ]
    response = log_trip(client, headers, gps_points=points, transport_modes=["Bicycle"])

    assert response.status_code == 201
    assert 0.25 < response.json()["distance_km"] < 0.4


def test_trip_stats(client, headers):
    log_trip(client, headers, distance_km=10, transport_modes=["Walking"])
    log_trip(client, headers, distance_km=10, transport_modes=["Petrol Car"])

    stats = client.get("/trips/stats", headers=headers).json()
    assert stats["total_trips"] == 2
    assert stats["total_distance_km"] == 20
    assert stats["total_co2_kg"] == round(10 * 0.113, 2)
    assert sum(point["trips"] for point in stats["daily"]) == 2
    assert [point["label"] for point in stats["weekly"]] == ["Week 1", "Week 2", "Week 3", "Week 4"]
