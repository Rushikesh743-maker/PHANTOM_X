
import re
from urllib.parse import urlsplit
from typing import List, Dict, Any, Tuple, Optional

from pydantic import BaseModel, Field

from shared.enums.common import SafetyClassification


class PolicyValidationResult(BaseModel):
    is_allowed: bool
    violations: List[str] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)
    approved_actions: List[Dict[str, Any]] = Field(default_factory=list)
    scenario_results: List[Dict[str, Any]] = Field(default_factory=list)


class DeterministicPolicyEngine:
    """
    Deterministic safety validation for proposed security test scenarios.

    AI proposes scenarios.
    This engine validates scope and safety before execution.

    State-modifying and destructive tests require explicit
    operator authorization through constructor settings.
    """

    def __init__(
        self,
        allowed_hosts: Optional[List[str]] = None,
        allow_destructive: bool = False,
        allow_state_modifying: bool = False,
        max_rate_rps: int = 10,
    ):
        self.allowed_hosts = [
            self._normalize_host(host)
            for host in (
                allowed_hosts or [
                    "localhost",
                    "127.0.0.1",
                    "api.example-target.local",
                ]
            )
        ]

        self.allowed_hosts = [
            host for host in self.allowed_hosts if host
        ]

        self.allow_destructive = allow_destructive
        self.allow_state_modifying = allow_state_modifying
        self.max_rate_rps = max(1, max_rate_rps)

        self.prohibited_sql_patterns = [
            r"\bDROP\s+TABLE\b",
            r"\bTRUNCATE\b",
            r"\bDELETE\s+FROM\b",
            r"\bALTER\s+SYSTEM\b",
            r"\bSHUTDOWN\b",
        ]

        self.prohibited_system_commands = [
            r"\brm\s+-rf\b",
            r"\bformat\b",
            r"\bmkfs\b",
            r"\b:\(\)\{\s*:\|:&\s*\};:",
        ]

    @staticmethod
    def _normalize_host(value: str) -> str:
        """Extract hostname while safely handling URLs and ports."""

        value = str(value or "").strip().lower()

        if not value:
            return ""

        if "://" not in value:
            value = "//" + value

        try:
            parsed = urlsplit(value)
            return (parsed.hostname or "").rstrip(".")
        except ValueError:
            return ""

    @staticmethod
    def _get_safety_value(scenario: Dict[str, Any]) -> str:
        safety = scenario.get(
            "safety_classification",
            SafetyClassification.SAFE_READ_ONLY
        )

        if isinstance(safety, SafetyClassification):
            return safety.value

        return str(safety).upper()

    def _is_host_allowed(self, target_host: str) -> bool:
        host = self._normalize_host(target_host)

        if not host:
            return False

        return any(
            host == allowed or host.endswith("." + allowed)
            for allowed in self.allowed_hosts
        )

    def validate_scenario(
        self,
        scenario: Dict[str, Any],
        target_host: str
    ) -> Tuple[bool, List[str]]:

        violations = []

        if not isinstance(scenario, dict):
            return False, ["Invalid scenario format."]

        # 1. Validate target scope.
        if not self._is_host_allowed(target_host):
            violations.append(
                f"Target host '{target_host}' is outside "
                "the authorized scope allowlist."
            )

        # 2. Validate safety classification.
        safety_class = self._get_safety_value(scenario)

        valid_classes = {
            item.value for item in SafetyClassification
        }

        if safety_class not in valid_classes:
            violations.append(
                f"Unknown safety classification: {safety_class}"
            )

        elif (
            safety_class == SafetyClassification.STATE_MODIFYING.value
            and not self.allow_state_modifying
        ):
            violations.append(
                "State-modifying test rejected: "
                "explicit operator approval required."
            )

        elif (
            safety_class == SafetyClassification.HIGH_RISK_DESTRUCTIVE.value
            and not self.allow_destructive
        ):
            violations.append(
                "High-risk destructive test rejected: "
                "explicit operator approval required."
            )

        # 3. Inspect scenario content for prohibited commands.
        payload_str = str(scenario)

        for pattern in self.prohibited_sql_patterns:
            if re.search(pattern, payload_str, re.IGNORECASE):
                violations.append(
                    "Prohibited destructive SQL pattern detected."
                )

        for pattern in self.prohibited_system_commands:
            if re.search(pattern, payload_str, re.IGNORECASE):
                violations.append(
                    "Prohibited destructive system command detected."
                )

        return len(violations) == 0, violations

    def validate_plan(
        self,
        proposed_plan: List[Dict[str, Any]],
        target_host: str
    ) -> PolicyValidationResult:

        all_violations = []
        approved = []
        scenario_results = []

        for scenario in proposed_plan:

            is_valid, violations = self.validate_scenario(
                scenario,
                target_host
            )

            scenario_id = (
                scenario.get("scenario_id", "UNKNOWN")
                if isinstance(scenario, dict)
                else "INVALID"
            )

            scenario_results.append({
                "scenario_id": scenario_id,
                "status": "APPROVED" if is_valid else "BLOCKED",
                "violations": violations
            })

            if is_valid:
                approved.append(scenario)
            else:
                all_violations.extend(
                    f"{scenario_id}: {violation}"
                    for violation in violations
                )

        is_allowed = len(all_violations) == 0

        return PolicyValidationResult(
            is_allowed=is_allowed,
            violations=all_violations,
            reasons=(
                ["All scenarios passed deterministic safety validation."]
                if is_allowed
                else ["One or more scenarios failed safety validation."]
            ),
            approved_actions=approved,
            scenario_results=scenario_results
        )