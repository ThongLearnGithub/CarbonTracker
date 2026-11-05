from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import VoucherStatus
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models import CreditWalletEntry, User, Voucher, VoucherRedemption
from app.services.wallet_service import get_balance, lock_user_ledger


def list_vouchers(db: Session) -> Sequence[Voucher]:
    return db.scalars(select(Voucher).order_by(Voucher.id)).all()


def get_voucher(db: Session, voucher_id: int, *, for_update: bool = False) -> Voucher:
    query = select(Voucher).where(Voucher.id == voucher_id)
    if for_update:
        query = query.with_for_update()
    voucher = db.scalar(query)
    if voucher is None:
        raise NotFoundError("Voucher not found")
    return voucher


def redeem_voucher(db: Session, user: User, voucher_id: int) -> Voucher:
    # Lock order (user, then voucher) is the same for every redemption, so concurrent requests cannot deadlock.
    lock_user_ledger(db, user.id)
    voucher = get_voucher(db, voucher_id, for_update=True)

    if voucher.status == VoucherStatus.expired:
        raise BusinessRuleError("Voucher expired")
    if voucher.status == VoucherStatus.redeemed:
        raise BusinessRuleError("Voucher already redeemed")
    if get_balance(db, user.id) < voucher.credits:
        raise BusinessRuleError("Not enough credits")

    redeemed_at = datetime.now().replace(microsecond=0)
    voucher.status = VoucherStatus.redeemed
    voucher.redeemed_at = redeemed_at
    voucher.redeemed_by_user_id = user.id
    db.add_all(
        [
            VoucherRedemption(voucher_id=voucher.id, user_id=user.id, redeemed_at=redeemed_at, credits=voucher.credits),
            CreditWalletEntry(
                user_id=user.id,
                voucher_id=voucher.id,
                delta=-voucher.credits,
                timestamp=redeemed_at,
                note="Voucher redeemed",
            ),
        ]
    )
    db.commit()
    return voucher
