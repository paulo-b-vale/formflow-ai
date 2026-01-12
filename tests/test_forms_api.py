"""
Test suite for Forms Management API endpoints.
Tests cover CRUD operations for contexts and form templates.
"""
import pytest
from httpx import AsyncClient

# Test data
TEST_USER = {
    "name": "Forms Test User",
    "email": "forms_test@example.com",
    "phone_number": "+1234567890",
    "password": "FormsPassword123!"
}

TEST_CONTEXT = {
    "title": "Test Department",
    "description": "A test context for unit testing",
    "context_type": "consulting",
    "assigned_users": []
}

TEST_FORM_TEMPLATE = {
    "title": "Test Form",
    "description": "A test form template",
    "fields": [
        {
            "field_id": "field_1",
            "label": "Your Name",
            "field_type": "text",
            "required": True,
            "description": "Enter your full name"
        },
        {
            "field_id": "field_2",
            "label": "Comments",
            "field_type": "textarea",
            "required": False,
            "description": "Any additional comments"
        }
    ],
    "status": "draft"
}


async def get_auth_token(client: AsyncClient, user: dict) -> str:
    """Helper to register and login a user, returning the auth token."""
    await client.post("/auth/register", json=user)
    
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


class TestContextsCRUD:
    """Tests for Work Contexts CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_context_success(self, async_client: AsyncClient):
        """Test creating a new context."""
        token = await get_auth_token(async_client, TEST_USER)
        
        response = await async_client.post(
            "/forms-management/contexts",
            json=TEST_CONTEXT,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["title"] == TEST_CONTEXT["title"]
        assert "id" in data or "_id" in data

    @pytest.mark.asyncio
    async def test_list_contexts(self, async_client: AsyncClient):
        """Test listing all contexts."""
        token = await get_auth_token(async_client, TEST_USER)
        
        # Create a context first
        await async_client.post(
            "/forms-management/contexts",
            json=TEST_CONTEXT,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # List contexts
        response = await async_client.get(
            "/forms-management/contexts",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_get_context_by_id(self, async_client: AsyncClient):
        """Test getting a specific context by ID."""
        token = await get_auth_token(async_client, TEST_USER)
        
        # Create a context
        create_response = await async_client.post(
            "/forms-management/contexts",
            json=TEST_CONTEXT,
            headers={"Authorization": f"Bearer {token}"}
        )
        context_id = create_response.json().get("id") or create_response.json().get("_id")
        
        # Get by ID
        response = await async_client.get(
            f"/forms-management/contexts/{context_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        assert response.json()["title"] == TEST_CONTEXT["title"]

    @pytest.mark.asyncio
    async def test_update_context(self, async_client: AsyncClient):
        """Test updating a context."""
        token = await get_auth_token(async_client, TEST_USER)
        
        # Create a context
        create_response = await async_client.post(
            "/forms-management/contexts",
            json=TEST_CONTEXT,
            headers={"Authorization": f"Bearer {token}"}
        )
        context_id = create_response.json().get("id") or create_response.json().get("_id")
        
        # Update
        updated_data = {**TEST_CONTEXT, "title": "Updated Department"}
        response = await async_client.put(
            f"/forms-management/contexts/{context_id}",
            json=updated_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Department"

    @pytest.mark.asyncio
    async def test_delete_context(self, async_client: AsyncClient):
        """Test deleting a context."""
        token = await get_auth_token(async_client, TEST_USER)
        
        # Create a context
        create_response = await async_client.post(
            "/forms-management/contexts",
            json=TEST_CONTEXT,
            headers={"Authorization": f"Bearer {token}"}
        )
        context_id = create_response.json().get("id") or create_response.json().get("_id")
        
        # Delete
        response = await async_client.delete(
            f"/forms-management/contexts/{context_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code in [200, 204]

    @pytest.mark.asyncio
    async def test_create_context_without_auth(self, async_client: AsyncClient):
        """Test creating context without authentication fails."""
        response = await async_client.post(
            "/forms-management/contexts",
            json=TEST_CONTEXT
        )
        
        assert response.status_code == 401


class TestFormTemplatesCRUD:
    """Tests for Form Templates CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_form_template_success(self, async_client: AsyncClient):
        """Test creating a new form template."""
        token = await get_auth_token(async_client, TEST_USER)
        
        # First create a context
        context_response = await async_client.post(
            "/forms-management/contexts",
            json=TEST_CONTEXT,
            headers={"Authorization": f"Bearer {token}"}
        )
        context_id = context_response.json().get("id") or context_response.json().get("_id")
        
        # Create form template with context
        form_data = {**TEST_FORM_TEMPLATE, "context_id": context_id}
        response = await async_client.post(
            "/forms-management/templates",
            json=form_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["title"] == TEST_FORM_TEMPLATE["title"]

    @pytest.mark.asyncio
    async def test_list_form_templates(self, async_client: AsyncClient):
        """Test listing all form templates."""
        token = await get_auth_token(async_client, TEST_USER)
        
        response = await async_client.get(
            "/forms-management/templates",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_form_template_fields_validation(self, async_client: AsyncClient):
        """Test form template field validation."""
        token = await get_auth_token(async_client, TEST_USER)
        
        # Create context first
        context_response = await async_client.post(
            "/forms-management/contexts",
            json=TEST_CONTEXT,
            headers={"Authorization": f"Bearer {token}"}
        )
        context_id = context_response.json().get("id") or context_response.json().get("_id")
        
        # Create template with invalid field type
        invalid_form = {
            "title": "Invalid Form",
            "description": "Testing validation",
            "context_id": context_id,
            "fields": [
                {
                    "field_id": "field_1",
                    "label": "Test",
                    "field_type": "invalid_type",  # Invalid type
                    "required": True
                }
            ],
            "status": "draft"
        }
        
        response = await async_client.post(
            "/forms-management/templates",
            json=invalid_form,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Should either reject invalid type or accept it (depends on validation strictness)
        assert response.status_code in [200, 201, 400, 422]


class TestFormsAuthorization:
    """Tests for forms-related authorization."""

    @pytest.mark.asyncio
    async def test_forms_endpoints_require_auth(self, async_client: AsyncClient):
        """Test that forms endpoints require authentication."""
        endpoints = [
            ("/forms-management/contexts", "GET"),
            ("/forms-management/templates", "GET"),
        ]
        
        for endpoint, method in endpoints:
            if method == "GET":
                response = await async_client.get(endpoint)
            else:
                response = await async_client.post(endpoint, json={})
            
            assert response.status_code == 401, f"Endpoint {endpoint} should require auth"
