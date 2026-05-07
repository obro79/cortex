from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from typer.testing import CliRunner

from cortex.config import get_settings
from cortex.contracts.entities import SourceObject
from cortex.contracts.enums import SourceObjectStatus


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def phase4_source_object() -> SourceObject:
    now = datetime.now(UTC)
    return SourceObject(
        id="so_1",
        workspace_id="ws_1",
        source_connection_id="src_1",
        provider="linear",
        object_type="linear_issue",
        external_object_id="COR-123",
        external_object_key="linear:COR-123",
        title="COR-123 migrate session reads",
        canonical_url="https://fixtures.local/linear/COR-123",
        content_hash="sha256:content",
        metadata_json={"source_kind": "linear_task"},
        status=SourceObjectStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
