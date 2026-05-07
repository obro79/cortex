from __future__ import annotations

import re
from dataclasses import dataclass, field

from cortex.ingestion.payloads import sha256_digest


@dataclass(frozen=True)
class QueryPlan:
    normalized_query: str
    issue_ids: list[str] = field(default_factory=list)
    pr_numbers: list[str] = field(default_factory=list)
    file_paths: list[str] = field(default_factory=list)
    provider_filters: list[str] = field(default_factory=list)
    source_allowlist: list[str] = field(default_factory=list)
    source_allowlist_snapshot_hash: str | None = None


class QueryPlanner:
    def plan(
        self,
        *,
        query: str,
        provider_filters: list[str] | None = None,
        source_allowlist: list[str] | None = None,
    ) -> QueryPlan:
        normalized = " ".join(query.lower().split())
        allowlist = sorted(source_allowlist or [])
        return QueryPlan(
            normalized_query=normalized,
            issue_ids=sorted(set(re.findall(r"\b[A-Z]+-\d+\b", query))),
            pr_numbers=sorted(set(re.findall(r"#(\d+)\b", query))),
            file_paths=sorted(set(re.findall(r"[\w./-]+\.\w+", query))),
            provider_filters=sorted(provider_filters or []),
            source_allowlist=allowlist,
            source_allowlist_snapshot_hash=sha256_digest("|".join(allowlist).encode())
            if allowlist
            else None,
        )
