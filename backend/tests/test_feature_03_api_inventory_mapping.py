import json
import uuid
import pytest
import jwt
from httpx import AsyncClient
from datetime import datetime, timezone, timedelta

from app.core.config import settings
from app.models.user import Organization, User
from app.models.application import Application
from app.models.endpoint import DiscoveredEndpoint, EndpointRelationship
from app.inventory import ApiCategory, RelationshipType, RelationshipProvenance
from shared.enums.common import UserRole, HttpMethod, EndpointRiskLevel


SAMPLE_OPENAPI_SPEC = json.dumps({
    "openapi": "3.0.0",
    "info": {"title": "Banking Core API", "version": "1.0.0"},
    "servers": [{"url": "https://api.banking.example.com"}],
    "paths": {
        "/api/v1/auth/login": {
            "post": {
                "tags": ["Auth"],
                "summary": "User authentication",
                "operationId": "loginUser",
                "requestBody": {"content": {"application/json": {"schema": {"type": "object"}}}},
                "responses": {"200": {"description": "JWT token response"}}
            }
        },
        "/api/v1/users": {
            "get": {
                "tags": ["Users"],
                "summary": "List users",
                "operationId": "listUsers",
                "parameters": [{"name": "page", "in": "query", "schema": {"type": "integer"}}],
                "responses": {"200": {"description": "User list"}}
            },
            "post": {
                "tags": ["Users"],
                "summary": "Create user",
                "operationId": "createUser",
                "requestBody": {"content": {"application/json": {"schema": {"type": "object"}}}},
                "responses": {"201": {"description": "User created"}}
            }
        },
        "/api/v1/users/{id}": {
            "get": {
                "tags": ["Users"],
                "summary": "Get user profile",
                "operationId": "getUserById",
                "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                "responses": {"200": {"description": "User profile"}, "404": {"description": "Not found"}}
            },
            "put": {
                "tags": ["Users"],
                "summary": "Update user",
                "operationId": "updateUser",
                "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                "responses": {"200": {"description": "User updated"}}
            },
            "delete": {
                "tags": ["Users"],
                "summary": "Delete user",
                "operationId": "deleteUser",
                "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                "responses": {"204": {"description": "Deleted"}}
            }
        },
        "/api/v1/users/{id}/accounts": {
            "get": {
                "summary": "Get user accounts",
                "operationId": "getUserAccounts",
                "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                "responses": {"200": {"description": "Accounts list"}}
            }
        },
        "/api/v1/payments/checkout": {
            "post": {
                "summary": "Process checkout payment",
                "operationId": "processPayment",
                "parameters": [{"name": "account_id", "in": "query", "schema": {"type": "string"}}],
                "responses": {"200": {"description": "Payment successful"}}
            }
        },
        "/api/v1/reports/monthly": {
            "get": {
                "summary": "Monthly financial report",
                "operationId": "getMonthlyReport",
                "responses": {"200": {"description": "Report data"}}
            }
        },
        "/api/v1/xyz/custom-widget": {
            "get": {
                "summary": "Miscellaneous internal widget",
                "responses": {"200": {"description": "Widget"}}
            }
        }
    }
})


@pytest.fixture
async def inventory_test_setup(client: AsyncClient):
    """Setup dual tenant organizations, users, tokens, and registered applications with scope policies."""
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

    # Register Application A with authorized scope
    resp_a = await client.post(
        "/api/v1/applications/",
        headers=auth_a,
        json={
            "name": "Inventory Test Banking App",
            "description": "Enterprise banking system for inventory and mapping tests",
            "target_url": "https://api.banking.example.com",
            "environment_name": "staging",
            "permitted_paths": ["/api/v1/*"],
            "excluded_paths": ["/api/v1/admin/destroy"],
            "allowed_methods": ["GET", "POST", "PUT", "DELETE", "PATCH"],
            "rate_limit_rps": 50,
            "confirm_authorization": True
        }
    )
    assert resp_a.status_code == 201, resp_a.text
    app_a_id = resp_a.json()["id"]

    # Ingest OpenAPI specification for App A
    import_resp = await client.post(
        "/api/v1/discovery/import/openapi",
        headers=auth_a,
        json={
            "application_id": app_a_id,
            "content": SAMPLE_OPENAPI_SPEC,
            "source_type": "OPENAPI"
        }
    )
    assert import_resp.status_code in (200, 201), import_resp.text

    # Rebuild inventory mappings for App A
    rebuild_resp = await client.post(
        f"/api/v1/inventory/rebuild?app_id={app_a_id}",
        headers=auth_a
    )
    assert rebuild_resp.status_code == 200, rebuild_resp.text

    return {
        "app_id": app_a_id,
        "auth_a": auth_a,
        "auth_b": auth_b,
        "org_a_id": str(org_a.id),
        "org_b_id": str(org_b.id),
    }


