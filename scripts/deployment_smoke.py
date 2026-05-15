from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class SmokeCommand:
    name: str
    argv: tuple[str, ...]


def smoke_commands(*, build: bool, full: bool) -> list[SmokeCommand]:
    commands = [
        SmokeCommand("compose config", ("docker", "compose", "config")),
        SmokeCommand(
            "compose migrate config",
            ("docker", "compose", "--profile", "migrate", "config"),
        ),
        SmokeCommand(
            "compose lifecycle config",
            ("docker", "compose", "--profile", "lifecycle", "config"),
        ),
        SmokeCommand(
            "compose provider-acl config",
            ("docker", "compose", "--profile", "provider-acl", "config"),
        ),
    ]
    if build:
        commands.append(
            SmokeCommand(
                "compose build api worker",
                ("docker", "compose", "build", "api", "worker"),
            )
        )
    if full:
        commands.extend(
            [
                SmokeCommand(
                    "start dependencies",
                    (
                        "docker",
                        "compose",
                        "up",
                        "-d",
                        "postgres",
                        "kafka",
                        "qdrant",
                        "minio",
                    ),
                ),
                SmokeCommand(
                    "run migrations",
                    (
                        "docker",
                        "compose",
                        "--profile",
                        "migrate",
                        "run",
                        "--rm",
                        "migrate",
                    ),
                ),
                SmokeCommand(
                    "start api and worker",
                    ("docker", "compose", "up", "-d", "api", "worker"),
                ),
                SmokeCommand("compose ps", ("docker", "compose", "ps")),
            ]
        )
    return commands


def run_command(command: SmokeCommand) -> None:
    print(f"==> {command.name}", flush=True)
    completed = subprocess.run(command.argv, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            f"{command.name} failed with exit code {completed.returncode}"
        )


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Phase 12 container deployment smoke checks."
    )
    parser.add_argument(
        "--no-build",
        action="store_true",
        help="Skip docker compose build api worker.",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Start local dependencies, run migrations, and start api/worker.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print planned smoke commands without executing them.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    commands = smoke_commands(build=not args.no_build, full=args.full)
    if args.list:
        for command in commands:
            print(" ".join(command.argv))
        return 0
    try:
        for command in commands:
            run_command(command)
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
