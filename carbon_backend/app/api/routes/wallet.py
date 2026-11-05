from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep
from app.schemas.wallet import WalletSummary
from app.services import wallet_service

router = APIRouter(prefix="/wallet", tags=["wallet"])


@router.get("/summary", response_model=WalletSummary)
def wallet_summary(user: CurrentUser, db: SessionDep):
    return wallet_service.get_wallet_summary(db, user)
