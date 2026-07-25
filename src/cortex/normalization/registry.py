from __future__ import annotations

from collections.abc import Callable

from cortex.contracts.entities import RawEvent
from cortex.normalization.normalizers.fixtures import normalize_fixture_payload
from cortex.normalization.result import NormalizationResult

Normalizer = Callable[[RawEvent, bytes], NormalizationResult]


class NormalizerNotFoundError(Exception):
    pass


class NormalizerRegistry:
    def __init__(self) -> None:
        self._normalizers: dict[str, Normalizer] = {
            "fixture": normalize_fixture_payload,
            "slack": normalize_fixture_payload,
            "linear": normalize_fixture_payload,
            "github": normalize_fixture_payload,
            "repo_docs": normalize_fixture_payload,
        }

    def resolve(self, raw_event: RawEvent) -> Normalizer:
        try:
            return self._normalizers[raw_event.provider]
        except KeyError as error:
            raise NormalizerNotFoundError(raw_event.provider) from error
