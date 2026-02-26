"""Unit tests for password hashing utilities — no DB required."""

from app.auth.password import hash_password, hash_token, verify_password


def test_hash_and_verify():
    plain = "SuperSecret123!"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed)


def test_wrong_password_fails():
    hashed = hash_password("correct-password")
    assert not verify_password("wrong-password", hashed)


def test_token_hash_is_deterministic():
    raw = "some-raw-refresh-token"
    assert hash_token(raw) == hash_token(raw)


def test_different_tokens_have_different_hashes():
    assert hash_token("token-a") != hash_token("token-b")
