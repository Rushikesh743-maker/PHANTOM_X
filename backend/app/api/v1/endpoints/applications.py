import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.application_service import ApplicationService
# pyrefly: ignore[missing-import]
from shared.contracts.models import (
    ApplicationCreate,
    ApplicationResponse,
    ApplicationUpdate,
    ApplicationScopeDetail,
)

router = APIRouter()


@router.get("/", response_model=List[ApplicationResponse])
async def list_applications(
    search: Optional[str] = Query(None, description="Search applications by name, URL, or description"),
    status: Optional[str] = Query(None, description="Filter applications by status (e.g. ACTIVE, INACTIVE)"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Pagination limit"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List registered target applications for the authenticated user's organization.
    Enforces strict tenant isolation.
    """
    return await ApplicationService.list_applications(
        db=db,
        current_user=current_user,
        search=search,
        status_filter=status,
        skip=skip,
        limit=limit
    )


@router.post("/", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def register_application(
    app_in: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new application target under authorized security boundaries.
    Validates required fields, target URLs, and authorized scope definitions.
    Enforces organization tenant isolation and explicit testing authorization.
    """
    return await ApplicationService.register_application(
        db=db,
        app_in=app_in,
        current_user=current_user
    )


@router.get("/{app_id}", response_model=ApplicationResponse)
async def get_application(
    app_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve profiling and scope details of a specific target application.
    Enforces organization boundaries: cross-tenant access is rejected.
    """
    return await ApplicationService.get_application(
        db=db,
        app_id=app_id,
        current_user=current_user
    )


@router.put("/{app_id}", response_model=ApplicationResponse)
async def update_application_put(
    app_id: uuid.UUID,
    app_update: ApplicationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update application profiling information and testing scope configuration (PUT).
    Validates updated URL, paths, and limits.
    """
    return await ApplicationService.update_application(
        db=db,
        app_id=app_id,
        app_update=app_update,
        current_user=current_user
    )


@router.patch("/{app_id}", response_model=ApplicationResponse)
async def update_application_patch(
    app_id: uuid.UUID,
    app_update: ApplicationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update application profiling information and testing scope configuration (PATCH).
    Validates updated URL, paths, and limits.
    """
    return await ApplicationService.update_application(
        db=db,
        app_id=app_id,
        app_update=app_update,
        current_user=current_user
    )


@router.delete("/{app_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_application(
    app_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove an application from tracking along with its environments and scope policies.
    Enforces organization tenant boundaries.
    """
    await ApplicationService.delete_application(
        db=db,
        app_id=app_id,
        current_user=current_user
    )
    return None


@router.get("/{app_id}/scope", response_model=ApplicationScopeDetail)
async def get_application_scope(
    app_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve the registered authorized testing scope for an application.
    Enables future Discovery Agent features to retrieve validated boundaries.
    """
    return await ApplicationService.get_application_scope(
        db=db,
        app_id=app_id,
        current_user=current_user
    )
