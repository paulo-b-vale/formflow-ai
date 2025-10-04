# app/models/database_schemas.py
"""
Database models and schemas for the form management system
"""
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field
from bson import ObjectId
from enum import Enum

class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic"""
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError('Invalid objectid')
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type='string')

# Form Field Types
class FieldType(str, Enum):
    TEXT = "text"
    NUMBER = "number"
    EMAIL = "email"
    DATE = "date"
    DATETIME = "datetime"
    SELECT = "select"
    MULTISELECT = "multiselect"
    RADIO = "radio"
    CHECKBOX = "checkbox"
    TEXTAREA = "textarea"
    FILE = "file"
    SIGNATURE = "signature"

class ValidationRule(BaseModel):
    """Validation rules for form fields"""
    required: bool = False
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[str] = None
    custom_message: Optional[str] = None

class FormField(BaseModel):
    """Individual form field definition"""
    id: str
    name: str
    label: str
    type: FieldType
    description: Optional[str] = None
    placeholder: Optional[str] = None
    default_value: Optional[Union[str, int, float, bool, List]] = None
    options: Optional[List[Dict[str, Any]]] = None  # For select, radio, etc.
    validation: ValidationRule = ValidationRule()
    conditional_logic: Optional[Dict[str, Any]] = None
    order: int = 0
    section: Optional[str] = None

class FormSection(BaseModel):
    """Form section grouping fields"""
    id: str
    title: str
    description: Optional[str] = None
    order: int = 0
    fields: List[str] = Field(default_factory=list)  # Field IDs in this section

class FormContext(BaseModel):
    """Form context information"""
    title: str
    department: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    use_cases: List[str] = Field(default_factory=list)

class FormTemplate(BaseModel):
    """Form template definition stored in MongoDB"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    title: str
    description: Optional[str] = None
    context: FormContext
    fields: List[FormField]
    sections: List[FormSection] = Field(default_factory=list)
    version: str = "1.0"
    status: str = "active"  # active, inactive, draft
    estimated_completion_time: Optional[str] = "5 minutes"
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# Form Submission Models
class FieldResponse(BaseModel):
    """Individual field response"""
    field_id: str
    field_name: str
    value: Optional[Union[str, int, float, bool, List, Dict]] = None
    file_attachments: List[str] = Field(default_factory=list)  # File IDs
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class FormSubmissionStatus(str, Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress" 
    COMPLETED = "completed"
    SUBMITTED = "submitted"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"

class FormSubmission(BaseModel):
    """Form submission stored in MongoDB"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    template_id: str
    template_version: str
    submitted_by: str
    submitted_by_name: Optional[str] = None
    session_id: Optional[str] = None
    
    # Response data
    responses: Dict[str, FieldResponse] = Field(default_factory=dict)
    completion_percentage: float = 0.0
    completed_fields: List[str] = Field(default_factory=list)
    missing_required_fields: List[str] = Field(default_factory=list)
    
    # Status and timing
    status: FormSubmissionStatus = FormSubmissionStatus.DRAFT
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    completion_time_seconds: Optional[int] = None
    
    # Review and approval
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_comments: Optional[str] = None
    
    # Metadata
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    location: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# Session Management Models
class SessionState(str, Enum):
    STARTING = "starting"
    ACTIVE = "active"
    FILLING_FORM = "filling_form"
    COMPLETED = "completed"
    ERROR = "error"
    EXPIRED = "expired"

class ConversationMessage(BaseModel):
    """Individual conversation message"""
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SessionData(BaseModel):
    """User session data"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    session_id: str = Field(unique=True)
    user_id: str
    user_name: Optional[str] = None
    
    # Current form context
    form_template_id: Optional[str] = None
    form_submission_id: Optional[str] = None
    current_field_id: Optional[str] = None
    
    # Session state
    state: SessionState = SessionState.STARTING
    conversation_history: List[ConversationMessage] = Field(default_factory=list)
    
    # Interactive context for follow-ups
    interaction_context: Dict[str, Any] = Field(default_factory=dict)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    
    # Confidence and prediction tracking
    prediction_confidence: Optional[float] = None
    alternative_forms: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Session metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# Analytics Models
class FormAnalytics(BaseModel):
    """Form analytics data"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    template_id: str
    date: datetime
    
    # Usage metrics
    total_starts: int = 0
    total_completions: int = 0
    total_submissions: int = 0
    completion_rate: float = 0.0
    
    # Timing metrics
    average_completion_time: float = 0.0
    median_completion_time: float = 0.0
    abandonment_points: Dict[str, int] = Field(default_factory=dict)
    
    # Field metrics
    field_completion_rates: Dict[str, float] = Field(default_factory=dict)
    field_error_rates: Dict[str, float] = Field(default_factory=dict)
    most_skipped_fields: List[str] = Field(default_factory=list)
    
    # User metrics
    unique_users: int = 0
    returning_users: int = 0
    user_segments: Dict[str, int] = Field(default_factory=dict)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# MongoDB Collection Schemas
MONGODB_COLLECTIONS = {
    "form_templates": {
        "validator": {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["title", "context", "fields", "created_by"],
                "properties": {
                    "title": {"bsonType": "string", "minLength": 1},
                    "description": {"bsonType": ["string", "null"]},
                    "context": {
                        "bsonType": "object",
                        "required": ["title"],
                        "properties": {
                            "title": {"bsonType": "string"},
                            "department": {"bsonType": ["string", "null"]},
                            "category": {"bsonType": ["string", "null"]},
                            "tags": {"bsonType": "array", "items": {"bsonType": "string"}},
                            "use_cases": {"bsonType": "array", "items": {"bsonType": "string"}}
                        }
                    },
                    "fields": {
                        "bsonType": "array",
                        "minItems": 1,
                        "items": {
                            "bsonType": "object",
                            "required": ["id", "name", "label", "type"],
                            "properties": {
                                "id": {"bsonType": "string"},
                                "name": {"bsonType": "string"},
                                "label": {"bsonType": "string"},
                                "type": {"enum": ["text", "number", "email", "date", "datetime", "select", "multiselect", "radio", "checkbox", "textarea", "file", "signature"]}
                            }
                        }
                    },
                    "status": {"enum": ["active", "inactive", "draft"]},
                    "version": {"bsonType": "string"},
                    "created_by": {"bsonType": "string"},
                    "created_at": {"bsonType": "date"},
                    "updated_at": {"bsonType": "date"}
                }
            }
        },
        "indexes": [
            {"title": 1, "status": 1},
            {"context.category": 1},
            {"context.department": 1},
            {"created_by": 1},
            {"status": 1, "created_at": -1},
            {"context.tags": 1}
        ]
    },
    
    "form_submissions": {
        "validator": {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["template_id", "submitted_by", "status"],
                "properties": {
                    "template_id": {"bsonType": "string"},
                    "submitted_by": {"bsonType": "string"},
                    "status": {"enum": ["draft", "in_progress", "completed", "submitted", "reviewed", "approved", "rejected"]},
                    "responses": {"bsonType": "object"},
                    "completion_percentage": {"bsonType": "number", "minimum": 0, "maximum": 100},
                    "started_at": {"bsonType": "date"},
                    "completed_at": {"bsonType": ["date", "null"]},
                    "submitted_at": {"bsonType": ["date", "null"]}
                }
            }
        },
        "indexes": [
            {"template_id": 1, "status": 1},
            {"submitted_by": 1, "submitted_at": -1},
            {"status": 1, "submitted_at": -1},
            {"template_id": 1, "submitted_by": 1},
            {"started_at": -1},
            {"completion_percentage": 1, "status": 1}
        ]
    },
    
    "user_sessions": {
        "validator": {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["session_id", "user_id", "state"],
                "properties": {
                    "session_id": {"bsonType": "string"},
                    "user_id": {"bsonType": "string"},
                    "state": {"enum": ["starting", "active", "filling_form", "completed", "error", "expired"]},
                    "form_template_id": {"bsonType": ["string", "null"]},
                    "created_at": {"bsonType": "date"},
                    "last_activity": {"bsonType": "date"},
                    "expires_at": {"bsonType": ["date", "null"]}
                }
            }
        },
        "indexes": [
            {"session_id": 1},
            {"user_id": 1, "last_activity": -1},
            {"expires_at": 1},  # For TTL cleanup
            {"form_template_id": 1, "state": 1},
            {"last_activity": -1}
        ]
    },
    
    "form_analytics": {
        "validator": {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["template_id", "date"],
                "properties": {
                    "template_id": {"bsonType": "string"},
                    "date": {"bsonType": "date"},
                    "total_starts": {"bsonType": "number", "minimum": 0},
                    "total_completions": {"bsonType": "number", "minimum": 0},
                    "completion_rate": {"bsonType": "number", "minimum": 0, "maximum": 1}
                }
            }
        },
        "indexes": [
            {"template_id": 1, "date": -1},
            {"date": -1},
            {"completion_rate": -1, "date": -1}
        ]
    }
}

# Database initialization functions
async def initialize_database(db):
    """Initialize database collections with schemas and indexes"""
    for collection_name, schema in MONGODB_COLLECTIONS.items():
        collection = db[collection_name]
        
        # Create collection with validator
        try:
            await db.create_collection(
                collection_name,
                validator=schema["validator"]
            )
            print(f"Created collection: {collection_name}")
        except Exception as e:
            if "already exists" not in str(e):
                print(f"Error creating collection {collection_name}: {e}")
        
        # Create indexes
        for index in schema["indexes"]:
            try:
                await collection.create_index(index)
                print(f"Created index on {collection_name}: {index}")
            except Exception as e:
                print(f"Error creating index on {collection_name}: {e}")

# Example form templates for testing
SAMPLE_FORM_TEMPLATES = [
    {
        "title": "Safety Incident Report",
        "description": "Report workplace safety incidents, near misses, and hazards",
        "context": {
            "title": "Safety Management",
            "department": "Safety",
            "category": "Incident Reporting",
            "tags": ["safety", "incident", "workplace", "emergency"],
            "use_cases": [
                "workplace accidents",
                "near miss reporting", 
                "equipment failures",
                "safety violations"
            ]
        },
        "fields": [
            {
                "id": "incident_date",
                "name": "incident_date",
                "label": "Date of Incident",
                "type": "datetime",
                "description": "When did the incident occur?",
                "validation": {"required": True},
                "order": 1
            },
            {
                "id": "incident_location",
                "name": "location",
                "label": "Location",
                "type": "text",
                "description": "Where did the incident occur?",
                "validation": {"required": True, "min_length": 3},
                "order": 2
            },
            {
                "id": "incident_type",
                "name": "incident_type", 
                "label": "Type of Incident",
                "type": "select",
                "options": [
                    {"value": "injury", "label": "Personal Injury"},
                    {"value": "near_miss", "label": "Near Miss"},
                    {"value": "equipment", "label": "Equipment Damage"},
                    {"value": "spill", "label": "Chemical Spill"},
                    {"value": "other", "label": "Other"}
                ],
                "validation": {"required": True},
                "order": 3
            },
            {
                "id": "severity",
                "name": "severity",
                "label": "Severity Level",
                "type": "radio",
                "options": [
                    {"value": "low", "label": "Low - No injury/damage"},
                    {"value": "medium", "label": "Medium - Minor injury/damage"},
                    {"value": "high", "label": "High - Serious injury/damage"},
                    {"value": "critical", "label": "Critical - Life threatening/major damage"}
                ],
                "validation": {"required": True},
                "order": 4
            },
            {
                "id": "description",
                "name": "description",
                "label": "Incident Description",
                "type": "textarea",
                "description": "Provide detailed description of what happened",
                "placeholder": "Describe the incident in detail...",
                "validation": {"required": True, "min_length": 20},
                "order": 5
            },
            {
                "id": "people_involved",
                "name": "people_involved",
                "label": "People Involved",
                "type": "textarea",
                "description": "Names and roles of people involved",
                "order": 6
            },
            {
                "id": "immediate_actions",
                "name": "immediate_actions",
                "label": "Immediate Actions Taken",
                "type": "textarea",
                "description": "What immediate actions were taken?",
                "validation": {"required": True},
                "order": 7
            },
            {
                "id": "photos",
                "name": "photos",
                "label": "Photos/Evidence",
                "type": "file",
                "description": "Upload photos or other evidence",
                "order": 8
            },
            {
                "id": "reporter_name",
                "name": "reporter_name",
                "label": "Reporter Name",
                "type": "text",
                "validation": {"required": True},
                "order": 9
            },
            {
                "id": "reporter_contact",
                "name": "reporter_contact",
                "label": "Reporter Contact",
                "type": "email",
                "validation": {"required": True},
                "order": 10
            }
        ],
        "sections": [
            {
                "id": "incident_details",
                "title": "Incident Details",
                "description": "Basic information about the incident",
                "order": 1,
                "fields": ["incident_date", "incident_location", "incident_type", "severity"]
            },
            {
                "id": "incident_description",
                "title": "Description & Actions",
                "description": "Detailed description and response",
                "order": 2,
                "fields": ["description", "people_involved", "immediate_actions"]
            },
            {
                "id": "reporter_info",
                "title": "Reporter Information",
                "description": "Contact information",
                "order": 3,
                "fields": ["photos", "reporter_name", "reporter_contact"]
            }
        ],
        "status": "active",
        "version": "1.0",
        "estimated_completion_time": "10 minutes",
        "created_by": "system"
    },
    
    {
        "title": "Daily Equipment Checklist",
        "description": "Daily inspection and maintenance checklist for equipment",
        "context": {
            "title": "Equipment Maintenance",
            "department": "Operations",
            "category": "Maintenance",
            "tags": ["equipment", "maintenance", "daily", "checklist", "inspection"],
            "use_cases": [
                "daily equipment checks",
                "preventive maintenance",
                "equipment inspection",
                "operational readiness"
            ]
        },
        "fields": [
            {
                "id": "check_date",
                "name": "check_date",
                "label": "Inspection Date",
                "type": "date",
                "validation": {"required": True},
                "default_value": "today",
                "order": 1
            },
            {
                "id": "equipment_id",
                "name": "equipment_id",
                "label": "Equipment ID/Name",
                "type": "text",
                "description": "Enter equipment identifier",
                "validation": {"required": True},
                "order": 2
            },
            {
                "id": "shift",
                "name": "shift",
                "label": "Shift",
                "type": "select",
                "options": [
                    {"value": "morning", "label": "Morning (6AM-2PM)"},
                    {"value": "afternoon", "label": "Afternoon (2PM-10PM)"},
                    {"value": "night", "label": "Night (10PM-6AM)"}
                ],
                "validation": {"required": True},
                "order": 3
            },
            {
                "id": "visual_inspection",
                "name": "visual_inspection",
                "label": "Visual Inspection",
                "type": "radio",
                "options": [
                    {"value": "pass", "label": "✅ Pass - No visible issues"},
                    {"value": "fail", "label": "❌ Fail - Issues found"}
                ],
                "validation": {"required": True},
                "order": 4
            },
            {
                "id": "operational_test",
                "name": "operational_test",
                "label": "Operational Test",
                "type": "radio",
                "options": [
                    {"value": "pass", "label": "✅ Pass - Operating normally"},
                    {"value": "fail", "label": "❌ Fail - Not operating properly"}
                ],
                "validation": {"required": True},
                "order": 5
            },
            {
                "id": "safety_features",
                "name": "safety_features",
                "label": "Safety Features Check",
                "type": "checkbox",
                "options": [
                    {"value": "guards_in_place", "label": "Guards in place"},
                    {"value": "emergency_stops", "label": "Emergency stops working"},
                    {"value": "warning_labels", "label": "Warning labels visible"},
                    {"value": "ppe_available", "label": "Required PPE available"}
                ],
                "validation": {"required": True},
                "order": 6
            },
            {
                "id": "issues_found",
                "name": "issues_found",
                "label": "Issues Found",
                "type": "textarea",
                "description": "Describe any issues, defects, or concerns",
                "placeholder": "Describe any problems found during inspection...",
                "order": 7,
                "conditional_logic": {
                    "show_when": {
                        "field": "visual_inspection",
                        "value": "fail"
                    }
                }
            },
            {
                "id": "actions_required",
                "name": "actions_required",
                "label": "Actions Required",
                "type": "multiselect",
                "options": [
                    {"value": "repair", "label": "Repair needed"},
                    {"value": "maintenance", "label": "Scheduled maintenance"},
                    {"value": "replacement", "label": "Part replacement"},
                    {"value": "cleaning", "label": "Deep cleaning required"},
                    {"value": "calibration", "label": "Calibration needed"},
                    {"value": "none", "label": "No action required"}
                ],
                "order": 8
            },
            {
                "id": "inspector_name",
                "name": "inspector_name",
                "label": "Inspector Name",
                "type": "text",
                "validation": {"required": True},
                "order": 9
            },
            {
                "id": "inspector_signature",
                "name": "inspector_signature",
                "label": "Digital Signature",
                "type": "signature",
                "description": "Sign to confirm inspection completion",
                "validation": {"required": True},
                "order": 10
            }
        ],
        "sections": [
            {
                "id": "basic_info",
                "title": "Basic Information",
                "order": 1,
                "fields": ["check_date", "equipment_id", "shift"]
            },
            {
                "id": "inspection_checks",
                "title": "Inspection Checks",
                "order": 2,
                "fields": ["visual_inspection", "operational_test", "safety_features"]
            },
            {
                "id": "issues_actions",
                "title": "Issues & Actions",
                "order": 3,
                "fields": ["issues_found", "actions_required"]
            },
            {
                "id": "sign_off",
                "title": "Inspector Sign-off",
                "order": 4,
                "fields": ["inspector_name", "inspector_signature"]
            }
        ],
        "status": "active",
        "version": "1.0",
        "estimated_completion_time": "5 minutes",
        "created_by": "system"
    }
]

# Database utility functions
async def seed_sample_forms(db):
    """Seed database with sample form templates"""
    forms_collection = db.form_templates
    
    for template_data in SAMPLE_FORM_TEMPLATES:
        # Check if form already exists
        existing = await forms_collection.find_one({"title": template_data["title"]})
        if not existing:
            template_data["created_at"] = datetime.utcnow()
            template_data["updated_at"] = datetime.utcnow()
            
            result = await forms_collection.insert_one(template_data)
            print(f"Created form template: {template_data['title']} (ID: {result.inserted_id})")
        else:
            print(f"Form template already exists: {template_data['title']}")

async def create_sample_submission(db, template_id: str, user_id: str):
    """Create a sample form submission for testing"""
    submissions_collection = db.form_submissions
    
    sample_submission = {
        "template_id": template_id,
        "template_version": "1.0",
        "submitted_by": user_id,
        "submitted_by_name": "Test User",
        "responses": {
            "incident_date": {
                "field_id": "incident_date",
                "field_name": "incident_date",
                "value": "2025-09-26T14:30:00Z",
                "timestamp": datetime.utcnow()
            },
            "incident_location": {
                "field_id": "incident_location", 
                "field_name": "location",
                "value": "Warehouse Section A",
                "timestamp": datetime.utcnow()
            },
            "incident_type": {
                "field_id": "incident_type",
                "field_name": "incident_type",
                "value": "near_miss",
                "timestamp": datetime.utcnow()
            }
        },
        "completion_percentage": 30.0,
        "completed_fields": ["incident_date", "incident_location", "incident_type"],
        "missing_required_fields": ["severity", "description", "immediate_actions", "reporter_name", "reporter_contact"],
        "status": "in_progress",
        "started_at": datetime.utcnow(),
        "completion_time_seconds": 120,
        "metadata": {"created_for": "testing"}
    }
    
    result = await submissions_collection.insert_one(sample_submission)
    print(f"Created sample submission: {result.inserted_id}")
    return result.inserted_id

# Usage example
async def setup_database():
    """Complete database setup example"""
    from motor.motor_asyncio import AsyncIOMotorClient
    
    # Connect to MongoDB
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.form_management_system
    
    # Initialize collections and schemas  
    await initialize_database(db)
    
    # Seed sample data
    await seed_sample_forms(db)
    
    # Create sample submissions
    forms = await db.form_templates.find({"status": "active"}).to_list(length=10)
    for form in forms:
        await create_sample_submission(db, str(form["_id"]), "test_user_123")
    
    print("Database setup complete!")
    return db

if __name__ == "__main__":
    import asyncio
    asyncio.run(setup_database())