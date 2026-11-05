from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep
from app.schemas.voucher import VoucherRead
from app.services import voucher_service

router = APIRouter(prefix="/vouchers", tags=["vouchers"])


@router.get("", response_model=list[VoucherRead])
def list_vouchers(db: SessionDep):
    return voucher_service.list_vouchers(db)


@router.get("/{voucher_id}", response_model=VoucherRead)
def get_voucher(voucher_id: int, db: SessionDep):
    return voucher_service.get_voucher(db, voucher_id)


@router.post("/{voucher_id}/redeem", response_model=VoucherRead)
def redeem_voucher(voucher_id: int, user: CurrentUser, db: SessionDep):
    return voucher_service.redeem_voucher(db, user, voucher_id)
