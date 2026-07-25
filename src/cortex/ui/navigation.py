from __future__ import annotations

from dataclasses import dataclass

from cortex.ui.auth import UiActorContext


@dataclass(frozen=True)
class AdminRoute:
    path: str
    label: str
    section: str
    implemented: bool = True
    requires_confirmation: bool = False


@dataclass(frozen=True)
class WorkspaceDisplay:
    workspace_id: str
    actor_id: str
    active_roles: tuple[str, ...]


@dataclass(frozen=True)
class UiState:
    kind: str
    title: str
    detail: str


@dataclass(frozen=True)
class ConfirmationPattern:
    action: str
    title: str
    confirm_label: str
    requires_csrf: bool = True


ADMIN_ROUTES: tuple[AdminRoute, ...] = (
    AdminRoute("/", "Overview", "operations"),
    AdminRoute("/sources", "Sources", "sources"),
    AdminRoute("/connectors", "Connectors", "sources"),
    AdminRoute("/evidence", "Evidence", "retrieval", implemented=False),
    AdminRoute("/decisions", "Decisions", "retrieval", implemented=False),
    AdminRoute("/jobs", "Jobs", "operations", implemented=False),
    AdminRoute("/team", "Team", "admin", implemented=False),
    AdminRoute("/billing", "Billing", "admin", implemented=False),
    AdminRoute("/settings", "Settings", "admin", implemented=False),
)

EMPTY_STATE = UiState(
    kind="empty",
    title="No records",
    detail="Nothing is available for this workspace yet.",
)
LOADING_STATE = UiState(
    kind="loading",
    title="Loading",
    detail="Workspace data is loading.",
)
ERROR_STATE = UiState(
    kind="error",
    title="Unable to load",
    detail="The requested workspace view could not be loaded.",
)
DENIED_STATE = UiState(
    kind="denied",
    title="Access denied",
    detail="This actor cannot view or change this workspace area.",
)


def workspace_display(context: UiActorContext) -> WorkspaceDisplay:
    return WorkspaceDisplay(
        workspace_id=context.workspace_id,
        actor_id=context.actor_id,
        active_roles=tuple(sorted(context.roles)),
    )


def route_by_path(path: str) -> AdminRoute | None:
    normalized = "/" + path.strip("/")
    if normalized == "/":
        return ADMIN_ROUTES[0]
    return next((route for route in ADMIN_ROUTES if route.path == normalized), None)


def confirmation_for(action: str) -> ConfirmationPattern:
    return ConfirmationPattern(
        action=action,
        title=f"Confirm {action.replace('_', ' ')}",
        confirm_label="Confirm",
    )
