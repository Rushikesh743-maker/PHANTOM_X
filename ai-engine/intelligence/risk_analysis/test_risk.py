
from intelligence.risk_analysis.risk import RiskScoringEngine


def main():

    vulnerabilities = [
        {
            "id": "VULN-001",
            "severity": "CRITICAL",
            "exploitability": "HIGH",
            "exposure": "PUBLIC",
            "business_impact": "CRITICAL",
            "auth_required": False
        },
        {
            "id": "VULN-002",
            "severity": "HIGH",
            "exploitability": "MEDIUM",
            "exposure": "RESTRICTED",
            "business_impact": "HIGH",
            "auth_required": True
        },
        {
            "id": "VULN-003",
            "severity": "LOW",
            "exploitability": "LOW",
            "exposure": "INTERNAL",
            "business_impact": "LOW",
            "auth_required": True
        }
    ]

    result = RiskScoringEngine.analyze_application(
        vulnerabilities
    )

    print("\nAPPLICATION RISK ANALYSIS")
    print("-------------------------")

    print("Application Score:",
          result["application_risk_score"])

    print("Application Risk:",
          result["application_risk_level"])

    print("Vulnerabilities Analyzed:",
          result["vulnerabilities_analyzed"])

    print("\nINDIVIDUAL VULNERABILITY SCORES")

    for item in result["vulnerability_results"]:
        vulnerability = item["vulnerability"]

        print("\nID:", vulnerability["id"])
        print("Score:", item["risk_score"])
        print("Risk Level:", item["risk_level"])
        print("Factors:", item["factors"])


if __name__ == "__main__":
    main()
