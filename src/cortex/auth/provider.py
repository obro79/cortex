from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class AuthIdentity:
    provider: str
    subject: str
    email: str
    display_name: str | None = None
    email_verified: bool = False

    @property
    def email_verified_at(self) -> datetime | None:
        if not self.email_verified:
            return None
        return datetime.now(UTC)


class LocalAuthProvider:
    provider_name = "local"

    def identity_from_verified_email(
        self, *, email: str, display_name: str | None = None
    ) -> AuthIdentity:
        normalized = email.strip().lower()
        if not normalized or "@" not in normalized:
            raise ValueError("valid email is required")
        return AuthIdentity(
            provider=self.provider_name,
            subject=normalized,
            email=normalized,
            display_name=display_name,
            email_verified=True,
        )
