# app/schemas/file.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.file import PyObjectId # <-- Import PyObjectId

class FileResponse(BaseModel):
    id: PyObjectId = Field(alias="_id") # <-- THE FIX: Changed from str to PyObjectId
    filename: str
    content_type: str
    file_size: int
    context_id: str
    uploaded_by: str
    description: Optional[str] = None
    s3_file_key: str
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }