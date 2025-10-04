"""
Field validation utilities for form processing.

This module handles validation of different field types with AI assistance
for complex validation scenarios.
"""

import re
import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class FieldValidator:
    """Handles validation of form fields with type-specific rules."""

    def __init__(self):
        self.validation_cache = {}

    async def validate_field_response(self, field: Dict, user_response: str) -> Dict[str, Any]:
        """
        Enhanced field validation with AI assistance for complex fields.

        Args:
            field: Field definition containing type, validation rules, etc.
            user_response: User's input to validate

        Returns:
            Dict containing validation result, processed value, and suggestions
        """
        field_type = field.get("field_type", "text")
        field_id = field.get("field_id")
        validation_result = {
            "is_valid": True,
            "processed_value": user_response.strip(),
            "suggestions": [],
            "warning": None
        }

        try:
            # Route to appropriate validation method
            if field_type == "email":
                validation_result = await self._validate_email(user_response, validation_result)
            elif field_type == "phone":
                validation_result = await self._validate_phone(user_response, validation_result)
            elif field_type == "number":
                validation_result = await self._validate_number(user_response, validation_result)
            elif field_type == "date":
                validation_result = await self._validate_date(user_response, validation_result)
            elif field_type == "url":
                validation_result = await self._validate_url(user_response, validation_result)
            elif field_type == "currency":
                validation_result = await self._validate_currency(user_response, validation_result)
            elif field_type in ["text", "textarea"]:
                validation_result = await self._validate_text(field, user_response, validation_result)

            # Apply field-specific constraints
            if field.get("required") and not user_response.strip():
                validation_result["is_valid"] = False
                validation_result["suggestions"] = ["This field is required."]

            # Check length constraints
            min_length = field.get("min_length")
            max_length = field.get("max_length")

            if min_length and len(user_response.strip()) < min_length:
                validation_result["is_valid"] = False
                validation_result["suggestions"].append(f"Minimum length is {min_length} characters.")

            if max_length and len(user_response.strip()) > max_length:
                validation_result["is_valid"] = False
                validation_result["suggestions"].append(f"Maximum length is {max_length} characters.")

        except Exception as e:
            logger.error(f"Error validating field {field_id}: {str(e)}")
            validation_result["is_valid"] = False
            validation_result["suggestions"] = ["Validation error occurred. Please try again."]

        return validation_result

    async def _validate_email(self, user_response: str, validation_result: Dict) -> Dict:
        """Validate email field."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, user_response.strip()):
            validation_result["is_valid"] = False
            validation_result["suggestions"] = ["Please provide a valid email address (e.g., user@example.com)"]
        return validation_result

    async def _validate_phone(self, user_response: str, validation_result: Dict) -> Dict:
        """Validate phone field."""
        # Remove common separators and check if it's a reasonable phone number
        clean_phone = re.sub(r'[\s\-\(\)\+]', '', user_response)
        if not clean_phone.isdigit() or len(clean_phone) < 7:
            validation_result["is_valid"] = False
            validation_result["suggestions"] = ["Please provide a valid phone number (e.g., +1-555-123-4567)"]
        else:
            validation_result["processed_value"] = clean_phone
        return validation_result

    async def _validate_number(self, user_response: str, validation_result: Dict) -> Dict:
        """Validate numeric field."""
        try:
            float(user_response.strip())
            validation_result["processed_value"] = user_response.strip()
        except ValueError:
            validation_result["is_valid"] = False
            validation_result["suggestions"] = ["Please provide a valid number."]
        return validation_result

    async def _validate_date(self, user_response: str, validation_result: Dict) -> Dict:
        """Validate date field."""
        date_formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S']
        parsed_date = None

        for date_format in date_formats:
            try:
                parsed_date = datetime.strptime(user_response.strip(), date_format)
                validation_result["processed_value"] = parsed_date.strftime('%Y-%m-%d')
                break
            except ValueError:
                continue

        if not parsed_date:
            validation_result["is_valid"] = False
            validation_result["suggestions"] = ["Please provide a valid date (YYYY-MM-DD, MM/DD/YYYY, or DD/MM/YYYY)"]

        return validation_result

    async def _validate_url(self, user_response: str, validation_result: Dict) -> Dict:
        """Validate URL field."""
        url_pattern = r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'
        if not re.match(url_pattern, user_response.strip()):
            validation_result["is_valid"] = False
            validation_result["suggestions"] = ["Please provide a valid URL (e.g., https://example.com)"]
        return validation_result

    async def _validate_currency(self, user_response: str, validation_result: Dict) -> Dict:
        """Validate currency field."""
        # Remove currency symbols and validate as number
        clean_value = re.sub(r'[\$,€£¥]', '', user_response.strip())
        try:
            float(clean_value)
            validation_result["processed_value"] = clean_value
        except ValueError:
            validation_result["is_valid"] = False
            validation_result["suggestions"] = ["Please provide a valid currency amount (e.g., $100.00 or 100)"]
        return validation_result

    async def _validate_text(self, field: Dict, user_response: str, validation_result: Dict) -> Dict:
        """Validate text/textarea fields."""
        # Add any pattern validation if specified in field
        pattern = field.get("validation_pattern")
        if pattern:
            try:
                if not re.match(pattern, user_response.strip()):
                    validation_result["is_valid"] = False
                    validation_result["suggestions"] = [f"Input doesn't match required pattern: {pattern}"]
            except re.error:
                logger.warning(f"Invalid regex pattern in field {field.get('field_id')}: {pattern}")

        return validation_result

    def get_confidence_display(self, confidence_score: float) -> str:
        """Generate a user-friendly confidence indicator."""
        if confidence_score >= 0.9:
            return "🟢 Very confident"
        elif confidence_score >= 0.7:
            return "🟡 Moderately confident"
        elif confidence_score >= 0.5:
            return "🟠 Low confidence"
        else:
            return "🔴 Very uncertain"

    def clear_cache(self):
        """Clear validation cache."""
        self.validation_cache.clear()