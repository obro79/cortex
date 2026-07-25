"""add billing persistence tables

Revision ID: 0014_billing_persistence
Revises: 0013_lifecycle_persistence
Create Date: 2026-05-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_billing_persistence"
down_revision: str | None = "0013_lifecycle_persistence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "billing_customers",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("organization_id", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("provider_customer_id", sa.String(length=256), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "organization_id",
            "provider",
            name="uq_billing_customers_organization_provider",
        ),
        sa.UniqueConstraint(
            "provider",
            "provider_customer_id",
            name="uq_billing_customers_provider_customer",
        ),
    )
    op.create_index(
        "ix_billing_customers_organization_status",
        "billing_customers",
        ["organization_id", "status"],
    )

    op.create_table(
        "billing_subscriptions",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("organization_id", sa.String(length=128), nullable=False),
        sa.Column("billing_customer_id", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("provider_subscription_id", sa.String(length=256), nullable=True),
        sa.Column("plan_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("grace_period_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "provider",
            "provider_subscription_id",
            name="uq_billing_subscriptions_provider_subscription",
        ),
    )
    op.create_index(
        "ix_billing_subscriptions_organization_status",
        "billing_subscriptions",
        ["organization_id", "status"],
    )
    op.create_index(
        "ix_billing_subscriptions_customer",
        "billing_subscriptions",
        ["billing_customer_id"],
    )

    op.create_table(
        "billing_usage_meters",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("organization_id", sa.String(length=128), nullable=False),
        sa.Column("dimension", sa.String(length=64), nullable=False),
        sa.Column("period_key", sa.String(length=128), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "organization_id",
            "dimension",
            "period_key",
            name="uq_billing_usage_meters_period",
        ),
    )
    op.create_index(
        "ix_billing_usage_meters_organization_dimension",
        "billing_usage_meters",
        ["organization_id", "dimension"],
    )

    op.create_table(
        "billing_usage_events",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("organization_id", sa.String(length=128), nullable=False),
        sa.Column("dimension", sa.String(length=64), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=256), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("source_ref", sa.String(length=256), nullable=True),
        sa.Column("period_key", sa.String(length=128), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "organization_id",
            "idempotency_key",
            name="uq_billing_usage_events_idempotency",
        ),
    )
    op.create_index(
        "ix_billing_usage_events_organization_dimension",
        "billing_usage_events",
        ["organization_id", "dimension"],
    )

    op.create_table(
        "billing_webhook_events",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("provider_event_id", sa.String(length=256), nullable=False),
        sa.Column("event_type", sa.String(length=256), nullable=False),
        sa.Column("object_id", sa.String(length=256), nullable=True),
        sa.Column("signature_status", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("provider_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload_hash", sa.String(length=128), nullable=False),
        sa.Column("api_version", sa.String(length=64), nullable=True),
        sa.Column("livemode", sa.String(length=16), nullable=True),
        sa.Column("last_error_code", sa.String(length=128), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint(
            "provider",
            "provider_event_id",
            name="uq_billing_webhook_events_provider_event",
        ),
    )
    op.create_index(
        "ix_billing_webhook_events_status",
        "billing_webhook_events",
        ["provider", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_billing_webhook_events_status",
        table_name="billing_webhook_events",
    )
    op.drop_table("billing_webhook_events")
    op.drop_index(
        "ix_billing_usage_events_organization_dimension",
        table_name="billing_usage_events",
    )
    op.drop_table("billing_usage_events")
    op.drop_index(
        "ix_billing_usage_meters_organization_dimension",
        table_name="billing_usage_meters",
    )
    op.drop_table("billing_usage_meters")
    op.drop_index(
        "ix_billing_subscriptions_customer",
        table_name="billing_subscriptions",
    )
    op.drop_index(
        "ix_billing_subscriptions_organization_status",
        table_name="billing_subscriptions",
    )
    op.drop_table("billing_subscriptions")
    op.drop_index(
        "ix_billing_customers_organization_status",
        table_name="billing_customers",
    )
    op.drop_table("billing_customers")
