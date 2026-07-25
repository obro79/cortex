# Phase 15 Engineering Review

## Recommendation

Build Phase 15 around one mandatory scoped context object. Do not scatter
workspace checks across handlers as ad hoc conditionals.

## Architecture Lock

Required flow:

```text
auth provider -> local user -> membership -> TenantContext -> service/repository
```

No customer-data service should accept a bare user ID or raw `workspace_id`
after Phase 15. It should accept a scoped context or a typed system/support
context with an audit reason.

## Data Isolation Checks

Add workspace scope at the lowest practical layer:

- route dependencies reject unauthorized workspace access,
- repositories require workspace predicates,
- worker jobs validate workspace ownership,
- retrieval filters before ranking and citation expansion,
- support operations require target workspace and audit reason.

The highest-risk gap is retrieval. It is easy to filter candidates and then leak
metadata during citation, source-object, related-object, or evidence-pack
hydration. Test each expansion path.

## Migration Order

1. Add tenant tables and local seed data.
2. Add `TenantContext` and factory/test helpers.
3. Update read/write repositories and services to require tenant scope.
4. Update worker job payloads.
5. Update retrieval and evidence hydration.
6. Add auth provider adapter.
7. Add onboarding, invites, workspace switch, and legal consent.
8. Disable production customer access through internal actor headers.

This order keeps isolation testable before public auth opens the surface area.

## Test Requirements

- Unit tests for tenant models, memberships, invites, legal consent, CSRF, and
  audit actor serialization.
- API tests for missing scope, wrong membership, and direct ID access.
- Worker tests for cross-workspace resource references.
- Retrieval tests for candidate filtering and citation/source hydration.
- Browser tests for signup, workspace creation, invite acceptance, workspace
  switching, CSRF failure, and logout.
- Migration tests from a pre-Phase-15 database snapshot or equivalent fixture.

## Open Decisions For Implementation

- Auth provider choice: Clerk, Auth0, Supabase Auth, or custom OIDC.
- Whether organization-level and workspace-level roles are separate in Phase 15.
- Whether account deletion is hard delete, deactivation, or anonymization under
  the retention policy.
- Whether workspace switching is stored in server session, signed cookie, or
  explicit route/API parameter resolved against membership.

These should be decided before implementation starts, but they do not block
recording the roadmap.
