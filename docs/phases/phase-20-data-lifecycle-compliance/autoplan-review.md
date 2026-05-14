# Phase 20 Autoplan Review

## Verdict

Proceed as implemented trust controls, not paperwork.

## CEO Review

Mode: hold scope.

Serious customers ask what happens when they leave, delete a source, rotate a
secret, or suffer an incident. Phase 20 makes those answers real.

## Design Review

Admin UI should make lifecycle actions clear, dangerous, confirmed, and
traceable. Avoid burying destructive actions beside ordinary settings.

## Engineering Review

Deletion is the hardest part because Cortex has raw events, source objects,
chunks, embeddings, indexes, evidence, and caches. Deletion must cover derived
data or make rebuild/tombstone behavior explicit.

## Decision Log

- Lifecycle actions are asynchronous jobs with audit records.
- Derived indexes must be cleaned or rebuilt after deletion.
- SOC2 language stays "ready/control mapping" until certified.

## Approval Conditions

- Deleted content cannot be retrieved.
- Export/deletion jobs are workspace-scoped.
- Security artifacts map to implemented controls.
