from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from cortex.events.bus import EventBus
from cortex.events.in_memory import InMemoryEventBus
from cortex.ingestion.payloads import InMemoryPayloadStore, PayloadStore
from cortex.ingestion.publisher import RawEventPublisher
from cortex.ingestion.raw_events import InMemoryRawEventRepository, RawEventInput
from cortex.ingestion.service import IngestionResult, RawEventIngestionService
from cortex.platform.rate_limits import (
    RateLimitExceededError,
    RateLimitPolicy,
    RateLimitService,
    RateLimitSubject,
)
from cortex.utils.asyncio import maybe_await

from .client import (
    EmptyGitHubClient,
    GitHubClient,
    GitHubPermanentError,
    GitHubRateLimitError,
)


class GitHubIngestionService(Protocol):
    async def ingest(self, item: RawEventInput) -> IngestionResult: ...


@dataclass
class GitHubConnectorServices:
    app_configured: bool = False
    installation_token: str = ""
    # The current connector accepts one installation token per process.  Bind
    # it to an explicit workspace so a multi-tenant API cannot let the first
    # caller claim a process-global credential. Empty means live operations
    # fail closed until deployment configuration provides the binding.
    installation_workspace_id: str = ""
    client: GitHubClient = field(default_factory=EmptyGitHubClient)
    webhook_secret: str = ""
    repo_ids: set[str] = field(default_factory=set)
    repo_source_connection_ids: dict[str, str] = field(default_factory=dict)
    # These maps are deliberately scoped by workspace.  The older ``repo_ids``
    # fields remain for backwards-compatible fixture setup, but all selections
    # made through select_repos use these bindings.
    workspace_repo_ids: dict[str, set[str]] = field(default_factory=dict)
    workspace_repo_source_connection_ids: dict[tuple[str, str], str] = field(
        default_factory=dict
    )
    workspace_repo_coordinates: dict[tuple[str, str], tuple[str, str]] = field(
        default_factory=dict
    )
    # GitHub's list endpoint identifies repos numerically while the live
    # backfill payloads use ``owner/name``. Keep the canonical event ID as an
    # alias of the selected record rather than treating them as two sources.
    workspace_repo_event_ids: dict[tuple[str, str], str] = field(default_factory=dict)
    removal_callback: (
        Callable[[str, str, str | None], Awaitable[None] | None] | None
    ) = None
    sync_state: dict[tuple[str, str], dict[str, object]] = field(default_factory=dict)
    raw_events: InMemoryRawEventRepository = field(
        default_factory=InMemoryRawEventRepository
    )
    payload_store: PayloadStore = field(default_factory=InMemoryPayloadStore)
    event_bus: EventBus = field(default_factory=InMemoryEventBus)
    ingestion: GitHubIngestionService | None = None
    provider_rate_limiter: RateLimitService | None = None
    provider_rate_limit_policy: RateLimitPolicy | None = None

    def __post_init__(self) -> None:
        if self.ingestion is None:
            self.ingestion = RawEventIngestionService(
                repository=self.raw_events,
                payload_store=self.payload_store,
                publisher=RawEventPublisher(self.event_bus),
            )

    def install_app(
        self,
        *,
        workspace_id: str,
        app_id: str,
        private_key: str,
        installation_token: str = "",
    ) -> dict[str, object]:
        # App credentials are not persisted or exchanged for an installation
        # token by this in-memory service. Never advertise supplied key material
        # as live credentials until that persistence/exchange seam exists.
        if installation_token:
            self.app_configured = True
            self.installation_token = installation_token
        elif app_id or private_key:
            return {
                "ok": False,
                "workspace_id": workspace_id,
                "auth_type": "github_app",
                "app_id": app_id if app_id else None,
                "private_key_ref": "github_private_key" if private_key else None,
                "installation_token_ref": None,
                "error": "github_credential_persistence_required",
            }
        return {
            "ok": bool(self.installation_token),
            "workspace_id": workspace_id,
            "auth_type": "github_app",
            "app_id": None,
            "private_key_ref": None,
            "installation_token_ref": "github_installation_token"
            if self.installation_token
            else None,
            "error": None,
        }

    def select_repos(
        self, *, workspace_id: str, repos: list[dict[str, Any]]
    ) -> dict[str, object]:
        if self.installation_token and (
            not self.installation_workspace_id
            or self.installation_workspace_id != workspace_id
        ):
            return {
                "ok": False,
                "workspace_id": workspace_id,
                "error": "github_installation_workspace_binding_required",
            }
        selected = []
        for repo in repos:
            repo_id = str(repo.get("id", ""))
            if repo_id:
                self.repo_ids.add(repo_id)
                self.workspace_repo_ids.setdefault(workspace_id, set()).add(repo_id)
                source_connection_id = repo.get("source_connection_id")
                if isinstance(source_connection_id, str) and source_connection_id:
                    self.repo_source_connection_ids[repo_id] = source_connection_id
                    self.workspace_repo_source_connection_ids[
                        (workspace_id, repo_id)
                    ] = source_connection_id
                coordinates = _canonical_repo_coordinates(repo)
                if coordinates is not None:
                    previous_coordinates = self.workspace_repo_coordinates.get(
                        (workspace_id, repo_id)
                    )
                    if previous_coordinates is not None:
                        self.workspace_repo_event_ids.pop(
                            (workspace_id, _repository_name(*previous_coordinates)),
                            None,
                        )
                    self.workspace_repo_coordinates[(workspace_id, repo_id)] = (
                        coordinates
                    )
                    self.workspace_repo_event_ids[
                        (workspace_id, _repository_name(*coordinates))
                    ] = repo_id
                selected.append({"id": repo_id})
        return {"ok": True, "workspace_id": workspace_id, "selected": selected}

    async def remove_repo(
        self,
        *,
        workspace_id: str,
        repo_id: str,
        source_connection_id: str | None = None,
    ) -> dict[str, object]:
        """Disable one selected repository without affecting another workspace."""
        selected = self.workspace_repo_ids.get(workspace_id, set())
        expected = self.workspace_repo_source_connection_ids.get(
            (workspace_id, repo_id)
        )
        if repo_id not in selected:
            return {
                "ok": True,
                "status": "already_unselected",
                "workspace_id": workspace_id,
            }
        if source_connection_id and expected and expected != source_connection_id:
            return {
                "ok": False,
                "status": "source_mismatch",
                "workspace_id": workspace_id,
            }
        if self.removal_callback is None:
            return {
                "ok": False,
                "status": "removal_cleanup_unavailable",
                "workspace_id": workspace_id,
            }
        await maybe_await(self.removal_callback(workspace_id, repo_id, expected))
        selected.remove(repo_id)
        self.workspace_repo_source_connection_ids.pop((workspace_id, repo_id), None)
        coordinates = self.workspace_repo_coordinates.pop((workspace_id, repo_id), None)
        if coordinates is not None:
            self.workspace_repo_event_ids.pop(
                (workspace_id, _repository_name(*coordinates)), None
            )
        if expected:
            self.sync_state.pop((workspace_id, expected), None)
        return {"ok": True, "status": "removed", "workspace_id": workspace_id}

    async def backfill(
        self,
        *,
        workspace_id: str,
        source_connection_id: str,
        events: list[dict[str, Any]],
    ) -> dict[str, object]:
        created = 0
        duplicates = 0
        ingestion = self.ingestion
        assert ingestion is not None
        for event in events:
            repo_id = _repo_id(event)
            if not self._source_is_selected(
                workspace_id=workspace_id,
                repo_id=repo_id,
                source_connection_id=source_connection_id,
            ):
                continue
            event_id = _event_id(event)
            result = await ingestion.ingest(
                RawEventInput(
                    workspace_id=workspace_id,
                    source_connection_id=source_connection_id,
                    provider="github",
                    external_event_id=event_id,
                    event_type=f"github.{_event_kind(event)}",
                    external_object_key=f"github:{repo_id}:{event_id}",
                    idempotency_key=f"github:{workspace_id}:{event_id}",
                    payload=event,
                )
            )
            created += int(result.created)
            duplicates += int(not result.created)
        self._record_sync_state(
            workspace_id=workspace_id,
            source_connection_id=source_connection_id,
            status="completed",
            provenance="fixture",
        )
        return {
            "ok": True,
            "raw_events_created": created,
            "duplicates": duplicates,
            "provenance": "fixture",
        }

    async def live_backfill(
        self,
        *,
        workspace_id: str,
        source_connection_id: str,
        owner: str = "",
        repo: str = "",
        limit: int = 25,
    ) -> dict[str, object]:
        if not self.installation_token:
            return {"ok": False, "error": "github_installation_token_required"}
        coordinates = self._live_selected_repository(
            workspace_id=workspace_id,
            source_connection_id=source_connection_id,
        )
        if coordinates is None:
            return {"ok": False, "error": "github_source_not_selected"}
        if self.provider_rate_limiter and self.provider_rate_limit_policy:
            try:
                self.provider_rate_limiter.enforce(
                    self.provider_rate_limit_policy,
                    RateLimitSubject(
                        workspace_id=workspace_id,
                        user_id="provider:github",
                        client_id="github-live-backfill",
                    ),
                )
            except RateLimitExceededError as exc:
                return {
                    "ok": False,
                    "error": "rate_limited",
                    "retry_after_seconds": exc.decision.retry_after_seconds,
                }
        try:
            backfill = await self.client.backfill_repository(
                access_token=self.installation_token,
                owner=coordinates[0],
                repo=coordinates[1],
                limit=limit,
            )
        except GitHubRateLimitError:
            self._record_sync_state(
                workspace_id=workspace_id,
                source_connection_id=source_connection_id,
                status="retrying",
                error="rate_limited",
                provenance="live",
            )
            return {"ok": False, "error": "rate_limited", "provenance": "live"}
        except GitHubPermanentError:
            self._record_sync_state(
                workspace_id=workspace_id,
                source_connection_id=source_connection_id,
                status="failed",
                error="provider_error",
                provenance="live",
            )
            return {"ok": False, "error": "provider_error", "provenance": "live"}
        result = await self.backfill(
            workspace_id=workspace_id,
            source_connection_id=source_connection_id,
            events=backfill.events,
        )
        self._record_sync_state(
            workspace_id=workspace_id,
            source_connection_id=source_connection_id,
            status="completed",
            cursor=_max_event_id(backfill.events),
            provenance="live",
        )
        return {
            "ok": True,
            "fetched": len(backfill.events),
            **result,
            "provenance": "live",
        }

    async def webhook(
        self,
        *,
        workspace_id: str,
        source_connection_id: str,
        body: bytes,
        signature: str,
        event_name: str,
        delivery_id: str,
    ) -> dict[str, object]:
        if not _valid_signature(body, signature, self.webhook_secret):
            return {"ok": False, "status": "invalid_signature"}
        payload = json.loads(body)
        repo_id = _repo_id(payload)
        expected_source_connection_id = self._expected_source_connection_id(
            workspace_id=workspace_id, repo_id=repo_id
        )
        if (
            expected_source_connection_id is not None
            and expected_source_connection_id != source_connection_id
        ):
            return {"ok": True, "status": "ignored_source_mismatch"}
        if not self._source_is_selected(
            workspace_id=workspace_id,
            repo_id=repo_id,
            source_connection_id=source_connection_id,
        ):
            return {"ok": True, "status": "ignored_unselected"}
        ingestion = self.ingestion
        assert ingestion is not None
        result = await ingestion.ingest(
            RawEventInput(
                workspace_id=workspace_id,
                source_connection_id=source_connection_id,
                provider="github",
                external_event_id=delivery_id,
                event_type=f"github.{event_name}",
                external_object_key=f"github:{delivery_id}",
                idempotency_key=f"github:{workspace_id}:delivery:{delivery_id}",
                payload=payload,
            )
        )
        self._record_sync_state(
            workspace_id=workspace_id,
            source_connection_id=source_connection_id,
            status="webhook_persisted",
            cursor=delivery_id,
            provenance="live",
        )
        return {"ok": True, "status": "persisted", "raw_event_created": result.created}

    def health(self, workspace_id: str) -> dict[str, object]:
        return {
            "ok": True,
            "workspace_id": workspace_id,
            "provider": "github",
            # Setup readiness and live-token readiness are intentionally
            # distinct: an app may be configured while installation-token
            # persistence/exchange remains unavailable.
            "auth_status": "active" if self.app_configured else "missing_app",
            "selected_source_count": len(
                self.workspace_repo_ids.get(workspace_id, self.repo_ids)
            ),
            "live_credentials_configured": bool(self.installation_token),
            "sync_sources": [
                {"source_connection_id": source_id, **state}
                for (state_workspace, source_id), state in self.sync_state.items()
                if state_workspace == workspace_id
            ],
        }

    def _source_is_selected(
        self, *, workspace_id: str, repo_id: str, source_connection_id: str
    ) -> bool:
        scoped_repos = self.workspace_repo_ids.get(workspace_id)
        if scoped_repos is not None:
            selected_repo_id = self._selected_repo_id(
                workspace_id=workspace_id, repo_id=repo_id
            )
            if selected_repo_id is None:
                return False
            expected = self.workspace_repo_source_connection_ids.get(
                (workspace_id, selected_repo_id)
            )
            return expected is None or expected == source_connection_id
        if self.workspace_repo_ids:
            # Once a caller has used the workspace-scoped selection API, do not
            # let that selection authorize the same repository in another tenant.
            return False
        if self.repo_ids and repo_id not in self.repo_ids:
            return False
        expected = self.repo_source_connection_ids.get(repo_id)
        return expected is None or expected == source_connection_id

    def _expected_source_connection_id(
        self, *, workspace_id: str, repo_id: str
    ) -> str | None:
        if workspace_id in self.workspace_repo_ids:
            selected_repo_id = self._selected_repo_id(
                workspace_id=workspace_id, repo_id=repo_id
            )
            if selected_repo_id is None:
                return None
            return self.workspace_repo_source_connection_ids.get(
                (workspace_id, selected_repo_id)
            )
        return self.repo_source_connection_ids.get(repo_id)

    def _selected_repo_id(self, *, workspace_id: str, repo_id: str) -> str | None:
        scoped = self.workspace_repo_ids.get(workspace_id, set())
        if repo_id in scoped:
            return repo_id
        return self.workspace_repo_event_ids.get(
            (workspace_id, _repository_name_from_event_id(repo_id))
        )

    def _live_selected_repository(
        self, *, workspace_id: str, source_connection_id: str
    ) -> tuple[str, str] | None:
        """Return the canonical selected repository bound to this source.

        Live imports intentionally have no legacy fallback: after a restart or
        without a persisted selection, there is no authority to call GitHub.
        """
        scoped = self.workspace_repo_ids.get(workspace_id)
        if not scoped:
            return None
        matches = [
            self.workspace_repo_coordinates.get((workspace_id, repo_id))
            for repo_id in scoped
            if self.workspace_repo_source_connection_ids.get((workspace_id, repo_id))
            == source_connection_id
        ]
        verified = [coordinates for coordinates in matches if coordinates is not None]
        return verified[0] if len(verified) == 1 else None

    def _record_sync_state(
        self,
        *,
        workspace_id: str,
        source_connection_id: str,
        status: str,
        provenance: str,
        cursor: str | None = None,
        error: str | None = None,
    ) -> None:
        self.sync_state[(workspace_id, source_connection_id)] = {
            "status": status,
            "cursor": cursor,
            "last_error": error,
            "provenance": provenance,
        }


