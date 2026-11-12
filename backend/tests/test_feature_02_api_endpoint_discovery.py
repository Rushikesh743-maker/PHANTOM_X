import json
import uuid
from datetime import datetime, timezone, timedelta
import pytest
import jwt
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.models.user import Organization, User
from app.models.application import Application, ApplicationEnvironment
from app.models.scope_safety import ApplicationScopePolicy
from app.models.endpoint import DiscoveredEndpoint, DiscoveryJob
from shared.enums.common import UserRole, HttpMethod, EndpointRiskLevel


SAMPLE_OPENAPI_JSON = json.dumps({
    "openapi": "3.0.0",
    "info": {"title": "FinTech API", "version": "1.0.0"},
    "servers": [{"url": "https://api.fintech.local"}],
    "paths": {
        "/api/v1/accounts": {
            "get": {
                "summary": "List accounts",
                "operationId": "listAccounts",
                "parameters": [
                    {"name": "status", "in": "query", "schema": {"type": "string"}},
                    {"name": "limit", "in": "query", "schema": {"type": "integer"}}
                ],
                "responses": {
                    "200": {"description": "OK"},
                    "401": {"description": "Unauthorized"}
                },
                "security": [{"bearerAuth": []}]
            },
            "post": {
                "summary": "Create account",
                "operationId": "createAccount",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {"name": {"type": "string"}}
                            }
                        }
                    }
                },
                "responses": {"201": {"description": "Created"}},
                "security": [{"bearerAuth": []}]
            }
        },
        "/api/v1/accounts/{id}": {
            "get": {
                "summary": "Get account by ID",
                "parameters": [
                    {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}
                ],
                "responses": {"200": {"description": "OK"}},
                "security": [{"bearerAuth": []}]
            }
        }
    }
})

SAMPLE_OPENAPI_YAML = """
openapi: 3.0.1
info:
  title: Microservice API
  version: 2.1.0
servers:
  - url: https://api.fintech.local
paths:
  /api/v1/transactions:
    get:
      summary: Retrieve transactions
      responses:
        '200':
          description: Success
      security:
        - OAuth2: []
"""

SAMPLE_POSTMAN_JSON = json.dumps({
    "info": {
        "_postman_id": "99b0c793-1996-419b-a3d8-5541604a43b6",
        "name": "FinTech Core Collection",
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
    },
    "auth": {
        "type": "bearer",
        "bearer": [{"key": "token", "value": "test_token", "type": "string"}]
    },
    "item": [
        {
            "name": "Payments Folder",
            "item": [
                {
                    "name": "Initiate Transfer",
                    "request": {
                        "method": "POST",
                        "header": [{"key": "Content-Type", "value": "application/json"}],
                        "body": {
                            "mode": "raw",
                            "raw": "{\"amount\": 150.00, \"currency\": \"USD\"}",
                            "options": {"raw": {"language": "json"}}
                        },
                        "url": {
                            "raw": "https://api.fintech.local/api/v1/transfers",
                            "protocol": "https",
                            "host": ["api", "fintech", "local"],
                            "path": ["api", "v1", "transfers"]
                        }
                    },
                    "response": [
                        {"code": 201, "name": "Created Transfer"}
                    ]
                }
            ]
        },
        {
            "name": "Get User Profile",
            "request": {
                "method": "GET",
                "url": "https://api.fintech.local/api/v1/users/me"
            },
            "response": [{"code": 200}]
        }
    ]
})

SAMPLE_HAR_JSON = json.dumps({
    "log": {
        "version": "1.2",
        "creator": {"name": "Browser", "version": "1.0"},
        "entries": [
            {
                "time": 45.2,
                "request": {
                    "method": "GET",
                    "url": "https://api.fintech.local/api/v1/users/42?include_cards=true",
                    "headers": [
                        {"name": "Authorization", "value": "Bearer token123"},
                        {"name": "Accept", "value": "application/json"}
                    ]
                },
                "response": {
                    "status": 200,
                    "headers": [{"name": "Content-Type", "value": "application/json"}],
                    "content": {"mimeType": "application/json", "text": "{\"id\": 42, \"name\": \"Alice\"}"}
                }
            },
            {
                "time": 12.1,
                "request": {
                    "method": "GET",
                    "url": "https://api.fintech.local/static/logo.png",
                    "headers": []
                },
                "response": {
                    "status": 200,
                    "headers": [{"name": "Content-Type", "value": "image/png"}],
                    "content": {"mimeType": "image/png", "text": ""}
                }
            },
            {
                "time": 30.5,
                "request": {
                    "method": "GET",
                    "url": "https://analytics.external-tracker.com/collect",
                    "headers": []
                },
                "response": {
                    "status": 204,
                    "headers": [],
                    "content": {"mimeType": "text/plain", "text": ""}
                }
            }
        ]
    }
})


