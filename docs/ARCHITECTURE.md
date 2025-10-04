# 🏗️ FormFlow AI - System Architecture

## Table of Contents
- [Overview](#overview)
- [High-Level Architecture](#high-level-architecture)
- [Component Details](#component-details)
- [AI Agent System](#ai-agent-system)
- [Data Flow](#data-flow)
- [Technology Stack](#technology-stack)
- [Design Patterns](#design-patterns)
- [Scalability](#scalability)

---

## Overview

FormFlow AI is a full-stack conversational AI system built using a microservices-oriented architecture. The system leverages advanced language models (Google Gemini and OpenAI) orchestrated through LangGraph to provide intelligent form filling capabilities through natural language conversations.

### Key Architectural Principles

1. **Separation of Concerns**: Clear boundaries between agents, services, and data layers
2. **Asynchronous Processing**: Non-blocking operations for high performance
3. **Stateful Conversations**: Redis-backed session management for context retention
4. **Observability**: Comprehensive tracing and logging throughout the system
5. **Modularity**: Pluggable components for easy testing and extension

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            Client Layer                                  │
├──────────────────┬──────────────────┬─────────────────┬─────────────────┤
│   Next.js Web    │  WhatsApp Bot    │   Mobile App    │   REST API      │
│   Application    │  (Puppeteer)     │  (Future)       │   Clients       │
└────────┬─────────┴────────┬─────────┴────────┬────────┴────────┬────────┘
         │                  │                  │                 │
         └──────────────────┼──────────────────┼─────────────────┘
                            │
                ┌───────────▼───────────┐
                │   API Gateway Layer   │
                │   FastAPI Routers     │
                └───────────┬───────────┘
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
    ┌────▼─────┐     ┌──────▼──────┐    ┌─────▼─────┐
    │  Auth    │     │ Conversation │    │  Forms    │
    │ Service  │     │   Service    │    │  Service  │
    └──────────┘     └──────┬───────┘    └───────────┘
                            │
                ┌───────────▼────────────┐
                │   AI Agent Layer       │
                │  (LangGraph Workflow)  │
                ├────────────────────────┤
                │  • Router Node         │
                │  • Form Predictor      │
                │  • Form Filler         │
                │  • Clarification       │
                │  • Report Generator    │
                └───────────┬────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
    ┌────▼─────┐     ┌──────▼──────┐    ┌─────▼─────┐
    │ MongoDB  │     │    Redis    │    │ MinIO/S3  │
    │ Database │     │    Cache    │    │  Storage  │
    └──────────┘     └─────────────┘    └───────────┘
                            │
                ┌───────────▼────────────┐
                │   External Services    │
                ├────────────────────────┤
                │  • Google Gemini API   │
                │  • OpenAI API          │
                │  • LangChain/LangGraph │
                └────────────────────────┘
```

---

## Component Details

### 1. **Frontend Layer (Next.js)**

**Location**: `frontend/`

```
frontend/
├── src/
│   ├── components/        # React components
│   │   ├── ChatInterface.tsx
│   │   ├── FormDisplay.tsx
│   │   └── Analytics.tsx
│   ├── pages/            # Next.js pages (routing)
│   │   ├── index.tsx     # Landing page
│   │   ├── chat.tsx      # Chat interface
│   │   └── dashboard.tsx # Analytics dashboard
│   ├── hooks/            # Custom React hooks
│   │   ├── useChat.ts
│   │   └── useAuth.ts
│   └── services/         # API client services
│       └── api.ts
└── public/               # Static assets
```

**Responsibilities**:
- User interface rendering
- State management (React hooks)
- API communication with backend
- Real-time message display
- Form visualization

**Key Technologies**:
- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- React Hook Form
- Axios for API calls

---

### 2. **API Layer (FastAPI)**

**Location**: `app/routers/`

```python
# Main routers
- auth_router.py          # Authentication endpoints
- enhanced_conversation_router.py  # Chat endpoints
- forms_router.py         # Form management
- analytics_router.py     # Analytics & reports
- file_router.py          # File uploads
- admin_router.py         # Admin operations
```

**Endpoints Architecture**:

```
/auth/
  POST /login           # Authenticate user
  POST /register        # Create account
  POST /refresh         # Refresh token

/enhanced_conversation/
  POST /message         # Send message to AI
  GET  /sessions        # List user sessions
  DELETE /session/{id}  # Clear session

/forms-management/
  GET  /templates       # List forms
  POST /templates       # Create form (admin)
  GET  /responses       # User's responses
  POST /responses       # Submit form

/reports/
  POST /generate        # Generate AI report
  GET  /analytics       # Get metrics
```

**Middleware Stack**:
1. CORS middleware (configured origins)
2. Authentication middleware (JWT validation)
3. Rate limiting middleware (prevent abuse)
4. Error handling middleware (standardized responses)
5. Logging middleware (request/response tracing)

---

### 3. **Service Layer**

**Location**: `app/services/`

Business logic is separated from routing:

```python
# Core services
enhanced_conversation_service.py  # Main conversation logic
forms_service.py                   # Form CRUD operations
auth_service.py                    # User authentication
analytics_service.py               # Report generation
file_service.py                    # S3 file handling
```

**Service Pattern**:

```python
class EnhancedConversationService(BaseService):
    def __init__(self, db, redis_cache):
        self.db = db
        self.cache = redis_cache
        self.agent_orchestrator = AgentOrchestrator()

    async def process_message(
        self,
        user_id: str,
        session_id: str,
        message: str
    ) -> Dict:
        # 1. Load session state
        # 2. Call agent orchestrator
        # 3. Update session state
        # 4. Return response
```

---

### 4. **AI Agent System (LangGraph)**

**Location**: `app/agents/`

The heart of FormFlow AI - a graph-based workflow of specialized agents.

#### Agent Workflow Graph

```
                    ┌──────────────┐
                    │   START      │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  Router Node │  (Classify intent)
                    └──────┬───────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
    ┌──────▼──────┐ ┌──────▼──────┐ ┌─────▼──────┐
    │ Form Search │ │   General   │ │   Report   │
    │    Intent   │ │    Query    │ │  Generator │
    └──────┬──────┘ └──────┬──────┘ └─────┬──────┘
           │               │               │
    ┌──────▼──────────┐    │               │
    │ Form Predictor  │    │               │
    │  (Select Form)  │    │               │
    └──────┬──────────┘    │               │
           │               │               │
    ┌──────▼──────────┐    │               │
    │  Form Filler    │    │               │
    │ (Multi-turn)    │◄───┤ (If needed)   │
    └──────┬──────────┘    │               │
           │               │               │
           │        ┌──────▼──────┐        │
           │        │Clarification│        │
           │        │    Node     │        │
           │        └──────┬──────┘        │
           │               │               │
           └───────────────┼───────────────┘
                           │
                    ┌──────▼───────┐
                    │   Response   │
                    │  Generation  │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │     END      │
                    └──────────────┘
```

#### Agent Node Details

**1. Router Node** (`app/agents/nodes/router.py`)
```python
class RouterNode(BaseNode):
    """
    Classifies user intent into:
    - form_filling: User wants to fill a form
    - report_generation: User wants a report
    - general_query: General question
    - clarification_needed: Ambiguous input
    """
    async def process(self, state: AgentState) -> AgentState:
        intent = await self._classify_intent(state.user_message)
        state.intent = intent
        return state
```

**2. Form Predictor Node** (`app/agents/enhanced_form_predictor_node.py`)
```python
class FormPredictorNode(BaseNode):
    """
    Selects the most appropriate form based on:
    - User message content
    - Available form templates
    - Conversation history
    - Confidence scoring
    """
    async def predict_form(self, user_message: str) -> FormPrediction:
        # Uses LLM with structured output
        # Returns: form_id, confidence_score, reasoning
```

**3. Form Filler Node** (`app/agents/nodes/form_filler.py`)
```python
class FormFillerNode(BaseNode):
    """
    Handles multi-turn conversation for form filling:
    - Extracts fields from messages
    - Asks for missing required fields
    - Validates field values
    - Confirms before submission
    """
    async def fill_form(self, state: AgentState) -> AgentState:
        # Multi-field extraction
        # Field validation
        # Next question generation
```

**4. Clarification Node** (`app/agents/nodes/clarification.py`)
```python
class ClarificationNode(BaseNode):
    """
    Handles ambiguous situations:
    - Multiple possible forms
    - Unclear user intent
    - Validation failures
    """
    async def clarify(self, state: AgentState) -> AgentState:
        # Generate clarifying question
        # Present options to user
```

**5. Report Generator Node** (`app/agents/report_generator_node.py`)
```python
class ReportGeneratorNode(BaseNode):
    """
    Generates analytical reports:
    - Queries database for relevant data
    - Uses LLM for analysis
    - Formats output
    """
    async def generate_report(self, query: str) -> str:
        # Data aggregation
        # AI-powered insights
        # Report formatting
```

---

### 5. **Advanced Features**

#### **A. Confidence Tracking System**

**Location**: `app/agents/reasoning/confidence.py`

```python
class ConfidenceTracker:
    """
    Tracks decision confidence with reasoning chains.
    """
    def start_reasoning_chain(
        self,
        decision_id: str,
        decision_type: str,
        initial_input: Dict
    ) -> ReasoningChain:
        # Creates new reasoning chain
        # Tracks all steps and confidence levels

    def add_reasoning_step(
        self,
        chain: ReasoningChain,
        step_type: str,
        confidence: float,
        reasoning: str,
        evidence: List[str]
    ):
        # Adds step to reasoning chain
        # Calculates cumulative confidence

    def get_confidence_explanation(
        self,
        chain: ReasoningChain,
        for_user: bool = True
    ) -> str:
        # Returns user-friendly or developer explanation
```

**Confidence Levels**:
- 🟢 **VERY_HIGH (>90%)**: Proceed automatically
- 🟢 **HIGH (80-90%)**: Proceed with confirmation
- 🟡 **MEDIUM (50-80%)**: Ask for confirmation
- 🔴 **LOW (<50%)**: Request clarification

#### **B. Prompt Management System**

**Location**: `app/agents/prompts/manager.py`

```python
class PromptManager:
    """
    Centralized prompt versioning and performance tracking.
    """
    def register_prompt(self, template: PromptTemplate):
        # Version control for prompts

    def execute_prompt(
        self,
        template_id: str,
        llm_function: Callable,
        **variables
    ) -> PromptResult:
        # Executes prompt with tracking
        # Records performance metrics

    def get_prompt_performance(self, template_id: str) -> Dict:
        # Returns success rate, avg time, etc.
```

#### **C. Execution Tracing**

**Location**: `app/agents/observability/tracer.py`

```python
class ExecutionTracer:
    """
    Traces every step of agent execution for debugging.
    """
    @trace_execution(TraceEventType.LLM_CALL, "Form Prediction")
    async def predict_form(self, message: str):
        # Automatically traced
        # Captures input, output, timing, errors

    def get_debug_info(self, session_id: str) -> Dict:
        # Returns full execution trace
        # Hierarchical view of operations
```

---

### 6. **Data Layer**

#### **MongoDB Collections**

```javascript
// users
{
  "_id": ObjectId,
  "email": "user@example.com",
  "hashed_password": "bcrypt_hash",
  "full_name": "John Doe",
  "role": "user",  // user | admin
  "created_at": ISODate,
  "is_active": true
}

// form_templates
{
  "_id": ObjectId,
  "title": "Incident Report Form",
  "description": "Safety incident documentation",
  "fields": [
    {
      "name": "incident_type",
      "label": "Type of Incident",
      "type": "select",
      "required": true,
      "options": ["Accident", "Near Miss", "Property Damage"]
    },
    {
      "name": "location",
      "label": "Location",
      "type": "text",
      "required": true
    }
  ],
  "category": "safety",
  "created_at": ISODate
}

// form_responses
{
  "_id": ObjectId,
  "form_template_id": ObjectId,
  "user_id": ObjectId,
  "responses": {
    "incident_type": "Near Miss",
    "location": "Construction Site - Building 2",
    "description": "Material fell from scaffolding"
  },
  "status": "complete",  // draft | complete | submitted
  "submitted_at": ISODate,
  "conversation_session_id": "session-123"
}

// conversation_logs
{
  "_id": ObjectId,
  "session_id": "session-123",
  "user_id": ObjectId,
  "messages": [
    {
      "role": "user",
      "content": "I need to report an incident",
      "timestamp": ISODate
    },
    {
      "role": "assistant",
      "content": "I'll help you with that. What type of incident?",
      "timestamp": ISODate,
      "metadata": {
        "agent": "form_predictor",
        "confidence": 0.95
      }
    }
  ],
  "created_at": ISODate,
  "updated_at": ISODate
}

// session_data (also in Redis)
{
  "_id": "session-123",
  "user_id": ObjectId,
  "current_form_id": ObjectId,
  "filled_fields": ["name", "email"],
  "unfilled_fields": ["location", "description"],
  "conversation_state": "filling_form",
  "last_activity": ISODate,
  "expires_at": ISODate
}
```

#### **Redis Cache Structure**

```redis
# Session data (TTL: 30 minutes)
session:{session_id} -> JSON serialized session state

# User authentication (TTL: 1 hour)
auth_token:{token} -> user_id

# Form template cache (TTL: 1 hour)
form_templates:all -> JSON array of templates

# Rate limiting (TTL: 1 minute)
rate_limit:{user_id}:{endpoint} -> request_count
```

---

### 7. **Session Management**

**Location**: `app/sessions/session_manager.py`

```python
class SessionManager:
    """
    Manages conversation sessions with Redis + MongoDB.
    """
    async def get_or_create_session(
        self,
        user_id: str,
        session_id: str
    ) -> SessionData:
        # Try Redis first (fast)
        # Fall back to MongoDB
        # Create if not exists

    async def update_session(
        self,
        session_id: str,
        updates: Dict
    ):
        # Update both Redis and MongoDB
        # Ensure consistency

    async def clear_session(self, session_id: str):
        # Remove from Redis
        # Archive in MongoDB
```

**Session State Machine**:

```
idle → form_searching → form_predicted → filling_form →
confirming → submitted → idle
```

---

### 8. **Authentication & Security**

#### JWT Token Structure

```python
# Access Token (15 min expiry)
{
  "sub": "user_id",
  "email": "user@example.com",
  "role": "user",
  "exp": 1234567890,
  "iat": 1234567890
}

# Refresh Token (7 days expiry)
{
  "sub": "user_id",
  "type": "refresh",
  "exp": 1234567890
}
```

#### Security Layers

1. **Password Security**
   - Bcrypt hashing (12 rounds)
   - Minimum 8 characters requirement

2. **API Security**
   - JWT Bearer token authentication
   - Token expiration enforcement
   - Refresh token rotation

3. **Rate Limiting**
   - Per-user, per-endpoint limits
   - Redis-backed counter
   - Configurable thresholds

4. **Input Validation**
   - Pydantic schema validation
   - SQL/NoSQL injection prevention
   - XSS sanitization

---

## Data Flow

### Example: Form Filling Flow

```
1. User sends message: "I need to report a workplace accident"

2. Frontend → POST /enhanced_conversation/message
   ├─ Headers: Authorization: Bearer {jwt_token}
   └─ Body: {session_id, user_message}

3. API Router → EnhancedConversationService
   ├─ Validate JWT token
   ├─ Check rate limits
   └─ Call service layer

4. Service → Load session state
   ├─ Check Redis cache
   └─ Fall back to MongoDB

5. Service → Agent Orchestrator
   ├─ Invoke LangGraph workflow
   └─ Pass session state + message

6. Agent Graph Execution:
   ├─ Router Node: Classify intent = "form_filling"
   ├─ Form Predictor: Identify form = "Incident Report" (95% confidence)
   ├─ Form Filler: Extract fields (none yet), ask first question
   └─ Return: "What is your name?"

7. Service → Update session
   ├─ Save to Redis (fast)
   ├─ Save to MongoDB (persistent)
   └─ Log conversation

8. Service → Return response
   └─ Format: {message, metadata, session_state}

9. Frontend receives response
   ├─ Display AI message
   ├─ Update UI state
   └─ Wait for user input

10. User responds: "John Silva"

11. Repeat steps 2-9:
    ├─ Form Filler: Extract name = "John Silva"
    ├─ Form Filler: Ask next question: "What's your email?"
    └─ Continue until form complete

12. Form completion:
    ├─ Confirmation step
    ├─ User confirms
    └─ Save to form_responses collection

13. Return success message
    └─ Session state → idle
```

---

## Technology Stack

### Backend
| Technology | Version | Purpose |
|-----------|---------|---------|
| Python | 3.11+ | Core language |
| FastAPI | 0.104+ | Web framework |
| MongoDB | 7.0+ | Primary database |
| Redis | 7.2+ | Cache & sessions |
| Google Gemini | Latest | Primary LLM |
| OpenAI GPT | 4+ | Secondary LLM |
| LangChain | 0.1+ | LLM framework |
| LangGraph | 0.0.30+ | Agent orchestration |
| Pydantic | 2.0+ | Data validation |
| Motor | 3.3+ | Async MongoDB driver |
| Passlib | 1.7+ | Password hashing |
| Python-Jose | 3.3+ | JWT handling |

### Frontend
| Technology | Version | Purpose |
|-----------|---------|---------|
| Next.js | 14+ | React framework |
| React | 18+ | UI library |
| TypeScript | 5+ | Type safety |
| Tailwind CSS | 3+ | Styling |
| Axios | 1.6+ | HTTP client |
| React Hook Form | 7+ | Form management |

### Infrastructure
| Technology | Purpose |
|-----------|---------|
| Docker | Containerization |
| Docker Compose | Multi-container orchestration |
| MinIO | S3-compatible storage |
| Nginx | Reverse proxy (production) |

---

## Design Patterns

### 1. **Repository Pattern**
Services interact with data through repository abstractions:

```python
class FormRepository:
    async def get_by_id(self, form_id: str) -> FormTemplate
    async def list_all(self) -> List[FormTemplate]
    async def create(self, form: FormTemplate) -> FormTemplate
```

### 2. **Strategy Pattern**
Different LLM providers can be swapped:

```python
class LLMStrategy(ABC):
    @abstractmethod
    async def invoke(self, prompt: str) -> str

class GeminiStrategy(LLMStrategy):
    async def invoke(self, prompt: str) -> str:
        # Gemini-specific implementation

class OpenAIStrategy(LLMStrategy):
    async def invoke(self, prompt: str) -> str:
        # OpenAI-specific implementation
```

### 3. **Observer Pattern**
Event-driven updates for session state changes:

```python
class SessionObserver(ABC):
    @abstractmethod
    async def on_session_update(self, session: SessionData)

class ConversationLogger(SessionObserver):
    async def on_session_update(self, session: SessionData):
        # Log to MongoDB

class CacheUpdater(SessionObserver):
    async def on_session_update(self, session: SessionData):
        # Update Redis
```

### 4. **Decorator Pattern**
Tracing and monitoring:

```python
@trace_execution(TraceEventType.LLM_CALL, "Form Prediction")
@cache_result(ttl=300)
@retry(max_attempts=3)
async def predict_form(message: str) -> FormPrediction:
    # Core logic
```

---

## Scalability

### Horizontal Scaling Strategies

1. **Stateless API Servers**
   - All state in Redis/MongoDB
   - Deploy multiple FastAPI instances
   - Load balancer distributes traffic

2. **Database Scaling**
   - MongoDB replica sets for read scaling
   - Sharding by user_id for write scaling
   - Redis cluster for cache distribution

3. **Async Processing**
   - Long-running tasks → background jobs (Celery)
   - Message queue (RabbitMQ/Redis)
   - Separate worker processes

4. **Caching Strategy**
   - Form templates (1 hour TTL)
   - User sessions (30 min TTL)
   - LLM responses (query-based caching)

5. **CDN for Static Assets**
   - Frontend hosted on Vercel/Netlify
   - S3/MinIO behind CloudFront

### Performance Optimizations

1. **Database Indexing**
   ```python
   # Indexes (see add_performance_indexes.py)
   users: ["email" (unique), "created_at"]
   form_templates: ["category", "created_at"]
   form_responses: ["user_id", "form_template_id", "submitted_at"]
   conversation_logs: ["session_id", "user_id", "updated_at"]
   ```

2. **Connection Pooling**
   - MongoDB: Motor connection pool (max 100)
   - Redis: Connection pool (max 50)

3. **Async Operations**
   - All I/O operations are async
   - Non-blocking LLM calls
   - Concurrent database queries

---

## Monitoring & Observability

### Metrics to Track

1. **Application Metrics**
   - Request rate (req/sec)
   - Response time (p50, p95, p99)
   - Error rate (%)
   - Active sessions

2. **AI Metrics**
   - LLM call latency
   - Token usage
   - Confidence scores distribution
   - Form prediction accuracy

3. **Infrastructure Metrics**
   - CPU/Memory usage
   - Database connections
   - Redis memory usage
   - API rate limit hits

### Logging Strategy

```python
# Structured logging
logger.info(
    "form_predicted",
    extra={
        "session_id": session_id,
        "form_id": form_id,
        "confidence": 0.95,
        "latency_ms": 234
    }
)
```

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────┐
│              Production Environment              │
├─────────────────────────────────────────────────┤
│                                                  │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐       │
│  │  API-1  │   │  API-2  │   │  API-3  │       │
│  └────┬────┘   └────┬────┘   └────┬────┘       │
│       └─────────────┼─────────────┘             │
│                     │                            │
│             ┌───────▼────────┐                   │
│             │ Load Balancer  │                   │
│             │    (Nginx)     │                   │
│             └───────┬────────┘                   │
│                     │                            │
│  ┌──────────────────┼──────────────────┐        │
│  │                  │                  │        │
│  ▼                  ▼                  ▼        │
│ MongoDB          Redis              MinIO       │
│ Replica Set      Cluster            Cluster     │
│                                                  │
└─────────────────────────────────────────────────┘
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions.

---

## Future Architectural Enhancements

1. **Microservices Split**
   - Form service
   - Auth service
   - AI agent service
   - Analytics service

2. **Event-Driven Architecture**
   - Kafka/RabbitMQ for event streaming
   - Event sourcing for audit trail
   - CQRS pattern

3. **GraphQL API**
   - Alternative to REST
   - Client-specific queries
   - Real-time subscriptions

4. **Service Mesh**
   - Istio for microservices
   - Advanced traffic management
   - Enhanced observability

---

## Conclusion

FormFlow AI's architecture is designed for:
- 🚀 **Performance**: Async operations, caching, connection pooling
- 🔒 **Security**: Multi-layer authentication and validation
- 📈 **Scalability**: Stateless design, horizontal scaling ready
- 🔍 **Observability**: Comprehensive tracing and logging
- 🧩 **Modularity**: Clean separation of concerns, pluggable components

This architecture supports the current feature set while providing a solid foundation for future growth and enhancements.
