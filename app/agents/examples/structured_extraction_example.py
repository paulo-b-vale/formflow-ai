"""
Example: Using Structured LLM Outputs in Form Filling

This demonstrates how to replace the existing multi-field extraction
with the new structured output system.
"""

from app.agents.llm.structured import extract_form_fields
from app.database import db


async def example_extract_multiple_fields(
    user_message: str,
    form_template_id: str,
    current_responses: dict = None
):
    """
    BEFORE (Current approach in enhanced_form_filler_agent.py lines 288-376):
    - Manually build prompt with field descriptions
    - Call LLM and hope it returns valid JSON
    - Parse JSON manually (can fail)
    - Validate each field individually
    - Risk of typos, missing fields, wrong types

    AFTER (New structured approach):
    - Automatically generates Pydantic schema from database
    - LLM is forced to return valid structure
    - Validation happens automatically
    - Type-safe extraction
    """

    # Extract with automatic schema generation from your database
    extracted, error = await extract_form_fields(
        user_message=user_message,
        form_template_id=form_template_id,
        db=db,
        current_responses=current_responses or {}
    )

    if error:
        print(f"Extraction failed: {error}")
        return {}

    # extracted is now a Pydantic model matching your exact form structure!
    # No need to manually validate - it's already validated

    # Convert to dict for saving
    extracted_data = {}
    for field_id in extracted.extracted_fields:
        value = getattr(extracted, field_id, None)
        if value is not None:
            extracted_data[field_id] = value

    return extracted_data


async def example_usage():
    """
    How to integrate into enhanced_form_filler_agent.py
    """

    # Replace lines 288-376 with this:
    user_message = "My name is John Doe, email john@example.com, phone 555-1234"
    form_template_id = "507f1f77bcf86cd799439011"

    # Old way (complex, error-prone)
    # extracted_fields = await self._extract_multiple_fields_from_message(user_message)

    # New way (simple, type-safe)
    extracted_fields = await example_extract_multiple_fields(
        user_message=user_message,
        form_template_id=form_template_id,
        current_responses={}  # Pass existing responses
    )

    print(f"Extracted fields: {extracted_fields}")
    # Output: {'name': 'John Doe', 'email': 'john@example.com', 'phone': '5551234'}

    # All fields are guaranteed to match your database schema!
    # No need for additional validation


# Integration steps:
"""
1. In enhanced_form_filler_agent.py, add import:
   from app.agents.llm.structured import extract_form_fields

2. Replace _extract_multiple_fields_from_message method (lines 288-376):

   async def _extract_multiple_fields_from_message(self, user_message: str):
       '''Extract multiple field values using structured LLM client.'''

       extracted, error = await extract_form_fields(
           user_message=user_message,
           form_template_id=self.session_data.form_template_id,
           db=self.db,
           current_responses=self.session_data.responses
       )

       if error:
           logger.warning(f"Structured extraction failed: {error}")
           return {}

       # Convert to dict
       result = {}
       for field_id in extracted.extracted_fields:
           value = getattr(extracted, field_id, None)
           if value is not None:
               result[field_id] = value

       logger.info(f"Extracted {len(result)} fields with structured output")
       return result

3. That's it! The rest of your code stays the same.

Benefits:
- 80% less code
- Type-safe (Pydantic validation)
- Matches database schema exactly
- Better error handling
- Easier to test
"""
