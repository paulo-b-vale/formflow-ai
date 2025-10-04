# tests/test_agent_graph_api.py
import pytest
import pytest_asyncio
from httpx import AsyncClient
import random
import string
import os

from app.models.enums import FormStatus

# This fixture sets up all the necessary data for our tests
@pytest_asyncio.fixture(scope="function")
async def setup_test_data(async_client: AsyncClient):
    """
    A function-scoped fixture to set up users, contexts, and forms
    that can be reused across multiple API tests for the agent graph.
    """
    print("\n--- [Fixture] Setting up test data for Agent Graph API tests ---")
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    ADMIN_EMAIL = f"graph_admin_{random_suffix}@test.com"
    USER_EMAIL = f"graph_user_{random_suffix}@test.com"

    # 1. Register Admin and User
    await async_client.post("/auth/register", json={"name": "Graph Admin", "email": ADMIN_EMAIL, "password": "password", "role": "admin"})
    user_res = await async_client.post("/auth/register", json={"name": "Graph User", "email": USER_EMAIL, "password": "password", "role": "user"})
    user_id = user_res.json()["id"]

    # 2. Login Admin to get token for creating forms
    admin_login_res = await async_client.post("/auth/login", data={"username": ADMIN_EMAIL, "password": "password"})
    admin_headers = {"Authorization": f"Bearer {admin_login_res.json()['tokens']['access_token']}"}

    # 3. Create a realistic context and form template
    context_res = await async_client.post(
        "/forms-management/contexts",
        json={"title": "General Hospital", "context_type": "hospital", "assigned_users": [user_id]},
        headers=admin_headers
    )
    context_id = context_res.json()["id"]

    form_payload = {
        "title": "Patient Vitals Check",
        "context_id": context_id,
        "fields": [
            {"field_id": "patient_name", "label": "Patient Name", "field_type": "text", "required": True},
            {"field_id": "heart_rate", "label": "Heart Rate (bpm)", "field_type": "number", "required": True},
        ],
        "status": FormStatus.ACTIVE.value
    }
    template_res = await async_client.post("/forms-management/templates", json=form_payload, headers=admin_headers)
    template_id = template_res.json()["id"]

    # 4. Login the regular user to get their token for conversations
    user_login_res = await async_client.post("/auth/login", data={"username": USER_EMAIL, "password": "password"})
    user_headers = {"Authorization": f"Bearer {user_login_res.json()['tokens']['access_token']}"}
    
    print("--- [Fixture] Setup complete ---")
    
    # Provide all necessary data to the tests
    yield {
        "user_headers": user_headers,
        "template_id": template_id,
        "user_name": "Graph User"
    }

@pytest.mark.asyncio
async def test_graph_router_and_form_filling(async_client: AsyncClient, setup_test_data):
    """
    Tests if the router correctly identifies the 'fill_form' intent
    and triggers the form prediction and filling workflow.
    """
    print("\n--- [TEST] Testing Router -> Form Filling Path ---")
    
    # The user states their intent to fill a specific form
    payload = {
        "user_input": "I need to do a patient vitals check"
    }
    
    response = await async_client.post("/conversation/message", json=payload, headers=setup_test_data["user_headers"])
    
    assert response.status_code == 200
    response_data = response.json()
    
    # Assert that the RouterNode correctly identified the intent
    assert response_data["intent"] == "fill_form"
    # Assert that the FormPredictorNode correctly identified the form
    # and the FormFillerNode started the conversation by asking the first question.
    assert "Patient Name" in response_data["message"]
    
    print("✅ Router correctly triggered the form filling flow.")

@pytest.mark.asyncio
async def test_graph_query_processor(async_client: AsyncClient, setup_test_data):
    """
    Tests if the router correctly identifies the 'query_forms' intent
    and triggers the QueryProcessorNode.
    """
    print("\n--- [TEST] Testing Router -> Query Processor Path ---")
    
    # The user asks a simple question to find forms
    payload = {
        "query": "Show me all patient vitals forms"
    }
    
    response = await async_client.post("/conversation/query", json=payload, headers=setup_test_data["user_headers"])
    
    assert response.status_code == 200
    response_data = response.json()
    
    # Assert that the RouterNode (bypassed by /query endpoint) set the correct intent
    assert response_data["intent"] == "query_forms"
    # Assert that the QueryProcessorNode ran. Since we haven't submitted any forms,
    # the correct response is that none were found.
    assert "couldn't find any forms" in response_data["message"].lower() or "no forms found" in response_data["message"].lower()
    
    print("✅ Query Processor correctly handled the search request.")

@pytest.mark.asyncio
async def test_graph_report_generator(async_client: AsyncClient, setup_test_data):
    """
    Tests if the router correctly identifies the 'generate_report' intent
    and triggers the ReportGeneratorNode.
    """
    print("\n--- [TEST] Testing Router -> Report Generator Path ---")
    
    # The user asks a complex, natural language question that requires a report
    payload = {
        "query": f"How is patient {setup_test_data['user_name']} doing today?"
    }
    
    # We use the /query endpoint to directly trigger the report generation logic
    response = await async_client.post("/conversation/query", json=payload, headers=setup_test_data["user_headers"])
    
    assert response.status_code == 200
    response_data = response.json()
    
    # Assert that the intent was correctly identified
    assert response_data["intent"] == "generate_report"
    # Assert that the ReportGeneratorNode ran. Since no forms exist for this user,
    # it should correctly report that it couldn't find any data.
    assert "couldn't find any data to generate a report" in response_data["message"].lower() or "no data found" in response_data["message"].lower()
    
    print("✅ Report Generator correctly handled the report request.")