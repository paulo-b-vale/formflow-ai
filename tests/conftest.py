import os
from pathlib import Path
import logging
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Enable MongoDB logging
logging.getLogger("pymongo").setLevel(logging.DEBUG)
logging.getLogger("motor").setLevel(logging.DEBUG)

# --- START OF AGGRESSIVE DEBUGGING BLOCK ---
# This code runs the moment pytest loads this file.
print("\n--- [DEBUG] Starting conftest.py ---")
try:
    # 1. Print the current working directory
    cwd = Path.cwd()
    print(f"[DEBUG] Current Working Directory: {cwd}")

    # 2. Check for the .env file in the current directory
    env_path = cwd / ".env"
    print(f"[DEBUG] Checking for .env file at: {env_path}")

    if env_path.is_file():
        print("[DEBUG] .env file FOUND. Contents:")
        # 3. Print the contents of the .env file
        with open(env_path, "r") as f:
            print(f.read())
    else:
        print("[DEBUG] .env file NOT FOUND in the current directory.")
        print("[DEBUG] Listing all files in current directory:")
        for item in cwd.iterdir():
            print(f"  - {item.name}")

except Exception as e:
    print(f"[DEBUG] An error occurred during the initial debug check: {e}")
print("--- [DEBUG] Finished initial debug check ---\n")
# --- END OF AGGRESSIVE DEBUGGING BLOCK ---


import pytest
import pytest_asyncio
from httpx import AsyncClient
from dotenv import load_dotenv

load_dotenv()

from app.database import connect_to_databases, close_database_connections, get_database
from app.config.settings import settings

# Import services for initialization
from app.services.auth_service import auth_service
from app.services.forms_service import forms_service
from app.services.user_service import user_service
from app.services.file_service import file_service
from app.services.form_prediction_service import form_prediction_service
# --- THE FIX IS HERE ---
from app.services.enhanced_conversation_service import enhanced_conversation_service as conversation_service

BASE_URL = "http://localhost:8000"

# --- FIX: Force a single event loop for the entire test session ---
@pytest.fixture(scope="session")
def event_loop():
    """
    Creates a session-wide event loop.
    This is the crucial fix to prevent the "attached to a different loop" error
    by ensuring that the database client and all test functions use the same loop.
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session", autouse=True)
async def db_connection_session():
    """A single database connection for the entire test session."""
    print("\n--- Establishing database connection for tests ---")
    await connect_to_databases()
    
    # Initialize services
    print("\n--- Initializing services for tests ---")
    db = await get_database()
    await auth_service.initialize()
    await forms_service.initialize()
    await user_service.initialize()
    await file_service.initialize()
    await form_prediction_service.initialize()
    await conversation_service.initialize()
    print("\n--- Services initialized for tests ---")
    
    yield
    print("\n--- Closing database connection for tests ---")
    await close_database_connections()

@pytest_asyncio.fixture(scope="function", autouse=True)
async def clean_db(db_connection_session):
    """Ensures the database is clean before each test function runs."""
    print(f"\n--- Cleaning database: {settings.DATABASE_NAME} ---")
    db = await get_database()
    
    # --- The try/except block is no longer strictly necessary with the event_loop fix,
    # but it's good practice to keep it for robustness. ---
    try:
        await db.client.drop_database(settings.DATABASE_NAME)
        print(f"--- Database {settings.DATABASE_NAME} dropped successfully ---")
        
        try:
            collections = await db.client[settings.DATABASE_NAME].list_collection_names()
            print(f"--- Collections in database after drop: {collections} ---")
        except Exception as e:
            print(f"--- Error listing collections after drop: {e} ---")
    except Exception as e:
        print(f"--- Warning: Database cleanup failed with error: {e} ---")

@pytest_asyncio.fixture(scope="function")
async def async_client():
    """Creates a reusable HTTP client for API requests, waiting for app readiness."""
    async with AsyncClient(base_url=BASE_URL, timeout=30) as client:
        # Wait for the app to be ready by probing the root endpoint
        import asyncio as _asyncio
        max_attempts = 30
        for _ in range(max_attempts):
            try:
                resp = await client.get("/")
                if resp.status_code == 200:
                    break
            except Exception:
                pass
            await _asyncio.sleep(0.5)
        yield client

@pytest_asyncio.fixture(scope="function")
async def async_client_long_timeout():
    """Creates a reusable HTTP client with a longer timeout for slow operations."""
    async with AsyncClient(base_url=BASE_URL, timeout=120) as client:
        yield client