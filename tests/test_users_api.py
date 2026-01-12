"""
Test suite for Users API endpoints.
Tests cover user listing, profile access, and role-based access control.
"""
import pytest
from httpx import AsyncClient

# Test data
TEST_USER = {
    "name": "Regular User",
    "email": "regular@example.com",
    "phone_number": "+1234567890",
    "password": "UserPassword123!"
}

ADMIN_USER = {
    "name": "Admin User",
    "email": "admin@example.com",
    "phone_number": "+0987654321",
    "password": "AdminPassword123!"
}


async def get_auth_token(client: AsyncClient, user: dict) -> str:
    """Helper to register and login a user, returning the auth token."""
    # Register
    await client.post("/auth/register", json=user)
    
    # Login
    login_data = {
        "username": user["email"],
        "password": user["password"]
    }
    response = await client.post(
        "/auth/login",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    login_json = response.json()
    return login_json.get("access_token") or login_json.get("tokens", {}).get("access_token")


class TestCurrentUser:
    """Tests for GET /users/me endpoint."""

    @pytest.mark.asyncio
    async def test_get_current_user_success(self, async_client: AsyncClient):
        """Test getting current user profile."""
        token = await get_auth_token(async_client, TEST_USER)
        
        response = await async_client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == TEST_USER["email"]
        assert data["name"] == TEST_USER["name"]
        assert "password" not in data

    @pytest.mark.asyncio
    async def test_get_current_user_without_auth(self, async_client: AsyncClient):
        """Test getting current user without authentication."""
        response = await async_client.get("/users/me")
        
        assert response.status_code == 401


class TestUsersList:
    """Tests for GET /users/ endpoint (admin only)."""

    @pytest.mark.asyncio
    async def test_get_users_list_as_regular_user(self, async_client: AsyncClient):
        """Test regular user cannot access users list."""
        token = await get_auth_token(async_client, TEST_USER)
        
        response = await async_client.get(
            "/users/",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Should be forbidden for regular users
        assert response.status_code in [403, 401]

    @pytest.mark.asyncio
    async def test_get_users_list_without_auth(self, async_client: AsyncClient):
        """Test accessing users list without authentication."""
        response = await async_client.get("/users/")
        
        assert response.status_code == 401


class TestUserRoles:
    """Tests for role-based access control."""

    @pytest.mark.asyncio
    async def test_user_has_default_role(self, async_client: AsyncClient):
        """Test that new users have the default 'user' role."""
        token = await get_auth_token(async_client, TEST_USER)
        
        response = await async_client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("role") in ["user", "USER"]

    @pytest.mark.asyncio
    async def test_user_is_active_by_default(self, async_client: AsyncClient):
        """Test that new users are active by default."""
        token = await get_auth_token(async_client, TEST_USER)
        
        response = await async_client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("is_active") is True


class TestUserValidation:
    """Tests for user data validation."""

    @pytest.mark.asyncio
    async def test_user_id_is_valid_objectid(self, async_client: AsyncClient):
        """Test that user IDs are valid MongoDB ObjectIds."""
        token = await get_auth_token(async_client, TEST_USER)
        
        response = await async_client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        user_id = data.get("id") or data.get("_id")
        
        # MongoDB ObjectId is 24 hex characters
        assert user_id is not None
        assert len(str(user_id)) == 24

    @pytest.mark.asyncio
    async def test_user_response_schema(self, async_client: AsyncClient):
        """Test that user response contains expected fields."""
        token = await get_auth_token(async_client, TEST_USER)
        
        response = await async_client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields exist
        assert "email" in data
        assert "name" in data
        assert "role" in data or "is_active" in data
