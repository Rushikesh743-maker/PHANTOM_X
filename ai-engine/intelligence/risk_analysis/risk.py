
from typing import List, Dict, Any


class RiskScoringEngine:
    """
    Contextual vulnerability risk scoring engine.

    Considers severity, exploitability, exposure,
    business impact and authentication requirements.
    """

    SEVERITY_WEIGHTS = {
        "CRITICAL": 25.0,
        "HIGH": 15.0,
        "MEDIUM": 7.5,
        "LOW": 2.5,
        "INFO": 0.5,
    }

    EXPLOITABILITY_WEIGHTS = {
        "LOW": 0.75,
        "MEDIUM": 1.0,
        "HIGH": 1.25,
        "CRITICAL": 1.5,
    }

    EXPOSURE_WEIGHTS = {
        "INTERNAL": 0.8,
        "RESTRICTED": 1.0,
        "PUBLIC": 1.2,
    }

    BUSINESS_IMPACT_WEIGHTS = {
        "LOW": 0.8,
        "MEDIUM": 1.0,
        "HIGH": 1.2,
        "CRITICAL": 1.4,
    }

    @classmethod
    def calculate_vulnerability_risk(
        cls,
        vulnerability: Dict[str, Any]
    ) -> Dict[str, Any]:

        severity = str(
            vulnerability.get("severity", "MEDIUM")
        ).upper()

        exploitability = str(
            vulnerability.get("exploitability", "MEDIUM")
        ).upper()

        exposure = str(
            vulnerability.get("exposure", "RESTRICTED")
        ).upper()

        business_impact = str(
            vulnerability.get("business_impact", "MEDIUM")
        ).upper()

        auth_required = vulnerability.get(
            "auth_required", True
        )

        # Get scoring weights
        severity_score = cls.SEVERITY_WEIGHTS.get(
            severity, cls.SEVERITY_WEIGHTS["MEDIUM"]
        )

        exploitability_weight = cls.EXPLOITABILITY_WEIGHTS.get(
            exploitability, 1.0
        )

        exposure_weight = cls.EXPOSURE_WEIGHTS.get(
            exposure, 1.0
        )

        impact_weight = cls.BUSINESS_IMPACT_WEIGHTS.get(
            business_impact, 1.0
        )

        # Publicly accessible endpoints receive a higher multiplier.
        # Authentication being required slightly reduces exposure,
        # but does not eliminate the vulnerability.
        authentication_weight = 0.9 if auth_required else 1.1

        score = (
            severity_score
            * exploitability_weight
            * exposure_weight
            * impact_weight
            * authentication_weight
        )

        score = round(min(100.0, score), 2)

        if score >= 35:
            risk_level = "CRITICAL"
        elif score >= 20:
            risk_level = "HIGH"
        elif score >= 8:
            risk_level = "MEDIUM"
        elif score >= 2:
            risk_level = "LOW"
        else:
            risk_level = "INFO"

        return {
            "risk_score": score,
            "risk_level": risk_level,
            "factors": {
                "severity": severity,
                "severity_score": severity_score,
                "exploitability": exploitability,
                "exposure": exposure,
                "business_impact": business_impact,
                "authentication_required": auth_required,
            }
        }

    @classmethod
    def calculate_application_risk(
        cls,
        vulnerabilities: List[Dict[str, Any]]
    ) -> float:
        """
        Calculates the combined application risk.

        Individual vulnerability scores are added and
        the final application score is capped at 100.
        """

        total_score = 0.0

        for vulnerability in vulnerabilities:
            result = cls.calculate_vulnerability_risk(
                vulnerability
            )

            total_score += result["risk_score"]

        return round(min(100.0, total_score), 1)

    @classmethod
    def analyze_application(
        cls,
        vulnerabilities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:

        results = []

        for vulnerability in vulnerabilities:
            result = cls.calculate_vulnerability_risk(
                vulnerability
            )

            results.append({
                "vulnerability": vulnerability,
                **result
            })

        application_score = cls.calculate_application_risk(
            vulnerabilities
        )

        if application_score >= 75:
            application_level = "CRITICAL"
        elif application_score >= 40:
            application_level = "HIGH"
        elif application_score >= 15:
            application_level = "MEDIUM"
        elif application_score > 0:
            application_level = "LOW"
        else:
            application_level = "INFO"

        return {
            "application_risk_score": application_score,
            "application_risk_level": application_level,
            "vulnerabilities_analyzed": len(vulnerabilities),
            "vulnerability_results": results
        }
