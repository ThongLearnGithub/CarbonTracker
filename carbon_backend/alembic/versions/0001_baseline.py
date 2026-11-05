"""Baseline: the schema the app had before Alembic (created by Base.metadata.create_all).

Tables are only created when missing, so this revision is safe to run on a database that the old
app already created. It also applies the old ad-hoc fix that turned trips.distance_km from INTEGER
into DOUBLE PRECISION.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-11-05
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_baseline"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEGACY_TABLES = [
    "credit_wallet",
    "voucher_redemptions",
    "vouchers",
    "trip_emission_factors",
    "trips",
    "emission_factors",
    "tokens",
    "users",
]


def _create_if_missing(name: str, *columns: sa.Column, indexes: Sequence[tuple[str, list[str], bool]] = ()) -> None:
    if sa.inspect(op.get_bind()).has_table(name):
        return
    op.create_table(name, *columns)
    for index_name, index_columns, unique in indexes:
        op.create_index(index_name, name, index_columns, unique=unique)


def upgrade() -> None:
    _create_if_missing(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("password", sa.String(), nullable=False),
        sa.Column("role", sa.Enum("user", "admin", "merchant", name="role"), nullable=False),
        indexes=[("ix_users_id", ["id"], False), ("ix_users_email", ["email"], True)],
    )
    _create_if_missing(
        "tokens",
        sa.Column("token", sa.String(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        indexes=[("ix_tokens_token", ["token"], False)],
    )
    _create_if_missing(
        "emission_factors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("mode", sa.String(), nullable=False, unique=True),
        sa.Column("factor", sa.Float(), nullable=False),
        indexes=[("ix_emission_factors_id", ["id"], False)],
    )
    _create_if_missing(
        "trips",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("date", sa.String(), nullable=False),
        sa.Column("distance_km", sa.Float(), nullable=False),
        sa.Column("transport_modes", sa.String(), nullable=False),
        sa.Column("credits", sa.Integer(), nullable=False),
        indexes=[("ix_trips_id", ["id"], False)],
    )
    _create_if_missing(
        "trip_emission_factors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("trip_id", sa.Integer(), sa.ForeignKey("trips.id"), nullable=False),
        sa.Column("emission_factor_id", sa.Integer(), sa.ForeignKey("emission_factors.id"), nullable=False),
        indexes=[("ix_trip_emission_factors_id", ["id"], False)],
    )
    _create_if_missing(
        "vouchers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("credits", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("rating", sa.Float(), nullable=False),
        sa.Column("availability", sa.String(), nullable=False),
        sa.Column("redeemed_at", sa.String(), nullable=True),
        sa.Column("redeemed_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        indexes=[("ix_vouchers_id", ["id"], False)],
    )
    _create_if_missing(
        "voucher_redemptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("voucher_id", sa.Integer(), sa.ForeignKey("vouchers.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("redeemed_at", sa.String(), nullable=False),
        sa.Column("credits", sa.Integer(), nullable=False),
        indexes=[("ix_voucher_redemptions_id", ["id"], False)],
    )
    _create_if_missing(
        "credit_wallet",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("trip_id", sa.Integer(), sa.ForeignKey("trips.id"), nullable=True),
        sa.Column("voucher_id", sa.Integer(), sa.ForeignKey("vouchers.id"), nullable=True),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.String(), nullable=False),
        sa.Column("note", sa.String(), nullable=True),
        indexes=[("ix_credit_wallet_id", ["id"], False)],
    )

    distance = next(c for c in sa.inspect(op.get_bind()).get_columns("trips") if c["name"] == "distance_km")
    if isinstance(distance["type"], sa.Integer):
        with op.batch_alter_table("trips") as batch:
            batch.alter_column(
                "distance_km",
                type_=sa.Float(),
                existing_nullable=False,
                postgresql_using="distance_km::double precision",
            )


def downgrade() -> None:
    for table in LEGACY_TABLES:
        op.drop_table(table)
    sa.Enum(name="role").drop(op.get_bind(), checkfirst=True)
