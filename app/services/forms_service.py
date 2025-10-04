# app/services/forms_service.py
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId

from app.services.base_service import BaseService
from app.models.forms import WorkContext, FormTemplate, FormResponse
from app.models.enums import UserRole, ResponseStatus, FormStatus
from app.schemas.forms import (
    WorkContextCreate, WorkContextUpdate, WorkContextResponse,
    FormTemplateCreate, FormTemplateUpdate, FormTemplateResponse,
    FormResponseCreate, FormResponseUpdate, FormResponseResponse
)
from app.core.exceptions import NotFoundError, ValidationError, PermissionError

logger = logging.getLogger(__name__)

class ContextManager:
    def __init__(self, db):
        self.db = db

    async def create(self, context_data: WorkContextCreate, current_user: Dict[str, Any]) -> WorkContextResponse:
        if current_user["role"] != UserRole.ADMIN.value:
            raise PermissionError("Only administrators can create contexts.")
        
        context = WorkContext(**context_data.model_dump(), created_by=current_user["id"])
        context_dict = context.model_dump(by_alias=True)
        del context_dict['_id']

        result = await self.db.contexts.insert_one(context_dict)
        created = await self.db.contexts.find_one({"_id": result.inserted_id})
        return WorkContextResponse.model_validate(created)

    async def get_by_id(self, context_id: str) -> Optional[Dict[str, Any]]:
        if not ObjectId.is_valid(context_id):
            raise ValidationError("Invalid context ID.")
        return await self.db.contexts.find_one({"_id": ObjectId(context_id)})

    async def update(self, context_id: str, context_data: WorkContextUpdate, current_user: Dict[str, Any]) -> WorkContextResponse:
        if current_user["role"] != UserRole.ADMIN.value:
            raise PermissionError("Only administrators can update contexts.")

        update_data = context_data.model_dump(exclude_unset=True)
        if not update_data:
            raise ValidationError("No update data provided.")
            
        update_data["updated_at"] = datetime.utcnow()

        result = await self.db.contexts.update_one({"_id": ObjectId(context_id)}, {"$set": update_data})
        if result.matched_count == 0:
            raise NotFoundError("Context not found.")
        
        updated = await self.db.contexts.find_one({"_id": ObjectId(context_id)})
        return WorkContextResponse.model_validate(updated)

    async def delete(self, context_id: str, current_user: Dict[str, Any]) -> bool:
        if current_user["role"] != UserRole.ADMIN.value:
            raise PermissionError("Only administrators can delete contexts.")

        result = await self.db.contexts.update_one(
            {"_id": ObjectId(context_id)},
            {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
        )
        if result.matched_count == 0:
            raise NotFoundError("Context not found.")
        return True

class FormTemplateManager:
    def __init__(self, db):
        self.db = db

    async def create(self, template_data: FormTemplateCreate, current_user: Dict[str, Any]) -> FormTemplateResponse:
        if current_user["role"] != UserRole.ADMIN.value:
            raise PermissionError("Only administrators can create form templates.")

        context = await self.db.contexts.find_one({"_id": ObjectId(template_data.context_id), "is_active": True})
        if not context:
            raise NotFoundError("Context not found.")

        template = FormTemplate(**template_data.model_dump(), created_by=current_user["id"])
        template_dict = template.model_dump(by_alias=True)
        del template_dict['_id']

        result = await self.db.form_templates.insert_one(template_dict)
        created = await self.db.form_templates.find_one({"_id": result.inserted_id})
        return FormTemplateResponse.model_validate(created)

    async def update(self, template_id: str, template_data: FormTemplateUpdate, current_user: Dict[str, Any]) -> FormTemplateResponse:
        if current_user["role"] != UserRole.ADMIN.value:
            raise PermissionError("Only administrators can update form templates.")
        
        update_data = template_data.model_dump(exclude_unset=True)
        if not update_data:
            raise ValidationError("No update data provided.")
        
        update_data["updated_at"] = datetime.utcnow()

        result = await self.db.form_templates.update_one({"_id": ObjectId(template_id)}, {"$set": update_data})
        if result.matched_count == 0:
            raise NotFoundError("Form template not found.")
            
        updated = await self.db.form_templates.find_one({"_id": ObjectId(template_id)})
        return FormTemplateResponse.model_validate(updated)

    async def archive(self, template_id: str, current_user: Dict[str, Any]) -> bool:
        if current_user["role"] != UserRole.ADMIN.value:
            raise PermissionError("Only administrators can archive form templates.")
            
        result = await self.db.form_templates.update_one(
            {"_id": ObjectId(template_id)},
            {"$set": {"status": FormStatus.ARCHIVED.value, "updated_at": datetime.utcnow()}}
        )
        if result.matched_count == 0:
            raise NotFoundError("Form template not found.")
        return True

class FormResponseManager:
    def __init__(self, db):
        self.db = db

    async def list(self, current_user: Dict[str, Any], filters: Dict[str, Any]) -> List[FormResponseResponse]:
        query = {}
        if current_user["role"] != UserRole.ADMIN.value:
            query["respondent_id"] = current_user["id"]
        else:
            if filters.get("status"):
                query["status"] = filters["status"]
            if filters.get("form_template_id"):
                query["form_template_id"] = filters["form_template_id"]
            if filters.get("search_term"):
                search_regex = {"$regex": filters["search_term"], "$options": "i"}
                query["$or"] = [
                    {"respondent_name": search_regex},
                    {"responses": {"$elemMatch": search_regex}}
                ]
        
        responses = await self.db.form_responses.find(query).sort("submitted_at", -1).to_list(length=100)
        return [FormResponseResponse.model_validate(r) for r in responses]

    async def get_by_id(self, response_id: str, current_user: Dict[str, Any]) -> FormResponseResponse:
        if not ObjectId.is_valid(response_id):
            raise ValidationError("Invalid response ID.")
        
        response = await self.db.form_responses.find_one({"_id": ObjectId(response_id)})
        if not response:
            raise NotFoundError("Form response not found.")
            
        if current_user["role"] != UserRole.ADMIN.value and response["respondent_id"] != current_user["id"]:
            raise PermissionError("You do not have permission to view this response.")
            
        return FormResponseResponse.model_validate(response)

    async def review(self, response_id: str, review_data: FormResponseUpdate, current_user: Dict[str, Any]) -> FormResponseResponse:
        if current_user["role"] != UserRole.ADMIN.value:
            raise PermissionError("Only administrators can review responses.")
        
        update_data = {
            "status": review_data.status,
            "review_notes": review_data.review_notes,
            "reviewed_by": current_user["id"],
            "reviewed_at": datetime.utcnow()
        }
        
        result = await self.db.form_responses.update_one(
            {"_id": ObjectId(response_id)},
            {"$set": update_data}
        )
        if result.matched_count == 0:
            raise NotFoundError("Form response not found.")
            
        updated = await self.db.form_responses.find_one({"_id": ObjectId(response_id)})
        return FormResponseResponse.model_validate(updated)

class FormsService(BaseService):
    def __init__(self):
        super().__init__()
        self._context_manager: Optional[ContextManager] = None
        self._template_manager: Optional[FormTemplateManager] = None
        self._response_manager: Optional[FormResponseManager] = None

    async def initialize(self):
        await super().initialize()
        self._context_manager = ContextManager(self.db)
        self._template_manager = FormTemplateManager(self.db)
        self._response_manager = FormResponseManager(self.db)

    # Context Methods
    async def create_context(self, context_data, user) -> WorkContextResponse: return await self._context_manager.create(context_data, user)
    async def update_context(self, id, data, user) -> WorkContextResponse: return await self._context_manager.update(id, data, user)
    async def delete_context(self, id, user) -> bool: return await self._context_manager.delete(id, user)
    
    # Form Template Methods
    async def create_form_template(self, data, user) -> FormTemplateResponse: return await self._template_manager.create(data, user)
    async def update_form_template(self, id, data, user) -> FormTemplateResponse: return await self._template_manager.update(id, data, user)
    async def archive_form_template(self, id, user) -> bool: return await self._template_manager.archive(id, user)

    # Form Response Methods
    async def list_form_responses(self, user, filters) -> List[FormResponseResponse]: return await self._response_manager.list(user, filters)
    async def get_form_response_by_id(self, id, user) -> FormResponseResponse: return await self._response_manager.get_by_id(id, user)
    async def review_form_response(self, id, data, user) -> FormResponseResponse: return await self._response_manager.review(id, data, user)

    # Other existing methods...
    async def get_context_by_id(self, context_id: str, current_user: Dict[str, Any]) -> WorkContextResponse:
        context = await self._context_manager.get_by_id(context_id)
        if not context:
            raise NotFoundError("Context not found.")
        await self._check_context_access(context, current_user)
        return WorkContextResponse.model_validate(context)

    async def list_user_contexts(self, current_user: Dict[str, Any]) -> List[WorkContextResponse]:
        query = {}
        if current_user["role"] != UserRole.ADMIN.value:
            user_id = current_user["id"]
            query["$or"] = [
                {"assigned_professionals": user_id},
                {"assigned_users": user_id},
                {"created_by": user_id}
            ]
        contexts = await self.db.contexts.find(query).to_list(length=None)
        return [WorkContextResponse.model_validate(ctx) for ctx in contexts]
    
    async def get_form_template_by_id(self, template_id: str, current_user: Dict[str, Any]) -> FormTemplateResponse:
        if not ObjectId.is_valid(template_id):
            raise ValidationError("Invalid template ID.")
        template = await self.db.form_templates.find_one({"_id": ObjectId(template_id)})
        if not template:
            raise NotFoundError("Form template not found.")
        
        await self.get_context_by_id(template["context_id"], current_user)
        return FormTemplateResponse.model_validate(template)

    async def list_form_templates(self, current_user: Dict[str, Any]) -> List[FormTemplateResponse]:
        if current_user["role"] != UserRole.ADMIN.value:
            raise PermissionError("You do not have permission to view all form templates.")
        
        templates = await self.db.form_templates.find().to_list(length=None)
        return [FormTemplateResponse.model_validate(t) for t in templates]

    async def _check_context_access(self, context_data: Dict[str, Any], current_user: Dict[str, Any]):
        if current_user["role"] == UserRole.ADMIN.value:
            return
        user_id = current_user["id"]
        if not (
            context_data["created_by"] == user_id
            or user_id in context_data.get("assigned_professionals", [])
            or user_id in context_data.get("assigned_users", [])
        ):
            raise PermissionError("Access denied to this context.")

    async def assign_users_to_context(
        self,
        context_id: str,
        user_ids: List[str],
        assign_type: str,
        current_user: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assign users to a context as either users or professionals"""
        if current_user["role"] != UserRole.ADMIN.value:
            raise PermissionError("Only administrators can assign users to contexts.")

        # Validate context exists
        context = await self.db.contexts.find_one({"_id": ObjectId(context_id)})
        if not context:
            raise NotFoundError(f"Context {context_id} not found")

        # Validate assignment type
        if assign_type not in ["users", "professionals"]:
            raise ValidationError("assign_type must be 'users' or 'professionals'")

        # Get the field name based on assignment type
        field_name = f"assigned_{assign_type}"

        # Add user IDs to the appropriate field
        current_assigned = context.get(field_name, [])
        new_assigned = list(set(current_assigned + user_ids))  # Remove duplicates

        # Update the context
        await self.db.contexts.update_one(
            {"_id": ObjectId(context_id)},
            {"$set": {field_name: new_assigned}}
        )

        return {
            "message": f"Successfully assigned {len(user_ids)} users as {assign_type} to context",
            "context_id": context_id,
            "assigned_users": new_assigned
        }

    async def remove_user_from_context(
        self,
        context_id: str,
        user_id: str,
        current_user: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Remove a user from all assignments in a context"""
        if current_user["role"] != UserRole.ADMIN.value:
            raise PermissionError("Only administrators can remove users from contexts.")

        # Validate context exists
        context = await self.db.contexts.find_one({"_id": ObjectId(context_id)})
        if not context:
            raise NotFoundError(f"Context {context_id} not found")

        # Remove user from both users and professionals lists
        update_doc = {}
        if user_id in context.get("assigned_users", []):
            update_doc["assigned_users"] = [uid for uid in context.get("assigned_users", []) if uid != user_id]
        if user_id in context.get("assigned_professionals", []):
            update_doc["assigned_professionals"] = [uid for uid in context.get("assigned_professionals", []) if uid != user_id]

        if update_doc:
            await self.db.contexts.update_one(
                {"_id": ObjectId(context_id)},
                {"$set": update_doc}
            )

        return {
            "message": f"Successfully removed user {user_id} from context",
            "context_id": context_id
        }

    async def get_context_users(
        self,
        context_id: str,
        current_user: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get all users assigned to a context with their details"""
        # Validate context exists and user has access
        context = await self.db.contexts.find_one({"_id": ObjectId(context_id)})
        if not context:
            raise NotFoundError(f"Context {context_id} not found")

        await self._check_context_access(context, current_user)

        # Get user details for assigned users and professionals
        all_user_ids = context.get("assigned_users", []) + context.get("assigned_professionals", [])

        users = []
        if all_user_ids:
            # Convert string IDs to ObjectIds for MongoDB query
            object_ids = [ObjectId(uid) for uid in all_user_ids if ObjectId.is_valid(uid)]
            user_docs = await self.db.users.find({"_id": {"$in": object_ids}}).to_list(length=None)

            for user_doc in user_docs:
                user_id_str = str(user_doc["_id"])
                assignment_type = []
                if user_id_str in context.get("assigned_users", []):
                    assignment_type.append("user")
                if user_id_str in context.get("assigned_professionals", []):
                    assignment_type.append("professional")

                users.append({
                    "id": user_id_str,
                    "name": user_doc.get("name", "Unknown"),
                    "email": user_doc.get("email", ""),
                    "assignment_type": assignment_type
                })

        return {
            "context_id": context_id,
            "context_title": context.get("title", ""),
            "users": users
        }

forms_service = FormsService()