def _repo_id(event: dict[str, Any]) -> str:
    repo = event.get("repository")
    if isinstance(repo, dict) and repo.get("id"):
        return str(repo["id"])
    return str(event.get("repository_id", "unknown-repo"))


def _canonical_repo_coordinates(repo: dict[str, Any]) -> tuple[str, str] | None:
    """Extract GitHub's canonical owner/name from a selected repository."""
    full_name = repo.get("full_name")
    if isinstance(full_name, str):
        owner, separator, name = full_name.strip().partition("/")
        if separator and owner and name and "/" not in name:
            return owner, name
    owner_value = repo.get("owner")
    candidate_owner: Any = (
        owner_value.get("login") if isinstance(owner_value, dict) else owner_value
    )
    candidate_name: Any = repo.get("name")
    if (
        isinstance(candidate_owner, str)
        and candidate_owner
        and isinstance(candidate_name, str)
        and candidate_name
    ):
        return candidate_owner, candidate_name
    return None


def _repository_name(owner: str, repo: str) -> str:
    return f"{owner}/{repo}".lower()


def _repository_name_from_event_id(repo_id: str) -> str:
    return repo_id.strip().lower()


def _event_id(event: dict[str, Any]) -> str:
    for key in ("pull_request", "issue", "commit"):
        value = event.get(key)
        if isinstance(value, dict):
            return f"{key}:{value.get('id') or value.get('sha') or value.get('number')}"
    return str(event.get("id", "github-event"))


def _event_kind(event: dict[str, Any]) -> str:
    for key in ("pull_request", "issue", "commit"):
        if isinstance(event.get(key), dict):
            return key
    return str(event.get("object_kind", "event"))


def _max_event_id(events: list[dict[str, Any]]) -> str | None:
    identifiers = [_event_id(event) for event in events]
    return max(identifiers) if identifiers else None


def _valid_signature(body: bytes, signature: str, secret: str) -> bool:
    if not secret:
        return False
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
