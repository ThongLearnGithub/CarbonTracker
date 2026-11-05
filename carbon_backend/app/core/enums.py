from enum import StrEnum


class Role(StrEnum):
    user = "user"
    admin = "admin"
    merchant = "merchant"


class VoucherStatus(StrEnum):
    pending = "pending"
    redeemed = "redeemed"
    expired = "expired"


class WalletEntryKind(StrEnum):
    trip_earned = "trip_earned"
    voucher_redeemed = "voucher_redeemed"
