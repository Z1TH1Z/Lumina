"""Unit tests for JWT security and password hashing utilities."""

import pytest
import time
from datetime import timedelta

from jose import jwt, JWTError

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
)
from app.core.config import get_settings

settings = get_settings()


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

class TestPasswordHashing:
    def test_hash_is_different_from_plaintext(self):
        hashed = hash_password("mysecretpassword")
        assert hashed != "mysecretpassword"

    def test_hash_is_bcrypt_format(self):
        hashed = hash_password("testpass")
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")

    def test_different_salts_produce_different_hashes(self):
        h1 = hash_password("samepassword")
        h2 = hash_password("samepassword")
        assert h1 != h2

    def test_verify_correct_password(self):
        hashed = hash_password("correct_horse_battery_staple")
        assert verify_password("correct_horse_battery_staple", hashed) is True

    def test_verify_wrong_password_fails(self):
        hashed = hash_password("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_verify_empty_password_fails(self):
        hashed = hash_password("somepassword")
        assert verify_password("", hashed) is False

    def test_verify_invalid_hash_returns_false(self):
        # Should not raise, just return False
        assert verify_password("password", "not-a-valid-hash") is False


# ---------------------------------------------------------------------------
# Access token
# ---------------------------------------------------------------------------

class TestAccessToken:
    def test_token_is_string(self):
        token = create_access_token({"sub": "user123"})
        assert isinstance(token, str)

    def test_token_contains_subject(self):
        token = create_access_token({"sub": "user42"})
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert payload["sub"] == "user42"

    def test_token_type_is_access(self):
        token = create_access_token({"sub": "user1"})
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert payload["type"] == "access"

    def test_token_has_expiry(self):
        token = create_access_token({"sub": "user1"})
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert "exp" in payload

    def test_custom_expiry_respected(self):
        short_token = create_access_token({"sub": "u1"}, expires_delta=timedelta(seconds=1))
        time.sleep(2)
        with pytest.raises(JWTError):
            jwt.decode(short_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

    def test_tampered_token_rejected(self):
        token = create_access_token({"sub": "user1"})
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(JWTError):
            jwt.decode(tampered, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

    def test_wrong_secret_rejected(self):
        token = create_access_token({"sub": "user1"})
        with pytest.raises(JWTError):
            jwt.decode(token, "wrong-secret", algorithms=[settings.JWT_ALGORITHM])

    def test_extra_claims_preserved(self):
        token = create_access_token({"sub": "user1", "role": "admin"})
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert payload["role"] == "admin"


# ---------------------------------------------------------------------------
# Refresh token
# ---------------------------------------------------------------------------

class TestRefreshToken:
    def test_refresh_token_is_string(self):
        token = create_refresh_token({"sub": "user1"})
        assert isinstance(token, str)

    def test_refresh_token_type(self):
        token = create_refresh_token({"sub": "user1"})
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert payload["type"] == "refresh"

    def test_refresh_token_has_longer_expiry_than_access(self):
        access = create_access_token({"sub": "user1"})
        refresh = create_refresh_token({"sub": "user1"})
        access_payload = jwt.decode(access, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        refresh_payload = jwt.decode(refresh, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert refresh_payload["exp"] > access_payload["exp"]

    def test_refresh_token_contains_subject(self):
        token = create_refresh_token({"sub": "userXYZ"})
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert payload["sub"] == "userXYZ"

    def test_access_and_refresh_tokens_are_different(self):
        data = {"sub": "user1"}
        access = create_access_token(data)
        refresh = create_refresh_token(data)
        assert access != refresh
