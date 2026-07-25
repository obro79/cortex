import importlib.util
from pathlib import Path


def _load_rehearsal_module() -> object:
    path = Path("scripts/hackathon_demo_rehearsal.py")
    spec = importlib.util.spec_from_file_location("hackathon_demo_rehearsal", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def test_rehearsal_report_is_recording_ready_and_redacts_source_data() -> None:
    rehearsal = _load_rehearsal_module()
    report = await rehearsal.build_rehearsal_report()
    rendered = rehearsal.render_human(report)

    assert report["corpus"]["source_object_count"] == 10
    assert report["corpus"]["source_file_count"] == 3
    assert report["corpus"]["provider_counts"] == {
        "github": 1,
        "google_drive": 2,
        "jira": 1,
        "linear": 2,
        "repo_docs": 1,
        "slack": 3,
    }
    assert report["corpus"]["media_counts"] == {
        "caption": 2,
        "video_transcript": 1,
    }
    assert report["query"]["issue"] == "COR-123"
    assert report["query"]["gate_status"] == "block"
    assert "deterministic" in rendered.lower()
    assert "not live ocr or transcription" in rendered.lower()
    assert "https://" not in rendered
    assert "Postgres is the approved" not in rendered
