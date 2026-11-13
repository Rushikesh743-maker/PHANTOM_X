
from intelligence.behavioral_twin.twin import (
    BehavioralDigitalTwin,
    EndpointBehavior
)


def test_register_endpoint():
    twin = BehavioralDigitalTwin(application_id="APP-001")

    endpoint = EndpointBehavior(
        path="/api/users",
        method="GET",
        expected_status_codes=[200],
        required_roles=["USER"]
    )

    twin.register_endpoint(endpoint)

    assert "GET:/api/users" in twin.endpoints


def test_get_mutating_endpoints():
    twin = BehavioralDigitalTwin(application_id="APP-001")

    endpoints = [
        EndpointBehavior(
            path="/api/users",
            method="GET",
            expected_status_codes=[200],
            required_roles=["USER"]
        ),
        EndpointBehavior(
            path="/api/users",
            method="POST",
            expected_status_codes=[201],
            required_roles=["ADMIN"]
        ),
        EndpointBehavior(
            path="/api/users/{id}",
            method="DELETE",
            expected_status_codes=[204],
            required_roles=["ADMIN"]
        )
    ]

    for endpoint in endpoints:
        twin.register_endpoint(endpoint)

    mutating = twin.get_mutating_endpoints()

    assert len(mutating) == 2
    assert all(
        endpoint.method in ["POST", "PUT", "DELETE", "PATCH"]
        for endpoint in mutating
    )


def test_validate_workflows():
    twin = BehavioralDigitalTwin(application_id="APP-001")

    endpoint = EndpointBehavior(
        path="/api/orders",
        method="POST",
        expected_status_codes=[201],
        required_roles=["USER"]
    )

    twin.register_endpoint(endpoint)

    twin.workflow_sequences = [
        ["POST:/api/orders", "GET:/api/orders"],
    ]

    result = twin.validate_workflows()

    assert result["workflows_checked"] == 1
    assert result["invalid_workflows"] == 1
    assert result["results"][0]["missing_endpoints"] == [
        "GET:/api/orders"
    ]


def test_analyze_role_boundaries():
    twin = BehavioralDigitalTwin(application_id="APP-001")

    endpoint = EndpointBehavior(
        path="/api/public",
        method="GET",
        expected_status_codes=[200],
        required_roles=[]
    )

    twin.register_endpoint(endpoint)

    findings = twin.analyze_role_boundaries()

    assert len(findings) == 1
    assert findings[0]["finding"] == "NO_REQUIRED_ROLE_DEFINED"


def test_analyze_state_mutations():
    twin = BehavioralDigitalTwin(application_id="APP-001")

    endpoint = EndpointBehavior(
        path="/api/orders",
        method="POST",
        expected_status_codes=[201],
        required_roles=["USER"],
        state_mutations=["CREATE_ORDER"]
    )

    twin.register_endpoint(endpoint)

    results = twin.analyze_state_mutations()

    assert len(results) == 1
    assert results[0]["requires_execution_review"] is True
