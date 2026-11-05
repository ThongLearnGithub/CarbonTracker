from datetime import datetime

from app.core.enums import VoucherStatus
from app.schemas.common import ORMModel


class VoucherRead(ORMModel):
    id: int
    title: str
    description: str
    credits: int
    status: VoucherStatus
    category: str | None = None
    rating: float
    availability: str
    redeemed_at: datetime | None = None
    redeemed_by_user_id: int | None = None
