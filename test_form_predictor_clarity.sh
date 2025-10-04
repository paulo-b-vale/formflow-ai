#!/bin/bash

# Test script for form predictor clarification fix
# Tests that clear intent gets direct form assignment and ambiguous intent shows alternatives

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

API_URL="http://localhost:8002"
TEST_EMAIL="ana.costa@usuario.com"
TEST_PASSWORD="test123"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Form Predictor Clarification Test Suite${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Step 1: Login and get token
echo -e "${YELLOW}[1/4] Logging in as ${TEST_EMAIL}...${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "${API_URL}/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=${TEST_EMAIL}&password=${TEST_PASSWORD}")

TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import json, sys; print(json.load(sys.stdin)['tokens']['access_token'])" 2>/dev/null)

if [ -z "$TOKEN" ]; then
    echo -e "${RED}✗ Login failed${NC}"
    echo "$LOGIN_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✓ Login successful${NC}\n"

# Test 1: Clear Intent - Should NOT ask for clarification
echo -e "${YELLOW}[2/4] Test 1: Clear Intent (Construction Incident)${NC}"
echo -e "Message: 'I need to fill a construction incident form'"

RESPONSE_1=$(curl -s -X POST "${API_URL}/enhanced_conversation/message" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{
    "session_id": "test_clear_intent",
    "user_message": "I need to fill a construction incident form",
    "form_id": null
  }')

# Check if response contains direct form assignment indicators
if echo "$RESPONSE_1" | grep -q "Vamos começar\|começar\|Pergunta 1"; then
    echo -e "${GREEN}✓ PASS: Direct form assignment (no clarification)${NC}"
    FORM_TITLE=$(echo "$RESPONSE_1" | python3 -c "import json, sys, re; r=json.load(sys.stdin)['response']; m=re.search(r\"'(.+?)'\", r); print(m.group(1) if m else 'Unknown')" 2>/dev/null)
    echo -e "  Assigned form: ${BLUE}${FORM_TITLE}${NC}"
else
    echo -e "${RED}✗ FAIL: Should have assigned form directly${NC}"
    echo -e "  Response: $(echo "$RESPONSE_1" | python3 -c "import json, sys; print(json.load(sys.stdin)['response'][:150])" 2>/dev/null)"
fi

echo ""

# Test 2: Ambiguous Intent - Should ask for clarification
echo -e "${YELLOW}[3/4] Test 2: Ambiguous Intent${NC}"
echo -e "Message: 'I want to fill out a form'"

RESPONSE_2=$(curl -s -X POST "${API_URL}/enhanced_conversation/message" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{
    "session_id": "test_ambiguous_intent",
    "user_message": "I want to fill out a form",
    "form_id": null
  }')

# Check if response shows alternatives
if echo "$RESPONSE_2" | grep -q "Escolha uma opção\|Choose an option"; then
    echo -e "${GREEN}✓ PASS: Shows form alternatives (requires clarification)${NC}"

    # Count alternatives
    ALT_COUNT=$(echo "$RESPONSE_2" | grep -o "\*\*[0-9]\." | wc -l)
    echo -e "  Number of alternatives shown: ${BLUE}${ALT_COUNT}${NC}"

    # Check if user message is preserved
    if echo "$RESPONSE_2" | grep -q "I want to fill out a form"; then
        echo -e "${GREEN}✓ User message preserved in response${NC}"
    else
        echo -e "${RED}✗ User message NOT preserved${NC}"
    fi
else
    echo -e "${RED}✗ FAIL: Should show alternatives for clarification${NC}"
    echo -e "  Response: $(echo "$RESPONSE_2" | python3 -c "import json, sys; print(json.load(sys.stdin)['response'][:150])" 2>/dev/null)"
fi

echo ""

# Test 3: Session ID preservation
echo -e "${YELLOW}[4/4] Test 3: Session ID Preservation${NC}"

SESSION_1=$(echo "$RESPONSE_1" | python3 -c "import json, sys; print(json.load(sys.stdin).get('session_id', 'None'))" 2>/dev/null)
SESSION_2=$(echo "$RESPONSE_2" | python3 -c "import json, sys; print(json.load(sys.stdin).get('session_id', 'None'))" 2>/dev/null)

if [ "$SESSION_1" = "test_clear_intent" ]; then
    echo -e "${GREEN}✓ PASS: Session ID preserved (Test 1)${NC}"
else
    echo -e "${RED}✗ FAIL: Session ID not preserved (Test 1): ${SESSION_1}${NC}"
fi

if [ "$SESSION_2" = "test_ambiguous_intent" ]; then
    echo -e "${GREEN}✓ PASS: Session ID preserved (Test 2)${NC}"
else
    echo -e "${RED}✗ FAIL: Session ID not preserved (Test 2): ${SESSION_2}${NC}"
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test Suite Complete${NC}"
echo -e "${BLUE}========================================${NC}"