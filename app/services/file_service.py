# app/services/file_service.py
import os
import uuid
import aiofiles
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from bson import ObjectId
import logging
from pathlib import Path

from app.services.base_service import BaseService
from app.models.file import File
from app.schemas.file import FileResponse
from app.config.settings import settings
from app.core.exceptions import NotFoundError, ValidationError, PermissionError
from app.models.enums import UserRole
from app.database import get_s3_storage

logger = logging.getLogger(__name__)

class FileService(BaseService):
    """Handles all logic for file uploads, retrieval, and management using S3 storage."""

    def __init__(self):
        super().__init__()
        self.s3_storage = None

    async def initialize(self):
        """Initialize the service by getting S3 storage connection."""
        await super().initialize()
        try:
            # --- THIS IS THE FIX ---
            # Attempt to get S3 storage, but catch the RuntimeError if it fails
            self.s3_storage = await get_s3_storage()
            logger.info("S3 storage connection established for FileService.")
        except RuntimeError as e:
            # Log a warning and continue with self.s3_storage as None
            logger.warning(f"S3 storage not available: {e}. File uploads will be handled locally.")
            self.s3_storage = None

    async def upload_file(
        self,
        file_data: bytes,
        filename: str,
        content_type: str,
        context_id: Optional[str],
        current_user: Dict[str, Any],
        description: Optional[str] = None
    ) -> FileResponse:
        """
        Validates and saves a file to S3, and records its metadata in the database.
        context_id is optional - if None, file is uploaded without context association (e.g., chat files).
        """
        if context_id is not None:
            await self._validate_file_permissions(context_id, current_user)
        self._validate_file_properties(file_data, content_type)

        # If S3 is not available, store in local filesystem temporarily
        if self.s3_storage is None:
            category = self._get_file_category(content_type)
            timestamp = datetime.utcnow().strftime("%Y%m%d")
            unique_id = str(uuid.uuid4())
            file_key = f"{category}/{timestamp}/{unique_id}-{filename}"
            
            full_path = Path(settings.UPLOAD_DIRECTORY) / file_key
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            async with aiofiles.open(full_path, 'wb') as f:
                await f.write(file_data)
            
            s3_file_key = file_key
            logger.warning(f"File stored locally: {s3_file_key}")
        else:
            # Upload file to S3
            metadata = {"uploaded_by": current_user["_id"]}
            if context_id is not None:
                metadata["context_id"] = context_id

            s3_file_key = self.s3_storage.upload_file(
                file_data,
                filename,
                content_type,
                metadata=metadata
            )

        category = self._get_file_category(content_type)
        
        file_model = File(
            filename=filename,
            content_type=content_type,
            file_size=len(file_data),
            context_id=context_id,
            uploaded_by=current_user["_id"],
            category=category,
            description=description or "",
            s3_file_key=s3_file_key
        )
        
        file_dict = file_model.model_dump(by_alias=True)
        del file_dict['_id']

        result = await self.db.files.insert_one(file_dict)
        created_file = await self.db.files.find_one({"_id": result.inserted_id})
        
        logger.info(f"File uploaded successfully: {created_file['_id']} with key {s3_file_key}")
        return FileResponse.model_validate(created_file)

    async def get_file_by_id(self, file_id: str, current_user: Dict[str, Any]) -> FileResponse:
        """Retrieves file metadata by its ID."""
        if not ObjectId.is_valid(file_id):
            raise ValidationError("Invalid file ID.")
            
        file_data = await self.db.files.find_one({"_id": ObjectId(file_id)})
        if not file_data or not file_data.get("is_active"):
            raise NotFoundError("File not found.")
        
        await self._validate_file_permissions(file_data["context_id"], current_user)
        return FileResponse.model_validate(file_data)

    async def get_file_content(self, file_id: str, current_user: Dict[str, Any]) -> Tuple[bytes, str, str]:
        """Retrieves the raw content of a file from S3 for downloading."""
        file_metadata = await self.get_file_by_id(file_id, current_user)
        
        if self.s3_storage is None:
            try:
                local_file_path = Path(settings.UPLOAD_DIRECTORY) / file_metadata.s3_file_key
                async with aiofiles.open(local_file_path, 'rb') as f:
                    content = await f.read()
                return content, file_metadata.filename, file_metadata.content_type
            except FileNotFoundError:
                logger.error(f"Failed to retrieve file from local storage: {file_metadata.s3_file_key}")
                raise NotFoundError("File content not found in local storage.")
        else:
            try:
                content, _, _, _ = self.s3_storage.get_file(file_metadata.s3_file_key)
                return content, file_metadata.filename, file_metadata.content_type
            except FileNotFoundError as e:
                logger.error(f"Failed to retrieve file from S3: {e}")
                raise NotFoundError("File content not found in S3 storage.")

    def _validate_file_properties(self, file_data: bytes, content_type: str):
        """Checks file size and type against configured limits."""
        if len(file_data) > settings.MAX_FILE_SIZE:
            raise ValidationError(f"File size exceeds the limit of {settings.MAX_FILE_SIZE / 1024 / 1024} MB.")
        
        allowed_prefixes = ["image/", "audio/", "application/pdf", "text/plain"]
        if not any(content_type.startswith(prefix) for prefix in allowed_prefixes):
            raise ValidationError(f"File type '{content_type}' is not allowed.")

    def _get_file_category(self, content_type: str) -> str:
        """Determines the storage sub-directory based on MIME type."""
        if content_type.startswith("image/"):
            return "images"
        elif content_type.startswith("audio/"):
            return "audio"
        else:
            return "files"
            
    async def _validate_file_permissions(self, context_id: str, current_user: Dict[str, Any]):
        """Checks if the current user has access to the file's context."""
        if current_user["role"] == UserRole.ADMIN.value:
            return

        if not ObjectId.is_valid(context_id):
            raise ValidationError("Invalid context ID.")
        
        context = await self.db.contexts.find_one({"_id": ObjectId(context_id)})
        if not context:
            raise NotFoundError("Associated context not found.")

        user_id = current_user["_id"]
        if not (
            context["created_by"] == user_id
            or user_id in context.get("assigned_professionals", [])
            or user_id in context.get("assigned_users", [])
        ):
            raise PermissionError("You do not have permission to access files in this context.")

    async def delete_file(self, file_id: str, current_user: Dict[str, Any]) -> bool:
        """Deletes a file from both S3 storage and the database."""
        file_metadata = await self.get_file_by_id(file_id, current_user)

        if self.s3_storage is not None:
            try:
                self.s3_storage.delete_file(file_metadata.s3_file_key)
            except Exception as e:
                logger.error(f"Failed to delete file from S3: {e}")
        else:
            try:
                local_file_path = Path(settings.UPLOAD_DIRECTORY) / file_metadata.s3_file_key
                if local_file_path.exists():
                    os.remove(local_file_path)
            except Exception as e:
                logger.error(f"Failed to delete file from local storage: {e}")

        result = await self.db.files.update_one(
            {"_id": ObjectId(file_id)},
            {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
        )

        if result.matched_count == 0:
            raise NotFoundError("File not found in database.")

        logger.info(f"File {file_id} marked as inactive in database.")
        return True

# Create a single instance of the service
file_service = FileService()