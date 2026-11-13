
from typing import Any, Dict, List
from uuid import uuid4

from pydantic import BaseModel, Field

from shared.enums.common import SafetyClassification


class CounterfactualHypothesis(BaseModel):
    """Represents a controlled counterfactual security scenario."""

    hypothesis_id: str
    scenario_type: str
    target_endpoint: str

    original_parameter: Dict[str, Any]
    mutated_parameter: Dict[str, Any]

    expected_safe_behavior: str
    vulnerability_indicator: str

    safety_classification: SafetyClassification = (
        SafetyClassification.SAFE_READ_ONLY
    )

    preconditions: List[str] = Field(default_factory=list)


class CounterfactualLab:
    """
    Generates controlled counterfactual security hypotheses.

    Compares original and mutated conditions to identify
    possible authorization and business logic weaknesses.

    This module generates hypotheses only.
    It does not execute HTTP requests.
    """

    def _generate_id(self, prefix: str) -> str:
        return f"{prefix}-{uuid4().hex[:8].upper()}"

    def _validate_endpoint(self, endpoint: str) -> str:
        endpoint = str(endpoint).strip()

        if not endpoint.startswith("/"):
            raise ValueError(
                "Endpoint must be an application-relative path."
            )

        return endpoint

    # ------------------------------------------------
    # 1. IDOR / BOLA counterfactual testing
    # ------------------------------------------------

    def generate_idor_hypotheses(
        self,
        endpoint: str,
        identifier_param: str = "id"
    ) -> List[CounterfactualHypothesis]:

        endpoint = self._validate_endpoint(endpoint)
        identifier_param = identifier_param.strip()

        if not identifier_param:
            raise ValueError("Identifier parameter cannot be empty.")

        return [
            CounterfactualHypothesis(
                hypothesis_id=self._generate_id("CF-IDOR"),
                scenario_type="OBJECT_LEVEL_AUTHORIZATION",
                target_endpoint=endpoint,

                original_parameter={
                    identifier_param: "synthetic_user_A_resource"
                },

                mutated_parameter={
                    identifier_param: "synthetic_user_B_resource"
                },

                expected_safe_behavior=(
                    "HTTP 403 Forbidden or HTTP 404 Not Found "
                    "when accessing another user's resource."
                ),

                vulnerability_indicator=(
                    "Unauthorized access to another user's resource."
                ),

                safety_classification=SafetyClassification.SAFE_READ_ONLY,

                preconditions=[
                    "Use an authorized test environment",
                    "Use approved synthetic user accounts",
                    "Use synthetic resource identifiers",
                    "Do not access real user data"
                ]
            )
        ]

    # ------------------------------------------------
    # 2. Identity boundary testing
    # ------------------------------------------------

    def generate_identity_hypotheses(
        self,
        endpoint: str
    ) -> List[CounterfactualHypothesis]:

        endpoint = self._validate_endpoint(endpoint)

        return [
            CounterfactualHypothesis(
                hypothesis_id=self._generate_id("CF-IDENTITY"),
                scenario_type="IDENTITY_BOUNDARY",
                target_endpoint=endpoint,

                original_parameter={
                    "authenticated_user": "synthetic_user_A"
                },

                mutated_parameter={
                    "authenticated_user": "synthetic_user_B"
                },

                expected_safe_behavior=(
                    "Each authenticated user should only access "
                    "resources permitted to that identity."
                ),

                vulnerability_indicator=(
                    "A user receives unauthorized access to "
                    "another user's private resources."
                ),

                safety_classification=SafetyClassification.SAFE_READ_ONLY,

                preconditions=[
                    "Use two approved synthetic accounts",
                    "Use isolated synthetic resources",
                    "Keep testing within approved scope"
                ]
            )
        ]

    # ------------------------------------------------
    # 3. Role boundary testing
    # ------------------------------------------------

    def generate_role_hypotheses(
        self,
        endpoint: str,
        original_role: str,
        mutated_role: str
    ) -> List[CounterfactualHypothesis]:

        endpoint = self._validate_endpoint(endpoint)
        original_role = original_role.strip().upper()
        mutated_role = mutated_role.strip().upper()

        if not original_role or not mutated_role:
            raise ValueError("Both role names must be provided.")

        if original_role == mutated_role:
            raise ValueError("Original and mutated roles must differ.")

        return [
            CounterfactualHypothesis(
                hypothesis_id=self._generate_id("CF-ROLE"),
                scenario_type="ROLE_BOUNDARY",
                target_endpoint=endpoint,

                original_parameter={
                    "user_role": original_role
                },

                mutated_parameter={
                    "user_role": mutated_role
                },

                expected_safe_behavior=(
                    "Access should be granted or denied according "
                    "to the permissions assigned to each role."
                ),

                vulnerability_indicator=(
                    "A lower-privileged role receives access "
                    "to a resource restricted to a higher role."
                ),

                safety_classification=SafetyClassification.SAFE_READ_ONLY,

                preconditions=[
                    "Use approved synthetic test roles",
                    "Use synthetic accounts",
                    "Confirm expected role permissions",
                    "Do not modify real user permissions"
                ]
            )
        ]

    # ------------------------------------------------
    # 4. Tenant isolation testing
    # ------------------------------------------------

    def generate_tenant_hypotheses(
        self,
        endpoint: str
    ) -> List[CounterfactualHypothesis]:

        endpoint = self._validate_endpoint(endpoint)

        return [
            CounterfactualHypothesis(
                hypothesis_id=self._generate_id("CF-TENANT"),
                scenario_type="TENANT_ISOLATION",
                target_endpoint=endpoint,

                original_parameter={
                    "tenant_id": "synthetic_tenant_A"
                },

                mutated_parameter={
                    "tenant_id": "synthetic_tenant_B"
                },

                expected_safe_behavior=(
                    "A tenant must only access resources belonging "
                    "to its own authorized boundary."
                ),

                vulnerability_indicator=(
                    "Cross-tenant data or resources become accessible."
                ),

                safety_classification=SafetyClassification.SAFE_READ_ONLY,

                preconditions=[
                    "Use isolated synthetic tenants",
                    "Use synthetic records only",
                    "Verify tenant ownership rules",
                    "Do not access real tenant data"
                ]
            )
        ]

    # ------------------------------------------------
    # 5. Generate all counterfactual hypotheses
    # ------------------------------------------------

    def generate_all_hypotheses(
        self,
        endpoint: str,
        identifier_param: str = "id",
        original_role: str = "ADMIN",
        mutated_role: str = "USER"
    ) -> List[CounterfactualHypothesis]:

        endpoint = self._validate_endpoint(endpoint)

        hypotheses = []

        hypotheses.extend(
            self.generate_idor_hypotheses(
                endpoint,
                identifier_param
            )
        )

        hypotheses.extend(
            self.generate_identity_hypotheses(endpoint)
        )

        hypotheses.extend(
            self.generate_role_hypotheses(
                endpoint,
                original_role,
                mutated_role
            )
        )

        hypotheses.extend(
            self.generate_tenant_hypotheses(endpoint)
        )

        return hypotheses