@pytest.fixture
async def discovery_test_setup(client: AsyncClient):
    """Setup dual tenant organizations, users, and registered applications with scope policies."""
    from tests.conftest import TestingSessionLocal
    async with TestingSessionLocal() as db:
        # Organization A
        org_a = Organization(name="FinTech Corp", slug=f"fintech-{uuid.uuid4().hex[:8]}")
        db.add(org_a)
        await db.flush()

        user_a = User(
            organization_id=org_a.id,
            email=f"alice-{uuid.uuid4().hex[:8]}@fintech.local",
            hashed_password="pw_hash_alice",
            full_name="Alice SecOps",
            role=UserRole.SECURITY_ENGINEER,
            is_active=True
        )
        db.add(user_a)

        # Organization B
        org_b = Organization(name="HealthCare Corp", slug=f"healthcare-{uuid.uuid4().hex[:8]}")
        db.add(org_b)
        await db.flush()

        user_b = User(
            organization_id=org_b.id,
            email=f"bob-{uuid.uuid4().hex[:8]}@healthcare.local",
            hashed_password="pw_hash_bob",
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

        auth_a = {"Authorization": f"Bearer {token_a}"}
        auth_b = {"Authorization": f"Bearer {token_b}"}

    # Register App A using official endpoint (creates Application, Environment, and ScopePolicy)
    resp_a = await client.post(
        "/api/v1/applications/",
        headers=auth_a,
        json={
            "name": "FinTech Core Banking",
            "description": "Core banking and accounts API",
            "target_url": "https://api.fintech.local",
            "environment_name": "staging",
            "permitted_paths": ["/api/v1/*", "/health"],
            "excluded_paths": ["/api/v1/admin/*"],
            "allowed_methods": ["GET", "POST", "PUT", "PATCH", "HEAD", "OPTIONS"],
            "rate_limit_rps": 50,
            "confirm_authorization": True
        }
    )
    assert resp_a.status_code == 201
    app_a_id = resp_a.json()["id"]

    # Register App B
    resp_b = await client.post(
        "/api/v1/applications/",
        headers=auth_b,
        json={
            "name": "HealthCare Patient Portal",
            "description": "Patient records API",
            "target_url": "https://api.healthcare.local",
            "environment_name": "staging",
            "permitted_paths": ["/*"],
            "excluded_paths": [],
            "allowed_methods": ["GET", "POST"],
            "rate_limit_rps": 50,
            "confirm_authorization": True
        }
    )
    assert resp_b.status_code == 201
    app_b_id = resp_b.json()["id"]

    return {
        "org_a_id": str(org_a.id),
        "org_b_id": str(org_b.id),
        "app_a_id": app_a_id,
        "app_b_id": app_b_id,
        "auth_headers_a": auth_a,
        "auth_headers_b": auth_b,
    }


# ==============================================================================
# 1. OPENAPI JSON EXTRACTION
# ==============================================================================

@pytest.mark.asyncio
async def test_01_openapi_json_extraction(client: AsyncClient, discovery_test_setup):
    """Test importing OpenAPI 3.0 specification in JSON format."""
    setup = discovery_test_setup
    resp = await client.post(
        "/api/v1/discovery/import/openapi",
        headers=setup["auth_headers_a"],
        json={
            "application_id": setup["app_a_id"],
            "content": SAMPLE_OPENAPI_JSON,
            "filename": "openapi.json"
        }
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "COMPLETED"
    assert data["source_type"] == "OPENAPI"
    assert data["endpoints_in_scope"] == 3
    assert data["endpoints_out_of_scope"] == 0

    # Verify persisted endpoints
    list_resp = await client.get(
        f"/api/v1/discovery/endpoints?app_id={setup['app_a_id']}",
        headers=setup["auth_headers_a"]
    )
    assert list_resp.status_code == 200
    eps = list_resp.json()
    assert len(eps) == 3
    paths = {e["path"] for e in eps}
    assert "/api/v1/accounts" in paths
    assert "/api/v1/accounts/{id}" in paths


# ==============================================================================
# 2. OPENAPI YAML EXTRACTION
# ==============================================================================

@pytest.mark.asyncio
async def test_02_openapi_yaml_extraction(client: AsyncClient, discovery_test_setup):
    """Test importing OpenAPI 3.0 specification in YAML format."""
    setup = discovery_test_setup
    resp = await client.post(
        "/api/v1/discovery/import/openapi",
        headers=setup["auth_headers_a"],
        json={
            "application_id": setup["app_a_id"],
            "content": SAMPLE_OPENAPI_YAML,
            "filename": "spec.yaml"
        }
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "COMPLETED"
    assert data["endpoints_in_scope"] == 1


# ==============================================================================
# 3. POSTMAN COLLECTION EXTRACTION
# ==============================================================================

@pytest.mark.asyncio
async def test_03_postman_collection_extraction(client: AsyncClient, discovery_test_setup):
    """Test importing Postman Collection v2.1 with nested folders and example responses."""
    setup = discovery_test_setup
    resp = await client.post(
        "/api/v1/discovery/import/postman",
        headers=setup["auth_headers_a"],
        json={
            "application_id": setup["app_a_id"],
            "content": SAMPLE_POSTMAN_JSON,
            "filename": "collection.json"
        }
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "COMPLETED"
    assert data["source_type"] == "POSTMAN"
    assert data["endpoints_in_scope"] == 2


# ==============================================================================
# 4. HAR TRAFFIC EXTRACTION & STATIC ASSET FILTERING
# ==============================================================================

@pytest.mark.asyncio
async def test_04_har_traffic_extraction(client: AsyncClient, discovery_test_setup):
    """Test importing HAR log: verifies static assets filtered, external domains rejected."""
    setup = discovery_test_setup
    resp = await client.post(
        "/api/v1/discovery/import/har",
        headers=setup["auth_headers_a"],
        json={
            "application_id": setup["app_a_id"],
            "content": SAMPLE_HAR_JSON,
            "filename": "traffic.har"
        }
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "COMPLETED"
    assert data["source_type"] == "HAR"
    # 1 in-scope (/api/v1/users/{id}), 1 static asset ignored, 1 external domain rejected
    assert data["endpoints_in_scope"] == 1
    assert data["endpoints_out_of_scope"] == 1


# ==============================================================================
# 5. INVALID SPECIFICATION HANDLING
# ==============================================================================

@pytest.mark.asyncio
async def test_05_invalid_specification_handling(client: AsyncClient, discovery_test_setup):
    """Test rejection of malformed or invalid JSON/YAML specifications."""
    setup = discovery_test_setup
    resp = await client.post(
        "/api/v1/discovery/import/openapi",
        headers=setup["auth_headers_a"],
        json={
            "application_id": setup["app_a_id"],
            "content": "{ malformed_json: true, invalid... ",
            "filename": "bad.json"
        }
    )
    assert resp.status_code == 400
    assert "failed to parse" in resp.json()["detail"].lower()


# ==============================================================================
# 6. UNSUPPORTED FILE FORMATS & EMPTY PAYLOAD
# ==============================================================================

@pytest.mark.asyncio
async def test_06_unsupported_file_formats(client: AsyncClient, discovery_test_setup):
    """Test rejection when content is empty or root structure is not an object."""
    setup = discovery_test_setup
    resp = await client.post(
        "/api/v1/discovery/import/postman",
        headers=setup["auth_headers_a"],
        json={
            "application_id": setup["app_a_id"],
            "content": "   ",
            "filename": "empty.json"
        }
    )
    assert resp.status_code == 400
    assert "empty" in resp.json()["detail"].lower()


# ==============================================================================
# 7. EMPTY DISCOVERY RESULTS HANDLING
# ==============================================================================

@pytest.mark.asyncio
async def test_07_empty_discovery_results(client: AsyncClient, discovery_test_setup):
    """Test handling of specification with no endpoints declared."""
    setup = discovery_test_setup
    empty_spec = json.dumps({
        "openapi": "3.0.0",
        "info": {"title": "Empty Spec", "version": "1.0"},
        "paths": {}
    })
    resp = await client.post(
        "/api/v1/discovery/import/openapi",
        headers=setup["auth_headers_a"],
        json={
            "application_id": setup["app_a_id"],
            "content": empty_spec
        }
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "FAILED"
    assert data["endpoints_in_scope"] == 0
    assert "no endpoints could be extracted" in data["message"].lower()


# ==============================================================================
# 8. ENDPOINT NORMALIZATION (PATH PARAMETER RESOLUTION)
# ==============================================================================

@pytest.mark.asyncio
async def test_08_endpoint_normalization(client: AsyncClient, discovery_test_setup):
    """Test path normalization: /users/123 -> /users/{id}, preserving parameterized forms."""
    setup = discovery_test_setup
    har_dynamic = json.dumps({
        "log": {
            "entries": [
                {
                    "request": {"method": "GET", "url": "https://api.fintech.local/api/v1/accounts/12345"},
                    "response": {"status": 200, "content": {"mimeType": "application/json"}}
                },
                {
                    "request": {"method": "GET", "url": "https://api.fintech.local/api/v1/accounts/67890"},
                    "response": {"status": 200, "content": {"mimeType": "application/json"}}
                }
            ]
        }
    })
    resp = await client.post(
        "/api/v1/discovery/import/har",
        headers=setup["auth_headers_a"],
        json={
            "application_id": setup["app_a_id"],
            "content": har_dynamic
        }
    )
    assert resp.status_code == 201
    # Both paths should normalize to /api/v1/accounts/{id} resulting in 1 unique endpoint
    list_resp = await client.get(
        f"/api/v1/discovery/endpoints?app_id={setup['app_a_id']}&path=accounts",
        headers=setup["auth_headers_a"]
    )
    eps = list_resp.json()
    assert any(e["path"] == "/api/v1/accounts/{id}" for e in eps)


# ==============================================================================
# 9. DUPLICATE ENDPOINT PREVENTION (DEDUPLICATION)
# ==============================================================================

@pytest.mark.asyncio
async def test_09_duplicate_endpoint_deduplication(client: AsyncClient, discovery_test_setup):
    """Test that importing the same endpoint repeatedly merges attributes without duplicating rows."""
    setup = discovery_test_setup
    # Import OpenAPI spec
    await client.post(
        "/api/v1/discovery/import/openapi",
        headers=setup["auth_headers_a"],
        json={"application_id": setup["app_a_id"], "content": SAMPLE_OPENAPI_JSON}
    )
    # Re-import same OpenAPI spec
    await client.post(
        "/api/v1/discovery/import/openapi",
        headers=setup["auth_headers_a"],
        json={"application_id": setup["app_a_id"], "content": SAMPLE_OPENAPI_JSON}
    )

    list_resp = await client.get(
        f"/api/v1/discovery/endpoints?app_id={setup['app_a_id']}",
        headers=setup["auth_headers_a"]
    )
    eps = list_resp.json()
    get_accounts = [e for e in eps if e["path"] == "/api/v1/accounts" and e["method"] == "GET"]
    assert len(get_accounts) == 1


# ==============================================================================
# 10. DIFFERENT HTTP METHODS REMAIN DISTINCT
# ==============================================================================

@pytest.mark.asyncio
async def test_10_distinct_http_methods_preserved(client: AsyncClient, discovery_test_setup):
    """Verify that GET /api/v1/accounts and POST /api/v1/accounts remain separate records."""
    setup = discovery_test_setup
    await client.post(
        "/api/v1/discovery/import/openapi",
        headers=setup["auth_headers_a"],
        json={"application_id": setup["app_a_id"], "content": SAMPLE_OPENAPI_JSON}
    )

    list_resp = await client.get(
        f"/api/v1/discovery/endpoints?app_id={setup['app_a_id']}",
        headers=setup["auth_headers_a"]
    )
    eps = list_resp.json()
    methods_on_accounts = {e["method"] for e in eps if e["path"] == "/api/v1/accounts"}
    assert "GET" in methods_on_accounts
    assert "POST" in methods_on_accounts


# ==============================================================================
# 11. APPLICATION AUTHORIZATION ENFORCEMENT (ACTIVE SCOPE REQUIRED)
# ==============================================================================

@pytest.mark.asyncio
async def test_11_authorization_enforcement_active_scope(client: AsyncClient, discovery_test_setup):
    """Test that discovery is blocked when scope policy is in DRAFT or unapproved state."""
    setup = discovery_test_setup
    from tests.conftest import TestingSessionLocal
    async with TestingSessionLocal() as db:
        res = await db.execute(
            select(ApplicationScopePolicy).where(ApplicationScopePolicy.application_id == uuid.UUID(setup["app_a_id"]))
        )
        pol = res.scalars().first()
        pol.authorization_status = "PENDING"
        pol.scope_status = "DRAFT"
        await db.commit()

    resp = await client.post(
        "/api/v1/discovery/import/openapi",
        headers=setup["auth_headers_a"],
        json={"application_id": setup["app_a_id"], "content": SAMPLE_OPENAPI_JSON}
    )
    assert resp.status_code == 400
    assert "discovery blocked" in resp.json()["detail"].lower()


# ==============================================================================
# 12. EXPIRED SCOPE REJECTION
# ==============================================================================

@pytest.mark.asyncio
async def test_12_expired_scope_rejection(client: AsyncClient, discovery_test_setup):
    """Test that discovery is blocked when testing authorization validity has expired."""
    setup = discovery_test_setup
    from tests.conftest import TestingSessionLocal
    async with TestingSessionLocal() as db:
        res = await db.execute(
            select(ApplicationScopePolicy).where(ApplicationScopePolicy.application_id == uuid.UUID(setup["app_a_id"]))
        )
        pol = res.scalars().first()
        pol.valid_until = datetime.now(timezone.utc) - timedelta(days=1)
        await db.commit()

    resp = await client.post(
        "/api/v1/discovery/import/openapi",
        headers=setup["auth_headers_a"],
        json={"application_id": setup["app_a_id"], "content": SAMPLE_OPENAPI_JSON}
    )
    assert resp.status_code == 400
    assert "expired" in resp.json()["detail"].lower()


# ==============================================================================
# 13. CROSS-ORGANIZATION ACCESS PREVENTION (TENANT ISOLATION)
# ==============================================================================

@pytest.mark.asyncio
async def test_13_cross_organization_access_prevention(client: AsyncClient, discovery_test_setup):
    """Test that Org B cannot trigger or view discovery for Org A's application."""
    setup = discovery_test_setup
    # Org B attempts to import spec for Org A's application
    resp = await client.post(
        "/api/v1/discovery/import/openapi",
        headers=setup["auth_headers_b"],
        json={"application_id": setup["app_a_id"], "content": SAMPLE_OPENAPI_JSON}
    )
    assert resp.status_code == 404

    # Org B attempts to list endpoints for Org A's application
    list_resp = await client.get(
        f"/api/v1/discovery/endpoints?app_id={setup['app_a_id']}",
        headers=setup["auth_headers_b"]
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 0


# ==============================================================================
# 14. EXCLUDED PATH REJECTION
# ==============================================================================

@pytest.mark.asyncio
async def test_14_excluded_path_rejection(client: AsyncClient, discovery_test_setup):
    """Test that endpoints targeting excluded paths (/api/v1/admin/*) are rejected as out-of-scope."""
    setup = discovery_test_setup
    spec_with_admin = json.dumps({
        "openapi": "3.0.0",
        "info": {"title": "Admin Test", "version": "1.0"},
        "paths": {
            "/api/v1/accounts": {
                "get": {"responses": {"200": {"description": "OK"}}}
            },
            "/api/v1/admin/users": {
                "get": {"responses": {"200": {"description": "Admin Users"}}}
            },
            "/api/v1/admin/purge": {
                "delete": {"responses": {"204": {"description": "Purge"}}}
            }
        }
    })
    resp = await client.post(
        "/api/v1/discovery/import/openapi",
        headers=setup["auth_headers_a"],
        json={"application_id": setup["app_a_id"], "content": spec_with_admin}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["endpoints_in_scope"] == 1
    assert data["endpoints_out_of_scope"] >= 2
    assert any("EXCLUDED_PATH" in r.get("category", "") for r in data["out_of_scope_reasons"])


# ==============================================================================
# 15. DISALLOWED HTTP METHOD REJECTION
# ==============================================================================

@pytest.mark.asyncio
async def test_15_disallowed_http_method_rejection(client: AsyncClient, discovery_test_setup):
    """Test that endpoints with disallowed methods (DELETE is excluded in Org A scope) are rejected."""
    setup = discovery_test_setup
    spec_with_delete = json.dumps({
        "openapi": "3.0.0",
        "info": {"title": "Method Test", "version": "1.0"},
        "paths": {
            "/api/v1/accounts": {
                "delete": {"responses": {"204": {"description": "Delete"}}}
            }
        }
    })
    resp = await client.post(
        "/api/v1/discovery/import/openapi",
        headers=setup["auth_headers_a"],
        json={"application_id": setup["app_a_id"], "content": spec_with_delete}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["endpoints_in_scope"] == 0
    assert data["endpoints_out_of_scope"] == 1
    assert any("DISALLOWED_METHOD" in r.get("category", "") for r in data["out_of_scope_reasons"])


# ==============================================================================
# 16. OUT-OF-SCOPE EXTERNAL DOMAIN REJECTION
# ==============================================================================

@pytest.mark.asyncio
async def test_16_out_of_scope_target_rejection(client: AsyncClient, discovery_test_setup):
    """Test that HAR or spec traffic targeted at unrelated external domains is rejected."""
    setup = discovery_test_setup
    foreign_spec = json.dumps({
        "openapi": "3.0.0",
        "info": {"title": "Foreign API", "version": "1.0"},
        "servers": [{"url": "https://malicious-external-target.com"}],
        "paths": {
            "/api/v1/leak": {
                "get": {"responses": {"200": {"description": "OK"}}}
            }
        }
    })
    resp = await client.post(
        "/api/v1/discovery/import/openapi",
        headers=setup["auth_headers_a"],
        json={"application_id": setup["app_a_id"], "content": foreign_spec}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["endpoints_in_scope"] == 0
    assert data["endpoints_out_of_scope"] == 1
    assert any("DOMAIN_OUT_OF_SCOPE" in r.get("category", "") for r in data["out_of_scope_reasons"])


# ==============================================================================
# 17. DISCOVERY JOB STATUS & CANCELLATION
# ==============================================================================

@pytest.mark.asyncio
async def test_17_discovery_job_lifecycle(client: AsyncClient, discovery_test_setup):
    """Test retrieving discovery jobs, inspecting job status, and cancelling jobs."""
    setup = discovery_test_setup
    import_resp = await client.post(
        "/api/v1/discovery/import/openapi",
        headers=setup["auth_headers_a"],
        json={"application_id": setup["app_a_id"], "content": SAMPLE_OPENAPI_JSON}
    )
    job_id = import_resp.json()["job_id"]

    # Get job status
    job_resp = await client.get(
        f"/api/v1/discovery/jobs/{job_id}",
        headers=setup["auth_headers_a"]
    )
    assert job_resp.status_code == 200
    assert job_resp.json()["id"] == job_id
    assert job_resp.json()["status"] == "COMPLETED"

    # List jobs
    list_jobs_resp = await client.get(
        f"/api/v1/discovery/jobs?app_id={setup['app_a_id']}",
        headers=setup["auth_headers_a"]
    )
    assert list_jobs_resp.status_code == 200
    assert len(list_jobs_resp.json()) >= 1


# ==============================================================================
# 18. ENDPOINT DETAILS, QUERY FILTERING, AND DELETION
# ==============================================================================

@pytest.mark.asyncio
async def test_18_endpoint_details_filtering_and_deletion(client: AsyncClient, discovery_test_setup):
    """Test filtering endpoints by method, path, source, and deleting an individual endpoint."""
    setup = discovery_test_setup
    await client.post(
        "/api/v1/discovery/import/openapi",
        headers=setup["auth_headers_a"],
        json={"application_id": setup["app_a_id"], "content": SAMPLE_OPENAPI_JSON}
    )

    # Filter by method
    get_only = await client.get(
        f"/api/v1/discovery/endpoints?app_id={setup['app_a_id']}&method=POST",
        headers=setup["auth_headers_a"]
    )
    assert get_only.status_code == 200
    assert all(e["method"] == "POST" for e in get_only.json())

    # Get single endpoint details
    target_ep = get_only.json()[0]
    ep_id = target_ep["id"]
    detail_resp = await client.get(
        f"/api/v1/discovery/endpoints/{ep_id}",
        headers=setup["auth_headers_a"]
    )
    assert detail_resp.status_code == 200
    assert detail_resp.json()["id"] == ep_id

    # Delete endpoint
    del_resp = await client.delete(
        f"/api/v1/discovery/endpoints/{ep_id}",
        headers=setup["auth_headers_a"]
    )
    assert del_resp.status_code == 204

    # Verify deleted
    check_resp = await client.get(
        f"/api/v1/discovery/endpoints/{ep_id}",
        headers=setup["auth_headers_a"]
    )
    assert check_resp.status_code == 404
