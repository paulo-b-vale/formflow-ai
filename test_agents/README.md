# Agent Test Suite

This test suite provides comprehensive testing for the form filling and report generation agents.

## Prerequisites

Before running the tests, make sure:

1. Docker containers are running:
   ```bash
   docker-compose up -d
   ```

2. The admin user exists (if not, create it):
   ```bash
   python create_admin_user.py
   ```

## Running the Tests

Execute the test suite with:

```bash
python test_agents.py
```

## What the Test Suite Tests

The test suite performs the following checks:

### 1. Authentication
- Tests login API with admin credentials
- Acquires and validates authentication token

### 2. Context Management
- Creates a test context in the database
- Validates context creation

### 3. Form Template Management
- Creates a test form with multiple field types
- Validates form creation and storage

### 4. Form Filling via Conversation
- Simulates a conversation with the EnhancedFormFillerAgent
- Provides answers to form questions
- Tests form submission

### 5. Form Response Retrieval
- Tests API endpoints for retrieving form responses
- Validates data integrity

### 6. Analytics Dashboard
- Tests the analytics reporting endpoint
- (May have known issues with the current implementation)

## Expected Output

The test suite will show:
- ✅ for successful tests
- ❌ for failed tests
- ⚠️ for tests with known issues
- Detailed summary of all tests

## Test Results

After running, the suite will provide:
- Individual test results
- Overall pass/fail summary  
- IDs of created test objects for manual verification
- Direct links to access created resources

## Troubleshooting

If tests fail:

1. Check if all Docker containers are running:
   ```bash
   docker-compose ps
   ```

2. Verify the API is accessible:
   ```bash
   curl http://localhost:8002/health
   ```

3. Check the application logs:
   ```bash
   docker-compose logs app
   ```