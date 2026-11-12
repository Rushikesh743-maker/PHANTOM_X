import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.database.session import get_db
from app.models.endpoint import DiscoveredEndpoint, DiscoveryJob
from app.models.application import Application
from app.models.user import User
from app.api.deps import get_current_user
from app.services.discovery_service import DiscoveryService
from shared.contracts.models import (
    EndpointCreate,
    EndpointResponse,
    DiscoveryImportRequest,
    DiscoveryTriggerRequest,
    DiscoveryJobResponse,
    DiscoverySummaryResponse,
)
from shared.enums.common import HttpMethod

router = APIRouter()


@router.post("/trigger", response_model=DiscoverySummaryResponse, status_code=status.HTTP_200_OK)
async def trigger_endpoint_discovery(
    payload: Optional[DiscoveryTriggerRequest] = None,
    app_id: Optional[uuid.UUID] = Query(None, description="Target Application UUID query param fallback"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Triggers automated discovery for an authorized target application.
    Enforces tenant boundaries, active authorization scope validation,
    and dispatches specification profiling without destructive live attacks.
    """
    target_app_id = (payload.application_id if payload else None) or app_id
    if not target_app_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="application_id is required in request body or query parameter"
        )

    source_type = (payload.source_type if payload else None) or "SPECIFICATION"
    spec_content = payload.spec_content if payload else None

    job, in_scope_eps, out_of_scope = await DiscoveryService.trigger_discovery(
        db=db,
        app_id=target_app_id,
        org_id=current_user.organization_id,
        source_type=source_type,
        spec_content=spec_content,
        user_id=current_user.id
    )

    return DiscoverySummaryResponse(
        job_id=job.id,
        application_id=target_app_id,
        status=job.status,
        source_type=job.source_type,
        endpoints_found=job.endpoints_found,
        endpoints_in_scope=len(in_scope_eps),
        endpoints_out_of_scope=len(out_of_scope),
        out_of_scope_reasons=out_of_scope,
        message=job.error_message or f"Successfully discovered {len(in_scope_eps)} authorized endpoints."
    )


@router.post("/import/openapi", response_model=DiscoverySummaryResponse, status_code=status.HTTP_201_CREATED)
async def import_openapi_specification(
    payload: DiscoveryImportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Imports and analyzes an OpenAPI v3.x or Swagger v2.0 specification in JSON or YAML.
    Normalizes routes, extracts schemas and auth requirements, and validates against scope.
    """
    job, in_scope_eps, out_of_scope = await DiscoveryService.import_openapi(
        db=db,
        app_id=payload.application_id,
        org_id=current_user.organization_id,
        content=payload.content,
        user_id=current_user.id
    )

    return DiscoverySummaryResponse(
        job_id=job.id,
        application_id=payload.application_id,
        status=job.status,
        source_type="OPENAPI",
        endpoints_found=job.endpoints_found,
        endpoints_in_scope=len(in_scope_eps),
        endpoints_out_of_scope=len(out_of_scope),
        out_of_scope_reasons=out_of_scope,
        message=job.error_message or f"Imported {len(in_scope_eps)} endpoints from OpenAPI specification."
    )


@router.post("/import/postman", response_model=DiscoverySummaryResponse, status_code=status.HTTP_201_CREATED)
async def import_postman_collection(
    payload: DiscoveryImportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Imports and analyzes a Postman Collection (v2.0 or v2.1).
    Traverses folder hierarchies, normalizes paths, and extracts query/body structures.
    """
    job, in_scope_eps, out_of_scope = await DiscoveryService.import_postman(
        db=db,
        app_id=payload.application_id,
        org_id=current_user.organization_id,
        content=payload.content,
        user_id=current_user.id
    )

    return DiscoverySummaryResponse(
        job_id=job.id,
        application_id=payload.application_id,
        status=job.status,
        source_type="POSTMAN",
        endpoints_found=job.endpoints_found,
        endpoints_in_scope=len(in_scope_eps),
        endpoints_out_of_scope=len(out_of_scope),
        out_of_scope_reasons=out_of_scope,
        message=job.error_message or f"Imported {len(in_scope_eps)} endpoints from Postman collection."
    )


@router.post("/import/har", response_model=DiscoverySummaryResponse, status_code=status.HTTP_201_CREATED)
async def import_har_traffic(
    payload: DiscoveryImportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Imports and analyzes an authorized HTTP Archive (.har) recorded application traffic log.
    Filters out static assets, normalizes parameterized routes, and extracts observed headers.
    """
    job, in_scope_eps, out_of_scope = await DiscoveryService.import_har(
        db=db,
        app_id=payload.application_id,
        org_id=current_user.organization_id,
        content=payload.content,
        user_id=current_user.id
    )

    return DiscoverySummaryResponse(
        job_id=job.id,
        application_id=payload.application_id,
        status=job.status,
        source_type="HAR",
        endpoints_found=job.endpoints_found,
        endpoints_in_scope=len(in_scope_eps),
        endpoints_out_of_scope=len(out_of_scope),
        out_of_scope_reasons=out_of_scope,
        message=job.error_message or f"Imported {len(in_scope_eps)} endpoints from HAR traffic log."
    )


@router.get("/endpoints", response_model=List[EndpointResponse])
async def list_discovered_endpoints(
    app_id: Optional[uuid.UUID] = None,
    method: Optional[str] = None,
    path: Optional[str] = None,
    search: Optional[str] = None,
    risk_level: Optional[str] = None,
    source: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List discovered API endpoints and attack surfaces filtered by tenant organization."""
    return await DiscoveryService.list_endpoints(
        db=db,
        org_id=current_user.organization_id,
        app_id=app_id,
        method=method,
        path=path,
        search=search,
        risk_level=risk_level,
        source=source,
        skip=skip,
        limit=limit
    )


@router.post("/endpoints", response_model=EndpointResponse, status_code=status.HTTP_201_CREATED)
async def record_endpoint(
    endpoint_in: EndpointCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Manually records an endpoint under the authenticated user's organization."""
    result = await db.execute(
        select(Application).where(
            and_(
                Application.id == endpoint_in.application_id,
                Application.organization_id == current_user.organization_id
            )
        )
    )
    app_obj = result.scalars().first()
    if not app_obj:
        raise HTTPException(status_code=404, detail="Target application not found")

    new_endpoint = DiscoveredEndpoint(
        application_id=endpoint_in.application_id,
        path=endpoint_in.path,
        method=endpoint_in.method,
        auth_required=endpoint_in.auth_required if endpoint_in.auth_required is not None else True,
        parameters=[p.model_dump() for p in endpoint_in.parameters],
        response_codes=endpoint_in.response_codes,
        risk_level=endpoint_in.risk_level,
        raw_metadata={
            "discovery_source": "MANUAL",
            "evidence_classification": "DOCUMENTED"
        }
    )
    db.add(new_endpoint)
    await db.commit()
    await db.refresh(new_endpoint)
    return new_endpoint


@router.get("/endpoints/{endpoint_id}", response_model=EndpointResponse)
async def get_endpoint_details(
    endpoint_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves full details for a discovered endpoint under tenant isolation."""
    return await DiscoveryService.get_endpoint(
        db=db,
        endpoint_id=endpoint_id,
        org_id=current_user.organization_id
    )


@router.delete("/endpoints/{endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_discovered_endpoint(
    endpoint_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Deletes a discovered endpoint under tenant isolation."""
    await DiscoveryService.delete_endpoint(
        db=db,
        endpoint_id=endpoint_id,
        org_id=current_user.organization_id
    )


@router.get("/jobs", response_model=List[DiscoveryJobResponse])
async def list_discovery_jobs(
    app_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Lists discovery execution jobs for the caller's organization."""
    return await DiscoveryService.list_jobs(
        db=db,
        org_id=current_user.organization_id,
        app_id=app_id,
        skip=skip,
        limit=limit
    )


@router.get("/jobs/{job_id}", response_model=DiscoveryJobResponse)
async def get_discovery_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves status and summary of a specific discovery job."""
    return await DiscoveryService.get_job(
        db=db,
        job_id=job_id,
        org_id=current_user.organization_id
    )


@router.post("/jobs/{job_id}/cancel", response_model=DiscoveryJobResponse)
async def cancel_discovery_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancels a pending or running discovery job."""
    return await DiscoveryService.cancel_job(
        db=db,
        job_id=job_id,
        org_id=current_user.organization_id
    )
