from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

ROOT = Path(__file__).parents[2]
ASSET_ROOT = ROOT / "apps" / "web" / "public" / "providers"


def test_provider_asset_manifest_matches_png_files() -> None:
    manifest = json.loads((ASSET_ROOT / "manifest.json").read_text())

    assert manifest["schema_version"] == "cortex.provider_assets.v1"
    assert {item["provider"] for item in manifest["assets"]} == {
        "slack",
        "github",
        "atlassian",
        "jira",
        "google_drive",
        "gmail",
        "anthropic",
    }
    assert {item["backend_provider"] for item in manifest["assets"]} == {
        None,
        "slack",
        "github",
        "jira",
        "google_drive",
        "email",
        "agent_session",
    }
    assert len({item["file"] for item in manifest["assets"]}) == len(manifest["assets"])
    assert {path.name for path in ASSET_ROOT.glob("*.png")} == {
        item["file"] for item in manifest["assets"]
    }
    for item in manifest["assets"]:
        asset = ASSET_ROOT / item["file"]
        content = asset.read_bytes()
        assert content.startswith(b"\x89PNG\r\n\x1a\n")
        width, height = struct.unpack(">II", content[16:24])
        assert item["dimensions"] == f"{width}x{height}"
        assert hashlib.sha256(content).hexdigest() == item["sha256"]
        assert item["display_name"].strip()
        assert item["provenance"] in {
            "official-media-kit",
            "simple-icons-derivative",
        }
        assert item["source"].startswith("https://")
        assert item["guidelines"].startswith("https://")
