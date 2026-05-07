"""String enums that define the v1 entity lifecycle states."""

from enum import StrEnum


class RawEventStatus(StrEnum):
    RECEIVED = "received"
    PERSISTED = "persisted"
    PUBLISHED = "published"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED_RETRYABLE = "failed_retryable"
    DEADLETTERED = "deadlettered"
    DELETED = "deleted"


class SourceObjectStatus(StrEnum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    STALE = "stale"
    DELETED = "deleted"


class SourceChunkStatus(StrEnum):
    ACTIVE = "active"
    STALE = "stale"
    DELETED = "deleted"


class EmbeddingJobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    PROVIDER_RATE_LIMITED = "provider_rate_limited"
    SCHEDULED_RETRY = "scheduled_retry"
    COMPLETED = "completed"
    FAILED_RETRYABLE = "failed_retryable"
    FAILED_TERMINAL = "failed_terminal"
    DEADLETTERED = "deadlettered"
    STALE = "stale"


class IndexJobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED_RETRYABLE = "failed_retryable"
    FAILED_TERMINAL = "failed_terminal"
    DEADLETTERED = "deadlettered"
    STALE = "stale"


class EvidencePackStatus(StrEnum):
    CREATED = "created"
    CONSUMED = "consumed"
    EXPIRED = "expired"
    DELETED = "deleted"


class ContextGateStatus(StrEnum):
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"
    FAILED = "failed"


class ApprovalStatus(StrEnum):
    PROPOSED = "proposed"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    EDITED = "edited"
    REJECTED = "rejected"
    MARKED_UNRESOLVED = "marked_unresolved"
    SUPERSEDED = "superseded"


class DeletionRequestStatus(StrEnum):
    REQUESTED = "requested"
    VALIDATED = "validated"
    DELETING = "deleting"
    VERIFYING = "verifying"
    TOMBSTONED = "tombstoned"
    COMPLETED = "completed"
    FAILED_RETRYABLE = "failed_retryable"
    FAILED_TERMINAL = "failed_terminal"
    MANUAL_REPAIR = "manual_repair"


class OAuthInstallationStatus(StrEnum):
    INSTALLING = "installing"
    ACTIVE = "active"
    NEEDS_REAUTH = "needs_reauth"
    DISABLED = "disabled"
    REVOKED = "revoked"


class SecretRefStatus(StrEnum):
    ACTIVE = "active"
    ROTATING = "rotating"
    REVOKED = "revoked"


class SourceConnectionStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


class WebhookDeliveryStatus(StrEnum):
    RECEIVED = "received"
    VERIFIED = "verified"
    PERSISTED = "persisted"
    IGNORED_DUPLICATE = "ignored_duplicate"
    FAILED = "failed"
    DEADLETTERED = "deadlettered"


class BackfillJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    RETRYING = "retrying"
    FAILED = "failed"
    DEADLETTERED = "deadlettered"


class ProviderCursorStatus(StrEnum):
    ACTIVE = "active"
    STALE = "stale"
    FAILED = "failed"
    RESET_REQUESTED = "reset_requested"
