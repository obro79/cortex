from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedRelationshipHint:
    relationship_type: str
    target_key: str
    matched_text: str
    confidence: float = 1.0


LINEAR_ID_RE = re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b")
GITHUB_PR_RE = re.compile(r"(?:github\.com/[^/\s]+/[^/\s]+/pull/|#)(\d+)\b")
SHA_RE = re.compile(r"\b[0-9a-f]{7,40}\b")
SLACK_LINK_RE = re.compile(r"https://[^/\s]*slack\.com/archives/[A-Z0-9]+/p\d+")
DOC_PATH_RE = re.compile(r"\b(?:docs|adr|architecture)/[\w./-]+\.md\b")
FILE_PATH_RE = re.compile(r"\b[\w./-]+\.(?:py|ts|tsx|js|md|yaml|yml|json)\b")


class DeterministicRelationshipParser:
    def parse_text(self, text: str) -> list[ParsedRelationshipHint]:
        hints: list[ParsedRelationshipHint] = []
        for value in LINEAR_ID_RE.findall(text):
            hints.append(
                ParsedRelationshipHint(
                    relationship_type="mentions_linear_issue",
                    target_key=f"linear:{value}",
                    matched_text=value,
                )
            )
        for value in GITHUB_PR_RE.findall(text):
            hints.append(
                ParsedRelationshipHint(
                    relationship_type="mentions_github_pr",
                    target_key=f"github:pr:{value}",
                    matched_text=value,
                )
            )
        for value in SHA_RE.findall(text):
            hints.append(
                ParsedRelationshipHint(
                    relationship_type="mentions_commit",
                    target_key=f"github:commit:{value}",
                    matched_text=value,
                    confidence=0.8,
                )
            )
        for value in SLACK_LINK_RE.findall(text):
            hints.append(
                ParsedRelationshipHint(
                    relationship_type="mentions_slack_thread",
                    target_key=f"slack:{value}",
                    matched_text=value,
                )
            )
        for value in DOC_PATH_RE.findall(text):
            hints.append(
                ParsedRelationshipHint(
                    relationship_type="mentions_doc_path",
                    target_key=f"doc:path:{value}",
                    matched_text=value,
                )
            )
        for value in FILE_PATH_RE.findall(text):
            hints.append(
                ParsedRelationshipHint(
                    relationship_type="mentions_file_path",
                    target_key=f"file:path:{value}",
                    matched_text=value,
                    confidence=0.85,
                )
            )
        return _dedupe(hints)


def _dedupe(
    hints: list[ParsedRelationshipHint],
) -> list[ParsedRelationshipHint]:
    seen = set()
    deduped = []
    for hint in hints:
        key = (hint.relationship_type, hint.target_key)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(hint)
    return deduped
