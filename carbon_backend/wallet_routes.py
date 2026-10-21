from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from models import WalletSummary, WalletHistoryItem
from database import get_db
from orm_models import CreditWallet as ORMCreditWallet

router = APIRouter(prefix="/wallet", tags=["wallet"])


@router.get("/summary", response_model=WalletSummary)
async def wallet_summary(user_id: int, db: Session = Depends(get_db)):
    
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())  
    end_of_week = start_of_week + timedelta(days=7)

    entries = db.query(ORMCreditWallet).filter(ORMCreditWallet.user_id == user_id).all()
    balance = sum(entry.delta for entry in entries)

    credits_this_week = 0
    for entry in entries:
        entry_dt = datetime.fromisoformat(entry.timestamp).date()
        if entry.delta > 0 and start_of_week <= entry_dt < end_of_week:
            credits_this_week += entry.delta

     
    credits_this_month = 0
    for entry in entries:
        entry_dt = datetime.fromisoformat(entry.timestamp).date()
        if entry.delta > 0 and entry_dt.year == today.year and entry_dt.month == today.month:
            credits_this_month += entry.delta

    dt_now = datetime.now()

    history: List[WalletHistoryItem] = []
    for entry in entries:
        entry_dt = datetime.fromisoformat(entry.timestamp) if entry.timestamp else dt_now
        if entry.delta >= 0:
            title = entry.note or "Trip earned"
            kind = "trip_earned"
        else:
            title = entry.note or (f"Redeemed - {entry.voucher.title}" if entry.voucher else "Voucher redeemed")
            kind = "voucher_redeemed"
        history.append(
            WalletHistoryItem(
                kind=kind,
                date=entry_dt.isoformat(),
                title=title,
                amount=entry.delta,
            )
        )

    history.sort(
        key=lambda item: (
            datetime.fromisoformat(item.date),
            1 if item.kind == "voucher_redeemed" else 0,
        ),
        reverse=True,
    )

    return WalletSummary(
        user_id=user_id,
        balance_credits=balance,
        credits_this_week=credits_this_week,
        credits_this_month=credits_this_month,
        history=history,
    )