@pytest.mark.asyncio
async def test_01_inventory_retrieval_and_categorization(client: AsyncClient, inventory_test_setup):
    """
    Verifies that discovered endpoints are categorized using source tags and rules,
    with confidence scores and clear explanations.
    """
    app_id = inventory_test_setup["app_id"]
    auth_a = inventory_test_setup["auth_a"]

    resp = await client.get(f"/api/v1/inventory/endpoints?app_id={app_id}", headers=auth_a)
    assert resp.status_code == 200
    endpoints = resp.json()
    assert len(endpoints) >= 7

    # Check /auth/login -> AUTH_IDENTITY
    login_ep = next((e for e in endpoints if "login" in e["path"]), None)
    assert login_ep is not None
    assert login_ep["raw_metadata"]["category"] == ApiCategory.AUTH_IDENTITY
    assert login_ep["raw_metadata"]["category_confidence"] >= 0.85
    assert "tag" in login_ep["raw_metadata"]["category_explanation"].lower() or "auth" in login_ep["raw_metadata"]["category_explanation"].lower()

    # Check /users -> USER_MANAGEMENT
    users_ep = next((e for e in endpoints if e["path"] == "/api/v1/users" and e["method"] == "GET"), None)
    assert users_ep is not None
    assert users_ep["raw_metadata"]["category"] == ApiCategory.USER_MANAGEMENT
    assert users_ep["raw_metadata"]["category_confidence"] >= 0.80

    # Check /payments/checkout -> PAYMENT_TRANSACTION
    pay_ep = next((e for e in endpoints if "checkout" in e["path"]), None)
    assert pay_ep is not None
    assert pay_ep["raw_metadata"]["category"] == ApiCategory.PAYMENT_TRANSACTION

    # Check /reports/monthly -> REPORTING_ANALYTICS
    rep_ep = next((e for e in endpoints if "reports" in e["path"]), None)
    assert rep_ep is not None
    assert rep_ep["raw_metadata"]["category"] == ApiCategory.REPORTING_ANALYTICS

    # Check unclassified endpoint
    xyz_ep = next((e for e in endpoints if "custom-widget" in e["path"]), None)
    assert xyz_ep is not None
    assert xyz_ep["raw_metadata"]["category"] == ApiCategory.UNCLASSIFIED
    assert xyz_ep["raw_metadata"]["category_confidence"] == 0.0


@pytest.mark.asyncio
async def test_02_resource_grouping_and_hierarchy(client: AsyncClient, inventory_test_setup):
    """
    Verifies resource extraction, grouping, and parent-child hierarchy detection.
    """
    app_id = inventory_test_setup["app_id"]
    auth_a = inventory_test_setup["auth_a"]

    resp = await client.get(f"/api/v1/inventory/resources?app_id={app_id}", headers=auth_a)
    assert resp.status_code == 200
    resources = resp.json()
    assert len(resources) >= 4

    res_names = {r["name"] for r in resources}
    assert "users" in res_names
    assert "login" in res_names or "auth" in res_names
    assert "checkout" in res_names or "payments" in res_names

    # Check users resource details
    users_res = next((r for r in resources if r["name"] == "users"), None)
    assert users_res is not None
    assert users_res["endpoint_count"] >= 3
    assert set(users_res["methods"]).issuperset({"GET", "POST", "PUT", "DELETE"})
    assert "accounts" in users_res["related_resources"]

    # Check nested resource accounts has parent 'users'
    accounts_res = next((r for r in resources if r["name"] == "accounts"), None)
    assert accounts_res is not None
    assert accounts_res["parent_resource"] == "users"

    # Single resource endpoint test
    detail_resp = await client.get(f"/api/v1/inventory/resources/users?app_id={app_id}", headers=auth_a)
    assert detail_resp.status_code == 200
    assert detail_resp.json()["name"] == "users"


