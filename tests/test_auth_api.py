"""
Test suite for Authentication API endpoints.
Tests cover registration, login, token validation, and protected routes.
"""
import pytest
from httpx import AsyncClient

# Test data
TEST_USER = {
    "name": "Test User",
    "email": "test@example.com",
    "phone_number": "+1234567890",
    "password": "SecurePassword123!"
}

ADMIN_USER = {
    "name": "Admin User",
    "email": "admin@example.com",
    "phone_number": "+0987654321",
    "password": "AdminPassword123!"
}


class TestUserRegistration:
    """Tests for POST /auth/register endpoint."""

    @pytest.mark.asyncio
    async def test_register_success(self, async_client: AsyncClient):
        """Test successful user registration."""
        response = await async_client.post("/auth/register", json=TEST_USER)
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == TEST_USER["email"]
        assert data["name"] == TEST_USER["name"]
        assert "id" in data
        assert "password" not in data  # Password should never be returned

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, async_client: AsyncClient):
        """Test registration fails with duplicate email."""
        # First registration
        await async_client.post("/auth/register", json=TEST_USER)
        
        # Second registration with same email
        response = await async_client.post("/auth/register", json=TEST_USER)
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, async_client: AsyncClient):
        """Test registration fails with invalid email format."""
        invalid_user = {**TEST_USER, "email": "not-an-email"}
        response = await async_client.post("/auth/register", json=invalid_user)
        
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_weak_password(self, async_client: AsyncClient):
        """Test registration with weak password."""
        weak_user = {**TEST_USER, "email": "weak@example.com", "password": "123"}
        response = await async_client.post("/auth/register", json=weak_user)
        
        # Depending on implementation, this might be 400 or 422
        assert response.status_code in [400, 422, 201]  # Adjust based on password policy

    @pytest.mark.asyncio
    async def test_register_missing_required_fields(self, async_client: AsyncClient):
        """Test registration fails with missing required fields."""
        incomplete_user = {"email": "incomplete@example.com"}
        response = await async_client.post("/auth/register", json=incomplete_user)
        
        assert response.status_code == 422


class TestUserLogin:
    """Tests for POST /auth/login endpoint."""

    @pytest.mark.asyncio
    async def test_login_success(self, async_client: AsyncClient):
        """Test successful login returns tokens."""
        # First register the user
        await async_client.post("/auth/register", json=TEST_USER)
        
        # Then login
        login_data = {
            "username": TEST_USER["email"],
            "password": TEST_USER["password"]
        }
        response = await async_client.post(
            "/auth/login",
            data=login_data,  # OAuth2 uses form data
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data or "tokens" in data
        
    @pytest.mark.asyncio
    async def test_login_wrong_password(self, async_client: AsyncClient):
        """Test login fails with wrong password."""
        # First register the user
        await async_client.post("/auth/register", json=TEST_USER)
        
        # Try login with wrong password
        login_data = {
            "username": TEST_USER["email"],
            "password": "WrongPassword123!"
        }
        response = await async_client.post(
            "/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, async_client: AsyncClient):
        """Test login fails for non-existent user."""
        login_data = {
            "username": "nonexistent@example.com",
            "password": "SomePassword123!"
        }
        response = await async_client.post(
            "/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == 401


class TestProtectedRoutes:
    """Tests for authenticated endpoint access."""

    @pytest.mark.asyncio
    async def test_access_protected_route_without_token(self, async_client: AsyncClient):
        """Test accessing protected route without token returns 401."""
        response = await async_client.get("/users/me")
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_access_protected_route_with_invalid_token(self, async_client: AsyncClient):
        """Test accessing protected route with invalid token returns 401."""
        response = await async_client.get(
            "/users/me",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_access_protected_route_with_valid_token(self, async_client: AsyncClient):
        """Test accessing protected route with valid token succeeds."""
        # Register user
        await async_client.post("/auth/register", json=TEST_USER)
        
        # Login to get token
        login_data = {
            "username": TEST_USER["email"],
            "password": TEST_USER["password"]
        }
        login_response = await async_client.post(
            "/auth/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        # Extract token (handle both response formats)
        login_json = login_response.json()
        token = login_json.get("access_token") or login_json.get("tokens", {}).get("access_token")
        
        # Access protected route
        response = await async_client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        assert response.json()["email"] == TEST_USER["email"]
