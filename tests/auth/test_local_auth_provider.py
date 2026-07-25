import pytest

from cortex.auth.provider import LocalAuthProvider


def test_local_auth_provider_normalizes_verified_email_identity() -> None:
    identity = LocalAuthProvider().identity_from_verified_email(
        email="User@Example.com", display_name="User"
    )

    assert identity.provider == "local"
    assert identity.subject == "user@example.com"
    assert identity.email == "user@example.com"
    assert identity.email_verified
    assert identity.email_verified_at is not None


def test_local_auth_provider_rejects_invalid_email() -> None:
    with pytest.raises(ValueError):
        LocalAuthProvider().identity_from_verified_email(email="not-an-email")
