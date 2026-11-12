
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, HttpUrl, ConfigDict

from shared.enums.common import (
    ScanStatus,
    VulnerabilitySeverity,
    VulnerabilityStatus,
    SecurityTestStatus,
    SafetyClassification,
    ExecutionMode,
    HttpMethod,
    EndpointRiskLevel,
    AttackChainSeverity,
    RegressionTestStatus,
    UserRole,
)


class BaseContract(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ==============================================================================
# 1. APPLICATION CONTRACTS
# ==============================================================================

class ApplicationScopeDetail(BaseContract):
    id: UUID
    organization_id: UUID
    application_id: UUID
    target_domain: str
    base_url: str
    permitted_paths: List[str] = Field(default_factory=lambda: ["/*"])
    excluded_paths: List[str] = Field(default_factory=lambda: ["/admin/*", "/logout", "/auth/reset-password"])
    scope_status: str = "ACTIVE"
    authorization_status: str = "AUTHORIZED"
    authorized_by: Optional[str] = None
    authorizer_role: Optional[str] = None
    authorization_notes: Optional[str] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    rate_limit_rps: int = 10
    max_concurrency: int = 2
    max_scan_duration_minutes: int = 60
    allowed_methods: List[str] = Field(default_factory=lambda: ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
    restricted_endpoint_patterns: List[str] = Field(default_factory=lambda: ["*/delete-account*", "*/purge*", "*/reset*"])
    require_synthetic_auth: bool = True
    allow_destructive: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ApplicationCreate(BaseContract):
    name: str = Field(..., min_length=2, max_length=100, description="Application display name")
    description: Optional[str] = Field(None, max_length=1000)
    target_url: str = Field(..., description="Base target URL for authorized testing")
    environment_name: str = Field(default="staging", description="e.g. staging, dev, sandbox")
    organization_id: Optional[UUID] = None

    # Authorized testing scope configuration
    permitted_paths: Optional[List[str]] = Field(default_factory=lambda: ["/*"], description="Permitted URL path patterns")
    excluded_paths: Optional[List[str]] = Field(default_factory=lambda: ["/admin/*", "/logout", "/auth/reset-password"], description="Excluded URL path patterns")
    rate_limit_rps: Optional[int] = Field(default=10, ge=1, le=100, description="Rate limit (req/s)")
    max_concurrency: Optional[int] = Field(default=2, ge=1, le=20, description="Max concurrent scans")
    max_scan_duration_minutes: Optional[int] = Field(default=60, ge=5, le=720, description="Max scan duration")
    allowed_methods: Optional[List[str]] = Field(default_factory=lambda: ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
    restricted_endpoint_patterns: Optional[List[str]] = Field(default_factory=lambda: ["*/delete-account*", "*/purge*", "*/reset*"])
    confirm_authorization: bool = Field(False, description="Explicit user confirmation of authorized testing consent")
    authorization_notes: Optional[str] = None


class ApplicationUpdate(BaseContract):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    target_url: Optional[str] = None
    environment_name: Optional[str] = None
    risk_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    status: Optional[str] = None

    # Scope updates
    permitted_paths: Optional[List[str]] = None
    excluded_paths: Optional[List[str]] = None
    rate_limit_rps: Optional[int] = Field(None, ge=1, le=100)
    max_concurrency: Optional[int] = Field(None, ge=1, le=20)
    max_scan_duration_minutes: Optional[int] = Field(None, ge=5, le=720)
    allowed_methods: Optional[List[str]] = None
    restricted_endpoint_patterns: Optional[List[str]] = None
    confirm_authorization: Optional[bool] = None
    authorization_notes: Optional[str] = None


class ApplicationResponse(BaseContract):
    id: UUID
    organization_id: UUID
    name: str
    description: Optional[str] = None
    target_url: str
    risk_score: float = 0.0
    status: str = "ACTIVE"
    created_at: datetime
    updated_at: datetime
    environment_name: Optional[str] = "staging"
    scope: Optional[ApplicationScopeDetail] = None


# ==============================================================================
# 2. SCAN CONTRACTS
# ==============================================================================

class ScanConfigurationCreate(BaseContract):
    name: str
    mode: ExecutionMode = ExecutionMode.OBSERVE
    max_depth: int = Field(default=3, ge=1, le=10)
    concurrency: int = Field(default=3, ge=1, le=20)
    rate_limit_rps: int = Field(default=10, ge=1, le=100)
    test_categories: List[str] = Field(default_factory=lambda: ["AUTH", "IDOR", "BOLA", "API_SECURITY"])


class ScanCreate(BaseContract):
    application_id: UUID
    configuration_id: Optional[UUID] = None
    mode: ExecutionMode = ExecutionMode.OBSERVE
    notes: Optional[str] = None


class ScanProgress(BaseContract):
    scan_id: UUID
    status: ScanStatus
    percent_complete: float = Field(ge=0.0, le=100.0)
    current_phase: str
    discovered_endpoints_count: int = 0
    executed_tests_count: int = 0
    findings_count: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ScanResponse(BaseContract):
    id: UUID
    organization_id: UUID
    application_id: UUID
    configuration_id: Optional[UUID] = None
    status: ScanStatus
    progress: float = 0.0
    findings_count: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# ==============================================================================
# 3. DISCOVERED ENDPOINT CONTRACTS
# ==============================================================================

class EndpointParameter(BaseContract):
    name: str
    location: str = "query"  # query, path, header, body
    param_type: str = "string"
    required: bool = False
    example: Optional[Any] = None


class EndpointAuthentication(BaseContract):
    auth_type: str = "BEARER"  # NONE, BEARER, BASIC, COOKIE, API_KEY
    header_name: Optional[str] = "Authorization"
    roles_permitted: List[str] = Field(default_factory=list)


class EndpointCreate(BaseContract):
    application_id: UUID
    path: str
    method: HttpMethod = HttpMethod.GET
    auth_required: bool = True
    parameters: List[EndpointParameter] = Field(default_factory=list)
    authentication: Optional[EndpointAuthentication] = None
    response_codes: List[int] = Field(default_factory=lambda: [200])
    risk_level: EndpointRiskLevel = EndpointRiskLevel.UNASSESSED


class EndpointResponse(BaseContract):
    id: UUID
    application_id: UUID
    path: str
    method: HttpMethod
    auth_required: bool
    parameters: List[Dict[str, Any]] = Field(default_factory=list)
    response_codes: List[int] = Field(default_factory=list)
    risk_level: EndpointRiskLevel
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class DiscoverySourceType(str, Enum):
    OPENAPI = "OPENAPI"
    POSTMAN = "POSTMAN"
    HAR = "HAR"
    PASSIVE = "PASSIVE"


class DiscoveryJobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class DiscoveryImportRequest(BaseContract):
    application_id: UUID
    content: str
    source_type: str = "OPENAPI"
    filename: Optional[str] = None


class DiscoveryTriggerRequest(BaseContract):
    application_id: UUID
    source_type: Optional[str] = "SPECIFICATION"
    spec_content: Optional[str] = None


class DiscoveryJobResponse(BaseContract):
    id: UUID
    organization_id: UUID
    application_id: UUID
    source_type: str
    status: str
    endpoints_found: int
    endpoints_in_scope: int
    endpoints_out_of_scope: int
    error_message: Optional[str] = None
    summary: Dict[str, Any] = Field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class DiscoverySummaryResponse(BaseContract):
    job_id: UUID
    application_id: UUID
    status: str
    source_type: str
    endpoints_found: int
    endpoints_in_scope: int
    endpoints_out_of_scope: int
    out_of_scope_reasons: List[Dict[str, Any]] = Field(default_factory=list)
    message: str


# ==============================================================================
# 3.1 API INVENTORY & MAPPING CONTRACTS
# ==============================================================================

class ApiCategory(str, Enum):
    AUTH_IDENTITY = "AUTH_IDENTITY"
    USER_MANAGEMENT = "USER_MANAGEMENT"
    ACCOUNT_MANAGEMENT = "ACCOUNT_MANAGEMENT"
    ADMIN_OPERATIONS = "ADMIN_OPERATIONS"
    FILE_MANAGEMENT = "FILE_MANAGEMENT"
    PAYMENT_TRANSACTION = "PAYMENT_TRANSACTION"
    DATA_RETRIEVAL = "DATA_RETRIEVAL"
    DATA_MODIFICATION = "DATA_MODIFICATION"
    REPORTING_ANALYTICS = "REPORTING_ANALYTICS"
    UNCLASSIFIED = "UNCLASSIFIED"


class RelationshipType(str, Enum):
    SAME_RESOURCE = "SAME_RESOURCE"
    PARENT_CHILD = "PARENT_CHILD"
    READ_WRITE = "READ_WRITE"
    AUTH_DEPENDENCY = "AUTH_DEPENDENCY"
    SHARED_PARAMETER = "SHARED_PARAMETER"
    SHARED_SCHEMA = "SHARED_SCHEMA"
    WORKFLOW_CANDIDATE = "WORKFLOW_CANDIDATE"


class RelationshipProvenance(str, Enum):
    OBSERVED = "OBSERVED"
    DOCUMENTED = "DOCUMENTED"
    INFERRED = "INFERRED"


class EndpointRelationshipResponse(BaseContract):
    id: UUID
    application_id: UUID
    source_endpoint_id: UUID
    target_endpoint_id: UUID
    source_endpoint_path: Optional[str] = None
    source_endpoint_method: Optional[str] = None
    target_endpoint_path: Optional[str] = None
    target_endpoint_method: Optional[str] = None
    relationship_type: str
    evidence_source: str
    confidence: float
    explanation: str
    provenance: str
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ApiResourceGroup(BaseContract):
    name: str
    parent_resource: Optional[str] = None
    endpoint_count: int
    endpoint_ids: List[UUID] = Field(default_factory=list)
    methods: List[str] = Field(default_factory=list)
    paths: List[str] = Field(default_factory=list)
    parameters: List[Dict[str, Any]] = Field(default_factory=list)
    request_schemas: List[Dict[str, Any]] = Field(default_factory=list)
    response_schemas: List[Dict[str, Any]] = Field(default_factory=list)
    related_resources: List[str] = Field(default_factory=list)
    discovery_sources: List[str] = Field(default_factory=list)
    confidence: float = 1.0
    evidence: str = ""


class InventoryOverviewStats(BaseContract):
    total_endpoints: int
    unique_resources: int
    method_distribution: Dict[str, int] = Field(default_factory=dict)
    category_distribution: Dict[str, int] = Field(default_factory=dict)
    source_distribution: Dict[str, int] = Field(default_factory=dict)
    documented_count: int = 0
    observed_count: int = 0
    imported_count: int = 0
    inferred_relationships_count: int = 0
    total_relationships_count: int = 0
    unclassified_count: int = 0
    incomplete_metadata_count: int = 0


class InventoryRebuildResponse(BaseContract):
    application_id: UUID
    endpoints_classified: int
    relationships_created: int
    unique_resources: int
    message: str


# ==============================================================================
# 4. ATTACK PLAN CONTRACTS
# ==============================================================================

class AttackScenario(BaseContract):
    scenario_id: str
    name: str
    category: str
    target_endpoint: str
    method: HttpMethod
    hypothesis: str
    safety_classification: SafetyClassification
    preconditions: List[str] = Field(default_factory=list)


class AttackPlanRequest(BaseContract):
    scan_id: UUID
    application_id: UUID
    risk_appetite: str = "LOW"  # LOW, MEDIUM, HIGH


class AttackPlanResponse(BaseContract):
    id: UUID
    scan_id: UUID
    application_id: UUID
    status: str = "DRAFT"  # DRAFT, APPROVED, REJECTED, EXECUTED
    scenarios: List[AttackScenario] = Field(default_factory=list)
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    created_at: datetime


# ==============================================================================
# 5. SECURITY TEST CONTRACTS
# ==============================================================================

class SecurityTestRequest(BaseContract):
    plan_id: UUID
    endpoint_id: UUID
    test_category: str
    test_parameters: Dict[str, Any] = Field(default_factory=dict)
    safety_classification: SafetyClassification = SafetyClassification.SAFE_READ_ONLY


class SecurityTestResponse(BaseContract):
    id: UUID
    plan_id: UUID
    endpoint_id: UUID
    test_category: str
    test_parameters: Dict[str, Any]
    safety_classification: SafetyClassification
    status: SecurityTestStatus
    result_summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ==============================================================================
# 6. EVIDENCE CONTRACTS
# ==============================================================================

class EvidenceCreate(BaseContract):
    vulnerability_id: Optional[UUID] = None
    test_id: Optional[UUID] = None
    request_dump: str
    response_dump: str
    proof_data: Dict[str, Any] = Field(default_factory=dict)
    screenshot_url: Optional[str] = None
    har_entry: Optional[Dict[str, Any]] = None


class EvidenceResponse(BaseContract):
    id: UUID
    vulnerability_id: Optional[UUID] = None
    test_id: Optional[UUID] = None
    request_dump: str
    response_dump: str
    proof_data: Dict[str, Any] = Field(default_factory=dict)
    screenshot_url: Optional[str] = None
    created_at: datetime


# ==============================================================================
# 7. VULNERABILITY CONTRACTS
# ==============================================================================

class VulnerabilityCreate(BaseContract):
    application_id: UUID
    scan_id: Optional[UUID] = None
    test_id: Optional[UUID] = None
    title: str
    severity: VulnerabilitySeverity
    status: VulnerabilityStatus = VulnerabilityStatus.DISCOVERED
    endpoint: str
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    recommendation: str
    cwe_id: Optional[str] = None
    cvss_score: Optional[float] = Field(None, ge=0.0, le=10.0)


class VulnerabilityResponse(BaseContract):
    id: UUID
    organization_id: UUID
    application_id: UUID
    scan_id: Optional[UUID] = None
    test_id: Optional[UUID] = None
    title: str
    severity: VulnerabilitySeverity
    status: VulnerabilityStatus
    endpoint: str
    confidence: float
    recommendation: str
    cwe_id: Optional[str] = None
    cvss_score: Optional[float] = None
    evidence: List[EvidenceResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


# ==============================================================================
# 8. ATTACK CHAIN CONTRACTS
# ==============================================================================

class AttackChainNode(BaseContract):
    id: str
    label: str
    step_type: str  # e.g., "DISCOVERY", "AUTH_BYPASS", "IDOR_READ", "PRIVILEGE_ESCALATION"
    endpoint: Optional[str] = None
    vulnerability_id: Optional[UUID] = None
    severity: VulnerabilitySeverity = VulnerabilitySeverity.MEDIUM


class AttackChainEdge(BaseContract):
    id: str
    source: str
    target: str
    description: str


class AttackChainResponse(BaseContract):
    id: UUID
    application_id: UUID
    scan_id: Optional[UUID] = None
    title: str
    description: str
    severity: AttackChainSeverity
    nodes: List[AttackChainNode]
    edges: List[AttackChainEdge]
    is_verified: bool = False
    created_at: datetime
    updated_at: datetime


# ==============================================================================
# 9. REGRESSION CONTRACTS
# ==============================================================================

class RegressionTestRequest(BaseContract):
    vulnerability_id: UUID
    application_id: UUID
    trigger_reason: str = "APPLICATION_UPDATE"


class RegressionResult(BaseContract):
    id: UUID
    vulnerability_id: UUID
    application_id: UUID
    status: RegressionTestStatus
    last_run_at: datetime
    result_summary: str
    is_reintroduced: bool = False
    created_at: datetime


# ==============================================================================
# 10. AUDIT & SAFETY CONTRACTS
# ==============================================================================

class AuditLogResponse(BaseContract):
    id: UUID
    organization_id: UUID
    user_id: Optional[UUID] = None
    action: str
    target_type: str
    target_id: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
    created_at: datetime


class ScopePermissionCreate(BaseContract):
    application_id: UUID
    host_pattern: str
    allowed_methods: List[HttpMethod] = Field(default_factory=lambda: [HttpMethod.GET, HttpMethod.POST])
    rate_limit_rps: int = Field(default=10, ge=1, le=100)
    is_destructive_allowed: bool = False


class ScopePermissionResponse(BaseContract):
    id: UUID
    organization_id: UUID
    application_id: UUID
    host_pattern: str
    allowed_methods: List[str]
    rate_limit_rps: int
    is_destructive_allowed: bool
    created_at: datetime
    updated_at: datetime


# ==============================================================================
# 11. AUTHENTICATION & USER CONTRACTS
# ==============================================================================

class UserLogin(BaseContract):
    email: str
    password: str


class TokenResponse(BaseContract):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: UUID
    email: str
    role: UserRole


class UserResponse(BaseContract):
    id: UUID
    organization_id: UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime

