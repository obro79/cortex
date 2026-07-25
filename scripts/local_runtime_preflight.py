#!/usr/bin/env python3
"""Fail fast when local dependency files are missing, offloaded, or corrupted.

macOS Files On-Demand can leave files under ``.venv`` or ``node_modules`` as
metadata-only placeholders. Runtime tools then either read an empty file or
block while the file provider tries to hydrate it. This preflight uses bounded
child processes so the normal local startup path reports a concrete recovery
command instead of appearing to hang.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

DEFAULT_TIMEOUT_SECONDS = 12


@dataclass(frozen=True)
class CheckFailure:
    name: str
    detail: str


def _run_check(
    name: str,
    command: Sequence[str],
    *,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> CheckFailure | None:
    """Run a dependency read in a bounded process and return a useful failure."""

    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except FileNotFoundError:
        return CheckFailure(name, f"required executable is missing: {command[0]}")
    except subprocess.TimeoutExpired:
        return CheckFailure(
            name,
            f"timed out after {timeout_seconds}s while reading installed files",
        )

    if completed.returncode == 0:
        return None

    output = (completed.stderr or completed.stdout).strip()
    return CheckFailure(name, output or f"exited with status {completed.returncode}")


def check_backend_runtime(repo_root: Path) -> CheckFailure | None:
    python = repo_root / ".venv" / "bin" / "python"
    if not python.is_file():
        return CheckFailure("backend runtime", f"missing virtual environment: {python}")
    return _run_check(
        "backend runtime",
        [str(python), "-c", "import fastapi, uvicorn; print('backend runtime ready')"],
    )


def check_frontend_runtime(repo_root: Path) -> CheckFailure | None:
    manifest = repo_root / "frontend" / "node_modules" / "next" / "package.json"
    if not manifest.is_file():
        return CheckFailure("frontend runtime", f"missing Next.js manifest: {manifest}")

    validator = (
        "import json, pathlib, sys; "
        "content = pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'); "
        "assert content.strip(), 'Next.js package.json is empty'; "
        "json.loads(content)"
    )
    return _run_check(
        "frontend runtime", [sys.executable, "-c", validator, str(manifest)]
    )


def repair_instructions(repo_root: Path) -> str:
    return "\n".join(
        (
            "Installed dependencies are unavailable or corrupted.",
            "This commonly happens",
            "when macOS Files On-Demand offloads .venv or frontend/node_modules.",
            "Rebuild them from the repository root:",
            f"  cd {repo_root}",
            "  uv sync --extra dev --reinstall",
            "  (cd frontend && npm ci)",
            "Keep dependency directories available offline;",
            "do not copy them between worktrees.",
        )
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--backend", action="store_true", help="check only Python dependencies"
    )
    parser.add_argument(
        "--frontend", action="store_true", help="check only Next.js dependencies"
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args(argv)
    repo_root = args.repo_root.resolve()

    check_backend = args.backend or not (args.backend or args.frontend)
    check_frontend = args.frontend or not (args.backend or args.frontend)
    failures = [
        failure
        for failure in (
            check_backend_runtime(repo_root) if check_backend else None,
            check_frontend_runtime(repo_root) if check_frontend else None,
        )
        if failure is not None
    ]
    if not failures:
        print("Local runtime preflight passed.")
        return 0

    for failure in failures:
        print(f"{failure.name}: {failure.detail}", file=sys.stderr)
    print(repair_instructions(repo_root), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
