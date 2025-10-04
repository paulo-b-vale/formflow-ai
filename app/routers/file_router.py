# app/routers/file_router.py
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from typing import Optional, List
import io

from app.schemas.file import FileResponse
from app.services.file_service import file_service
from app.dependencies.auth import get_current_active_user
from app.schemas.user import UserResponse
from app.core.exceptions import NotFoundError, ValidationError, PermissionError

router = APIRouter()

@router.post("/upload", response_model=FileResponse, status_code=status.HTTP_201_CREATED, response_model_by_alias=False)
async def upload_file(
    context_id: str = Form(...),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user: UserResponse = Depends(get_current_active_user)
):
    """Uploads a file and associates it with a context."""
    try:
        file_content = await file.read()
        return await file_service.upload_file(
            file_data=file_content,
            filename=file.filename,
            content_type=file.content_type,
            context_id=context_id,
            current_user=current_user.model_dump(),
            description=description
        )
    except (ValidationError, PermissionError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.post("/chat/upload", status_code=status.HTTP_201_CREATED)
async def upload_chat_files(
    files: List[UploadFile] = File(...),
    current_user: UserResponse = Depends(get_current_active_user)
):
    """
    Uploads files for chat conversation (without requiring context_id).
    Returns list of file IDs that can be sent with the message.
    """
    try:
        uploaded_files = []
        for file in files:
            file_content = await file.read()
            # Upload without context_id - will be associated when used in conversation
            file_response = await file_service.upload_file(
                file_data=file_content,
                filename=file.filename,
                content_type=file.content_type,
                context_id=None,  # No context yet
                current_user=current_user.model_dump(),
                description=f"Chat upload: {file.filename}"
            )
            uploaded_files.append({
                "file_id": str(file_response.id),
                "filename": file_response.filename,
                "content_type": file_response.content_type,
                "size": file_response.size
            })

        return {"files": uploaded_files}
    except (ValidationError, PermissionError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/{file_id}/download")
async def download_file(
    file_id: str,
    current_user: UserResponse = Depends(get_current_active_user)
):
    """Downloads the content of a specific file."""
    try:
        content, filename, content_type = await file_service.get_file_content(
            file_id, current_user.model_dump()
        )
        return StreamingResponse(
            io.BytesIO(content),
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename=\"{filename}\""}
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))