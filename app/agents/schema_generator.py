"""
Dynamic Pydantic Schema Generator
Generates type-safe Pydantic models from database form templates.
This ensures LLMs output correctly structured JSONs matching your exact form schemas.
"""

from typing import Dict, Any, List, Optional, Type, Union
from pydantic import BaseModel, Field, create_model, validator
from datetime import datetime
from enum import Enum
import logging
from bson import ObjectId

logger = logging.getLogger(__name__)


class FieldType(str, Enum):
    """Form field types that map to Python types"""
    TEXT = "text"
    EMAIL = "email"
    PHONE = "phone"
    NUMBER = "number"
    DATE = "date"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    SELECT = "select"
    MULTISELECT = "multiselect"
    TEXTAREA = "textarea"
    FILE = "file"
    URL = "url"


# Mapping from form field types to Python types
FIELD_TYPE_MAPPING = {
    FieldType.TEXT: str,
    FieldType.EMAIL: str,
    FieldType.PHONE: str,
    FieldType.NUMBER: float,
    FieldType.DATE: str,  # ISO format string
    FieldType.DATETIME: str,  # ISO format string
    FieldType.BOOLEAN: bool,
    FieldType.SELECT: str,
    FieldType.MULTISELECT: List[str],
    FieldType.TEXTAREA: str,
    FieldType.FILE: str,  # File ID
    FieldType.URL: str,
}


