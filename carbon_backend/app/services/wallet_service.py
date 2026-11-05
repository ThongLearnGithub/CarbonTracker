from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import WalletEntryKind
from app.models import CreditWalletEntry, User
from app.schemas.wallet import WalletHistoryItem, WalletSummary


def lock_user_ledger(db: Session, user_id: int) -> None:
    """Serialise ledger writes per user (SELECT ... FOR UPDATE on the user row) until commit.

    Prevents two concurrent requests from both passing a balance check, or both creating the same day's trip.
    """
    db.execute(select(User.id).where(User.id == user_id).with_for_update())


def get_balance(db: Session, user_id: int) -> int:
    return db.scalar(
        select(func.coalesce(func.sum(CreditWalletEntry.delta), 0)).where(CreditWalletEntry.user_id == user_id)
    )


def _history_item(entry: CreditWalletEntry) -> WalletHistoryItem:
    if entry.delta >= 0:
        kind, title = WalletEntryKind.trip_earned, entry.note or "Trip earned"
    else:
        fallback = f"Redeemed - {entry.voucher.title}" if entry.voucher else "Voucher redeemed"
        kind, title = WalletEntryKind.voucher_redeemed, entry.note or fallback
    return WalletHistoryItem(kind=kind, date=entry.timestamp, title=title, amount=entry.delta)


def get_wallet_summary(db: Session, user: User, today: date | None = None) -> WalletSummary:
    today = today or date.today()
    start_of_week = today - timedelta(days=today.weekday())
    entries = db.scalars(
        select(CreditWalletEntry)
        .where(CreditWalletEntry.user_id == user.id)
        .options(selectinload(CreditWalletEntry.voucher))
    ).all()

    earned = [entry for entry in entries if entry.delta > 0]
    history = sorted(
        (_history_item(entry) for entry in entries),
        # Newest first; at the same instant, list the redemption before the earning.
        key=lambda item: (item.date, item.kind == WalletEntryKind.voucher_redeemed),
        reverse=True,
    )
    return WalletSummary(
        user_id=user.id,
        balance_credits=sum(entry.delta for entry in entries),
        credits_this_week=sum(
            entry.delta for entry in earned if start_of_week <= entry.timestamp.date() < start_of_week + timedelta(days=7)
        ),
        credits_this_month=sum(
            entry.delta for entry in earned if (entry.timestamp.year, entry.timestamp.month) == (today.year, today.month)
        ),
        history=history,
    )
