"""
Symmetric encryption helpers for vault secrets.

Secrets are encrypted at rest with Fernet (AES-128-CBC + HMAC-SHA256).
``MultiFernet`` is used so keys can be rotated: the first configured key
encrypts, every configured key may decrypt.
"""

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings


class DecryptionError(Exception):
    """Raised when stored ciphertext cannot be decrypted with any known key."""


def generate_key() -> str:
    """Return a new random Fernet key as a string."""
    return Fernet.generate_key().decode()


def _derive_key_from_secret(secret: str) -> bytes:
    digest = hashlib.pbkdf2_hmac(
        "sha256", secret.encode(), b"vaultify-field-encryption", 200_000
    )
    return base64.urlsafe_b64encode(digest)


@lru_cache(maxsize=8)
def _build_fernet(keys: tuple[str, ...], secret_key: str) -> MultiFernet:
    if keys:
        fernets = [Fernet(k.encode() if isinstance(k, str) else k) for k in keys]
    else:
        fernets = [Fernet(_derive_key_from_secret(secret_key))]
    return MultiFernet(fernets)


def get_fernet() -> MultiFernet:
    return _build_fernet(tuple(settings.VAULT_ENCRYPTION_KEYS), settings.SECRET_KEY)


def encrypt(plaintext: str) -> str:
    if plaintext is None or plaintext == "":
        return ""
    return get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str:
    if not token:
        return ""
    try:
        return get_fernet().decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise DecryptionError("Unable to decrypt vault data with the configured keys.") from exc


def rotate(token: str) -> str:
    """Re-encrypt a token with the current primary key."""
    if not token:
        return ""
    return get_fernet().rotate(token.encode()).decode()
