"""
Enhanced Form Filler Agent - Refactored Version

This is a cleaner, more modular version of the enhanced form filler agent
that uses separate modules for validation, form management, and prompts.
"""

import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from bson import ObjectId

from app.sessions.session_manager import EnhancedBaseAgent, SessionData
from app.utils.langchain_utils import get_gemini_llm
from app.config.settings import settings
from app.agents.validators import FieldValidator
from app.agents.managers import FormTemplateManager
from app.agents.prompts import FormPromptManager
from app.core.exceptions import ValidationError, NotFoundError

logger = logging.getLogger(__name__)


class EnhancedFormFillerAgent(EnhancedBaseAgent):
    """
    Enhanced form filling agent with modular architecture.

    This agent helps users fill out forms through conversational interface,
    providing validation, suggestions, and guidance throughout the process.
    """

    def __init__(self, db, session_data: SessionData):
        super().__init__(db, session_data)
        self.llm = get_gemini_llm()

        # Initialize modular components
        self.validator = FieldValidator()
        self.form_manager = FormTemplateManager(db)
        self.prompt_manager = FormPromptManager()

        # Agent state
        self.form_template = None
        self.context_info = None
        self.current_field = None
        self.waiting_for_confirmation = False

    async def process_user_message(self, user_message: str) -> str:
        """
        Process user message and return appropriate response.

        Args:
            user_message: User's input message

        Returns:
            Agent's response message
        """
        try:
            logger.info(f"Processing user message in session {self.session_data.session_id}")

            # Add to conversation history
            self.prompt_manager.add_to_conversation_history("USER", user_message)

            # Load form template if not already loaded
            if not self.form_template:
                await self._load_form_data()

            # Parse user intent and respond accordingly
            response = await self._handle_user_input(user_message.strip().lower())

            # Add response to conversation history
            self.prompt_manager.add_to_conversation_history("AGENT", response)

            return response

        except Exception as e:
            logger.error(f"Error processing user message: {str(e)}")
            return self.prompt_manager.generate_error_prompt(
                "I encountered an error while processing your request. Please try again."
            )

    async def _load_form_data(self):
        """Load form template and context data."""
        try:
            template_id = self.session_data.form_template_id
            if not template_id:
                raise ValueError("No form template ID provided")

            # Load form template
            self.form_template = await self.form_manager.load_form_template(template_id)

            # Load context if available
            context_id = self.form_template.get('context_id')
            if context_id:
                self.context_info = await self.form_manager.load_context(context_id)

            logger.info(f"Loaded form data for template {template_id}")

        except Exception as e:
            logger.error(f"Error loading form data: {str(e)}")
            raise NotFoundError("form template", self.session_data.form_template_id)

    async def _handle_user_input(self, user_input: str) -> str:
        """
        Handle user input based on current state and intent.

        Args:
            user_input: Processed user input (lowercase, trimmed)

        Returns:
            Response message
        """
        # Handle special commands
        if user_input in ['help', '?']:
            return self.prompt_manager.generate_help_prompt(self.current_field)

        elif user_input == 'submit':
            return await self._handle_submit_command()

        elif user_input == 'review':
            return await self._handle_review_command()

        elif user_input.startswith('edit '):
            field_name = user_input[5:].strip()
            return await self._handle_edit_command(field_name)

        elif user_input in ['skip', 'next']:
            return await self._handle_skip_command()

        elif user_input in ['cancel', 'quit', 'exit']:
            return await self._handle_cancel_command()

        elif user_input == 'restart':
            return await self._handle_restart_command()

        # Handle confirmation responses
        elif self.waiting_for_confirmation:
            return await self._handle_confirmation_response(user_input)

        # Handle field input
        else:
            return await self._handle_field_input(user_input)

    async def _handle_field_input(self, user_input: str) -> str:
        """Handle user input for form fields."""
        # If no current field, find the next one
        if not self.current_field:
            answered_fields = set(self.session_data.responses.keys())
            self.current_field = await self.form_manager.get_next_unanswered_field(
                self.session_data.form_template_id, answered_fields
            )

            if not self.current_field:
                # All fields completed, show confirmation
                return await self._show_confirmation()

        # Validate the field input
        field_id = self.current_field.get('field_id')
        validation_result = await self.validator.validate_field_response(
            self.current_field, user_input
        )

        if not validation_result['is_valid']:
            # Show validation error and ask again
            return self.prompt_manager.generate_validation_error_prompt(
                self.current_field, validation_result
            )

        # Save the response
        processed_value = validation_result['processed_value']
        self.session_data.responses[field_id] = processed_value

        # Move to next field
        answered_fields = set(self.session_data.responses.keys())
        next_field = await self.form_manager.get_next_unanswered_field(
            self.session_data.form_template_id, answered_fields
        )

        if next_field:
            self.current_field = next_field
            return await self._ask_next_field()
        else:
            # All fields completed
            return await self._show_confirmation()

    async def _ask_next_field(self) -> str:
        """Generate prompt for the next field."""
        if not self.current_field:
            return await self._show_confirmation()

        # Calculate progress
        total_fields = len(self.form_template.get('fields', []))
        answered_fields = len(self.session_data.responses)
        progress = self.form_manager.get_form_progress(total_fields, answered_fields)

        # Generate field prompt
        return self.prompt_manager.generate_field_prompt(
            self.current_field,
            progress,
            self.session_data.responses
        )

    async def _show_confirmation(self) -> str:
        """Show confirmation screen with all responses."""
        self.waiting_for_confirmation = True
        self.current_field = None

        return self.prompt_manager.generate_confirmation_prompt(
            self.session_data.responses,
            self.form_template
        )

    async def _handle_submit_command(self) -> str:
        """Handle form submission."""
        if not self.session_data.responses:
            return "You haven't filled out any fields yet. Let me help you get started."

        # Check if required fields are completed
        required_fields = [
            f for f in self.form_template.get('fields', [])
            if f.get('required', False)
        ]

        missing_required = []
        for field in required_fields:
            field_id = field.get('field_id')
            if field_id not in self.session_data.responses:
                missing_required.append(field.get('label', field_id))

        if missing_required:
            return f"Please complete these required fields first: {', '.join(missing_required)}"

        # Submit the form
        return await self._submit_form()

    async def _submit_form(self) -> str:
        """Submit the form to the database."""
        try:
            # Create form response document
            form_response = {
                "form_template_id": ObjectId(self.session_data.form_template_id),
                "user_id": ObjectId(self.session_data.user_id),
                "responses": self.session_data.responses,
                "status": "submitted",
                "submitted_at": datetime.utcnow(),
                "created_at": datetime.utcnow(),
                "session_id": self.session_data.session_id
            }

            # Insert into database
            result = await self.db.form_responses.insert_one(form_response)
            response_id = str(result.inserted_id)

            # Clear session state
            self.session_data.responses.clear()
            self.current_field = None
            self.waiting_for_confirmation = False

            logger.info(f"Form submitted successfully with ID: {response_id}")

            return self.prompt_manager.generate_submission_success_prompt(
                self.form_template.get('title', 'Form'),
                response_id
            )

        except Exception as e:
            logger.error(f"Error submitting form: {str(e)}")
            return "I encountered an error while submitting your form. Please try again."

    async def _handle_review_command(self) -> str:
        """Handle review command to show current responses."""
        if not self.session_data.responses:
            return "You haven't filled out any fields yet."

        return self.prompt_manager.generate_confirmation_prompt(
            self.session_data.responses,
            self.form_template
        )

    async def _handle_edit_command(self, field_name: str) -> str:
        """Handle edit command for a specific field."""
        # Find the field by name or ID
        fields = self.form_template.get('fields', [])
        target_field = None

        for field in fields:
            if (field.get('label', '').lower() == field_name or
                field.get('field_id', '').lower() == field_name):
                target_field = field
                break

        if not target_field:
            return f"I couldn't find a field named '{field_name}'. Use 'review' to see all fields."

        field_id = target_field.get('field_id')
        current_value = self.session_data.responses.get(field_id, "Not answered")

        self.current_field = target_field
        self.waiting_for_confirmation = False

        return self.prompt_manager.generate_edit_field_prompt(target_field, current_value)

    async def _handle_skip_command(self) -> str:
        """Handle skip command for optional fields."""
        if not self.current_field:
            return "There's no current field to skip."

        if self.current_field.get('required', False):
            return "This field is required and cannot be skipped."

        # Move to next field
        answered_fields = set(self.session_data.responses.keys())
        next_field = await self.form_manager.get_next_unanswered_field(
            self.session_data.form_template_id, answered_fields
        )

        if next_field:
            self.current_field = next_field
            return await self._ask_next_field()
        else:
            return await self._show_confirmation()

    async def _handle_cancel_command(self) -> str:
        """Handle cancel command."""
        self.session_data.responses.clear()
        self.current_field = None
        self.waiting_for_confirmation = False
        return "Form filling has been cancelled. Your responses have been cleared."

    async def _handle_restart_command(self) -> str:
        """Handle restart command."""
        self.session_data.responses.clear()
        self.current_field = None
        self.waiting_for_confirmation = False

        return self.prompt_manager.generate_initial_form_prompt(
            self.form_template, self.context_info
        )

    async def _handle_confirmation_response(self, user_input: str) -> str:
        """Handle user response during confirmation phase."""
        if user_input in ['1', 'submit', 'yes', 'y']:
            return await self._submit_form()

        elif user_input in ['2', 'edit', 'change', 'modify']:
            self.waiting_for_confirmation = False
            return "Which field would you like to edit? You can say something like 'edit project name'."

        elif user_input in ['3', 'cancel', 'restart']:
            return await self._handle_restart_command()

        else:
            return "Please choose: 1 (Submit), 2 (Make changes), or 3 (Start over)."

    async def start_conversation(self) -> str:
        """Start the form filling conversation."""
        try:
            await self._load_form_data()

            # Check if form is already started
            if self.session_data.responses:
                answered_fields = set(self.session_data.responses.keys())
                next_field = await self.form_manager.get_next_unanswered_field(
                    self.session_data.form_template_id, answered_fields
                )

                if next_field:
                    self.current_field = next_field
                    return f"Welcome back! Let's continue with your form.\n\n{await self._ask_next_field()}"
                else:
                    return await self._show_confirmation()

            # Start fresh form
            return self.prompt_manager.generate_initial_form_prompt(
                self.form_template, self.context_info
            )

        except Exception as e:
            logger.error(f"Error starting conversation: {str(e)}")
            return self.prompt_manager.generate_error_prompt(
                "I couldn't load the form. Please try again or contact support."
            )