@pytest.mark.asyncio
async def test_03_endpoint_relationships_creation_and_provenance(client: AsyncClient, inventory_test_setup):
    """
    Verifies automated generation of relationships: SAME_RESOURCE, PARENT_CHILD,
    READ_WRITE, AUTH_DEPENDENCY, and WORKFLOW_CANDIDATE with correct provenance and confidence.
    """
    app_id = inventory_test_setup["app_id"]
    auth_a = inventory_test_setup["auth_a"]

    resp = await client.get(f"/api/v1/inventory/relationships?app_id={app_id}", headers=auth_a)
    assert resp.status_code == 200
    relationships = resp.json()
    assert len(relationships) > 0

    rel_types = {r["relationship_type"] for r in relationships}
    assert RelationshipType.SAME_RESOURCE in rel_types
    assert RelationshipType.PARENT_CHILD in rel_types
    assert RelationshipType.READ_WRITE in rel_types
    assert RelationshipType.AUTH_DEPENDENCY in rel_types
    assert RelationshipType.WORKFLOW_CANDIDATE in rel_types

    # Read-Write relationships must have provenance INFERRED
    rw_rels = [r for r in relationships if r["relationship_type"] == RelationshipType.READ_WRITE]
    assert len(rw_rels) > 0
    for r in rw_rels:
        assert r["provenance"].lower() == "inferred"
        assert r["confidence"] >= 0.80

    # Same Resource relationships
    same_res_rels = [r for r in relationships if r["relationship_type"] == RelationshipType.SAME_RESOURCE]
    assert len(same_res_rels) > 0

    # Auth Dependency: target requires auth, source is auth login
    auth_rels = [r for r in relationships if r["relationship_type"] == RelationshipType.AUTH_DEPENDENCY]
    assert len(auth_rels) > 0
    for r in auth_rels:
        assert "login" in r["source_endpoint_path"]
        assert r["confidence"] >= 0.85


@pytest.mark.asyncio
async def test_04_relationship_deduplication(client: AsyncClient, inventory_test_setup):
    """
    Verifies that re-running rebuild does not create duplicate relationships.
    """
    app_id = inventory_test_setup["app_id"]
    auth_a = inventory_test_setup["auth_a"]

    # Initial count
    resp1 = await client.get(f"/api/v1/inventory/relationships?app_id={app_id}", headers=auth_a)
    count1 = len(resp1.json())

    # Rebuild inventory mappings
    rebuild_resp = await client.post(f"/api/v1/inventory/rebuild?app_id={app_id}", headers=auth_a)
    assert rebuild_resp.status_code == 200
    rebuild_data = rebuild_resp.json()
    assert rebuild_data["relationships_created"] > 0

    # Check count after rebuild
    resp2 = await client.get(f"/api/v1/inventory/relationships?app_id={app_id}", headers=auth_a)
    count2 = len(resp2.json())
    assert count1 == count2, "Rebuild should replace or deduplicate, not duplicate"


