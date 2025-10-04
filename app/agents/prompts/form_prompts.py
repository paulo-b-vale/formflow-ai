"""
AI prompt templates and conversation handling for form filling agents.

This module contains all the prompt templates and conversation logic
used by the enhanced form filler agent.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class FormPromptManager:
    """Manages AI prompts and conversation flows for form filling."""

    def __init__(self):
        self.conversation_history = []

    def generate_initial_form_prompt(self, form_template: Dict, context_info: Optional[Dict] = None) -> str:
        """
        Generate the initial prompt when starting to fill a form.

        Args:
            form_template: The form template dictionary
            context_info: Optional context information

        Returns:
            Formatted prompt string
        """
        form_title = form_template.get('title', 'Unknown Form')
        form_description = form_template.get('description', '')
        fields = form_template.get('fields', [])

        context_info_text = ""
        if context_info:
            context_title = context_info.get('title', '')
            context_description = context_info.get('description', '')
            if context_title or context_description:
                context_info_text = f"\n\n**Context Information:**\n{context_title}\n{context_description}"

        prompt = f"""
Hello! I'm here to help you fill out the "{form_title}" form.

{form_description}{context_info_text}

This form has {len(fields)} fields total. I'll guide you through each field step by step.

Would you like to start filling out the form? I'll ask you one question at a time and help ensure all information is accurate.
"""
        return prompt.strip()

    def generate_field_prompt(
        self,
        field: Dict,
        progress: Dict,
        previous_responses: Dict = None,
        suggestions: List[str] = None
    ) -> str:
        """
        Generate a prompt for a specific field.

        Args:
            field: Field definition
            progress: Form completion progress
            previous_responses: Previously submitted responses
            suggestions: AI-generated suggestions for the field

        Returns:
            Formatted prompt string
        """
        field_label = field.get('label', 'Field')
        field_type = field.get('field_type', 'text')
        field_description = field.get('description', '')
        is_required = field.get('required', False)

        # Progress indicator
        progress_text = f"Progress: {progress['completed']}/{progress['total']} fields completed ({progress['percentage']}%)"

        # Required indicator
        required_text = " (Required)" if is_required else " (Optional)"

        # Field description
        description_text = f"\n{field_description}" if field_description else ""

        # Type-specific guidance
        type_guidance = self._get_field_type_guidance(field_type)

        # AI suggestions
        suggestions_text = ""
        if suggestions:
            suggestions_text = f"\n\n💡 **Suggestions:**\n" + "\n".join(f"• {s}" for s in suggestions)

        prompt = f"""
{progress_text}

**{field_label}**{required_text}{description_text}

{type_guidance}{suggestions_text}

Please provide your answer:
"""
        return prompt.strip()

    def _get_field_type_guidance(self, field_type: str) -> str:
        """Get type-specific guidance for field input."""
        guidance_map = {
            'email': "Please enter a valid email address (e.g., user@example.com)",
            'phone': "Please enter your phone number (e.g., +1-555-123-4567)",
            'number': "Please enter a numeric value",
            'currency': "Please enter a monetary amount (e.g., $100.00 or 100)",
            'date': "Please enter a date (YYYY-MM-DD, MM/DD/YYYY, or DD/MM/YYYY)",
            'url': "Please enter a valid URL (e.g., https://example.com)",
            'textarea': "You can provide a detailed response for this field",
            'text': "Please provide your response"
        }
        return guidance_map.get(field_type, "Please provide your response")

    def generate_validation_error_prompt(self, field: Dict, validation_result: Dict) -> str:
        """
        Generate a prompt when field validation fails.

        Args:
            field: Field definition
            validation_result: Validation result with errors and suggestions

        Returns:
            Formatted error prompt
        """
        field_label = field.get('label', 'Field')
        suggestions = validation_result.get('suggestions', [])

        suggestions_text = ""
        if suggestions:
            suggestions_text = "\n\n" + "\n".join(f"• {s}" for s in suggestions)

        prompt = f"""
I noticed there's an issue with your response for "{field_label}".{suggestions_text}

