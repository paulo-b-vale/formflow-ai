# app/models/file.py
from pydantic import BaseModel, Field, ConfigDict
from pydantic_core import core_schema
from typing import Optional, Any
from datetime import datetime
from bson import ObjectId

# --- START OF CORRECTED CODE for Pydantic v2 ---

class PyObjectId(ObjectId):
    """Custom Pydantic type for MongoDB's ObjectId."""
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: Any
    ) -> core_schema.CoreSchema:
        """Defines how this type should be validated and serialized by Pydantic v2."""
        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.union_schema(
                [
                    core_schema.is_instance_schema(ObjectId),
                    core_schema.chain_schema(
                        [
                            core_schema.str_schema(),
                            core_schema.no_info_plain_validator_function(cls.validate),
                        ]
                    ),
                ]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: str(x)
            ),
        )

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

class MongoBaseModel(BaseModel):
    """Base model for MongoDB documents, now compatible with Pydantic v2."""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str} # Fallback for serialization
    )

# --- END OF CORRECTED CODE ---

class File(MongoBaseModel):
    """Represents a file stored in MongoDB with reference to S3 storage."""
    filename: str = Field(...)
    content_type: str = Field(...)
    file_size: int = Field(...)
    
    context_id: str = Field(...)
    response_id: Optional[str] = Field(None)
    uploaded_by: str = Field(...)
    
    category: str = Field(...)
    description: Optional[str] = Field(None)
    s3_file_key: str = Field(...)  # Reference to the S3 file key
    is_active: bool = Field(True)