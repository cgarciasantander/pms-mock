"""Unit tests for JWT utilities — no DB required."""

import time

import pytest
from jose import JWTError

from app.auth.jwt import create_access_token, create_refresh_token, decode_token


def test_access_token_decode():
    token = create_access_token(subject="user-123", role="admin")
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["role"] == "admin"
    assert payload["type"] == "access"


def test_refresh_token_decode():
    raw, expires_at = create_refresh_token(subject="user-456")
    payload = decode_token(raw)
    assert payload["sub"] == "user-456"
    assert payload["type"] == "refresh"


def test_invalid_token_raises():
    with pytest.raises(JWTError):
        decode_token("not.a.valid.token")


def test_tampered_token_raises():
    token = create_access_token(subject="u1", role="front_desk")
    tampered = token[:-5] + "XXXXX"
    with pytest.raises(JWTError):
        decode_token(tampered)