@pytest.mark.asyncio
async def test_05_inventory_filtering_and_search(client: AsyncClient, inventory_test_setup):
    """
    Tests filtering by resource, category, HTTP method, source, text search,
    and unclassified endpoints.
    """
    app_id = inventory_test_setup["app_id"]
    auth_a = inventory_test_setup["auth_a"]

    # 1. Filter by resource = users
    r1 = await client.get(f"/api/v1/inventory/endpoints?app_id={app_id}&resource=users", headers=auth_a)
    assert r1.status_code == 200
    eps1 = r1.json()
    assert len(eps1) >= 3
    assert all("users" in e["path"] for e in eps1)

    # 2. Filter by category = AUTH_IDENTITY
    r2 = await client.get(f"/api/v1/inventory/endpoints?app_id={app_id}&category=AUTH_IDENTITY", headers=auth_a)
    assert r2.status_code == 200
    eps2 = r2.json()
    assert len(eps2) >= 1
    assert any("login" in e["path"] for e in eps2)

    # 3. Filter by method = POST
    r3 = await client.get(f"/api/v1/inventory/endpoints?app_id={app_id}&method=POST", headers=auth_a)
    assert r3.status_code == 200
    eps3 = r3.json()
    assert all(e["method"] == "POST" for e in eps3)

    # 4. Search query = "checkout"
    r4 = await client.get(f"/api/v1/inventory/endpoints?app_id={app_id}&search=checkout", headers=auth_a)
    assert r4.status_code == 200
    eps4 = r4.json()
    assert len(eps4) == 1
    assert "checkout" in eps4[0]["path"]

    # 5. Filter unclassified_only = true
    r5 = await client.get(f"/api/v1/inventory/endpoints?app_id={app_id}&unclassified_only=true", headers=auth_a)
    assert r5.status_code == 200
    eps5 = r5.json()
    assert len(eps5) >= 1
    assert all(e["raw_metadata"].get("category") == ApiCategory.UNCLASSIFIED for e in eps5)


@pytest.mark.asyncio
async def test_06_inventory_statistics_calculation(client: AsyncClient, inventory_test_setup):
    """
    Verifies that inventory statistics return real database-derived counts and distributions.
    """
    app_id = inventory_test_setup["app_id"]
    auth_a = inventory_test_setup["auth_a"]

    resp = await client.get(f"/api/v1/inventory/stats?app_id={app_id}", headers=auth_a)
    assert resp.status_code == 200
    stats = resp.json()

    assert stats["total_endpoints"] >= 7
    assert stats["unique_resources"] >= 4
    assert stats["documented_count"] >= 7
    assert stats["total_relationships_count"] > 0
    assert stats["inferred_relationships_count"] > 0
    assert "GET" in stats["method_distribution"]
    assert "POST" in stats["method_distribution"]
    assert stats["unclassified_count"] >= 1


@pytest.mark.asyncio
async def test_07_inventory_export_json_and_csv(client: AsyncClient, inventory_test_setup):
    """
    Verifies structured JSON and formula-sanitized CSV exports.
    """
    app_id = inventory_test_setup["app_id"]
    auth_a = inventory_test_setup["auth_a"]

    # 1. JSON Export
    resp_json = await client.get(f"/api/v1/inventory/export?app_id={app_id}&format=json", headers=auth_a)
    assert resp_json.status_code == 200
    assert resp_json.headers["content-type"] == "application/json"
    exported_data = resp_json.json()
    assert isinstance(exported_data, list)
    assert len(exported_data) >= 7
    assert "resource" in exported_data[0]
    assert "category" in exported_data[0]

    # 2. CSV Export
    resp_csv = await client.get(f"/api/v1/inventory/export?app_id={app_id}&format=csv", headers=auth_a)
    assert resp_csv.status_code == 200
    assert "text/csv" in resp_csv.headers["content-type"]
    csv_text = resp_csv.text
    assert "ID,Method,Path,Resource,Category" in csv_text
    assert "/api/v1/users" in csv_text


@pytest.mark.asyncio
async def test_08_tenant_isolation_and_ownership(client: AsyncClient, inventory_test_setup):
    """
    Verifies that attempting to access inventory for a non-existent application
    or an application belonging to another tenant returns 404 Not Found.
    """
    app_id = inventory_test_setup["app_id"]
    auth_b = inventory_test_setup["auth_b"]  # Different tenant
    random_app_id = str(uuid.uuid4())

    # Tenant B tries to access Tenant A's app -> 404
    r1 = await client.get(f"/api/v1/inventory/endpoints?app_id={app_id}", headers=auth_b)
    assert r1.status_code == 404

    r2 = await client.get(f"/api/v1/inventory/resources?app_id={app_id}", headers=auth_b)
    assert r2.status_code == 404

    r3 = await client.get(f"/api/v1/inventory/relationships?app_id={app_id}", headers=auth_b)
    assert r3.status_code == 404

    r4 = await client.get(f"/api/v1/inventory/stats?app_id={app_id}", headers=auth_b)
    assert r4.status_code == 404

    r5 = await client.get(f"/api/v1/inventory/export?app_id={app_id}", headers=auth_b)
    assert r5.status_code == 404

    # Non-existent app ID -> 404
    r6 = await client.get(f"/api/v1/inventory/endpoints?app_id={random_app_id}", headers=auth_b)
    assert r6.status_code == 404


@pytest.mark.asyncio
async def test_09_cascade_deletion_preserves_integrity(client: AsyncClient, inventory_test_setup):
    """
    Verifies that deleting an endpoint removes associated relationships
    without leaving orphaned foreign key records.
    """
    app_id = inventory_test_setup["app_id"]
    auth_a = inventory_test_setup["auth_a"]

    # 1. Get all endpoints
    ep_resp = await client.get(f"/api/v1/inventory/endpoints?app_id={app_id}", headers=auth_a)
    endpoints = ep_resp.json()
    user_detail_ep = next((e for e in endpoints if e["path"] == "/api/v1/users/{id}" and e["method"] == "GET"), None)
    assert user_detail_ep is not None
    ep_id = user_detail_ep["id"]

    # 2. Check that relationships exist for this endpoint
    rel_resp_before = await client.get(f"/api/v1/inventory/relationships?app_id={app_id}&endpoint_id={ep_id}", headers=auth_a)
    rels_before = rel_resp_before.json()
    assert len(rels_before) > 0

    # 3. Delete the endpoint
    del_resp = await client.delete(f"/api/v1/discovery/endpoints/{ep_id}", headers=auth_a)
    assert del_resp.status_code in (200, 204)

    # 4. Check that relationships connected to this endpoint are gone
    rel_resp_after = await client.get(f"/api/v1/inventory/relationships?app_id={app_id}&endpoint_id={ep_id}", headers=auth_a)
    rels_after = rel_resp_after.json()
    assert len(rels_after) == 0


@pytest.mark.asyncio
async def test_10_empty_inventory_handling(client: AsyncClient, inventory_test_setup):
    """
    Verifies that an application with zero discovered endpoints returns
    empty structures and zero counts gracefully without 500 errors.
    """
    auth_a = inventory_test_setup["auth_a"]

    # Register clean app with no endpoints
    create_resp = await client.post(
        "/api/v1/applications/",
        headers=auth_a,
        json={
            "name": "Empty Inventory App",
            "description": "App without endpoints",
            "target_url": "https://empty.example.com",
            "environment_name": "dev",
            "permitted_paths": ["/"],
            "allowed_methods": ["GET"],
            "rate_limit_rps": 10,
            "confirm_authorization": True
        }
    )
    assert create_resp.status_code == 201
    empty_app_id = create_resp.json()["id"]

    # Query endpoints
    r1 = await client.get(f"/api/v1/inventory/endpoints?app_id={empty_app_id}", headers=auth_a)
    assert r1.status_code == 200
    assert r1.json() == []

    # Query resources
    r2 = await client.get(f"/api/v1/inventory/resources?app_id={empty_app_id}", headers=auth_a)
    assert r2.status_code == 200
    assert r2.json() == []

    # Query relationships
    r3 = await client.get(f"/api/v1/inventory/relationships?app_id={empty_app_id}", headers=auth_a)
    assert r3.status_code == 200
    assert r3.json() == []

    # Query stats
    r4 = await client.get(f"/api/v1/inventory/stats?app_id={empty_app_id}", headers=auth_a)
    assert r4.status_code == 200
    stats = r4.json()
    assert stats["total_endpoints"] == 0
    assert stats["unique_resources"] == 0
    assert stats["total_relationships_count"] == 0
