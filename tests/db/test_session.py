from cortex.db.session import normalize_asyncpg_url


def test_normalize_asyncpg_url_converts_neon_sslmode_for_asyncpg() -> None:
    raw = (
        "postgresql+asyncpg://user:pass@example.neon.tech/neondb"
        "?sslmode=require&channel_binding=require"
    )

    normalized = normalize_asyncpg_url(raw)

    assert normalized == (
        "postgresql+asyncpg://user:pass@example.neon.tech/neondb?ssl=require"
    )


def test_normalize_asyncpg_url_leaves_non_asyncpg_urls_unchanged() -> None:
    raw = "postgresql://user:pass@example.neon.tech/neondb?sslmode=require"

    assert normalize_asyncpg_url(raw) == raw
