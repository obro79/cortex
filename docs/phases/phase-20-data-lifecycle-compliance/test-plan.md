# Phase 20 Test Plan

- Workspace deletion removes or tombstones retrievable data.
- Source deletion removes source objects, chunks, files, embeddings, indexes, and
  derived evidence as required.
- User deletion/deactivation preserves required audit/legal records.
- Retention sweep respects policy and workspace scope.
- Export job includes expected workspace data and excludes other workspaces.
- Deletion jobs are idempotent and resumable.
- Derived indexes no longer return deleted content.
- Secret rotation invalidates old secrets.
- Abuse/rate-limit tests cover public routes and expensive jobs.
- Incident runbook tabletop evidence recorded.