class SchemaGenerator:
    """
    Generates Pydantic schemas dynamically from database form templates.
    These schemas are used to enforce structured outputs from LLMs.
    """

    def __init__(self, db):
        self.db = db
        self._schema_cache: Dict[str, Type[BaseModel]] = {}

    async def generate_form_response_schema(
        self,
        form_template_id: str,
        include_metadata: bool = True
    ) -> Type[BaseModel]:
        """
        Generate a Pydantic schema for a specific form template.
        This schema matches the exact structure of the form in your database.

        Args:
            form_template_id: MongoDB ObjectId of the form template
            include_metadata: Whether to include metadata fields

        Returns:
            Dynamically created Pydantic model class
        """
        # Check cache first
        cache_key = f"{form_template_id}_{include_metadata}"
        if cache_key in self._schema_cache:
            logger.debug(f"Using cached schema for form {form_template_id}")
            return self._schema_cache[cache_key]

        # Fetch form template from database
        form_template = await self.db.form_templates.find_one(
            {"_id": ObjectId(form_template_id)}
        )

        if not form_template:
            raise ValueError(f"Form template {form_template_id} not found")

        logger.info(f"Generating schema for form: {form_template.get('title', 'Unknown')}")

        # Build field definitions
        field_definitions = {}
        validators_dict = {}

        for field in form_template.get("fields", []):
            field_id = field.get("field_id")
            field_type = field.get("field_type", "text")
            field_label = field.get("label", field_id)
            field_description = field.get("description", "")
            is_required = field.get("required", False)
            options = field.get("options", [])
            examples = field.get("examples", [])

            # Get Python type for this field
            python_type = FIELD_TYPE_MAPPING.get(
                FieldType(field_type),
                str
            )

            # Make optional if not required
            if not is_required:
                python_type = Optional[python_type]

            # Build field kwargs
            field_kwargs = {
                "description": f"{field_label}: {field_description}".strip(),
            }

            # Add examples to description if available
            if examples:
                field_kwargs["description"] += f" (Examples: {', '.join(examples)})"

            # Handle default values
            if not is_required:
                if field_type == FieldType.BOOLEAN:
                    field_kwargs["default"] = None
                elif field_type == FieldType.MULTISELECT:
                    field_kwargs["default"] = []
                else:
                    field_kwargs["default"] = None
            else:
                field_kwargs["default"] = ...  # Required field

            # Add enum constraint for select fields
            if field_type == FieldType.SELECT and options:
                # Create an Enum for valid options
                field_kwargs["description"] += f" (Valid options: {', '.join(options)})"

            # Add validation for select fields
            if field_type == FieldType.SELECT and options:
                # Create validator to ensure value is in options
                validator_name = f"validate_{field_id}"
                validators_dict[validator_name] = validator(field_id, allow_reuse=True)(
                    self._create_select_validator(options, field_label)
                )

            # Add validation for email fields
            if field_type == FieldType.EMAIL:
                validator_name = f"validate_{field_id}"
                validators_dict[validator_name] = validator(field_id, allow_reuse=True)(
                    self._create_email_validator(field_label)
                )

            # Add validation for phone fields
            if field_type == FieldType.PHONE:
                validator_name = f"validate_{field_id}"
                validators_dict[validator_name] = validator(field_id, allow_reuse=True)(
                    self._create_phone_validator(field_label)
                )

            # Add validation for number fields
            if field_type == FieldType.NUMBER:
                min_value = field.get("min_value")
                max_value = field.get("max_value")
                if min_value is not None:
                    field_kwargs["ge"] = min_value
                if max_value is not None:
                    field_kwargs["le"] = max_value

            # Create Field
            field_definitions[field_id] = (python_type, Field(**field_kwargs))

        # Add metadata fields if requested
        if include_metadata:
            field_definitions.update({
                "session_id": (str, Field(..., description="Session identifier")),
                "form_template_id": (str, Field(..., description="Form template ID")),
                "respondent_id": (str, Field(..., description="User ID")),
                "confidence_scores": (
                    Optional[Dict[str, float]],
                    Field(default=None, description="Confidence score per field")
                ),
                "extraction_metadata": (
                    Optional[Dict[str, Any]],
                    Field(default=None, description="Additional extraction metadata")
                ),
            })

        # Create the dynamic model
        model_name = f"FormResponse_{form_template.get('title', 'Unknown').replace(' ', '_')}"

        dynamic_model = create_model(
            model_name,
            **field_definitions,
            __validators__=validators_dict,
        )

        # Cache the schema
        self._schema_cache[cache_key] = dynamic_model

        logger.info(f"Created schema {model_name} with {len(field_definitions)} fields")

        return dynamic_model

    @staticmethod
    def _create_select_validator(options: List[str], field_label: str):
        """Create a validator function for select fields"""
        def validate_select(cls, v):
            if v is not None and v not in options:
                raise ValueError(
                    f"{field_label} must be one of: {', '.join(options)}. Got: {v}"
                )
            return v
        return validate_select

    @staticmethod
    def _create_email_validator(field_label: str):
        """Create a validator function for email fields"""
        import re
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

        def validate_email(cls, v):
            if v is not None and not email_pattern.match(v):
                raise ValueError(f"{field_label} must be a valid email address")
            return v
        return validate_email

    @staticmethod
    def _create_phone_validator(field_label: str):
        """Create a validator function for phone fields"""
        import re

        def validate_phone(cls, v):
            if v is not None:
                # Remove common separators
                clean_phone = re.sub(r'[\s\-\(\)\+]', '', v)
                if not clean_phone.isdigit() or len(clean_phone) < 7:
                    raise ValueError(f"{field_label} must be a valid phone number")
            return v
        return validate_phone

    async def generate_form_extraction_schema(
        self,
        form_template_id: str
    ) -> Type[BaseModel]:
        """
        Generate a schema for extracting data from user messages.
        This is what the LLM uses to structure its extraction output.

        Args:
            form_template_id: Form template ID

        Returns:
            Pydantic model for extraction
        """
        # Get form template
        form_template = await self.db.form_templates.find_one(
            {"_id": ObjectId(form_template_id)}
        )

        if not form_template:
            raise ValueError(f"Form template {form_template_id} not found")

        # Build field definitions (all optional for extraction)
        field_definitions = {}

        for field in form_template.get("fields", []):
            field_id = field.get("field_id")
            field_type = field.get("field_type", "text")
            field_label = field.get("label", field_id)
            field_description = field.get("description", "")

            # Get Python type
            python_type = FIELD_TYPE_MAPPING.get(
                FieldType(field_type),
                str
            )

            # All fields optional for extraction (since we might not extract everything)
            python_type = Optional[python_type]

            # Create Field
            field_definitions[field_id] = (
                python_type,
                Field(
                    default=None,
                    description=f"Extracted value for {field_label}: {field_description}"
                )
            )

        # Add metadata
        field_definitions.update({
            "extracted_fields": (
                List[str],
                Field(default=[], description="List of field IDs that were extracted")
            ),
            "confidence_per_field": (
                Dict[str, float],
                Field(default={}, description="Confidence score per extracted field")
            ),
            "needs_clarification": (
                Optional[List[str]],
                Field(default=None, description="Fields that need clarification")
            ),
        })

        model_name = f"Extraction_{form_template.get('title', 'Unknown').replace(' ', '_')}"

        return create_model(model_name, **field_definitions)

    async def get_form_schema_json(
        self,
        form_template_id: str,
        schema_type: str = "response"
    ) -> Dict[str, Any]:
        """
        Get JSON Schema representation for a form.
        This is what you send to the LLM as part of the prompt.

        Args:
            form_template_id: Form template ID
            schema_type: "response" or "extraction"

        Returns:
            JSON Schema dict
        """
        if schema_type == "response":
            schema_model = await self.generate_form_response_schema(form_template_id)
        else:
            schema_model = await self.generate_form_extraction_schema(form_template_id)

        return schema_model.model_json_schema()

    async def validate_llm_output(
        self,
        form_template_id: str,
        llm_output: Dict[str, Any],
        schema_type: str = "response"
    ) -> tuple[bool, Optional[BaseModel], Optional[str]]:
        """
        Validate LLM output against the form schema.

        Args:
            form_template_id: Form template ID
            llm_output: Raw output from LLM
            schema_type: "response" or "extraction"

        Returns:
            Tuple of (is_valid, parsed_model, error_message)
        """
        try:
            if schema_type == "response":
                schema_model = await self.generate_form_response_schema(form_template_id)
            else:
                schema_model = await self.generate_form_extraction_schema(form_template_id)

            # Validate and parse
            parsed = schema_model(**llm_output)
            return True, parsed, None

        except Exception as e:
            logger.error(f"Validation failed for form {form_template_id}: {e}")
            return False, None, str(e)

    def clear_cache(self):
        """Clear schema cache"""
        self._schema_cache.clear()
        logger.info("Schema cache cleared")


# Helper function to create schema generator instances
def create_schema_generator(db) -> SchemaGenerator:
    """Create a SchemaGenerator instance"""
    return SchemaGenerator(db)
