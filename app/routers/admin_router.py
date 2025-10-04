# app/routers/admin_router.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app.schemas.forms import (
    WorkContextCreate, WorkContextUpdate, WorkContextResponse,
    FormTemplateCreate, FormTemplateUpdate, FormTemplateResponse,
    FormResponseUpdate, FormResponseResponse
)
from app.services.forms_service import forms_service
from app.dependencies.auth import get_current_active_user, require_admin
from app.schemas.user import UserResponse
from app.core.exceptions import NotFoundError, ValidationError, PermissionError
from app.models.enums import ResponseStatus

router = APIRouter()

# --- Context Management Endpoints ---
@router.post("/contexts", response_model=WorkContextResponse, status_code=status.HTTP_201_CREATED, response_model_by_alias=False)
async def create_context(context_data: WorkContextCreate, current_user: UserResponse = Depends(require_admin)):
    try:
        return await forms_service.create_context(context_data, current_user.model_dump())
    except (ValidationError, PermissionError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/contexts", response_model=List[WorkContextResponse], response_model_by_alias=False)
async def list_contexts(current_user: UserResponse = Depends(require_admin)):
    # Admins can view all contexts via the list_user_contexts method which handles admin permissions
    return await forms_service.list_user_contexts(current_user.model_dump())


@router.get("/contexts/{context_id}", response_model=WorkContextResponse, response_model_by_alias=False)
async def get_context(context_id: str, current_user: UserResponse = Depends(require_admin)):
    try:
        return await forms_service.get_context_by_id(context_id, current_user.model_dump())
    except (NotFoundError, PermissionError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/contexts/{context_id}", response_model=WorkContextResponse, response_model_by_alias=False)
async def update_context(context_id: str, context_data: WorkContextUpdate, current_user: UserResponse = Depends(require_admin)):
    try:
        return await forms_service.update_context(context_id, context_data, current_user.model_dump())
    except (NotFoundError, ValidationError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/contexts/{context_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_context(context_id: str, current_user: UserResponse = Depends(require_admin)):
    try:
        await forms_service.delete_context(context_id, current_user.model_dump())
    except (NotFoundError, PermissionError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# --- Form Template Endpoints ---
@router.post("/templates", response_model=FormTemplateResponse, status_code=status.HTTP_201_CREATED, response_model_by_alias=False)
async def create_form_template(template_data: FormTemplateCreate, current_user: UserResponse = Depends(require_admin)):
    try:
        return await forms_service.create_form_template(template_data, current_user.model_dump())
    except (NotFoundError, ValidationError, PermissionError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/templates/{template_id}", response_model=FormTemplateResponse, response_model_by_alias=False)
async def update_form_template(template_id: str, template_data: FormTemplateUpdate, current_user: UserResponse = Depends(require_admin)):
    try:
        return await forms_service.update_form_template(template_id, template_data, current_user.model_dump())
    except (NotFoundError, ValidationError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_form_template(template_id: str, current_user: UserResponse = Depends(require_admin)):
    try:
        await forms_service.archive_form_template(template_id, current_user.model_dump())
    except (NotFoundError, PermissionError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/templates", response_model=List[FormTemplateResponse], response_model_by_alias=False)
async def list_form_templates(current_user: UserResponse = Depends(require_admin)):
    return await forms_service.list_form_templates(current_user.model_dump())


@router.get("/templates/{template_id}", response_model=FormTemplateResponse)
async def get_form_template(template_id: str, current_user: UserResponse = Depends(require_admin)):
    try:
        return await forms_service.get_form_template_by_id(template_id, current_user.model_dump())
    except (NotFoundError, PermissionError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# --- Form Response Endpoints ---
@router.get("/responses", response_model=List[FormResponseResponse], response_model_by_alias=False)
async def list_form_responses(
    status: ResponseStatus = None,
    form_template_id: str = None,
    search_term: str = None,
    current_user: UserResponse = Depends(require_admin)
):
    filters = {
        "status": status,
        "form_template_id": form_template_id,
        "search_term": search_term,
    }
    # Admins can view all form responses via the list_form_responses method which handles admin permissions
    return await forms_service.list_form_responses(current_user.model_dump(), filters)


@router.get("/responses/{response_id}", response_model=FormResponseResponse, response_model_by_alias=False)
async def get_form_response(response_id: str, current_user: UserResponse = Depends(require_admin)):
    try:
        return await forms_service.get_form_response_by_id(response_id, current_user.model_dump())
    except (NotFoundError, PermissionError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/responses/{response_id}/review", response_model=FormResponseResponse, response_model_by_alias=False)
async def review_form_response(response_id: str, review_data: FormResponseUpdate, current_user: UserResponse = Depends(require_admin)):
    try:
        return await forms_service.review_form_response(response_id, review_data, current_user.model_dump())
    except (NotFoundError, ValidationError, PermissionError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))