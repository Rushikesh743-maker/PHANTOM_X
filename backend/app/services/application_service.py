import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple, Dict, Any
from urllib.parse import urlparse

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, desc
from sqlalchemy.orm import selectinload

from app.models.application import Application, ApplicationEnvironment
from app.models.scope_safety import ApplicationScopePolicy
from app.models.user import User
from app.models.audit import AuditLog
from app.features.security_operations.audit_logs.event_recorder import AuditEventRecorder
from app.features.security_operations.audit_logs.schemas import (
    AuditEventCreate,
    AuditCategory,
    AuditStatus,
    AuditSeverity,
)
from shared.contracts.models import (
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationResponse,
    ApplicationScopeDetail,
)

VALID_HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}


class ApplicationService:
    """Service handling application registration, profiling, scope management, and lifecycle."""

    @staticmethod
    def validate_target_url(target_url: str) -> Tuple[str, str]:
        """
        Validate and normalize target application base URL.
        Returns normalized URL and clean hostname.
        """
        if not target_url or not isinstance(target_url, str):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Target URL is required."
            )
        url_stripped = target_url.strip()
        if not url_stripped:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Target URL cannot be empty."
            )

        try:
            parsed = urlparse(url_stripped)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Malformed target URL: {str(e)}"
            )

        if parsed.scheme.lower() not in ("http", "https"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Target URL must use HTTP or HTTPS protocol (e.g., https://example.com)."
            )

        if not parsed.netloc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Target URL must include a valid hostname or domain."
            )

        host = parsed.netloc.split(":")[0].strip().lower()
        if not host or " " in host or any(c in host for c in ["<", ">", ";", "'", '"', "\\"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Target URL contains an invalid domain or hostname format."
            )

        if ":" in parsed.netloc:
            port_str = parsed.netloc.split(":")[1].strip()
            try:
                port = int(port_str)
                if port < 1 or port > 65535:
                    raise ValueError()
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Target URL has an invalid port number: {port_str}."
                )

        clean_url = f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"
        if parsed.path and parsed.path != "/":
            clean_url += parsed.path.rstrip("/")

        return clean_url, host

    @staticmethod
    def validate_scope_paths(
        permitted_paths: Optional[List[str]],
        excluded_paths: Optional[List[str]]
    ) -> Tuple[List[str], List[str]]:
        """Validate permitted and excluded path pattern definitions."""
        valid_permitted: List[str] = []
        if permitted_paths is not None:
            if not isinstance(permitted_paths, list):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Permitted paths must be provided as a list of path patterns."
                )
            for p in permitted_paths:
                if not isinstance(p, str) or not p.strip():
                    continue
                clean = p.strip()
                if not clean.startswith("/"):
                    clean = "/" + clean
                valid_permitted.append(clean)

        if not valid_permitted:
            valid_permitted = ["/*"]

        valid_excluded: List[str] = []
        if excluded_paths is not None:
            if not isinstance(excluded_paths, list):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Excluded paths must be provided as a list of path patterns."
                )
            for p in excluded_paths:
                if not isinstance(p, str) or not p.strip():
                    continue
                clean = p.strip()
                if not clean.startswith("/"):
                    clean = "/" + clean
                valid_excluded.append(clean)

        return valid_permitted, valid_excluded

    @staticmethod
    def validate_allowed_methods(allowed_methods: Optional[List[str]]) -> List[str]:
        """Validate that HTTP methods in scope are recognized standard methods."""
        if not allowed_methods:
            return ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
        methods: List[str] = []
        for m in allowed_methods:
            m_upper = str(m).strip().upper()
            if m_upper not in VALID_HTTP_METHODS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid HTTP method in scope: {m}. Allowed: {sorted(VALID_HTTP_METHODS)}."
                )
            if m_upper not in methods:
                methods.append(m_upper)
        return methods

    @staticmethod
    def _resolve_scope_status(sp: ApplicationScopePolicy) -> Tuple[str, str]:
        """
        Dynamically determine scope_status and authorization_status based on valid_until window.
        Returns (scope_status, authorization_status).
        """
        scope_st = sp.scope_status
        auth_st = sp.authorization_status
        if sp.valid_until:
            valid_until_utc = sp.valid_until if sp.valid_until.tzinfo else sp.valid_until.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > valid_until_utc and sp.authorization_status == "AUTHORIZED":
                auth_st = "EXPIRED"
                scope_st = "EXPIRED"
        return scope_st, auth_st

    @classmethod
    def build_response(cls, app: Application) -> ApplicationResponse:
        """Convert an Application DB model into an ApplicationResponse schema with scope & environment."""
        env_name = "staging"
        if app.environments and len(app.environments) > 0:
            env_name = app.environments[0].name

        scope_detail: Optional[ApplicationScopeDetail] = None
        if app.scope_policy:
            sp = app.scope_policy
            scope_st, auth_st = cls._resolve_scope_status(sp)
            scope_detail = ApplicationScopeDetail(
                id=sp.id,
                organization_id=sp.organization_id,
                application_id=sp.application_id,
                target_domain=sp.target_domain,
                base_url=sp.base_url,
                permitted_paths=sp.permitted_paths or ["/*"],
                excluded_paths=sp.excluded_paths or [],
                scope_status=scope_st,
                authorization_status=auth_st,
                authorized_by=sp.authorized_by,
                authorizer_role=sp.authorizer_role,
                authorization_notes=sp.authorization_notes,
                valid_from=sp.valid_from,
                valid_until=sp.valid_until,
                rate_limit_rps=sp.rate_limit_rps,
                max_concurrency=sp.max_concurrency,
                max_scan_duration_minutes=sp.max_scan_duration_minutes,
                allowed_methods=sp.allowed_methods or [],
                restricted_endpoint_patterns=sp.restricted_endpoint_patterns or [],
                require_synthetic_auth=sp.require_synthetic_auth,
                allow_destructive=sp.allow_destructive,
                created_at=sp.created_at,
                updated_at=sp.updated_at,
            )

        return ApplicationResponse(
            id=app.id,
            organization_id=app.organization_id,
            name=app.name,
            description=app.description,
            target_url=app.target_url,
            risk_score=app.risk_score,
            status=app.status,
            created_at=app.created_at,
            updated_at=app.updated_at,
            environment_name=env_name,
            scope=scope_detail,
        )

    @classmethod
    async def register_application(
        cls,
        db: AsyncSession,
        app_in: ApplicationCreate,
        current_user: User
    ) -> ApplicationResponse:
        """
        Register a new application target under authorized security boundaries.
        Persists application, environment, and testing scope policy atomically.
        """
        # 1. Validate application name
        name = app_in.name.strip() if app_in.name else ""
        if len(name) < 2 or len(name) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Application name must be between 2 and 100 characters."
            )

        # 2. Validate target URL
        clean_url, host = cls.validate_target_url(app_in.target_url)

        # 3. Explicit authorization confirmation check
        if not app_in.confirm_authorization:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Explicit authorization confirmation is required to register an application for security testing."
            )

        # 4. Validate scope paths and methods
        permitted_paths, excluded_paths = cls.validate_scope_paths(
            app_in.permitted_paths,
            app_in.excluded_paths
        )
        allowed_methods = cls.validate_allowed_methods(app_in.allowed_methods)

        # 5. Check for duplicate application name in this organization
        existing_dup = await db.execute(
            select(Application).where(
                Application.organization_id == current_user.organization_id,
                Application.name == name
            )
        )
        if existing_dup.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An application named '{name}' is already registered in your organization."
            )

        # 6. Create Application record
        new_app = Application(
            organization_id=current_user.organization_id,
            name=name,
            description=app_in.description.strip() if app_in.description else None,
            target_url=clean_url,
            risk_score=0.0,
            status="ACTIVE"
        )
        db.add(new_app)
        await db.flush()

        # 7. Create default ApplicationEnvironment
        env_tier = (app_in.environment_name or "staging").strip().lower()
        if env_tier not in ("staging", "development", "sandbox", "dev"):
            env_tier = "staging"
        env = ApplicationEnvironment(
            application_id=new_app.id,
            name=env_tier,
            base_url=clean_url,
            env_type=env_tier
        )
        db.add(env)

        # 8. Create ApplicationScopePolicy
        now = datetime.now(timezone.utc)
        scope_policy = ApplicationScopePolicy(
            organization_id=current_user.organization_id,
            application_id=new_app.id,
            target_domain=host,
            base_url=clean_url,
            permitted_paths=permitted_paths,
            excluded_paths=excluded_paths,
            scope_status="ACTIVE",
            authorization_status="AUTHORIZED",
            authorized_by=current_user.email,
            authorizer_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
            authorization_notes=app_in.authorization_notes or "Authorized during application registration.",
            valid_from=now,
            valid_until=now + timedelta(days=90),
            rate_limit_rps=app_in.rate_limit_rps or 10,
            max_concurrency=app_in.max_concurrency or 2,
            max_scan_duration_minutes=app_in.max_scan_duration_minutes or 60,
            allowed_methods=allowed_methods,
            restricted_endpoint_patterns=app_in.restricted_endpoint_patterns or ["*/delete-account*", "*/purge*", "*/reset*"],
            require_synthetic_auth=True,
            allow_destructive=False,
        )
        db.add(scope_policy)

        # 9. Record Audit Log
        try:
            await AuditEventRecorder.record_authorization_event(
                db=db,
                org_id=current_user.organization_id,
                app_id=new_app.id,
                event_type="AUTHZ_GRANTED",
                action=f"Registered target application '{new_app.name}' and authorized testing scope",
                authorizer_email=current_user.email,
                authorizer_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
                details={
                    "name": new_app.name,
                    "target_url": clean_url,
                    "target_domain": host,
                    "environment": env_tier,
                    "scope_status": "ACTIVE",
                }
            )
        except Exception:
            pass  # Non-blocking for core registration transaction

        await db.commit()

        # Eagerly reload with relationships
        result = await db.execute(
            select(Application)
            .options(
                selectinload(Application.environments),
                selectinload(Application.scope_policy)
            )
            .where(Application.id == new_app.id)
        )
        loaded_app = result.scalars().first()
        return cls.build_response(loaded_app or new_app)

    @classmethod
    async def list_applications(
        cls,
        db: AsyncSession,
        current_user: User,
        search: Optional[str] = None,
        status_filter: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[ApplicationResponse]:
        """
        List registered applications for the user's organization.
        Guarantees strict tenant isolation.
        """
        query = (
            select(Application)
            .options(
                selectinload(Application.environments),
                selectinload(Application.scope_policy)
            )
            .where(Application.organization_id == current_user.organization_id)
        )

        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Application.name.ilike(term),
                    Application.target_url.ilike(term),
                    Application.description.ilike(term)
                )
            )

        if status_filter and status_filter.strip().upper() != "ALL":
            query = query.where(Application.status == status_filter.strip().upper())

        query = query.order_by(desc(Application.created_at)).offset(skip).limit(limit)
        result = await db.execute(query)
        apps = result.scalars().all()

        return [cls.build_response(a) for a in apps]

    @classmethod
    async def get_application(
        cls,
        db: AsyncSession,
        app_id: uuid.UUID,
        current_user: User
    ) -> ApplicationResponse:
        """
        Retrieve details of a specific target application.
        Strictly enforces organization tenant boundaries.
        """
        result = await db.execute(
            select(Application)
            .options(
                selectinload(Application.environments),
                selectinload(Application.scope_policy)
            )
            .where(
                Application.id == app_id,
                Application.organization_id == current_user.organization_id
            )
        )
        app_obj = result.scalars().first()
        if not app_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )
        return cls.build_response(app_obj)

    @classmethod
    async def update_application(
        cls,
        db: AsyncSession,
        app_id: uuid.UUID,
        app_update: ApplicationUpdate,
        current_user: User
    ) -> ApplicationResponse:
        """
        Update application details and testing scope configuration.
        Validates target URL and scope constraints.
        """
        result = await db.execute(
            select(Application)
            .options(
                selectinload(Application.environments),
                selectinload(Application.scope_policy)
            )
            .where(
                Application.id == app_id,
                Application.organization_id == current_user.organization_id
            )
        )
        app_obj = result.scalars().first()
        if not app_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )

        updated_fields: List[str] = []

        # 1. Update Name
        if app_update.name is not None:
            name = app_update.name.strip()
            if len(name) < 2 or len(name) > 100:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Application name must be between 2 and 100 characters."
                )
            # Check for conflict with another app in same org
            dup = await db.execute(
                select(Application).where(
                    Application.organization_id == current_user.organization_id,
                    Application.name == name,
                    Application.id != app_id
                )
            )
            if dup.scalars().first():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Another application named '{name}' already exists in your organization."
                )
            app_obj.name = name
            updated_fields.append("name")

        # 2. Update Description
        if app_update.description is not None:
            app_obj.description = app_update.description.strip() if app_update.description else None
            updated_fields.append("description")

        # 3. Update Target URL
        if app_update.target_url is not None:
            clean_url, host = cls.validate_target_url(app_update.target_url)
            app_obj.target_url = clean_url
            updated_fields.append("target_url")

            # Update environment base_url
            if app_obj.environments:
                for env in app_obj.environments:
                    env.base_url = clean_url

            # Update scope policy base_url and target_domain
            if app_obj.scope_policy:
                app_obj.scope_policy.base_url = clean_url
                app_obj.scope_policy.target_domain = host

        # 4. Update Environment name/tier
        if app_update.environment_name is not None:
            env_tier = app_update.environment_name.strip().lower()
            if app_obj.environments and len(app_obj.environments) > 0:
                app_obj.environments[0].name = env_tier
                app_obj.environments[0].env_type = env_tier
            updated_fields.append("environment_name")

        # 5. Update Risk score or status
        if app_update.risk_score is not None:
            app_obj.risk_score = app_update.risk_score
            updated_fields.append("risk_score")

        if app_update.status is not None:
            app_obj.status = app_update.status.strip().upper()
            updated_fields.append("status")

        # 6. Update Scope Policy attributes if provided
        if app_obj.scope_policy:
            sp = app_obj.scope_policy
            if app_update.permitted_paths is not None:
                paths, _ = cls.validate_scope_paths(app_update.permitted_paths, None)
                sp.permitted_paths = paths
                updated_fields.append("permitted_paths")

            if app_update.excluded_paths is not None:
                _, ex_paths = cls.validate_scope_paths(None, app_update.excluded_paths)
                sp.excluded_paths = ex_paths
                updated_fields.append("excluded_paths")

            if app_update.rate_limit_rps is not None:
                sp.rate_limit_rps = app_update.rate_limit_rps
                updated_fields.append("rate_limit_rps")

            if app_update.max_concurrency is not None:
                sp.max_concurrency = app_update.max_concurrency
                updated_fields.append("max_concurrency")

            if app_update.max_scan_duration_minutes is not None:
                sp.max_scan_duration_minutes = app_update.max_scan_duration_minutes
                updated_fields.append("max_scan_duration_minutes")

            if app_update.allowed_methods is not None:
                sp.allowed_methods = cls.validate_allowed_methods(app_update.allowed_methods)
                updated_fields.append("allowed_methods")

            if app_update.restricted_endpoint_patterns is not None:
                sp.restricted_endpoint_patterns = app_update.restricted_endpoint_patterns
                updated_fields.append("restricted_endpoint_patterns")

            if app_update.authorization_notes is not None:
                sp.authorization_notes = app_update.authorization_notes
                updated_fields.append("authorization_notes")

            if app_update.confirm_authorization is True:
                sp.authorization_status = "AUTHORIZED"
                sp.scope_status = "ACTIVE"
                sp.authorized_by = current_user.email
                sp.valid_from = datetime.now(timezone.utc)
                sp.valid_until = datetime.now(timezone.utc) + timedelta(days=90)
                updated_fields.append("confirm_authorization")

        # 7. Record Audit Log
        try:
            await AuditEventRecorder.record_event(
                db=db,
                org_id=current_user.organization_id,
                event_in=AuditEventCreate(
                    category=AuditCategory.CONFIG_CHANGE,
                    event_type="APPLICATION_UPDATED",
                    action=f"Updated profiling for target application '{app_obj.name}'",
                    status=AuditStatus.SUCCESS,
                    severity=AuditSeverity.LOW,
                    source_module="APPLICATION_INTELLIGENCE",
                    target_type="Application",
                    target_id=str(app_obj.id),
                    application_id=app_obj.id,
                    user_id=current_user.id,
                    actor_email=current_user.email,
                    details={"updated_fields": updated_fields}
                ),
                commit=False
            )
        except Exception:
            pass

        await db.commit()
        await db.refresh(app_obj)
        return cls.build_response(app_obj)

    @classmethod
    async def delete_application(
        cls,
        db: AsyncSession,
        app_id: uuid.UUID,
        current_user: User
    ) -> None:
        """
        Delete an application and its associated environments, scope policy, and data.
        Guarantees tenant isolation.
        """
        result = await db.execute(
            select(Application).where(
                Application.id == app_id,
                Application.organization_id == current_user.organization_id
            )
        )
        app_obj = result.scalars().first()
        if not app_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )

        app_name = app_obj.name

        # Record Audit Log prior to delete
        try:
            await AuditEventRecorder.record_event(
                db=db,
                org_id=current_user.organization_id,
                event_in=AuditEventCreate(
                    category=AuditCategory.RESOURCE_MANAGEMENT,
                    event_type="APPLICATION_DELETED",
                    action=f"Deleted target application '{app_name}'",
                    status=AuditStatus.SUCCESS,
                    severity=AuditSeverity.MEDIUM,
                    source_module="APPLICATION_INTELLIGENCE",
                    target_type="Application",
                    target_id=str(app_id),
                    application_id=app_id,
                    user_id=current_user.id,
                    actor_email=current_user.email,
                    details={"name": app_name, "deleted_by": current_user.email}
                ),
                commit=False
            )
        except Exception:
            pass

        await db.delete(app_obj)
        await db.commit()

    @classmethod
    async def get_application_scope(
        cls,
        db: AsyncSession,
        app_id: uuid.UUID,
        current_user: User
    ) -> ApplicationScopeDetail:
        """
        Retrieve authorized testing scope for an application.
        Ensures future discovery and scanning features access validated boundaries.
        """
        # Ensure application exists and belongs to organization
        app_res = await db.execute(
            select(Application).where(
                Application.id == app_id,
                Application.organization_id == current_user.organization_id
            )
        )
        app_obj = app_res.scalars().first()
        if not app_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )

        # Retrieve scope policy
        policy_res = await db.execute(
            select(ApplicationScopePolicy).where(
                ApplicationScopePolicy.application_id == app_id,
                ApplicationScopePolicy.organization_id == current_user.organization_id
            )
        )
        sp = policy_res.scalars().first()
        if not sp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Authorized scope policy not configured for this application."
            )

        scope_st, auth_st = cls._resolve_scope_status(sp)
        return ApplicationScopeDetail(
            id=sp.id,
            organization_id=sp.organization_id,
            application_id=sp.application_id,
            target_domain=sp.target_domain,
            base_url=sp.base_url,
            permitted_paths=sp.permitted_paths or ["/*"],
            excluded_paths=sp.excluded_paths or [],
            scope_status=scope_st,
            authorization_status=auth_st,
            authorized_by=sp.authorized_by,
            authorizer_role=sp.authorizer_role,
            authorization_notes=sp.authorization_notes,
            valid_from=sp.valid_from,
            valid_until=sp.valid_until,
            rate_limit_rps=sp.rate_limit_rps,
            max_concurrency=sp.max_concurrency,
            max_scan_duration_minutes=sp.max_scan_duration_minutes,
            allowed_methods=sp.allowed_methods or [],
            restricted_endpoint_patterns=sp.restricted_endpoint_patterns or [],
            require_synthetic_auth=sp.require_synthetic_auth,
            allow_destructive=sp.allow_destructive,
            created_at=sp.created_at,
            updated_at=sp.updated_at,
        )
