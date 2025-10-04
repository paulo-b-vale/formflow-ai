# 📡 FormFlow AI - API Documentation

## Table of Contents
- [Overview](#overview)
- [Authentication](#authentication)
- [API Endpoints](#api-endpoints)
  - [Authentication](#authentication-endpoints)
  - [Conversations](#conversation-endpoints)
  - [Forms Management](#forms-management-endpoints)
  - [Analytics & Reports](#analytics--reports-endpoints)
  - [File Management](#file-management-endpoints)
  - [Admin](#admin-endpoints)
- [Request/Response Formats](#requestresponse-formats)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Examples](#examples)

---

## Overview

**Base URL**: `http://localhost:8002` (development) or `https://your-domain.com/api` (production)

**API Version**: v1

**Protocol**: HTTPS (production)

**Content-Type**: `application/json`

**Interactive Documentation**:
- **Swagger UI**: `http://localhost:8002/docs`
- **ReDoc**: `http://localhost:8002/redoc`

---

## Authentication

FormFlow AI uses **JWT (JSON Web Token)** authentication.

### Authentication Flow

```
1. POST /auth/login → Returns access_token + refresh_token
2. Include in requests: Authorization: Bearer {access_token}
3. When access_token expires → POST /auth/refresh
4. Logout: Client discards tokens
```

### Token Details

| Token Type | Expiry | Purpose |
|-----------|--------|---------|
| Access Token | 60 minutes | API authentication |
| Refresh Token | 7 days | Renew access token |

### Headers Required

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json
```

---

## API Endpoints

### Authentication Endpoints

#### 1. Register User

Create a new user account.

```http
POST /auth/register
```

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "full_name": "John Silva",
  "role": "user"  // optional, defaults to "user"
}
```

**Response** (201 Created):
```json
{
  "user_id": "64f8a1234567890abcdef123",
  "email": "user@example.com",
  "full_name": "John Silva",
  "role": "user",
  "created_at": "2025-01-15T10:30:00Z",
  "is_active": true
}
```

**Errors**:
- `400`: Invalid email format or password too weak
- `409`: Email already registered

---

#### 2. Login

Authenticate and receive JWT tokens.

```http
POST /auth/login
Content-Type: application/x-www-form-urlencoded
```

**Request Body** (form-urlencoded):
```
username=user@example.com&password=SecurePass123!
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "user_id": "64f8a1234567890abcdef123",
    "email": "user@example.com",
    "full_name": "John Silva",
    "role": "user"
  }
}
```

**Errors**:
- `401`: Invalid credentials
- `403`: Account inactive or banned

---

#### 3. Refresh Token

Obtain a new access token using refresh token.

```http
POST /auth/refresh
Authorization: Bearer {refresh_token}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Errors**:
- `401`: Invalid or expired refresh token

---

#### 4. Get Current User

Retrieve authenticated user's information.

```http
GET /auth/me
Authorization: Bearer {access_token}
```

**Response** (200 OK):
```json
{
  "user_id": "64f8a1234567890abcdef123",
  "email": "user@example.com",
  "full_name": "John Silva",
  "role": "user",
  "created_at": "2025-01-10T08:00:00Z",
  "is_active": true
}
```

---

### Conversation Endpoints

#### 1. Send Message to AI

Send a message to the conversational AI assistant.

```http
POST /enhanced_conversation/message
Authorization: Bearer {access_token}
```

**Request Body**:
```json
{
  "session_id": "session-12345",  // optional, auto-generated if omitted
  "user_message": "I need to report a workplace incident",
  "metadata": {  // optional
    "source": "web",
    "language": "en"
  }
}
```

**Response** (200 OK):
```json
{
  "session_id": "session-12345",
  "ai_response": {
    "message": "🟢 I've identified that you want to fill an incident report (95% confidence). Let's get started. What is your name?",
    "response_type": "question",
    "metadata": {
      "agent": "form_filler",
      "intent": "form_filling",
      "form_id": "68d9625a4c602d9030f33d49",
      "form_title": "Workplace Incident Report",
      "confidence_score": 0.95,
      "reasoning": "Keywords 'report' and 'incident' strongly indicate incident reporting"
    }
  },
  "session_state": {
    "current_form_id": "68d9625a4c602d9030f33d49",
    "filled_fields": [],
    "unfilled_required_fields": ["name", "email", "incident_type", "location", "description"],
    "conversation_stage": "filling_form",
    "progress_percentage": 0
  },
  "timestamp": "2025-01-15T10:30:45Z"
}
```

**Possible response_type values**:
- `question`: AI asking for information
- `confirmation`: Requesting user confirmation
- `success`: Action completed successfully
- `error`: Error occurred
- `clarification`: Needs clarification

**Errors**:
- `401`: Unauthorized (invalid/missing token)
- `429`: Rate limit exceeded
- `500`: Internal server error

---

#### 2. List User Sessions

Retrieve all conversation sessions for the authenticated user.

```http
GET /enhanced_conversation/sessions
Authorization: Bearer {access_token}
```

**Query Parameters**:
- `limit` (optional, default: 20): Number of sessions to return
- `offset` (optional, default: 0): Pagination offset
- `status` (optional): Filter by status (`active`, `completed`, `archived`)

**Response** (200 OK):
```json
{
  "sessions": [
    {
      "session_id": "session-12345",
      "user_id": "64f8a1234567890abcdef123",
      "created_at": "2025-01-15T10:00:00Z",
      "updated_at": "2025-01-15T10:30:45Z",
      "status": "active",
      "current_form_id": "68d9625a4c602d9030f33d49",
      "form_title": "Workplace Incident Report",
      "progress_percentage": 40,
      "message_count": 8
    },
    {
      "session_id": "session-12344",
      "user_id": "64f8a1234567890abcdef123",
      "created_at": "2025-01-14T15:00:00Z",
      "updated_at": "2025-01-14T15:20:00Z",
      "status": "completed",
      "current_form_id": "68d9625a4c602d9030f33d48",
      "form_title": "Safety Evaluation",
      "progress_percentage": 100,
      "message_count": 12
    }
  ],
  "total": 2,
  "limit": 20,
  "offset": 0
}
```

---

#### 3. Get Session Details

Retrieve full conversation history for a specific session.

```http
GET /enhanced_conversation/sessions/{session_id}
Authorization: Bearer {access_token}
```

**Response** (200 OK):
```json
{
  "session_id": "session-12345",
  "user_id": "64f8a1234567890abcdef123",
  "created_at": "2025-01-15T10:00:00Z",
  "updated_at": "2025-01-15T10:30:45Z",
  "status": "active",
  "messages": [
    {
      "role": "user",
      "content": "I need to report a workplace incident",
      "timestamp": "2025-01-15T10:00:00Z"
    },
    {
      "role": "assistant",
      "content": "🟢 I've identified that you want to fill an incident report...",
      "timestamp": "2025-01-15T10:00:05Z",
      "metadata": {
        "agent": "form_predictor",
        "confidence": 0.95
      }
    },
    {
      "role": "user",
      "content": "John Silva",
      "timestamp": "2025-01-15T10:00:30Z"
    },
    {
      "role": "assistant",
      "content": "✅ Great! I've saved your name. What's your email address?",
      "timestamp": "2025-01-15T10:00:32Z",
      "metadata": {
        "agent": "form_filler",
        "extracted_fields": {"name": "John Silva"}
      }
    }
  ],
  "current_form": {
    "form_id": "68d9625a4c602d9030f33d49",
    "title": "Workplace Incident Report",
    "filled_fields": {"name": "John Silva"},
    "unfilled_required_fields": ["email", "incident_type", "location", "description"]
  }
}
```

**Errors**:
- `404`: Session not found
- `403`: Access denied (session belongs to another user)

---

#### 4. Delete Session

Clear a conversation session (soft delete - archives it).

```http
DELETE /enhanced_conversation/sessions/{session_id}
Authorization: Bearer {access_token}
```

**Response** (200 OK):
```json
{
  "message": "Session deleted successfully",
  "session_id": "session-12345"
}
```

---

### Forms Management Endpoints

#### 1. List Form Templates

Retrieve available form templates.

```http
GET /forms-management/templates
Authorization: Bearer {access_token}
```

**Query Parameters**:
- `category` (optional): Filter by category (`safety`, `evaluation`, `report`, etc.)
- `search` (optional): Search in title/description

**Response** (200 OK):
```json
{
  "templates": [
    {
      "form_id": "68d9625a4c602d9030f33d49",
      "title": "Workplace Incident Report",
      "description": "Document workplace safety incidents",
      "category": "safety",
      "fields": [
        {
          "name": "incident_type",
          "label": "Type of Incident",
          "type": "select",
          "required": true,
          "options": ["Accident", "Near Miss", "Property Damage"],
          "validation": {
            "type": "enum",
            "values": ["Accident", "Near Miss", "Property Damage"]
          }
        },
        {
          "name": "location",
          "label": "Location",
          "type": "text",
          "required": true,
          "placeholder": "e.g., Building 2, 3rd Floor",
          "validation": {
            "type": "string",
            "min_length": 3,
            "max_length": 200
          }
        },
        {
          "name": "description",
          "label": "Incident Description",
          "type": "textarea",
          "required": true,
          "placeholder": "Describe what happened...",
          "validation": {
            "type": "string",
            "min_length": 10
          }
        },
        {
          "name": "witnesses",
          "label": "Witnesses",
          "type": "text",
          "required": false
        }
      ],
      "created_at": "2025-01-01T00:00:00Z",
      "is_active": true
    }
  ],
  "total": 1
}
```

**Field Types**:
- `text`: Single-line text input
- `textarea`: Multi-line text
- `select`: Dropdown selection
- `multiselect`: Multiple choice
- `date`: Date picker
- `time`: Time picker
- `number`: Numeric input
- `email`: Email validation
- `phone`: Phone number
- `file`: File upload

---

#### 2. Get Form Template

Retrieve a specific form template.

```http
GET /forms-management/templates/{form_id}
Authorization: Bearer {access_token}
```

**Response** (200 OK):
```json
{
  "form_id": "68d9625a4c602d9030f33d49",
  "title": "Workplace Incident Report",
  "description": "Document workplace safety incidents",
  "category": "safety",
  "fields": [...],  // Same as in list
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-10T12:00:00Z",
  "is_active": true,
  "total_submissions": 156
}
```

---

#### 3. Create Form Template (Admin Only)

Create a new form template.

```http
POST /forms-management/templates
Authorization: Bearer {access_token}
```

**Request Body**:
```json
{
  "title": "Safety Evaluation Form",
  "description": "Monthly safety compliance check",
  "category": "evaluation",
  "fields": [
    {
      "name": "evaluator_name",
      "label": "Evaluator Name",
      "type": "text",
      "required": true,
      "validation": {
        "type": "string",
        "min_length": 2,
        "max_length": 100
      }
    },
    {
      "name": "safety_score",
      "label": "Safety Score (1-10)",
      "type": "number",
      "required": true,
      "validation": {
        "type": "number",
        "min": 1,
        "max": 10
      }
    }
  ]
}
```

**Response** (201 Created):
```json
{
  "form_id": "68d9625a4c602d9030f33d50",
  "title": "Safety Evaluation Form",
  "message": "Form template created successfully"
}
```

**Errors**:
- `403`: Forbidden (admin only)
- `400`: Invalid field definition

---

#### 4. List User's Form Responses

Retrieve form submissions by the authenticated user.

```http
GET /forms-management/responses
Authorization: Bearer {access_token}
```

**Query Parameters**:
- `form_id` (optional): Filter by specific form
- `status` (optional): Filter by status (`draft`, `complete`, `submitted`)
- `start_date` (optional): Filter from date (ISO 8601)
- `end_date` (optional): Filter to date (ISO 8601)
- `limit` (default: 20)
- `offset` (default: 0)

**Response** (200 OK):
```json
{
  "responses": [
    {
      "response_id": "66f8a1234567890abcdef123",
      "form_template_id": "68d9625a4c602d9030f33d49",
      "form_title": "Workplace Incident Report",
      "user_id": "64f8a1234567890abcdef123",
      "responses": {
        "incident_type": "Near Miss",
        "location": "Building 2, 3rd Floor - Welding Area",
        "description": "Material fell from scaffolding due to strong winds",
        "witnesses": "Jane Doe, Mike Johnson"
      },
      "status": "submitted",
      "submitted_at": "2025-01-15T10:45:00Z",
      "created_at": "2025-01-15T10:00:00Z",
      "conversation_session_id": "session-12345"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

---

#### 5. Get Form Response

Retrieve a specific form response.

```http
GET /forms-management/responses/{response_id}
Authorization: Bearer {access_token}
```

**Response** (200 OK):
```json
{
  "response_id": "66f8a1234567890abcdef123",
  "form_template_id": "68d9625a4c602d9030f33d49",
  "form_title": "Workplace Incident Report",
  "form_template": {
    "title": "Workplace Incident Report",
    "fields": [...]  // Full field definitions
  },
  "user_id": "64f8a1234567890abcdef123",
  "user_name": "John Silva",
  "responses": {
    "incident_type": "Near Miss",
    "location": "Building 2, 3rd Floor - Welding Area",
    "description": "Material fell from scaffolding due to strong winds",
    "witnesses": "Jane Doe, Mike Johnson"
  },
  "status": "submitted",
  "submitted_at": "2025-01-15T10:45:00Z",
  "created_at": "2025-01-15T10:00:00Z",
  "conversation_session_id": "session-12345"
}
```

---

#### 6. Submit Form Response

Manually submit a form (without conversation).

```http
POST /forms-management/responses
Authorization: Bearer {access_token}
```

**Request Body**:
```json
{
  "form_template_id": "68d9625a4c602d9030f33d49",
  "responses": {
    "incident_type": "Accident",
    "location": "Warehouse A",
    "description": "Forklift collision with storage rack",
    "witnesses": "Bob Smith"
  }
}
```

**Response** (201 Created):
```json
{
  "response_id": "66f8a1234567890abcdef124",
  "message": "Form response submitted successfully",
  "submitted_at": "2025-01-15T11:00:00Z"
}
```

**Errors**:
- `400`: Missing required fields or validation errors
- `404`: Form template not found

---

### Analytics & Reports Endpoints

#### 1. Generate AI Report

Generate an analytical report using AI.

```http
POST /reports/generate
Authorization: Bearer {access_token}
```

**Request Body**:
```json
{
  "report_type": "incidents_summary",  // or "safety_trends", "user_activity"
  "filters": {
    "start_date": "2025-01-01T00:00:00Z",
    "end_date": "2025-01-31T23:59:59Z",
    "form_ids": ["68d9625a4c602d9030f33d49"],  // optional
    "categories": ["safety"]  // optional
  },
  "format": "markdown"  // or "pdf", "json"
}
```

**Response** (200 OK):
```json
{
  "report_id": "report-12345",
  "report_type": "incidents_summary",
  "generated_at": "2025-01-15T11:15:00Z",
  "content": {
    "title": "Workplace Incidents Summary - January 2025",
    "summary": "# Executive Summary\n\nDuring January 2025, a total of 23 incidents were reported...",
    "statistics": {
      "total_incidents": 23,
      "by_type": {
        "Accident": 5,
        "Near Miss": 15,
        "Property Damage": 3
      },
      "trend": "decreasing",
      "top_locations": [
        {"location": "Building 2", "count": 8},
        {"location": "Warehouse A", "count": 6}
      ]
    },
    "insights": [
      "Near miss incidents increased by 20% compared to previous month",
      "Building 2 remains the highest risk area",
      "Weekend incidents are 30% lower than weekdays"
    ],
    "recommendations": [
      "Increase safety inspections in Building 2",
      "Conduct additional safety training for welding area",
      "Review scaffolding procedures"
    ]
  },
  "metadata": {
    "data_points_analyzed": 156,
    "ai_model": "gemini-pro",
    "generation_time_ms": 2340
  }
}
```

**Report Types**:
- `incidents_summary`: Incident statistics and trends
- `safety_trends`: Safety compliance over time
- `user_activity`: User engagement metrics
- `form_performance`: Form completion rates
- `custom`: Custom query (provide `query` parameter)

---

#### 2. Get Analytics Dashboard

Retrieve dashboard metrics.

```http
GET /reports/analytics
Authorization: Bearer {access_token}
```

**Query Parameters**:
- `period` (optional, default: `30d`): Time period (`7d`, `30d`, `90d`, `1y`)

**Response** (200 OK):
```json
{
  "period": "30d",
  "generated_at": "2025-01-15T11:20:00Z",
  "metrics": {
    "total_forms_submitted": 156,
    "total_conversations": 203,
    "active_users": 45,
    "average_form_completion_time": 420,  // seconds
    "form_completion_rate": 0.92,  // 92%
    "top_forms": [
      {
        "form_id": "68d9625a4c602d9030f33d49",
        "title": "Workplace Incident Report",
        "submissions": 89
      },
      {
        "form_id": "68d9625a4c602d9030f33d48",
        "title": "Safety Evaluation",
        "submissions": 67
      }
    ],
    "user_satisfaction": {
      "average_confidence_score": 0.87,
      "high_confidence_interactions": 0.78
    }
  },
  "charts": {
    "submissions_over_time": [
      {"date": "2025-01-01", "count": 4},
      {"date": "2025-01-02", "count": 7},
      // ...
    ],
    "forms_by_category": {
      "safety": 120,
      "evaluation": 36
    }
  }
}
```

---

### File Management Endpoints

#### 1. Upload File

Upload a file (images, PDFs, documents).

```http
POST /files/upload
Authorization: Bearer {access_token}
Content-Type: multipart/form-data
```

**Form Data**:
- `file`: File binary
- `category` (optional): File category (`incident_photo`, `document`, `signature`)
- `description` (optional): File description

**Response** (201 Created):
```json
{
  "file_id": "file-12345",
  "filename": "incident_photo.jpg",
  "url": "https://storage.formflow.ai/uploads/user-123/file-12345.jpg",
  "size_bytes": 245678,
  "mime_type": "image/jpeg",
  "uploaded_at": "2025-01-15T11:30:00Z"
}
```

**Limits**:
- Max file size: 10MB
- Allowed types: images (jpg, png, gif), documents (pdf, docx), archives (zip)

---

#### 2. Get File

Retrieve file metadata or download file.

```http
GET /files/{file_id}
Authorization: Bearer {access_token}
```

**Response** (200 OK):
```json
{
  "file_id": "file-12345",
  "filename": "incident_photo.jpg",
  "url": "https://storage.formflow.ai/uploads/user-123/file-12345.jpg",
  "size_bytes": 245678,
  "mime_type": "image/jpeg",
  "category": "incident_photo",
  "uploaded_at": "2025-01-15T11:30:00Z",
  "uploaded_by": "64f8a1234567890abcdef123"
}
```

**Download**:
```http
GET /files/{file_id}/download
Authorization: Bearer {access_token}
```

Returns file binary with appropriate Content-Type header.

---

### Admin Endpoints

#### 1. List All Users (Admin Only)

```http
GET /admin/users
Authorization: Bearer {access_token}
```

**Response** (200 OK):
```json
{
  "users": [
    {
      "user_id": "64f8a1234567890abcdef123",
      "email": "user@example.com",
      "full_name": "John Silva",
      "role": "user",
      "created_at": "2025-01-10T08:00:00Z",
      "is_active": true,
      "total_forms_submitted": 12,
      "last_activity": "2025-01-15T10:30:00Z"
    }
  ],
  "total": 1
}
```

---

#### 2. Update User (Admin Only)

```http
PATCH /admin/users/{user_id}
Authorization: Bearer {access_token}
```

**Request Body**:
```json
{
  "role": "admin",  // optional
  "is_active": false  // optional
}
```

**Response** (200 OK):
```json
{
  "message": "User updated successfully",
  "user_id": "64f8a1234567890abcdef123"
}
```

---

## Request/Response Formats

### Standard Response Structure

**Success Response**:
```json
{
  "data": {...},  // Response payload
  "timestamp": "2025-01-15T11:30:00Z",
  "request_id": "req-abc123"  // For support/debugging
}
```

**Error Response**:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input: email is required",
    "details": {
      "field": "email",
      "reason": "required_field_missing"
    }
  },
  "timestamp": "2025-01-15T11:30:00Z",
  "request_id": "req-abc123"
}
```

### Error Codes

| HTTP Status | Error Code | Description |
|------------|-----------|-------------|
| 400 | `VALIDATION_ERROR` | Invalid request data |
| 401 | `UNAUTHORIZED` | Missing or invalid authentication |
| 403 | `FORBIDDEN` | Insufficient permissions |
| 404 | `NOT_FOUND` | Resource not found |
| 409 | `CONFLICT` | Resource conflict (e.g., duplicate email) |
| 429 | `RATE_LIMIT_EXCEEDED` | Too many requests |
| 500 | `INTERNAL_SERVER_ERROR` | Server error |
| 503 | `SERVICE_UNAVAILABLE` | Service temporarily unavailable |

---

## Rate Limiting

**Limits**:
- Anonymous: 10 requests/minute
- Authenticated users: 100 requests/minute
- Admin users: 500 requests/minute

**Headers**:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1673785200
```

**Rate Limit Response** (429):
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Please try again in 45 seconds.",
    "retry_after": 45
  }
}
```

---

## Examples

### Complete Flow Example (Python)

```python
import requests

BASE_URL = "http://localhost:8002"

# 1. Register
response = requests.post(f"{BASE_URL}/auth/register", json={
    "email": "john@example.com",
    "password": "SecurePass123!",
    "full_name": "John Silva"
})
print(response.json())

# 2. Login
response = requests.post(f"{BASE_URL}/auth/login", data={
    "username": "john@example.com",
    "password": "SecurePass123!"
})
tokens = response.json()
access_token = tokens["access_token"]

# 3. Send message to AI
headers = {"Authorization": f"Bearer {access_token}"}
response = requests.post(
    f"{BASE_URL}/enhanced_conversation/message",
    headers=headers,
    json={
        "user_message": "I need to report a workplace incident"
    }
)
ai_response = response.json()
print(f"AI: {ai_response['ai_response']['message']}")

# 4. Continue conversation
session_id = ai_response["session_id"]
response = requests.post(
    f"{BASE_URL}/enhanced_conversation/message",
    headers=headers,
    json={
        "session_id": session_id,
        "user_message": "John Silva, john@example.com"
    }
)
print(f"AI: {response.json()['ai_response']['message']}")

# 5. Get form responses
response = requests.get(
    f"{BASE_URL}/forms-management/responses",
    headers=headers
)
print(f"Total submissions: {response.json()['total']}")
```

### cURL Examples

```bash
# Login
curl -X POST "http://localhost:8002/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=john@example.com&password=SecurePass123!"

# Send message
curl -X POST "http://localhost:8002/enhanced_conversation/message" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_message": "I need to report an incident"
  }'

# List forms
curl -X GET "http://localhost:8002/forms-management/templates" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Generate report
curl -X POST "http://localhost:8002/reports/generate" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "report_type": "incidents_summary",
    "filters": {
      "start_date": "2025-01-01T00:00:00Z",
      "end_date": "2025-01-31T23:59:59Z"
    },
    "format": "markdown"
  }'
```

### JavaScript (Axios) Example

```javascript
import axios from 'axios';

const API = axios.create({
  baseURL: 'http://localhost:8002',
  headers: {
    'Content-Type': 'application/json'
  }
});

// Interceptor to add auth token
API.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Login
async function login(email, password) {
  const formData = new URLSearchParams();
  formData.append('username', email);
  formData.append('password', password);

  const response = await API.post('/auth/login', formData, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
  });

  localStorage.setItem('access_token', response.data.access_token);
  return response.data;
}

// Send message
async function sendMessage(message, sessionId = null) {
  const response = await API.post('/enhanced_conversation/message', {
    user_message: message,
    session_id: sessionId
  });
  return response.data;
}

// Get forms
async function getForms() {
  const response = await API.get('/forms-management/templates');
  return response.data.templates;
}

// Usage
(async () => {
  await login('john@example.com', 'SecurePass123!');
  const aiResponse = await sendMessage('I need to report an incident');
  console.log('AI:', aiResponse.ai_response.message);
})();
```

---

## WebSocket Support (Future)

Real-time conversation updates will be available via WebSocket:

```javascript
const ws = new WebSocket('ws://localhost:8002/ws/conversation');

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'auth',
    token: 'YOUR_ACCESS_TOKEN'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('AI response:', data.message);
};
```

---

## Versioning

API versioning is handled via URL prefix:
- Current: `/api/v1/...`
- Future: `/api/v2/...`

When breaking changes are introduced, a new version will be released while maintaining backward compatibility for at least 6 months.

---

## Support

For API support:
- 📧 **Email**: api-support@formflow-ai.com
- 📖 **Interactive Docs**: `http://localhost:8002/docs`
- 💬 **Issues**: [GitHub Issues](https://github.com/YOUR_USERNAME/formflow-ai/issues)

---

**Last Updated**: January 2025
