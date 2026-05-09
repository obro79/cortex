# Backup and Restore Runbook

This runbook covers the durable stores Cortex needs to recover beta traffic.
Redis, Qdrant, and OpenSearch are not source-of-truth systems.

## Authorities

- Postgres stores source records, permissions, audit records, leases, jobs,
  retrieval requests, evidence packs, canonical decisions, and connector state.
- Object storage stores raw payloads and private files by durable pointer.
- Kafka stores in-flight pipeline events; after processing, durable state must be
  recoverable from Postgres and object storage.

## Postgres Backup

1. Confirm the target environment and database host.
2. Capture the migration revision with `alembic current`.
3. Run a managed snapshot or `pg_dump --format=custom`.
4. Store the dump in the approved backup bucket with environment, timestamp, and
   migration revision in the object key.
5. Record backup object key, byte size, checksum, actor, and trace or ticket ID.

## Postgres Restore

1. Restore into a new database or isolated staging database first.
2. Verify migration revision and row counts for critical tables.
3. Run app readiness against the restored database.
4. Run retrieval and context-gate smoke checks for a known fixture workspace.
5. Promote only after checks pass and the incident owner approves.

## Object Storage Restore

1. Restore representative raw payloads and private files by object key.
2. Verify checksums against the Postgres payload hash where available.
3. Confirm APIs and workers only emit payload pointers, counts, hashes, and
   statuses during restore checks.

## Smoke Command

Use the local/static smoke to verify the runbook has required commands and safe
boundaries:

```bash
python scripts/backup_restore_smoke.py --list
python scripts/backup_restore_smoke.py --static
```

Use `--full` only in a local or staging environment with disposable restore
targets configured.
