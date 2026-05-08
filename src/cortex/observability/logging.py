from __future__ import annotations

import logging

from cortex.security.redaction import REDACTED, is_sensitive_key, redact_mapping


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


__all__ = ["REDACTED", "is_sensitive_key", "redact_mapping", "setup_logging"]
