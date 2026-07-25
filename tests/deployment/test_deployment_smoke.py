import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "deployment_smoke", ROOT / "scripts" / "deployment_smoke.py"
)
assert SPEC is not None
deployment_smoke = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules["deployment_smoke"] = deployment_smoke
SPEC.loader.exec_module(deployment_smoke)

main = deployment_smoke.main
smoke_commands = deployment_smoke.smoke_commands


def test_default_smoke_commands_validate_compose_and_build_images() -> None:
    commands = smoke_commands(build=True, full=False)

    assert [command.name for command in commands] == [
        "compose config",
        "compose migrate config",
        "compose lifecycle config",
        "compose provider-acl config",
        "compose build api worker",
    ]
    assert commands[0].argv == ("docker", "compose", "config")
    assert commands[1].argv == ("docker", "compose", "--profile", "migrate", "config")
    assert commands[2].argv == (
        "docker",
        "compose",
        "--profile",
        "lifecycle",
        "config",
    )
    assert commands[3].argv == (
        "docker",
        "compose",
        "--profile",
        "provider-acl",
        "config",
    )
    assert commands[4].argv == ("docker", "compose", "build", "api", "worker")


def test_full_smoke_includes_dependency_start_migration_api_and_worker() -> None:
    commands = smoke_commands(build=False, full=True)

    assert [command.name for command in commands] == [
        "compose config",
        "compose migrate config",
        "compose lifecycle config",
        "compose provider-acl config",
        "start dependencies",
        "run migrations",
        "start api and worker",
        "compose ps",
    ]


def test_smoke_list_mode_prints_commands(capsys) -> None:
    result = main(["--no-build", "--list"])

    assert result == 0
    output = capsys.readouterr().out
    assert "docker compose config" in output
    assert "docker compose --profile migrate config" in output
    assert "docker compose --profile provider-acl config" in output
    assert "docker compose build" not in output