Could you please provide the information again?
"""
        return prompt.strip()

    def generate_confirmation_prompt(self, responses: Dict, form_template: Dict) -> str:
        """
        Generate a confirmation prompt showing all responses.

        Args:
            responses: All form responses
            form_template: Form template for field labels

        Returns:
            Formatted confirmation prompt
        """
        form_title = form_template.get('title', 'Form')
        fields = {f.get('field_id'): f for f in form_template.get('fields', [])}

        response_lines = []
        for field_id, response in responses.items():
            field = fields.get(field_id, {})
            label = field.get('label', field_id)
            response_lines.append(f"**{label}:** {response}")

        responses_text = "\n".join(response_lines)

        prompt = f"""
Great! You've completed all the fields for "{form_title}".

Here's a summary of your responses:

{responses_text}

Would you like to:
1. Submit the form as is
2. Make changes to any field
3. Cancel and start over

Please let me know what you'd like to do.
"""
        return prompt.strip()

    def generate_submission_success_prompt(self, form_title: str, response_id: str = None) -> str:
        """
        Generate a success prompt after form submission.

        Args:
            form_title: Title of the submitted form
            response_id: Optional response ID for reference

        Returns:
            Formatted success prompt
        """
        reference_text = ""
        if response_id:
            reference_text = f"\nYour reference ID is: {response_id}"

        prompt = f"""
🎉 **Success!** Your "{form_title}" form has been submitted successfully.{reference_text}

Thank you for completing the form. Your information has been recorded and will be processed accordingly.

Is there anything else I can help you with today?
"""
        return prompt.strip()

    def generate_help_prompt(self, current_field: Dict = None) -> str:
        """
        Generate a help prompt explaining available commands.

        Args:
            current_field: Current field being processed (optional)

        Returns:
            Formatted help prompt
        """
        field_specific_help = ""
        if current_field:
            field_label = current_field.get('label', 'current field')
            field_type = current_field.get('field_type', 'text')
            type_guidance = self._get_field_type_guidance(field_type)
            field_specific_help = f"\n\n**For the current field ({field_label}):**\n{type_guidance}"

        prompt = f"""
**Help - Available Commands:**

• **submit** - Submit the form (when all required fields are complete)
• **review** - Review all your current responses
• **edit [field_name]** - Edit a specific field
• **skip** - Skip the current field (if optional)
• **restart** - Start over with a fresh form
• **help** - Show this help message
• **cancel** - Cancel form filling

**General Tips:**
• I'll guide you through each field step by step
• Required fields must be completed before submission
• You can always ask for help or clarification{field_specific_help}

What would you like to do?
"""
        return prompt.strip()

    def generate_edit_field_prompt(self, field: Dict, current_value: str) -> str:
        """
        Generate a prompt for editing a specific field.

        Args:
            field: Field definition
            current_value: Current value of the field

        Returns:
            Formatted edit prompt
        """
        field_label = field.get('label', 'Field')

        prompt = f"""
**Editing: {field_label}**

Current value: "{current_value}"

Please provide the new value for this field, or type "cancel" to keep the current value:
"""
        return prompt.strip()

    def generate_error_prompt(self, error_message: str) -> str:
        """
        Generate a user-friendly error prompt.

        Args:
            error_message: Error message to display

        Returns:
            Formatted error prompt
        """
        prompt = f"""
I encountered an issue: {error_message}

Please try again, or type "help" for assistance.
"""
        return prompt.strip()

    def add_to_conversation_history(self, role: str, message: str):
        """Add a message to conversation history."""
        self.conversation_history.append({
            "role": role,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })

    def get_conversation_context(self, last_n: int = 5) -> str:
        """Get recent conversation context for AI prompts."""
        recent_history = self.conversation_history[-last_n:] if self.conversation_history else []

        context_lines = []
        for entry in recent_history:
            role = entry["role"].upper()
            message = entry["message"]
            context_lines.append(f"{role}: {message}")

        return "\n".join(context_lines)

    def clear_conversation_history(self):
        """Clear conversation history."""
        self.conversation_history.clear()