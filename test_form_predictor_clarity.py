#!/usr/bin/env python3
"""
Test script for form predictor clarification fix
Tests that clear intent gets direct form assignment and ambiguous intent shows alternatives
"""

import requests
import json
import sys
from typing import Dict, Any

# Configuration
API_URL = "http://localhost:8002"
TEST_EMAIL = "ana.costa@usuario.com"
TEST_PASSWORD = "test123"

# Colors for terminal output
class Colors:
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

def print_header(text: str):
    """Print a blue header"""
    print(f"{Colors.BLUE}{'=' * 40}{Colors.NC}")
    print(f"{Colors.BLUE}{text}{Colors.NC}")
    print(f"{Colors.BLUE}{'=' * 40}{Colors.NC}\n")

def print_step(text: str):
    """Print a yellow step indicator"""
    print(f"{Colors.YELLOW}{text}{Colors.NC}")

def print_success(text: str):
    """Print a green success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.NC}")

def print_fail(text: str):
    """Print a red failure message"""
    print(f"{Colors.RED}✗ {text}{Colors.NC}")

def print_info(text: str):
    """Print a blue info message"""
    print(f"{Colors.BLUE}{text}{Colors.NC}")

def login() -> str:
    """Login and return access token"""
    print_step(f"[1/4] Logging in as {TEST_EMAIL}...")

    response = requests.post(
        f"{API_URL}/auth/login",
        data={
            "username": TEST_EMAIL,
            "password": TEST_PASSWORD
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )

    if response.status_code != 200:
        print_fail(f"Login failed: {response.status_code}")
        print(response.text)
        sys.exit(1)

    token = response.json()["tokens"]["access_token"]
    print_success("Login successful\n")
    return token

def send_message(token: str, session_id: str, message: str) -> Dict[str, Any]:
    """Send a message to the conversation API"""
    response = requests.post(
        f"{API_URL}/enhanced_conversation/message",
        json={
            "session_id": session_id,
            "user_message": message,
            "form_id": None
        },
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
    )

    if response.status_code != 200:
        print_fail(f"API call failed: {response.status_code}")
        print(response.text)
        return {"error": response.text}

    return response.json()

def test_clear_intent(token: str) -> bool:
    """Test that clear intent gets direct form assignment"""
    print_step("[2/4] Test 1: Clear Intent (Construction Incident)")
    print("Message: 'I need to fill a construction incident form'\n")

    response = send_message(
        token,
        "test_clear_intent",
        "I need to fill a construction incident form"
    )

    if "error" in response:
        return False

    response_text = response.get("response", "")

    # Check for direct form assignment indicators
    is_direct = any(word in response_text.lower() for word in ["vamos começar", "começar", "pergunta 1"])

    if is_direct:
        print_success("PASS: Direct form assignment (no clarification)")

        # Extract form title if possible
        import re
        match = re.search(r"'(.+?)'", response_text)
        if match:
            print_info(f"  Assigned form: {match.group(1)}")
        return True
    else:
        print_fail("FAIL: Should have assigned form directly")
        print(f"  Response preview: {response_text[:150]}")
        return False

def test_ambiguous_intent(token: str) -> bool:
    """Test that ambiguous intent shows alternatives"""
    print_step("\n[3/4] Test 2: Ambiguous Intent")
    print("Message: 'I want to fill out a form'\n")

    response = send_message(
        token,
        "test_ambiguous_intent",
        "I want to fill out a form"
    )

    if "error" in response:
        return False

    response_text = response.get("response", "")

    # Check for alternatives
    shows_alternatives = "Escolha uma opção" in response_text or "Choose an option" in response_text

    if shows_alternatives:
        print_success("PASS: Shows form alternatives (requires clarification)")

        # Count alternatives
        import re
        alternatives = re.findall(r"\*\*\d+\.", response_text)
        print_info(f"  Number of alternatives shown: {len(alternatives)}")

        # Check if user message is preserved
        if "I want to fill out a form" in response_text:
            print_success("User message preserved in response")
        else:
            print_fail("User message NOT preserved")

        return True
    else:
        print_fail("FAIL: Should show alternatives for clarification")
        print(f"  Response preview: {response_text[:150]}")
        return False

def test_session_preservation(token: str) -> bool:
    """Test that session IDs are preserved"""
    print_step("\n[4/4] Test 3: Session ID Preservation\n")

    # Test 1: Clear intent
    response_1 = send_message(
        token,
        "test_session_1",
        "construction incident form"
    )

    session_1 = response_1.get("session_id")
    if session_1 == "test_session_1":
        print_success("PASS: Session ID preserved (Clear Intent)")
    else:
        print_fail(f"FAIL: Session ID not preserved (Clear Intent): {session_1}")
        return False

    # Test 2: Ambiguous intent
    response_2 = send_message(
        token,
        "test_session_2",
        "I want a form"
    )

    session_2 = response_2.get("session_id")
    if session_2 == "test_session_2":
        print_success("PASS: Session ID preserved (Ambiguous Intent)")
    else:
        print_fail(f"FAIL: Session ID not preserved (Ambiguous Intent): {session_2}")
        return False

    return True

def main():
    """Run all tests"""
    print_header("Form Predictor Clarification Test Suite")

    try:
        # Login
        token = login()

        # Run tests
        test1_pass = test_clear_intent(token)
        test2_pass = test_ambiguous_intent(token)
        test3_pass = test_session_preservation(token)

        # Summary
        print()
        print_header("Test Suite Complete")

        total_tests = 3
        passed_tests = sum([test1_pass, test2_pass, test3_pass])

        if passed_tests == total_tests:
            print_success(f"All {total_tests} tests passed!")
            sys.exit(0)
        else:
            print_fail(f"{total_tests - passed_tests} test(s) failed")
            sys.exit(1)

    except Exception as e:
        print_fail(f"Test suite error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()