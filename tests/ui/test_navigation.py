from cortex.ui.auth import UiActorContext
from cortex.ui.navigation import (
    ADMIN_ROUTES,
    DENIED_STATE,
    confirmation_for,
    route_by_path,
    workspace_display,
)
from cortex.ui.render import render_shell


def test_admin_route_map_includes_core_customer_admin_areas() -> None:
    labels = {route.label for route in ADMIN_ROUTES}

    assert {
        "Overview",
        "Sources",
        "Connectors",
        "Evidence",
        "Decisions",
        "Jobs",
        "Team",
        "Billing",
        "Settings",
    }.issubset(labels)
    assert route_by_path("/billing").label == "Billing"  # type: ignore[union-attr]


def test_workspace_display_sorts_roles_without_session_details() -> None:
    display = workspace_display(_context())

    assert display.workspace_id == "ws_1"
    assert display.actor_id == "actor_1"
    assert display.active_roles == ("billing_admin", "workspace_admin")


def test_render_shell_uses_unified_navigation() -> None:
    html = render_shell(context=_context(), title="Overview", body="<p>Body</p>")

    assert "/ui/connectors" in html
    assert "/ui/billing" in html
    assert "aria-disabled" in html
    assert "session_1" not in html


def test_ui_state_and_confirmation_patterns_are_stable() -> None:
    confirmation = confirmation_for("revoke_connector")

    assert DENIED_STATE.kind == "denied"
    assert confirmation.requires_csrf is True
    assert confirmation.confirm_label == "Confirm"


def _context() -> UiActorContext:
    return UiActorContext(
        actor_id="actor_1",
        workspace_id="ws_1",
        roles=frozenset({"workspace_admin", "billing_admin"}),
        session_id="session_1",
        trace_id="trace_1",
        csrf_token="csrf_1",
    )
