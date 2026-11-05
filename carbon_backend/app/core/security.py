import hashlib
import secrets

from pwdlib import PasswordHash

_password_hash = PasswordHash.recommended()  # Argon2id


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return _password_hash.verify(password, hashed_password)


def generate_access_token() -> str:
    return secrets.token_urlsafe(32)


def hash_access_token(token: str) -> str:
    """Only this digest is stored, so a leaked tokens table cannot be replayed."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
