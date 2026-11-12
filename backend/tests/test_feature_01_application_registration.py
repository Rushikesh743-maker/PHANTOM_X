import uuid
import pytest
import jwt
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.models.user import Organization, User
from app.models.application import Application, ApplicationEnvironment
from app.models.scope_safety import ApplicationScopePolicy
from app.models.audit import AuditLog
from shared.enums.common import UserRole


@pytest.fixture
async def app_test_setup():
    """Setup dual tenant organizations and authenticated users."""
    from tests.conftest import TestingSessionLocal
    async with TestingSessionLocal() as db:
        # Organization A & User A
        org_a = Organization(name="FinTech Corp", slug=f"fintech-{uuid.uuid4().hex[:8]}")
        db.add(org_a)
        await db.flush()

        user_a = User(
            organization_id=org_a.id,
            email=f"alice-{uuid.uuid4().hex[:8]}@fintech.local",
            hashed_password="hashed_pw_alice",
            full_name="Alice SecOps",
            role=UserRole.SECURITY_ENGINEER,
            is_active=True
        )
        db.add(user_a)

        # Organization B & User B
        org_b = Organization(name="HealthCare Corp", slug=f"healthcare-{uuid.uuid4().hex[:8]}")
        db.add(org_b)
        await db.flush()

        user_b = User(
            organization_id=org_b.id,
            email=f"bob-{uuid.uuid4().hex[:8]}@healthcare.local",
            hashed_password="hashed_pw_bob",
            full_name="Bob Security",
            role=UserRole.SECURITY_ENGINEER,
            is_active=True
        )
        db.add(user_b)
        await db.commit()
        await db.refresh(user_a)
        await db.refresh(user_b)

        token_a = jwt.encode(
            {"sub": str(user_a.id), "org_id": str(org_a.id), "role": user_a.role.value},
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        token_b = jwt.encode(
            {"sub": str(user_b.id), "org_id": str(org_b.id), "role": user_b.role.value},
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )

        return {
            "org_a_id": str(org_a.id),
            "org_b_id": str(org_b.id),
            "user_a_id": str(user_a.id),
            "user_b_id": str(user_b.id),
            "user_a_email": user_a.email,
            "user_b_email": user_b.email,
            "auth_a": {"Authorization": f"Bearer {token_a}"},
            "auth_b": {"Authorization": f"Bearer {token_b}"},
        }


# ==============================================================================
# 1. SUCCESSFUL APPLICATION REGISTRATION
# ==============================================================================

@pytest.mark.asyncio
async def test_01_successful_application_registration(client: AsyncClient, app_test_setup):
    """Verify complete application registration workflow with authorized scope policy persistence."""
    payload = {
        "name": "Payments Portal API",
        "description": "Core payment processing microservice staging cluster",
        "target_url": "https://staging-pay.fintech.local:8443",
        "environment_name": "staging",
        "permitted_paths": ["/api/v1/*", "/health", "/checkout/*"],
        "excluded_paths": ["/admin/*", "/internal/metrics", "/logout"],
        "rate_limit_rps": 25,
        "max_concurrency": 4,
        "max_scan_duration_minutes": 90,
        "allowed_methods": ["GET", "POST", "PUT", "PATCH"],
        "restricted_endpoint_patterns": ["*/purge*", "*/destroy*"],
        "confirm_authorization": True,
        "authorization_notes": "Authorized by Security Lead for sprint assessment."
    }

    res = await client.post("/api/v1/applications/", json=payload, headers=app_test_setup["auth_a"])
    assert res.status_code == 201
    data = res.json()

    assert data["name"] == "Payments Portal API"
    assert data["description"] == "Core payment processing microservice staging cluster"
    assert data["target_url"] == "https://staging-pay.fintech.local:8443"
    assert data["organization_id"] == app_test_setup["org_a_id"]
    assert data["status"] == "ACTIVE"
    assert data["environment_name"] == "staging"

    # Verify Scope Policy attached
    scope = data["scope"]
    assert scope is not None
    assert scope["target_domain"] == "staging-pay.fintech.local"
    assert scope["base_url"] == "https://staging-pay.fintech.local:8443"
    assert scope["permitted_paths"] == ["/api/v1/*", "/health", "/checkout/*"]
    assert scope["excluded_paths"] == ["/admin/*", "/internal/metrics", "/logout"]
    assert scope["scope_status"] == "ACTIVE"
    assert scope["authorization_status"] == "AUTHORIZED"
    assert scope["authorized_by"] == app_test_setup["user_a_email"]
    assert scope["rate_limit_rps"] == 25
    assert scope["max_concurrency"] == 4
    assert scope["max_scan_duration_minutes"] == 90
    assert set(scope["allowed_methods"]) == {"GET", "POST", "PUT", "PATCH"}
    assert scope["allow_destructive"] is False
    assert scope["require_synthetic_auth"] is True


# ==============================================================================
# 2. VALIDATION: MISSING REQUIRED FIELDS
# ==============================================================================

@pytest.mark.asyncio
async def test_02_missing_required_fields_validation(client: AsyncClient, app_test_setup):
    """Verify validation errors when required fields are missing."""
    headers = app_test_setup["auth_a"]

    # Missing name
    res1 = await client.post("/api/v1/applications/", json={
        "target_url": "https://valid.target.com",
        "confirm_authorization": True
    }, headers=headers)
    assert res1.status_code == 422

    # Missing target_url
    res2 = await client.post("/api/v1/applications/", json={
        "name": "App Without Target",
        "confirm_authorization": True
    }, headers=headers)
    assert res2.status_code == 422

    # Whitespace-only name
    res3 = await client.post("/api/v1/applications/", json={
        "name": "   ",
        "target_url": "https://valid.target.com",
        "confirm_authorization": True
    }, headers=headers)
    assert res3.status_code == 400


# ==============================================================================
# 3. VALIDATION: INVALID TARGET URLS
# ==============================================================================

@pytest.mark.asyncio
async def test_03_invalid_target_url_validation(client: AsyncClient, app_test_setup):
    """Verify rejection of invalid target URL formats, schemes, and ports."""
    headers = app_test_setup["auth_a"]

    invalid_urls = [
        "not-a-valid-url",
        "ftp://ftp.example.com",
        "javascript:alert(1)",
        "file:///etc/passwd",
        "data:text/html;base64,PHNjcmlwdD4=",
        "http://",
        "https://invalid port:99999",
        "https://example.com:99999",  # Port out of range
        "https://bad domain with spaces.com",
    ]

    for bad_url in invalid_urls:
        res = await client.post("/api/v1/applications/", json={
            "name": f"App-{uuid.uuid4().hex[:6]}",
            "target_url": bad_url,
            "confirm_authorization": True
        }, headers=headers)
        assert res.status_code in (400, 422), f"URL '{bad_url}' should have been rejected, got {res.status_code}"


# ==============================================================================
# 4. SECURITY: EXPLICIT AUTHORIZATION CONFIRMATION REQUIRED
# ==============================================================================

@pytest.mark.asyncio
async def test_04_explicit_authorization_confirmation_required(client: AsyncClient, app_test_setup):
    """Verify application registration is rejected when authorization confirmation is missing/false."""
    headers = app_test_setup["auth_a"]

    # confirm_authorization is False
    res1 = await client.post("/api/v1/applications/", json={
        "name": "Unauthorized Target",
        "target_url": "https://target.fintech.local",
        "confirm_authorization": False
    }, headers=headers)
    assert res1.status_code == 400
    assert "authorization confirmation is required" in res1.json()["detail"].lower()

    # confirm_authorization omitted (defaults to False)
    res2 = await client.post("/api/v1/applications/", json={
        "name": "Unauthorized Target 2",
        "target_url": "https://target2.fintech.local"
    }, headers=headers)
    assert res2.status_code == 400


# ==============================================================================
# 5. VALIDATION: INVALID SCOPE SPECIFICATION
# ==============================================================================

@pytest.mark.asyncio
async def test_05_invalid_scope_specification(client: AsyncClient, app_test_setup):
    """Verify rejection of invalid HTTP methods or malformed scope structures."""
    headers = app_test_setup["auth_a"]

    # Invalid HTTP method
    res1 = await client.post("/api/v1/applications/", json={
        "name": "Scope Test App",
        "target_url": "https://staging.fintech.local",
        "confirm_authorization": True,
        "allowed_methods": ["GET", "PROPFIND", "FAKE_METHOD"]
    }, headers=headers)
    assert res1.status_code == 400
    assert "invalid http method" in res1.json()["detail"].lower()

    # Permitted paths not a list
    res2 = await client.post("/api/v1/applications/", json={
        "name": "Scope Test App 2",
        "target_url": "https://staging.fintech.local",
        "confirm_authorization": True,
        "permitted_paths": "not-a-list"
    }, headers=headers)
    assert res2.status_code in (400, 422)


# ==============================================================================
# 6. DUPLICATE APPLICATION NAME CONFLICT
# ==============================================================================

@pytest.mark.asyncio
async def test_06_duplicate_application_name_conflict(client: AsyncClient, app_test_setup):
    """Verify conflict error (409) when creating an application with a duplicate name in same organization."""
    headers = app_test_setup["auth_a"]
    app_name = f"Duplicate App {uuid.uuid4().hex[:6]}"

    # First registration
    res1 = await client.post("/api/v1/applications/", json={
        "name": app_name,
        "target_url": "https://app1.fintech.local",
        "confirm_authorization": True
    }, headers=headers)
    assert res1.status_code == 201

    # Second registration with same name
    res2 = await client.post("/api/v1/applications/", json={
        "name": app_name,
        "target_url": "https://app2.fintech.local",
        "confirm_authorization": True
    }, headers=headers)
    assert res2.status_code == 409
    assert "already registered" in res2.json()["detail"]


# ==============================================================================
# 7. APPLICATION LISTING & SEARCH FILTERING (TENANT ISOLATED)
# ==============================================================================

@pytest.mark.asyncio
async def test_07_application_listing_and_filtering(client: AsyncClient, app_test_setup):
    """Verify application listing respects organization boundaries and supports search."""
    headers_a = app_test_setup["auth_a"]
    headers_b = app_test_setup["auth_b"]

    prefix = uuid.uuid4().hex[:6]
    app_a1_name = f"Alpha-{prefix}"
    app_a2_name = f"Beta-{prefix}"
    app_b1_name = f"Gamma-{prefix}"

    # Register 2 apps in Org A
    await client.post("/api/v1/applications/", json={
        "name": app_a1_name,
        "target_url": "https://alpha.fintech.local",
        "confirm_authorization": True
    }, headers=headers_a)

    await client.post("/api/v1/applications/", json={
        "name": app_a2_name,
        "target_url": "https://beta.fintech.local",
        "confirm_authorization": True
    }, headers=headers_a)

    # Register 1 app in Org B
    await client.post("/api/v1/applications/", json={
        "name": app_b1_name,
        "target_url": "https://gamma.healthcare.local",
        "confirm_authorization": True
    }, headers=headers_b)

    # Org A lists: should see Alpha and Beta, but NOT Gamma
    res_a = await client.get("/api/v1/applications/", headers=headers_a)
    assert res_a.status_code == 200
    names_a = [a["name"] for a in res_a.json()]
    assert app_a1_name in names_a
    assert app_a2_name in names_a
    assert app_b1_name not in names_a

    # Org B lists: should see Gamma, but NOT Alpha or Beta
    res_b = await client.get("/api/v1/applications/", headers=headers_b)
    assert res_b.status_code == 200
    names_b = [a["name"] for a in res_b.json()]
    assert app_b1_name in names_b
    assert app_a1_name not in names_b
    assert app_a2_name not in names_b

    # Search filter in Org A
    search_res = await client.get(f"/api/v1/applications/?search={app_a1_name}", headers=headers_a)
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert len(search_data) == 1
    assert search_data[0]["name"] == app_a1_name


# ==============================================================================
# 8. RETRIEVE APPLICATION BY ID
# ==============================================================================

@pytest.mark.asyncio
async def test_08_get_application_by_id(client: AsyncClient, app_test_setup):
    """Verify application retrieval by ID includes full profiling and scope policy."""
    headers = app_test_setup["auth_a"]

    create_res = await client.post("/api/v1/applications/", json={
        "name": f"Detail App {uuid.uuid4().hex[:6]}",
        "target_url": "https://details.fintech.local/api",
        "description": "Comprehensive details test target",
        "confirm_authorization": True
    }, headers=headers)
    app_id = create_res.json()["id"]

    get_res = await client.get(f"/api/v1/applications/{app_id}", headers=headers)
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["id"] == app_id
    assert data["target_url"] == "https://details.fintech.local/api"
    assert data["scope"]["target_domain"] == "details.fintech.local"


# ==============================================================================
# 9. RETRIEVE APPLICATION SCOPE FOR FUTURE DISCOVERY
# ==============================================================================

@pytest.mark.asyncio
async def test_09_get_application_scope_for_discovery(client: AsyncClient, app_test_setup):
    """Verify the dedicated GET /{app_id}/scope endpoint retrieves authorized boundaries for Discovery Agent."""
    headers = app_test_setup["auth_a"]

    create_res = await client.post("/api/v1/applications/", json={
        "name": f"Scope Discovery Target {uuid.uuid4().hex[:6]}",
        "target_url": "https://discovery-target.fintech.local",
        "permitted_paths": ["/api/v2/*", "/graphql"],
        "excluded_paths": ["/admin/*"],
        "rate_limit_rps": 15,
        "confirm_authorization": True
    }, headers=headers)
    app_id = create_res.json()["id"]

    scope_res = await client.get(f"/api/v1/applications/{app_id}/scope", headers=headers)
    assert scope_res.status_code == 200
    scope_data = scope_res.json()
    assert scope_data["application_id"] == app_id
    assert scope_data["target_domain"] == "discovery-target.fintech.local"
    assert scope_data["permitted_paths"] == ["/api/v2/*", "/graphql"]
    assert scope_data["excluded_paths"] == ["/admin/*"]
    assert scope_data["rate_limit_rps"] == 15
    assert scope_data["authorization_status"] == "AUTHORIZED"


# ==============================================================================
# 10. UPDATE APPLICATION INFORMATION & SCOPE
# ==============================================================================

@pytest.mark.asyncio
async def test_10_update_application_information_and_scope(client: AsyncClient, app_test_setup):
    """Verify PUT and PATCH updates modify application profiling, target URL, and scope limits."""
    headers = app_test_setup["auth_a"]

    # Register initial app
    create_res = await client.post("/api/v1/applications/", json={
        "name": f"Pre-Update App {uuid.uuid4().hex[:6]}",
        "target_url": "https://old.fintech.local",
        "confirm_authorization": True
    }, headers=headers)
    app_id = create_res.json()["id"]

    # Update via PUT
    updated_name = f"Updated App {uuid.uuid4().hex[:6]}"
    put_res = await client.put(f"/api/v1/applications/{app_id}", json={
        "name": updated_name,
        "description": "Updated description after architecture review",
        "target_url": "https://new.fintech.local:8080/v2",
        "environment_name": "sandbox",
        "rate_limit_rps": 30,
        "permitted_paths": ["/v2/*"],
        "excluded_paths": ["/v2/admin/*"]
    }, headers=headers)
    assert put_res.status_code == 200
    put_data = put_res.json()
    assert put_data["name"] == updated_name
    assert put_data["description"] == "Updated description after architecture review"
    assert put_data["target_url"] == "https://new.fintech.local:8080/v2"
    assert put_data["environment_name"] == "sandbox"
    assert put_data["scope"]["target_domain"] == "new.fintech.local"
    assert put_data["scope"]["rate_limit_rps"] == 30
    assert put_data["scope"]["permitted_paths"] == ["/v2/*"]

    # Partial update via PATCH
    patch_res = await client.patch(f"/api/v1/applications/{app_id}", json={
        "status": "ACTIVE",
        "risk_score": 15.5
    }, headers=headers)
    assert patch_res.status_code == 200
    assert patch_res.json()["risk_score"] == 15.5


# ==============================================================================
# 11. DELETE APPLICATION LIFECYCLE
# ==============================================================================

@pytest.mark.asyncio
async def test_11_delete_application_lifecycle(client: AsyncClient, app_test_setup):
    """Verify application deletion removes application, scope policies, and cascades properly."""
    headers = app_test_setup["auth_a"]

    create_res = await client.post("/api/v1/applications/", json={
        "name": f"To Delete App {uuid.uuid4().hex[:6]}",
        "target_url": "https://to-delete.fintech.local",
        "confirm_authorization": True
    }, headers=headers)
    app_id = create_res.json()["id"]

    # Delete application
    del_res = await client.delete(f"/api/v1/applications/{app_id}", headers=headers)
    assert del_res.status_code == 204

    # Verification: retrieving deleted application must return 404
    get_res = await client.get(f"/api/v1/applications/{app_id}", headers=headers)
    assert get_res.status_code == 404

    # Deleting already deleted application returns 404
    del_again = await client.delete(f"/api/v1/applications/{app_id}", headers=headers)
    assert del_again.status_code == 404


# ==============================================================================
# 12. SECURITY: UNAUTHORIZED ACCESS ENFORCEMENT
# ==============================================================================

@pytest.mark.asyncio
async def test_12_unauthorized_access_enforcement(client: AsyncClient, app_test_setup):
    """Verify all application endpoints reject unauthenticated or invalid token requests with 401."""
    fake_id = uuid.uuid4()
    invalid_headers = {"Authorization": "Bearer forged.invalid.token.signature"}

    # 1. No Authorization Header
    assert (await client.get("/api/v1/applications/")).status_code == 401
    assert (await client.post("/api/v1/applications/", json={"name": "X", "target_url": "https://x.com", "confirm_authorization": True})).status_code == 401
    assert (await client.get(f"/api/v1/applications/{fake_id}")).status_code == 401
    assert (await client.put(f"/api/v1/applications/{fake_id}", json={"name": "X"})).status_code == 401
    assert (await client.patch(f"/api/v1/applications/{fake_id}", json={"name": "X"})).status_code == 401
    assert (await client.delete(f"/api/v1/applications/{fake_id}")).status_code == 401
    assert (await client.get(f"/api/v1/applications/{fake_id}/scope")).status_code == 401

    # 2. Forged / Invalid Token
    assert (await client.get("/api/v1/applications/", headers=invalid_headers)).status_code == 401
    assert (await client.post("/api/v1/applications/", json={"name": "X", "target_url": "https://x.com", "confirm_authorization": True}, headers=invalid_headers)).status_code == 401
    assert (await client.get(f"/api/v1/applications/{fake_id}", headers=invalid_headers)).status_code == 401


# ==============================================================================
# 13. SECURITY: CROSS-ORGANIZATION ACCESS PREVENTION (TENANT ISOLATION)
# ==============================================================================

@pytest.mark.asyncio
async def test_13_cross_organization_access_prevention(client: AsyncClient, app_test_setup):
    """Verify users from Organization B cannot view, modify, or delete applications owned by Organization A."""
    headers_a = app_test_setup["auth_a"]
    headers_b = app_test_setup["auth_b"]

    # Create app in Org A
    create_res = await client.post("/api/v1/applications/", json={
        "name": f"Org A Secret App {uuid.uuid4().hex[:6]}",
        "target_url": "https://secret.fintech.local",
        "confirm_authorization": True
    }, headers=headers_a)
    app_a_id = create_res.json()["id"]

    # User B attempts to GET App A -> 404
    get_res = await client.get(f"/api/v1/applications/{app_a_id}", headers=headers_b)
    assert get_res.status_code == 404

    # User B attempts to GET App A's scope -> 404
    scope_res = await client.get(f"/api/v1/applications/{app_a_id}/scope", headers=headers_b)
    assert scope_res.status_code == 404

    # User B attempts to UPDATE App A -> 404
    put_res = await client.put(f"/api/v1/applications/{app_a_id}", json={
        "name": "Hijacked Name"
    }, headers=headers_b)
    assert put_res.status_code == 404

    # User B attempts to DELETE App A -> 404
    del_res = await client.delete(f"/api/v1/applications/{app_a_id}", headers=headers_b)
    assert del_res.status_code == 404

    # Verify App A still exists and is untouched in Org A
    check_res = await client.get(f"/api/v1/applications/{app_a_id}", headers=headers_a)
    assert check_res.status_code == 200
    assert check_res.json()["id"] == app_a_id


# ==============================================================================
# 14. SECURITY: AUTHORIZATION EXPIRY ENFORCEMENT
# ==============================================================================

@pytest.mark.asyncio
async def test_14_authorization_expiry_enforcement(client: AsyncClient, app_test_setup):
    """Verify scope authorization automatically resolves to EXPIRED when validity window has passed."""
    from datetime import datetime, timezone, timedelta
    from tests.conftest import TestingSessionLocal
    from sqlalchemy import update

    headers = app_test_setup["auth_a"]

    create_res = await client.post("/api/v1/applications/", json={
        "name": f"Expiring App {uuid.uuid4().hex[:6]}",
        "target_url": "https://expiring.fintech.local",
        "confirm_authorization": True
    }, headers=headers)
    app_id = create_res.json()["id"]

    # Manually simulate expired validity window in DB (yesterday)
    past_date = datetime.now(timezone.utc) - timedelta(days=2)
    async with TestingSessionLocal() as db:
        await db.execute(
            update(ApplicationScopePolicy)
            .where(ApplicationScopePolicy.application_id == uuid.UUID(app_id))
            .values(valid_until=past_date)
        )
        await db.commit()

    # Query application details
    get_res = await client.get(f"/api/v1/applications/{app_id}", headers=headers)
    assert get_res.status_code == 200
    scope_data = get_res.json()["scope"]
    assert scope_data["authorization_status"] == "EXPIRED"
    assert scope_data["scope_status"] == "EXPIRED"

    # Query dedicated scope endpoint
    scope_endpoint_res = await client.get(f"/api/v1/applications/{app_id}/scope", headers=headers)
    assert scope_endpoint_res.status_code == 200
    assert scope_endpoint_res.json()["authorization_status"] == "EXPIRED"


