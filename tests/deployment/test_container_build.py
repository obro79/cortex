from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read_repo_file(path: str) -> str:
    return (ROOT / path).read_text()


def test_dockerfile_uses_lockfile_and_non_root_runtime() -> None:
    dockerfile = read_repo_file("Dockerfile")

    assert "COPY pyproject.toml uv.lock README.md" in dockerfile
    assert "uv sync --locked --no-dev" in dockerfile
    assert "COPY config ./config" in dockerfile
    assert "useradd --create-home --uid 10001" in dockerfile
    assert "USER cortex" in dockerfile


def test_dockerfile_exposes_api_and_worker_targets() -> None:
    dockerfile = read_repo_file("Dockerfile")

    assert "FROM runtime AS api" in dockerfile
    assert 'CMD ["uvicorn", "cortex.api.app:create_app"' in dockerfile
    assert "FROM runtime AS worker" in dockerfile
    assert "HEALTHCHECK NONE" in dockerfile
    assert 'CMD ["cortex-worker", "--role", "noop"]' in dockerfile
    assert "HEALTHCHECK" in dockerfile


def test_dockerfile_has_image_revision_labels_without_baked_secrets() -> None:
    dockerfile = read_repo_file("Dockerfile")

    assert "org.opencontainers.image.version" in dockerfile
    assert "org.opencontainers.image.revision" in dockerfile
    assert "SLACK_CLIENT_SECRET" not in dockerfile
    assert "GITHUB_TOKEN" not in dockerfile
    assert "LINEAR_API_TOKEN" not in dockerfile
    assert "OPENAI_API_KEY" not in dockerfile
    assert "GEMINI_API_KEY" not in dockerfile
