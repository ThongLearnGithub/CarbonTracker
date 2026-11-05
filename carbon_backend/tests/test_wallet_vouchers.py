from datetime import date

import pytest
from sqlalchemy import select

from app.core.enums import VoucherStatus
from app.models import CreditWalletEntry, Voucher


@pytest.fixture
def voucher(db):
    voucher = Voucher(
        title="Free Bus Ticket",
        description="One-day ticket",
        credits=4,
        status=VoucherStatus.pending,
        category="transport",
        rating=4.8,
        availability="7 days left",
    )
    db.add(voucher)
    db.commit()
    return voucher


def earn(client, headers, km):
    client.post("/trips", headers=headers, json={"date": date.today().isoformat(), "distance_km": km, "transport_modes": ["Walking"]})


def test_voucher_list_is_public(client, voucher):
    response = client.get("/vouchers")

    assert response.status_code == 200
    assert response.json()[0]["title"] == "Free Bus Ticket"
    assert response.json()[0]["status"] == "pending"


def test_redeem_requires_authentication(client, voucher):
    assert client.post(f"/vouchers/{voucher.id}/redeem", json={"user_id": 1}).status_code == 401


def test_redeem_without_enough_credits(client, db, headers, voucher):
    response = client.post(f"/vouchers/{voucher.id}/redeem", headers=headers)

    assert response.status_code == 400
    assert response.json() == {"detail": "Not enough credits"}
    assert db.scalars(select(CreditWalletEntry)).all() == []


def test_redeem_spends_credits_once(client, headers, voucher):
    earn(client, headers, km=10)  # 5 credits

    response = client.post(f"/vouchers/{voucher.id}/redeem", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "redeemed"

    wallet = client.get("/wallet/summary", headers=headers).json()
    assert wallet["balance_credits"] == 1
    assert wallet["credits_this_month"] == 5
    assert [item["kind"] for item in wallet["history"]] == ["voucher_redeemed", "trip_earned"]
    assert wallet["history"][0]["amount"] == -4

    again = client.post(f"/vouchers/{voucher.id}/redeem", headers=headers)
    assert again.status_code == 400
    assert again.json() == {"detail": "Voucher already redeemed"}


def test_homepage_balance_matches_wallet_after_redeeming(client, headers, voucher):
    earn(client, headers, km=10)
    client.post(f"/vouchers/{voucher.id}/redeem", headers=headers)

    home = client.get("/homepage/summary", headers=headers).json()
    wallet = client.get("/wallet/summary", headers=headers).json()
    assert home["balance_credits"] == wallet["balance_credits"] == 1
    assert home["credits_this_week"] == 5
    assert home["distance_km"] == 10
    assert home["co2_saved_kg"] == 5.0
