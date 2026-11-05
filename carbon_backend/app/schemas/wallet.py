from datetime import datetime

from pydantic import BaseModel

from app.core.enums import WalletEntryKind


class WalletHistoryItem(BaseModel):
    kind: WalletEntryKind
    date: datetime
    title: str
    amount: int


class WalletSummary(BaseModel):
    user_id: int
    balance_credits: int
    credits_this_week: int
    credits_this_month: int
    history: list[WalletHistoryItem]

