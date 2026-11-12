import uuid
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.inventory_service import InventoryService
from shared.contracts.models import (
    EndpointResponse,
    EndpointRelationshipResponse,
    ApiResourceGroup,
    InventoryOverviewStats,
    InventoryRebuildResponse,
)

logger = logging.getLogger("phantom_x.api.inventory")

router = APIRouter()


@router.get("/endpoints", response_model=List[EndpointResponse])
async def list_inventory_endpoints(
    app_id: uuid.UUID = Query(..., description="Target application ID"),
    resource: Optional[str] = Query(None, description="Filter by logical resource name"),
    category: Optional[str] = Query(None, description="Filter by API category"),
    method: Optional[str] = Query(None, description="Filter by HTTP method"),
    source: Optional[str] = Query(None, description="Filter by discovery source (OPENAPI, POSTMAN, HAR)"),
    search: Optional[str] = Query(None, description="Search across path, resource, operation ID, or description"),
    unclassified_only: bool = Query(False, description="Filter to only unclassified endpoints"),
    incomplete_metadata_only: bool = Query(False, description="Filter to endpoints missing description or parameters"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves filtered and categorized API endpoints for an application.
    Enforces tenant organization isolation.
    """
    endpoints = await InventoryService.list_inventory(
        db=db,
        app_id=app_id,
        org_id=current_user.organization_id,
        resource=resource,
        category=category,
        method=method,
        source=source,
        search=search,
        unclassified_only=unclassified_only,
        incomplete_metadata_only=incomplete_metadata_only,
        skip=skip,
        limit=limit,
    )
    return endpoints


@router.get("/resources", response_model=List[ApiResourceGroup])
async def list_resources(
    app_id: uuid.UUID = Query(..., description="Target application ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves resource-oriented view of API endpoints grouped by logical entity.
    """
    resources = await InventoryService.get_resource_groups(
        db=db,
        app_id=app_id,
        org_id=current_user.organization_id,
    )
    return resources


@router.get("/resources/{resource_name}", response_model=ApiResourceGroup)
async def get_resource_detail(
    resource_name: str,
    app_id: uuid.UUID = Query(..., description="Target application ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves details for a specific resource group including methods,
    paths, parameters, and related sub-resources.
    """
    resources = await InventoryService.get_resource_groups(
        db=db,
        app_id=app_id,
        org_id=current_user.organization_id,
    )
    for r in resources:
        if r["name"].lower() == resource_name.lower():
            return r
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Resource '{resource_name}' not found for this application"
    )


@router.get("/relationships", response_model=List[EndpointRelationshipResponse])
async def list_relationships(
    app_id: uuid.UUID = Query(..., description="Target application ID"),
    endpoint_id: Optional[uuid.UUID] = Query(None, description="Filter by connected endpoint ID"),
    relationship_type: Optional[str] = Query(None, description="Filter by relationship type (SAME_RESOURCE, PARENT_CHILD, READ_WRITE, AUTH_DEPENDENCY, etc.)"),
    provenance: Optional[str] = Query(None, description="Filter by evidence level (observed, documented, inferred)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves mapped endpoint dependencies and relationships with confidence scoring.
    """
    relationships = await InventoryService.get_relationships(
        db=db,
        app_id=app_id,
        org_id=current_user.organization_id,
        endpoint_id=endpoint_id,
        relationship_type=relationship_type,
        provenance=provenance,
        skip=skip,
        limit=limit,
    )
    return relationships


@router.get("/stats", response_model=InventoryOverviewStats)
async def get_inventory_statistics(
    app_id: uuid.UUID = Query(..., description="Target application ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves real inventory distribution metrics and counts from database records.
    """
    stats = await InventoryService.get_inventory_stats(
        db=db,
        app_id=app_id,
        org_id=current_user.organization_id,
    )
    return stats


@router.post("/rebuild", response_model=InventoryRebuildResponse)
async def rebuild_inventory(
    app_id: uuid.UUID = Query(..., description="Target application ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Re-runs API categorization, resource grouping, and relationship inference
    over all discovered endpoints for the target application.
    """
    result = await InventoryService.rebuild_inventory_mappings(
        db=db,
        app_id=app_id,
        org_id=current_user.organization_id,
    )
    return result


@router.get("/export")
async def export_inventory_data(
    app_id: uuid.UUID = Query(..., description="Target application ID"),
    format: str = Query("json", description="Export format: 'json' or 'csv'"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Exports API inventory in structured JSON or formula-sanitized CSV.
    """
    content, media_type = await InventoryService.export_inventory(
        db=db,
        app_id=app_id,
        org_id=current_user.organization_id,
        export_format=format,
    )
    filename = f"api_inventory_{app_id}.{ 'csv' if format.lower() == 'csv' else 'json' }"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

