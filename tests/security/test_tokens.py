import pytest

from cortex.security.tokens import TokenCipher, TokenCipherError


def test_token_cipher_round_trips_and_hides_plaintext() -> None:
    cipher = TokenCipher(TokenCipher.generate_key())

    ciphertext = cipher.encrypt("xoxb-secret-token")

    assert "xoxb-secret-token" not in ciphertext
    assert cipher.decrypt(ciphertext) == "xoxb-secret-token"


def test_token_cipher_rejects_wrong_key() -> None:
    first = TokenCipher(TokenCipher.generate_key())
    second = TokenCipher(TokenCipher.generate_key())
    ciphertext = first.encrypt("xoxb-secret-token")

    with pytest.raises(TokenCipherError):
        second.decrypt(ciphertext)
