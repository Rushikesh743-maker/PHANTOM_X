
from intelligence.attack_chain.chain import AttackGraph, AttackNode


def main():
    graph = AttackGraph(
        chain_title="Authorization Weakness Attack Path"
    )

    node1 = AttackNode(
        node_id="NODE-001",
        phase="INITIAL_ACCESS",
        description="Weak authentication controls",
        vulnerability_id="VULN-001",
        severity="HIGH"
    )

    node2 = AttackNode(
        node_id="NODE-002",
        phase="PRIVILEGE_ESCALATION",
        description="Broken role authorization",
        vulnerability_id="VULN-002",
        severity="CRITICAL"
    )

    node3 = AttackNode(
        node_id="NODE-003",
        phase="RESOURCE_ACCESS",
        description="Potential unauthorized resource access",
        vulnerability_id="VULN-003",
        severity="HIGH"
    )

    graph.add_step(node1)
    graph.add_step(
        node2,
        incoming_from_id="NODE-001",
        mechanism="Weak authentication may expose an authorization weakness"
    )
    graph.add_step(
        node3,
        incoming_from_id="NODE-002",
        mechanism="Broken authorization may permit unauthorized resource access"
    )

    print("\nATTACK CHAIN INTELLIGENCE")
    print("=" * 40)

    print("\nSummary:")
    print(graph.get_summary())

    print("\nAttack Paths:")
    for path in graph.get_attack_paths():
        print(" -> ".join(path))

    print("\nOverall Severity:", graph.severity)


if __name__ == "__main__":
    main()
