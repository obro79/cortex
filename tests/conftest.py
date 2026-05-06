from collections.abc import Iterator

import pytest
from typer.testing import CliRunner

from cortex.config import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()
