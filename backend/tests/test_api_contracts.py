import uuid
import pytest
import jwt
from httpx import AsyncClient
from app.core.config import settings
from app.models.user import Organization, User
from shared.enums.common import UserRole


@pytest.fixture
async def contract_test_user():
    """Create test organization, user, and JWT auth header."""
    from tests.conftest import TestingSessionLocal
    async with TestingSessionLocal() as db:
        org = Organization(name="Contract Org", slug=f"contract-org-{uuid.uuid4().hex[:8]}")
        db.add(org)
        await db.flush()

        user = User(
            organization_id=org.id,
            email=f"contract-user-{uuid.uuid4().hex[:8]}@phantom-x.local",
            hashed_password="hashed_pw_placeholder",
            full_name="Contract User",
            role=UserRole.SECURITY_ENGINEER,
            is_active=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        token = jwt.encode(
            {"sub": str(user.id), "org_id": str(org.id), "role": user.role.value},
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        return {
            "org_id": str(org.id),
            "user_id": str(user.id),
            "auth_headers": {"Authorization": f"Bearer {token}"}
        }


@pytest.mark.asyncio
async def test_application_lifecycle(client: AsyncClient, contract_test_user):
    headers = contract_test_user["auth_headers"]

    # 1. Register application target
    create_payload = {
        "name": "Integration Test Target",
        "target_url": "http://localhost:3000",
        "description": "Validation target application",
        "environment_name": "staging",
        "confirm_authorization": True
    }
    create_res = await client.post("/api/v1/applications/", json=create_payload, headers=headers)
    assert create_res.status_code == 201
    app_data = create_res.json()
    assert app_data["name"] == "Integration Test Target"
    assert app_data["target_url"] == "http://localhost:3000"
    assert app_data["scope"] is not None
    assert app_data["scope"]["authorization_status"] == "AUTHORIZED"
    app_id = app_data["id"]

    # 2. Get application details
    get_res = await client.get(f"/api/v1/applications/{app_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == app_id
    assert get_res.json()["scope"]["target_domain"] == "localhost"

    # 3. List applications
    list_res = await client.get("/api/v1/applications/", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1


@pytest.mark.asyncio
async def test_safety_policy_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/settings/safety-policy")
    assert response.status_code == 200
    data = response.json()
    assert data["execution_mode"] in ["OBSERVE", "ACTIVE_VERIFY", "ATTACK_SIMULATION"]
    assert "allowed_target_hosts" in data
    assert data["synthetic_data_enforced"] is True
