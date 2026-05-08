"""Permission scope primitives for source allowlist enforcement."""

from cortex.permissions.scopes import InMemoryPermissionScopeRepository
from cortex.permissions.service import PermissionService

__all__ = ["InMemoryPermissionScopeRepository", "PermissionService"]
