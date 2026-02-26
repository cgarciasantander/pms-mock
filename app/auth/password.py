import hashlib

import bcrypt


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def hash_token(raw_token: str) -> str:
    """SHA-256 hash of a raw refresh token for safe DB storage."""
    return hashlib.sha256(raw_token.encode()).hexdigest()
