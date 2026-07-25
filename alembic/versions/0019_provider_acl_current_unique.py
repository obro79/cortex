"""enforce one current provider ACL snapshot per resource

Revision ID: 0019_provider_acl_current_unique
Revises: 0018_permission_scopes
Create Date: 2026-07-20
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import context, op

revision: str = "0019_provider_acl_current_unique"
down_revision: str | None = "0018_permission_scopes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INDEX_NAME = "uq_provider_acl_snapshots_current_resource"
_OFFLINE_DUPLICATE_REPAIR_SQL = """
DO $$
DECLARE
    duplicate_group RECORD;
BEGIN
    FOR duplicate_group IN
        SELECT
            workspace_id,
            provider,
            resource_type,
            resource_id_hash,
            MIN(id) AS sentinel_id
        FROM provider_acl_snapshots
        WHERE is_current = TRUE
        GROUP BY workspace_id, provider, resource_type, resource_id_hash
        HAVING COUNT(*) > 1
    LOOP
        UPDATE provider_acl_snapshots
        SET is_current = FALSE
        WHERE workspace_id = duplicate_group.workspace_id
          AND provider = duplicate_group.provider
          AND resource_type = duplicate_group.resource_type
          AND resource_id_hash = duplicate_group.resource_id_hash
          AND is_current = TRUE;

        UPDATE provider_acl_snapshots
        SET is_current = TRUE,
            expires_at = CURRENT_TIMESTAMP
        WHERE id = duplicate_group.sentinel_id;
    END LOOP;
END $$
"""


def upgrade() -> None:
    """Install a partial unique current-snapshot invariant.

    A pre-existing duplicate must never be resolved by choosing an arbitrary
    allow list.  Each duplicate group is instead reduced to one intentionally
    expired sentinel snapshot, so the normal ACL evaluator rejects the
    resource until the collector writes a fresh snapshot.
    """
    if context.is_offline_mode():
        # The launch gate renders PostgreSQL DDL with ``--sql``.  Emit the
        # equivalent fail-closed repair block rather than trying to execute
        # against Alembic's offline mock connection.
        op.execute(sa.text(_OFFLINE_DUPLICATE_REPAIR_SQL))
    else:
        bind = op.get_bind()
        snapshots = sa.table(
            "provider_acl_snapshots",
            sa.column("id", sa.String()),
            sa.column("workspace_id", sa.String()),
            sa.column("provider", sa.String()),
            sa.column("resource_type", sa.String()),
            sa.column("resource_id_hash", sa.String()),
            sa.column("is_current", sa.Boolean()),
            sa.column("expires_at", sa.DateTime(timezone=True)),
        )
        key_columns = (
            snapshots.c.workspace_id,
            snapshots.c.provider,
            snapshots.c.resource_type,
            snapshots.c.resource_id_hash,
        )
        duplicate_groups = list(
            bind.execute(
                sa.select(
                    *key_columns,
                    sa.func.min(snapshots.c.id).label("sentinel_id"),
                )
                .where(snapshots.c.is_current.is_(True))
                .group_by(*key_columns)
                .having(sa.func.count() > 1)
            ).mappings()
        )
        expired_at = datetime.now(UTC)
        for group in duplicate_groups:
            predicate = sa.and_(
                snapshots.c.workspace_id == group["workspace_id"],
                snapshots.c.provider == group["provider"],
                snapshots.c.resource_type == group["resource_type"],
                snapshots.c.resource_id_hash == group["resource_id_hash"],
                snapshots.c.is_current.is_(True),
            )
            bind.execute(sa.update(snapshots).where(predicate).values(is_current=False))
            bind.execute(
                sa.update(snapshots)
                .where(snapshots.c.id == group["sentinel_id"])
                .values(is_current=True, expires_at=expired_at)
            )

    op.create_index(
        _INDEX_NAME,
        "provider_acl_snapshots",
        ["workspace_id", "provider", "resource_type", "resource_id_hash"],
        unique=True,
        postgresql_where=sa.text("is_current"),
        sqlite_where=sa.text("is_current = 1"),
    )


def downgrade() -> None:
    op.drop_index(_INDEX_NAME, table_name="provider_acl_snapshots")
