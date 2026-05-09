from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken


class TokenCipherError(RuntimeError):
    pass


class TokenCipher:
    encryption_scheme = "fernet-v1"

    def __init__(self, key: str) -> None:
        if not key:
            raise TokenCipherError("CORTEX_SECRET_ENCRYPTION_KEY is required")
        try:
            self._fernet = Fernet(key.encode())
        except ValueError as error:
            raise TokenCipherError("invalid secret encryption key") from error

    @classmethod
    def generate_key(cls) -> str:
        return Fernet.generate_key().decode()

    def encrypt(self, token: str) -> str:
        return self._fernet.encrypt(token.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken as error:
            raise TokenCipherError("secret token decrypt failed") from error
