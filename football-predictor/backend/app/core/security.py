"""Admin auth + provider-key encryption.

- Passwords are hashed with bcrypt (passlib).
- Admin login issues a short JWT.
- Provider API keys are encrypted at rest with Fernet, using a key derived
  from SECRET_KEY, so they never sit in the DB (or logs) in plaintext.
"""
from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

ALGORITHM = "HS256"
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# --------------------------------------------------------------------------- #
# Passwords
# --------------------------------------------------------------------------- #
def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


# --------------------------------------------------------------------------- #
# JWT
# --------------------------------------------------------------------------- #
def create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.access_token_expire_minutes
    )
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str | None:
    """Return the subject if valid, else None."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


# --------------------------------------------------------------------------- #
# Provider-key encryption (Fernet, key derived from SECRET_KEY)
# --------------------------------------------------------------------------- #
def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.secret_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:  # wrong SECRET_KEY, or corrupted value
        raise ValueError(
            "Could not decrypt provider secret — SECRET_KEY may have changed."
        ) from exc


def mask_key(key: str | None) -> str:
    """Safe representation for logs / API responses. Never returns the full key."""
    if not key:
        return ""
    if len(key) <= 4:
        return "****"
    return f"{'*' * (len(key) - 4)}{key[-4:]}"
