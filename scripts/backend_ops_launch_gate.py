from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class GateCommand:
    name: str
    argv: tuple[str, ...]


def gate_commands() -> list[GateCommand]:
    return [
        GateCommand("ruff", ("uv", "run", "ruff", "check", ".")),
        GateCommand("ruff format", ("uv", "run", "ruff", "format", "--check", ".")),
        GateCommand("mypy", ("uv", "run", "mypy", "src")),
        GateCommand(
            "focused backend tests",
            (
                "uv",
                "run",
                "pytest",
                "tests/billing",
                "tests/lifecycle",
                "tests/permissions",
                "tests/deployment",
                "tests/smoke/test_worker.py",
                "tests/workers/test_provider_acl_worker.py",
            ),
        ),
        GateCommand("compose config", ("docker", "compose", "config")),
        GateCommand(
            "compose lifecycle config",
            ("docker", "compose", "--profile", "lifecycle", "config"),
        ),
        GateCommand(
            "compose provider-acl config",
            ("docker", "compose", "--profile", "provider-acl", "config"),
        ),
        GateCommand("alembic heads", ("uv", "run", "alembic", "heads")),
        GateCommand(
            "alembic upgrade sql",
            ("uv", "run", "alembic", "upgrade", "head", "--sql"),
        ),
        GateCommand(
            "alembic downgrade sql",
            (
                "uv",
                "run",
                "alembic",
                "downgrade",
                "0016_provider_principal_mappings:0013_lifecycle_persistence",
                "--sql",
            ),
        ),
        GateCommand(
            "backup restore static smoke",
            ("uv", "run", "python", "scripts/backup_restore_smoke.py", "--static"),
        ),
        GateCommand(
            "derived index static smoke",
            (
                "uv",
                "run",
                "python",
                "scripts/derived_index_rebuild_smoke.py",
                "--static",
            ),
        ),
        GateCommand(
            "stripe activation static smoke",
            (
                "uv",
                "run",
                "python",
                "scripts/stripe_activation_smoke.py",
                "--static",
                "--fake-gateway",
            ),
        ),
    ]


def run_command(command: GateCommand) -> str:
    print(f"==> {command.name}", flush=True)
    completed = subprocess.run(
        command.argv,
        check=False,
        capture_output=True,
        text=True,
    )
    output = "\n".join(
        part for part in (completed.stdout.strip(), completed.stderr.strip()) if part
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"{command.name} failed with exit code {completed.returncode}\n{output}"
        )
    return output


def write_evidence(
    *,
    path: Path,
    results: list[tuple[GateCommand, str]],
    status: str,
) -> None:
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%SZ")
    lines = [
        "# Backend Ops Launch Gate Local Evidence",
        "",
        f"Date: {now}",
        "Environment: local",
        "Owner: Codex",
        "Status: not staging evidence",
        "",
        "This evidence records no-secret local backend and operations gate checks.",
        "It does not replace staging or live Stripe/provider drill evidence.",
        "",
        "## Result",
        "",
        f"- {status}",
        "",
        "## Commands",
        "",
    ]
    for command, output in results:
        lines.extend(
            [
                f"### {command.name}",
                "",
                f"`{' '.join(command.argv)}`",
                "",
                "Result: passed",
                "",
            ]
        )
        if output:
            lines.extend(["Output summary:", "", "```", _summarize(output), "```", ""])
    lines.extend(
        [
            "## Residual Risk",
            "",
            (
                "- Live Stripe checkout, portal, and webhook proof still require "
                "Stripe secrets."
            ),
            "- Lifecycle deletion/export still needs a deployed staging drill.",
            (
                "- Provider ACL refresh still needs scheduled staging execution "
                "with provider tokens."
            ),
            "- Restore, rollback, load, and cost drills still need staging evidence.",
            "",
            "## Follow-Up",
            "",
            "- Run this gate before staging drills.",
            "- Append staging drill records in this directory after each live run.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the no-secret backend and operations launch gate."
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print planned commands without executing them.",
    )
    parser.add_argument(
        "--evidence",
        type=Path,
        default=None,
        help="Write a local evidence markdown file after a successful run.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    commands = gate_commands()
    if args.list:
        for command in commands:
            print(" ".join(command.argv))
        return 0
    results: list[tuple[GateCommand, str]] = []
    try:
        for command in commands:
            results.append((command, run_command(command)))
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 1
    if args.evidence is not None:
        write_evidence(path=args.evidence, results=results, status="passed")
    return 0


def _summarize(output: str, *, max_lines: int = 12) -> str:
    lines = [line.rstrip() for line in output.splitlines()]
    if len(lines) <= max_lines:
        return "\n".join(lines)
    return "\n".join([*lines[:max_lines], "..."])


if __name__ == "__main__":
    raise SystemExit(main())
