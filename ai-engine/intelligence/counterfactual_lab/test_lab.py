
from intelligence.counterfactual_lab.lab import CounterfactualLab


def main():
    lab = CounterfactualLab()

    endpoint = "/api/users/{id}"

    hypotheses = lab.generate_all_hypotheses(
        endpoint=endpoint,
        identifier_param="id",
        original_role="ADMIN",
        mutated_role="USER"
    )

    print("\nCOUNTERFACTUAL ATTACK LABORATORY")
    print("=" * 45)

    print("Endpoint:", endpoint)
    print("Total hypotheses:", len(hypotheses))

    for hypothesis in hypotheses:
        print("\nID:", hypothesis.hypothesis_id)
        print("Type:", hypothesis.scenario_type)
        print("Endpoint:", hypothesis.target_endpoint)
        print("Original:", hypothesis.original_parameter)
        print("Mutated:", hypothesis.mutated_parameter)
        print("Expected:", hypothesis.expected_safe_behavior)
        print("Vulnerability indicator:", hypothesis.vulnerability_indicator)
        print("Safety:", hypothesis.safety_classification.value)


if __name__ == "__main__":
    main()
