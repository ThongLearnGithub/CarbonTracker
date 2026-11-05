from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep
from app.schemas.homepage import HomePageSummary
from app.services import homepage_service

router = APIRouter(prefix="/homepage", tags=["homepage"])


@router.get("/summary", response_model=HomePageSummary)
def homepage_summary(user: CurrentUser, db: SessionDep):
    return homepage_service.get_homepage_summary(db, user)
