from __future__ import annotations

from collections.abc import Callable

from cortex.contracts.entities import RawEvent
from cortex.normalization.normalizers.fixtures import normalize_fixture_payload
from cortex.normalization.normalizers.github import normalize_github_payload
from cortex.normalization.normalizers.linear import normalize_linear_payload
from cortex.normalization.normalizers.repo_docs import normalize_repo_doc_payload
from cortex.normalization.normalizers.slack import normalize_slack_payload
from cortex.normalization.result import NormalizationResult

Normalizer = Callable[[RawEvent, bytes], NormalizationResult]


class NormalizerNotFoundError(Exception):
    pass


class NormalizerRegistry:
    def __init__(self) -> None:
        self._normalizers: dict[str, Normalizer] = {
            "fixture": normalize_fixture_payload,
            "slack": normalize_slack_payload,
            "linear": normalize_linear_payload,
            "github": normalize_github_payload,
            "repo_docs": normalize_repo_doc_payload,
        }

    def resolve(self, raw_event: RawEvent) -> Normalizer:
        try:
            return self._normalizers[raw_event.provider]
        except KeyError as error:
            raise NormalizerNotFoundError(raw_event.provider) from error
