"""Integration tests for authentication endpoints."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestRegister:
    async def test_register_success(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/register", json={
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "StrongPass1!",
            "full_name": "New User",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert "password" not in data  # password must never be returned

    async def test_register_duplicate_email_fails(self, client: AsyncClient, registered_user: dict):
        response = await client.post("/api/v1/auth/register", json={
            "email": registered_user["email"],
            "username": "another",
            "password": "AnotherPass1!",
        })
        assert response.status_code == 400

    async def test_register_missing_required_fields(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/register", json={"email": "x@x.com"})
        assert response.status_code == 422  # Pydantic validation error


class TestLogin:
    async def test_login_success_returns_tokens(self, client: AsyncClient, registered_user: dict):
        response = await client.post("/api/v1/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password_returns_401(self, client: AsyncClient, registered_user: dict):
        response = await client.post("/api/v1/auth/login", json={
            "email": registered_user["email"],
            "password": "WrongPassword!",
        })
        assert response.status_code == 401

    async def test_login_unknown_email_returns_401(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/login", json={
            "email": "ghost@nobody.com",
            "password": "irrelevant",
        })
        assert response.status_code == 401

    async def test_login_empty_credentials(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422


class TestGetMe:
    async def test_get_me_authenticated(self, client: AsyncClient, auth_headers: dict, registered_user: dict):
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == registered_user["email"]

    async def test_get_me_no_token_returns_401(self, client: AsyncClient):
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

    async def test_get_me_invalid_token_returns_401(self, client: AsyncClient):
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer this.is.not.valid"},
        )
        assert response.status_code == 401


class TestRefreshToken:
    async def test_refresh_issues_new_tokens(self, client: AsyncClient, registered_user: dict):
        # Log in to get a refresh token
        login = await client.post("/api/v1/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        refresh_token = login.json()["refresh_token"]

        response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    async def test_refresh_with_access_token_fails(self, client: AsyncClient, auth_headers: dict):
        # Passing an access token where a refresh token is expected should fail
        access_token = auth_headers["Authorization"].split(" ")[1]
        response = await client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
        assert response.status_code == 401

    async def test_refresh_with_garbage_token_fails(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/refresh", json={"refresh_token": "garbage.token.here"})
        assert response.status_code == 401
