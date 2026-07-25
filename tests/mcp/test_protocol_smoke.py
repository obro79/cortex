import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_mcp_protocol_smoke_exercises_stdio_discovery_and_safe_handoff() -> None:
    process = subprocess.run(
        [sys.executable, "scripts/mcp_protocol_smoke.py"],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
    )

    assert process.returncode == 0, process.stderr
    assert json.loads(process.stdout) == {
        "discovered_tool": "create_handoff_bundle",
        "handoff_opt_in": True,
        "native_claude_resume_supported": False,
        "opaque_handles": ["opaque:demo-handle"],
        "session_accessed": False,
    }
