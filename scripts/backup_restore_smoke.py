from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SmokeCommand:
    name: str
    argv: tuple[str, ...]


def smoke_commands(*, full: bool) -> list[SmokeCommand]:
    commands = [
        SmokeCommand(
            "runbook exists", ("test", "-f", "docs/runbooks/backup-restore.md")
        ),
        SmokeCommand("alembic heads", ("alembic", "heads")),
    ]
    if full:
        commands.extend(
            [
                SmokeCommand(
                    "postgres backup placeholder",
                    ("pg_dump", "--format=custom", "--file=/tmp/cortex.backup"),
                ),
                SmokeCommand(
                    "postgres restore placeholder",
                    ("pg_restore", "--list", "/tmp/cortex.backup"),
                ),
            ]
        )
    return commands


def static_smoke() -> None:
    runbook = Path("docs/runbooks/backup-restore.md").read_text()
    required = [
        "Postgres Backup",
        "Postgres Restore",
        "Object Storage Restore",
        "Redis, Qdrant, and OpenSearch are not source-of-truth systems",
        "python scripts/backup_restore_smoke.py --static",
    ]
    missing = [item for item in required if item not in runbook]
    if missing:
        raise RuntimeError(f"backup restore runbook missing: {', '.join(missing)}")


def run_command(command: SmokeCommand) -> None:
    print(f"==> {command.name}", flush=True)
    completed = subprocess.run(command.argv, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            f"{command.name} failed with exit code {completed.returncode}"
        )


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Phase 13 backup and restore smoke checks."
    )
    parser.add_argument(
        "--static",
        action="store_true",
        help="Validate runbook coverage without external services.",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Include local/staging backup and restore commands.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print planned smoke commands without executing them.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    commands = smoke_commands(full=args.full)
    if args.list:
        for command in commands:
            print(" ".join(command.argv))
        return 0
    try:
        if args.static:
            static_smoke()
            return 0
        for command in commands:
            run_command(command)
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
