from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def dockerignore_patterns() -> set[str]:
    return {
        line.strip()
        for line in (ROOT / ".dockerignore").read_text().splitlines()
        if line.strip() and not line.startswith("#")
    }


def test_dockerignore_excludes_local_env_files_but_allows_example() -> None:
    patterns = dockerignore_patterns()

    assert ".env" in patterns
    assert ".env.*" in patterns
    assert "!.env.example" in patterns


def test_dockerignore_excludes_run_artifacts_payloads_and_caches() -> None:
    patterns = dockerignore_patterns()

    assert ".venv" in patterns
    assert ".pytest_cache" in patterns
    assert ".mypy_cache" in patterns
    assert ".ruff_cache" in patterns
    assert "payloads" in patterns
    assert "payload-store" in patterns
    assert "manual-runs" in patterns
    assert "run-logs" in patterns
    assert "*.log" in patterns


def test_dockerignore_excludes_common_key_material() -> None:
    patterns = dockerignore_patterns()

    assert "*.pem" in patterns
    assert "*.key" in patterns
    assert "id_rsa*" in patterns
    assert "id_ed25519*" in patterns
