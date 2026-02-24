"""
Security helpers for dashboard secrets.
"""

import base64
import hashlib
import os

try:
    from cryptography.fernet import Fernet
except ImportError:  # pragma: no cover
    Fernet = None


class EncryptionError(RuntimeError):
    """Raised when encryption is unavailable or fails."""


def _derive_fernet_key(seed: str) -> bytes:
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _resolve_fernet_key() -> bytes:
    env_key = os.getenv("STACKSENSE_ENCRYPTION_KEY")

    if env_key:
        key_bytes = env_key.encode("utf-8")
        if len(key_bytes) == 44:
            return key_bytes
        return _derive_fernet_key(env_key)

    session_seed = os.getenv("STACKSENSE_SESSION_SECRET", "stacksense-dashboard-dev-secret")
    return _derive_fernet_key(session_seed)


def _get_fernet() -> "Fernet":
    if Fernet is None:  # pragma: no cover
        raise EncryptionError(
            "Missing dependency 'cryptography'. Install dashboard extras: pip install \"stacksense[dashboard]\""
        )
    try:
        return Fernet(_resolve_fernet_key())
    except Exception as exc:  # pragma: no cover
        raise EncryptionError("Invalid encryption key configuration") from exc


def encrypt_secret(secret_value: str) -> str:
    """Encrypt a plaintext secret for storage."""
    if not secret_value:
        raise EncryptionError("Cannot encrypt an empty secret")

    fernet = _get_fernet()
    return fernet.encrypt(secret_value.encode("utf-8")).decode("utf-8")


def decrypt_secret(encrypted_value: str) -> str:
    """Decrypt a stored secret."""
    if not encrypted_value:
        raise EncryptionError("Cannot decrypt an empty secret")

    fernet = _get_fernet()
    return fernet.decrypt(encrypted_value.encode("utf-8")).decode("utf-8")


def mask_secret(secret_value: str) -> str:
    """Mask a secret for display in the UI."""
    if not secret_value:
        return ""
    if len(secret_value) <= 4:
        return "*" * len(secret_value)
    return f"{'*' * 8}{secret_value[-4:]}"
