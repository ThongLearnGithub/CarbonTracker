from typing import List

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
from sqlalchemy.orm import Session
from models import Voucher, RedeemRequest
from database import get_db
from orm_models import Voucher as ORMVoucher, Trip as ORMTrip, VoucherRedemption as ORMVoucherRedemption, CreditWallet as ORMCreditWallet

router = APIRouter(prefix="/vouchers", tags=["vouchers"])


@router.get("", response_model=List[Voucher])
async def list_vouchers(db: Session = Depends(get_db)):
    vs = db.query(ORMVoucher).all()
    return [
        Voucher(
            id=v.id,
            title=v.title,
            description=v.description,
            credits=v.credits,
            status=v.status,
            category=v.category,
            rating=v.rating,
            availability=v.availability,
            redeemed_at=v.redeemed_at,
            redeemed_by_user_id=v.redeemed_by_user_id,
        )
        for v in vs
    ]


@router.get("/{voucher_id}", response_model=Voucher)
async def get_voucher(voucher_id: int, db: Session = Depends(get_db)):
    v = db.query(ORMVoucher).filter(ORMVoucher.id == voucher_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Voucher not found")
    return Voucher(
        id=v.id,
        title=v.title,
        description=v.description,
        credits=v.credits,
        status=v.status,
        category=v.category,
        rating=v.rating,
        availability=v.availability,
        redeemed_at=v.redeemed_at,
        redeemed_by_user_id=v.redeemed_by_user_id,
    )


@router.post("/{voucher_id}/redeem", response_model=Voucher)
async def redeem_voucher(voucher_id: int, body: RedeemRequest, db: Session = Depends(get_db)):
    user_id = body.user_id

    v = db.query(ORMVoucher).filter(ORMVoucher.id == voucher_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Voucher not found")

    if v.status == "expired":
        raise HTTPException(status_code=400, detail="Voucher expired")
    if v.status == "redeemed":
        raise HTTPException(status_code=400, detail="Voucher already redeemed")

    balance = sum(
        entry.delta
        for entry in db.query(ORMCreditWallet).filter(ORMCreditWallet.user_id == user_id).all()
    )

    if balance < v.credits:
        raise HTTPException(status_code=400, detail="Not enough credits")

    redeemed_at = datetime.now().isoformat(timespec="seconds")
    v.status = "redeemed"
    v.redeemed_at = redeemed_at
    v.redeemed_by_user_id = user_id

    redemption = ORMVoucherRedemption(
        voucher_id=v.id,
        user_id=user_id,
        redeemed_at=redeemed_at,
        credits=v.credits,
    )
    wallet_entry = ORMCreditWallet(
        user_id=user_id,
        voucher_id=v.id,
        delta=-v.credits,
        timestamp=redeemed_at,
        note="Voucher redeemed",
    )
    db.add(v)
    db.add(redemption)
    db.add(wallet_entry)
    db.commit()
    db.refresh(v)

    return Voucher(
        id=v.id,
        title=v.title,
        description=v.description,
        credits=v.credits,
        status=v.status,
        category=v.category,
        rating=v.rating,
        availability=v.availability,
        redeemed_at=v.redeemed_at,
        redeemed_by_user_id=v.redeemed_by_user_id,
    )
