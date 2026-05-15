"""Permission scope primitives for source allowlist enforcement."""

from cortex.permissions.provider_acl_ingestion import (
    ProviderAclFreshnessResource,
    ProviderAclFreshnessService,
    ProviderAclIngestionService,
    ProviderAclProviderCollector,
    ProviderAclRefreshResult,
    ProviderAclRefreshService,
    ProviderAclRefreshTarget,
    ProviderPrincipalMappingInput,
)
from cortex.permissions.provider_acls import (
    InMemoryProviderAclRepository,
    InMemoryProviderPrincipalMappingRepository,
    ProviderAclEntry,
    ProviderAclPrincipal,
    ProviderAclResourceRef,
    ProviderAclSnapshot,
    ProviderPrincipalMapping,
    SqlAlchemyProviderAclRepository,
    SqlAlchemyProviderPrincipalMappingRepository,
)
from cortex.permissions.scopes import InMemoryPermissionScopeRepository
from cortex.permissions.service import PermissionService

__all__ = [
    "InMemoryPermissionScopeRepository",
    "InMemoryProviderAclRepository",
    "InMemoryProviderPrincipalMappingRepository",
    "PermissionService",
    "ProviderAclEntry",
    "ProviderAclFreshnessResource",
    "ProviderAclFreshnessService",
    "ProviderAclIngestionService",
    "ProviderAclPrincipal",
    "ProviderAclProviderCollector",
    "ProviderAclRefreshResult",
    "ProviderAclRefreshService",
    "ProviderAclRefreshTarget",
    "ProviderAclResourceRef",
    "ProviderAclSnapshot",
    "ProviderPrincipalMapping",
    "ProviderPrincipalMappingInput",
    "SqlAlchemyProviderAclRepository",
    "SqlAlchemyProviderPrincipalMappingRepository",
]
