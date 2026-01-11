"""
Structured LLM Output Module
Handles forcing LLMs to return properly structured JSON based on Pydantic schemas.

This module integrates with your schema_generator to ensure LLMs return
data that matches your exact database form structures.
"""

import json
import logging
from typing import Type, TypeVar, Optional, Dict, Any, List
from pydantic import BaseModel, ValidationError

from app.agents.schema_generator import SchemaGenerator
from app.utils.langchain_utils import get_gemini_llm
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class StructuredLLMClient:
    """
    LLM client that enforces structured outputs via Pydantic schemas.

    This ensures LLMs return JSON that matches your database schemas exactly,
    preventing data corruption and validation errors.
    """

    def __init__(self, db=None):
        self.llm = get_gemini_llm()
        self.schema_generator = SchemaGenerator(db) if db else None
        self._cache = {}

    async def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_retries: int = 2
    ) -> tuple[Optional[T], Optional[str]]:
        """
        Generate structured output from LLM based on Pydantic schema.

        Args:
            prompt: User prompt
            schema: Pydantic model class to enforce
            system_prompt: Optional system instructions
            temperature: LLM temperature (lower = more deterministic)
            max_retries: Max retry attempts on validation failure

        Returns:
            Tuple of (parsed_model, error_message)
        """
        # Get JSON schema from Pydantic model
        json_schema = schema.model_json_schema()

        # Build enhanced prompt with schema
        enhanced_prompt = self._build_schema_prompt(prompt, json_schema)

        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=enhanced_prompt))

        for attempt in range(max_retries + 1):
            try:
                # Call LLM
                response = await self.llm.ainvoke(messages, temperature=temperature)
                raw_output = response.content

                # Parse JSON
                parsed_json = self._extract_json(raw_output)

                # Validate against Pydantic schema
                validated = schema(**parsed_json)

                logger.debug(f"Successfully generated structured output (attempt {attempt + 1})")
                return validated, None

            except ValidationError as e:
                error_msg = f"Validation error: {str(e)}"
                logger.warning(f"Attempt {attempt + 1} failed: {error_msg}")

                if attempt < max_retries:
                    # Add error feedback to next attempt
                    messages.append(HumanMessage(
                        content=f"Your previous response had validation errors:\n{error_msg}\n\n"
                                f"Please try again, ensuring all required fields are present and have correct types."
                    ))
                else:
                    return None, error_msg

            except json.JSONDecodeError as e:
                error_msg = f"JSON parsing error: {str(e)}"
                logger.warning(f"Attempt {attempt + 1} failed: {error_msg}")

                if attempt < max_retries:
                    messages.append(HumanMessage(
                        content=f"Your previous response was not valid JSON:\n{error_msg}\n\n"
                                f"Please respond with ONLY valid JSON, no additional text."
                    ))
                else:
                    return None, error_msg

            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                logger.error(f"Attempt {attempt + 1} failed: {error_msg}")
                return None, error_msg

        return None, "Max retries exceeded"

    async def extract_form_data(
        self,
        user_message: str,
        form_template_id: str,
        current_responses: Dict[str, Any] = None
    ) -> tuple[Optional[BaseModel], Optional[str]]:
        """
        Extract form data from user message using the actual form schema.

        This generates a Pydantic schema from your database form template,
        then forces the LLM to return data matching that exact structure.

        Args:
            user_message: User's input message
            form_template_id: Form template ID from database
            current_responses: Already collected responses

        Returns:
            Tuple of (extracted_data, error_message)
        """
        if not self.schema_generator:
            return None, "Schema generator not initialized with database"

        try:
            # Generate extraction schema from database
            extraction_schema = await self.schema_generator.generate_form_extraction_schema(
                form_template_id
            )

            # Build context-aware prompt
            prompt = self._build_extraction_prompt(
                user_message,
                extraction_schema,
                current_responses
            )

            system_prompt = """You are a precise data extraction assistant. Extract structured information from user messages.

IMPORTANT RULES:
1. Return ONLY valid JSON - no explanations, no markdown
2. Only extract information explicitly stated by the user
3. Do NOT invent or assume information not in the message
4. If a field is not mentioned, omit it or set to null
5. Maintain exact field names from the schema
6. Follow the data types specified in the schema"""

            # Generate structured output
            return await self.generate_structured(
                prompt,
                extraction_schema,
                system_prompt=system_prompt,
                temperature=0.1,  # Low temperature for precision
                max_retries=2
            )

        except Exception as e:
            logger.exception(f"Error extracting form data: {e}")
            return None, str(e)

    def _build_schema_prompt(self, prompt: str, json_schema: Dict[str, Any]) -> str:
        """Build prompt that includes schema specification"""
        schema_str = json.dumps(json_schema, indent=2)

        return f"""{prompt}

RESPONSE FORMAT:
You MUST respond with valid JSON matching this exact schema:

{schema_str}

RULES:
- Return ONLY the JSON object, no other text
- Include all required fields
- Use correct data types
- No markdown formatting
- No explanations outside the JSON

JSON Response:"""

    def _build_extraction_prompt(
        self,
        user_message: str,
        schema: Type[BaseModel],
        current_responses: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build prompt for form data extraction"""
        json_schema = schema.model_json_schema()

        prompt_parts = [
            f"Extract information from this user message:\n\"{user_message}\"\n"
        ]

        if current_responses:
            prompt_parts.append(
                f"Already collected data:\n{json.dumps(current_responses, indent=2)}\n"
            )

        prompt_parts.append(
            f"Extract any NEW information and return as JSON matching this schema:\n"
            f"{json.dumps(json_schema, indent=2)}\n"
        )

        prompt_parts.append(
            "IMPORTANT:\n"
            "- Only extract information explicitly mentioned in the message\n"
            "- Do NOT invent or assume data\n"
            "- If nothing can be extracted, return empty JSON: {}\n"
            "- Mark fields you extracted in 'extracted_fields' list\n"
        )

        return "\n".join(prompt_parts)

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """
        Extract JSON from LLM response that might have markdown or extra text.

        Handles common patterns:
        - ```json ... ```
        - ```\n...\n```
        - Plain JSON
        """
        text = text.strip()

        # Remove markdown code blocks
        if text.startswith("```"):
            lines = text.split("\n")
            json_lines = []
            in_block = False

            for line in lines:
                if line.strip().startswith("```"):
                    in_block = not in_block
                    continue
                if in_block:
                    json_lines.append(line)

            text = "\n".join(json_lines).strip()

        # Try to parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON object in text
            start = text.find("{")
            end = text.rfind("}") + 1

            if start != -1 and end > start:
                json_str = text[start:end]
                return json.loads(json_str)

            raise

    async def validate_form_response(
        self,
        form_template_id: str,
        responses: Dict[str, Any]
    ) -> tuple[bool, Optional[BaseModel], Optional[str]]:
        """
        Validate form responses against database schema.

        Args:
            form_template_id: Form template ID
            responses: Response data to validate

        Returns:
            Tuple of (is_valid, validated_model, error_message)
        """
        if not self.schema_generator:
            return False, None, "Schema generator not initialized"

        return await self.schema_generator.validate_llm_output(
            form_template_id,
            responses,
            schema_type="response"
        )

    async def get_form_schema_for_prompt(
        self,
        form_template_id: str,
        schema_type: str = "extraction"
    ) -> str:
        """
        Get formatted schema string to include in prompts.

        Args:
            form_template_id: Form template ID
            schema_type: "extraction" or "response"

        Returns:
            Formatted schema string for prompt
        """
        if not self.schema_generator:
            return ""

        schema = await self.schema_generator.get_form_schema_json(
            form_template_id,
            schema_type
        )

        return json.dumps(schema, indent=2)


# Helper functions for common patterns

async def extract_with_schema(
    user_message: str,
    schema: Type[T],
    system_instructions: Optional[str] = None,
    db=None
) -> tuple[Optional[T], Optional[str]]:
    """
    Quick helper to extract data with a schema.

    Example:
        from pydantic import BaseModel

        class UserInfo(BaseModel):
            name: str
            email: str
            phone: Optional[str] = None

        data, error = await extract_with_schema(
            "My name is John and email is john@example.com",
            UserInfo
        )
    """
    client = StructuredLLMClient(db)
    return await client.generate_structured(
        user_message,
        schema,
        system_prompt=system_instructions
    )


async def extract_form_fields(
    user_message: str,
    form_template_id: str,
    db,
    current_responses: Optional[Dict[str, Any]] = None
) -> tuple[Optional[BaseModel], Optional[str]]:
    """
    Quick helper to extract form fields from user message.

    This uses your actual database form schema.

    Example:
        extracted, error = await extract_form_fields(
            "John Doe, john@example.com, 555-1234",
            form_template_id="507f1f77bcf86cd799439011",
            db=db
        )

        if extracted:
            print(f"Name: {extracted.name}")
            print(f"Email: {extracted.email}")
    """
    client = StructuredLLMClient(db)
    return await client.extract_form_data(
        user_message,
        form_template_id,
        current_responses
    )
