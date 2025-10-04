"""
Form template management utilities for form processing agents.

This module handles loading, caching, and managing form templates and contexts.
"""

import logging
from typing import Dict, Optional, Any
from bson import ObjectId

logger = logging.getLogger(__name__)


class FormTemplateManager:
    """Manages form templates and contexts for agents."""

    def __init__(self, db):
        self.db = db
        self._form_template_cache = {}
        self._context_cache = {}

    async def load_form_template(self, template_id: str, force_reload: bool = False) -> Dict[str, Any]:
        """
        Load form template from database with caching.

        Args:
            template_id: The ID of the form template to load
            force_reload: Whether to bypass cache and reload from database

        Returns:
            Form template dictionary

        Raises:
            ValueError: If template ID is invalid or template not found
        """
        # Check cache first unless force reload is requested
        if not force_reload and template_id in self._form_template_cache:
            logger.debug(f"Using cached form template: {template_id}")
            return self._form_template_cache[template_id]

        logger.info(f"Loading form template with ID: {template_id}")

        try:
            # Validate ObjectId format
            if not ObjectId.is_valid(template_id):
                raise ValueError(f"Invalid template ID format: {template_id}")

            # Load from database
            form_template = await self.db.form_templates.find_one({"_id": ObjectId(template_id)})

            if not form_template:
                raise ValueError(f"Form template with ID {template_id} not found.")

            # Cache the template
            self._form_template_cache[template_id] = form_template

            logger.info(f"Loaded form template: {form_template.get('title', 'Unknown')}")
            logger.info(f"Form has {len(form_template.get('fields', []))} fields")

            return form_template

        except Exception as e:
            logger.error(f"Error loading form template {template_id}: {e}")
            raise

    async def load_context(self, context_id: str, force_reload: bool = False) -> Optional[Dict[str, Any]]:
        """
        Load context information from database with caching.

        Args:
            context_id: The ID of the context to load
            force_reload: Whether to bypass cache and reload from database

        Returns:
            Context dictionary or None if not found/invalid
        """
        if not context_id:
            return None

        # Check cache first unless force reload is requested
        if not force_reload and context_id in self._context_cache:
            logger.debug(f"Using cached context: {context_id}")
            return self._context_cache[context_id]

        try:
            # Validate ObjectId format
            if not ObjectId.is_valid(context_id):
                logger.warning(f"Invalid context ID format: {context_id}")
                return None

            # Load from database
            context = await self.db.contexts.find_one({"_id": ObjectId(context_id)})

            if context:
                # Cache the context
                self._context_cache[context_id] = context
                logger.info(f"Loaded context: {context.get('title', 'Unknown')}")
            else:
                logger.warning(f"Context {context_id} not found")

            return context

        except Exception as e:
            logger.warning(f"Could not load context {context_id}: {e}")
            return None

    async def get_form_fields(self, template_id: str) -> list:
        """
        Get fields from a form template.

        Args:
            template_id: The ID of the form template

        Returns:
            List of form fields
        """
        template = await self.load_form_template(template_id)
        return template.get('fields', [])

    async def get_field_by_id(self, template_id: str, field_id: str) -> Optional[Dict]:
        """
        Get a specific field from a form template.

        Args:
            template_id: The ID of the form template
            field_id: The ID of the field to find

        Returns:
            Field dictionary or None if not found
        """
        fields = await self.get_form_fields(template_id)
        for field in fields:
            if field.get('field_id') == field_id:
                return field
        return None

    async def get_next_unanswered_field(self, template_id: str, answered_fields: set) -> Optional[Dict]:
        """
        Get the next unanswered required field from a form.

        Args:
            template_id: The ID of the form template
            answered_fields: Set of field IDs that have been answered

        Returns:
            Next field dictionary or None if all required fields are answered
        """
        fields = await self.get_form_fields(template_id)

        # First, find required fields that haven't been answered
        for field in fields:
            field_id = field.get('field_id')
            if field.get('required', False) and field_id not in answered_fields:
                return field

        # Then, find optional fields that haven't been answered
        for field in fields:
            field_id = field.get('field_id')
            if field_id not in answered_fields:
                return field

        return None

    def get_form_progress(self, total_fields: int, answered_fields: int) -> Dict[str, Any]:
        """
        Calculate form completion progress.

        Args:
            total_fields: Total number of fields in the form
            answered_fields: Number of fields that have been answered

        Returns:
            Dictionary with progress information
        """
        if total_fields == 0:
            return {"percentage": 100, "remaining": 0, "completed": 0}

        percentage = (answered_fields / total_fields) * 100
        return {
            "percentage": round(percentage, 1),
            "remaining": total_fields - answered_fields,
            "completed": answered_fields,
            "total": total_fields
        }

    def clear_cache(self):
        """Clear all cached templates and contexts."""
        self._form_template_cache.clear()
        self._context_cache.clear()
        logger.info("Form template and context cache cleared")

    def clear_template_cache(self, template_id: str):
        """Clear cache for a specific template."""
        if template_id in self._form_template_cache:
            del self._form_template_cache[template_id]
            logger.info(f"Cleared cache for template {template_id}")

    def clear_context_cache(self, context_id: str):
        """Clear cache for a specific context."""
        if context_id in self._context_cache:
            del self._context_cache[context_id]
            logger.info(f"Cleared cache for context {context_id}")

    async def validate_template_access(self, template_id: str, user_id: str) -> bool:
        """
        Validate if a user has access to a form template.

        Args:
            template_id: The ID of the form template
            user_id: The ID of the user

        Returns:
            True if user has access, False otherwise
        """
        try:
            template = await self.load_form_template(template_id)
            context_id = template.get('context_id')

            if not context_id:
                # If no context, assume public access
                return True

            context = await self.load_context(context_id)
            if not context:
                return False

            # Check if user is in assigned_users or assigned_professionals
            user_obj_id = ObjectId(user_id)
            assigned_users = context.get('assigned_users', [])
            assigned_professionals = context.get('assigned_professionals', [])

            return user_obj_id in assigned_users or user_obj_id in assigned_professionals

        except Exception as e:
            logger.error(f"Error validating template access: {e}")
            return False