"""Hash passwords and tokens, add token expiry, store dates as DATE/TIMESTAMP, add lookup indexes.

- users.password (plaintext) -> users.hashed_password (Argon2id). Already-hashed values are left alone.
- tokens (plaintext, no expiry) -> access_tokens (SHA-256 digest + created_at/expires_at).
  Existing sessions stay valid for 7 days.
- trips.date, credit_wallet.timestamp, vouchers.redeemed_at, voucher_redemptions.redeemed_at:
  ISO-8601 strings -> DATE / TIMESTAMP (wall-clock local time, as before).

Revision ID: 0002_secure_auth_typed_dates
Revises: 0001_baseline
Create Date: 2026-11-05
"""
import hashlib
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import sqlalchemy as sa
from alembic import op
from pwdlib import PasswordHash

revision: str = "0002_secure_auth_typed_dates"
down_revision: str | Sequence[str] | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEGACY_SESSION_TTL = timedelta(days=7)


def _hash_passwords() -> None:
    bind = op.get_bind()
    hasher = PasswordHash.recommended()
    users = sa.table("users", sa.column("id", sa.Integer), sa.column("hashed_password", sa.String))
    for user_id, password in bind.execute(sa.select(users.c.id, users.c.hashed_password)).all():
        if not password.startswith("$argon2"):
            bind.execute(users.update().where(users.c.id == user_id).values(hashed_password=hasher.hash(password)))


def _migrate_tokens() -> None:
    access_tokens = op.create_table(
        "access_tokens",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_access_tokens_user_id", "access_tokens", ["user_id"])
    op.create_index("ix_access_tokens_expires_at", "access_tokens", ["expires_at"])

    bind = op.get_bind()
    now = datetime.now(UTC)
    legacy = sa.table("tokens", sa.column("token", sa.String), sa.column("user_id", sa.Integer))
    rows = [
        {
            "token_hash": hashlib.sha256(token.encode("utf-8")).hexdigest(),
            "user_id": user_id,
            "created_at": now,
            "expires_at": now + LEGACY_SESSION_TTL,
        }
        for token, user_id in bind.execute(sa.select(legacy.c.token, legacy.c.user_id)).all()
    ]
    if rows:
        op.bulk_insert(access_tokens, rows)
    op.drop_table("tokens")


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.alter_column("password", new_column_name="hashed_password", existing_type=sa.String(), existing_nullable=False)
    _hash_passwords()
    _migrate_tokens()

    with op.batch_alter_table("trips") as batch:
        batch.alter_column("date", type_=sa.Date(), existing_nullable=False, postgresql_using="date::date")
        batch.create_index("ix_trips_user_id_date", ["user_id", "date"])

    with op.batch_alter_table("credit_wallet") as batch:
        batch.alter_column(
            "timestamp",
            type_=sa.DateTime(),
            existing_nullable=False,
            postgresql_using='"timestamp"::timestamp without time zone',
        )
        batch.create_index("ix_credit_wallet_user_id", ["user_id"])

    with op.batch_alter_table("vouchers") as batch:
        batch.alter_column(
            "redeemed_at",
            type_=sa.DateTime(),
            existing_nullable=True,
            postgresql_using="NULLIF(redeemed_at, '')::timestamp without time zone",
        )
        batch.alter_column("status", type_=sa.String(20), existing_nullable=False)

    with op.batch_alter_table("voucher_redemptions") as batch:
        batch.alter_column(
            "redeemed_at",
            type_=sa.DateTime(),
            existing_nullable=False,
            postgresql_using="redeemed_at::timestamp without time zone",
        )


def downgrade() -> None:
    # Hashed passwords and tokens cannot be reversed: every user must sign in again after a downgrade,
    # and password logins only work for accounts whose password is reset.
    with op.batch_alter_table("voucher_redemptions") as batch:
        batch.alter_column("redeemed_at", type_=sa.String(), existing_nullable=False,
                           postgresql_using="to_char(redeemed_at, 'YYYY-MM-DD\"T\"HH24:MI:SS')")
    with op.batch_alter_table("vouchers") as batch:
        batch.alter_column("status", type_=sa.String(), existing_nullable=False)
        batch.alter_column("redeemed_at", type_=sa.String(), existing_nullable=True,
                           postgresql_using="to_char(redeemed_at, 'YYYY-MM-DD\"T\"HH24:MI:SS')")
    with op.batch_alter_table("credit_wallet") as batch:
        batch.drop_index("ix_credit_wallet_user_id")
        batch.alter_column("timestamp", type_=sa.String(), existing_nullable=False,
                           postgresql_using="to_char(\"timestamp\", 'YYYY-MM-DD\"T\"HH24:MI:SS')")
    with op.batch_alter_table("trips") as batch:
        batch.drop_index("ix_trips_user_id_date")
        batch.alter_column("date", type_=sa.String(), existing_nullable=False,
                           postgresql_using="to_char(date, 'YYYY-MM-DD')")

    op.drop_table("access_tokens")
    op.create_table(
        "tokens",
        sa.Column("token", sa.String(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
    )
    op.create_index("ix_tokens_token", "tokens", ["token"])
    with op.batch_alter_table("users") as batch:
        batch.alter_column("hashed_password", new_column_name="password", existing_type=sa.String(), existing_nullable=False)
