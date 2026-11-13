
from typing import List, Optional, Dict, Set
from pydantic import BaseModel, Field, ConfigDict


SEVERITY_RANK = {
    "INFO": 0,
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "CRITICAL": 4,
}


class AttackNode(BaseModel):
    """Represents one vulnerability or stage in a potential attack path."""

    node_id: str
    phase: str
    description: str
    vulnerability_id: str
    severity: str

    model_config = ConfigDict(str_strip_whitespace=True)

    def normalized_severity(self) -> str:
        severity = self.severity.upper()
        return severity if severity in SEVERITY_RANK else "MEDIUM"


class AttackEdge(BaseModel):
    """Represents a relationship between two attack-chain stages."""

    source_id: str
    target_id: str
    transition_mechanism: str


class AttackGraph(BaseModel):
    """
    Builds and analyzes potential attack paths from related vulnerabilities.

    This graph represents hypothetical paths, not confirmed exploitation.
    """

    chain_title: str
    severity: str = "INFO"
    nodes: List[AttackNode] = Field(default_factory=list)
    edges: List[AttackEdge] = Field(default_factory=list)

    def _node_ids(self) -> Set[str]:
        return {node.node_id for node in self.nodes}

    def _has_path(self, start: str, destination: str) -> bool:
        """Check whether destination is already reachable from start."""

        adjacency: Dict[str, List[str]] = {}

        for edge in self.edges:
            adjacency.setdefault(edge.source_id, []).append(edge.target_id)

        stack = [start]
        visited = set()

        while stack:
            current = stack.pop()

            if current == destination:
                return True

            if current in visited:
                continue

            visited.add(current)
            stack.extend(adjacency.get(current, []))

        return False

    def add_step(
        self,
        node: AttackNode,
        incoming_from_id: Optional[str] = None,
        mechanism: Optional[str] = None
    ) -> None:
        """Add a node and optionally connect it to an existing node."""

        if node.node_id in self._node_ids():
            raise ValueError(f"Duplicate node ID: {node.node_id}")

        if incoming_from_id:
            if incoming_from_id not in self._node_ids():
                raise ValueError(
                    f"Source node does not exist: {incoming_from_id}"
                )

        self.nodes.append(node)

        if incoming_from_id:
            self.add_connection(
                source_id=incoming_from_id,
                target_id=node.node_id,
                mechanism=mechanism or "Potentially enables the next stage"
            )

        self.update_severity()

    def add_connection(
        self,
        source_id: str,
        target_id: str,
        mechanism: str
    ) -> None:
        """Connect two existing nodes without creating a cycle."""

        node_ids = self._node_ids()

        if source_id not in node_ids or target_id not in node_ids:
            raise ValueError("Both source and target nodes must exist.")

        if source_id == target_id:
            raise ValueError("A node cannot connect to itself.")

        if not mechanism or not mechanism.strip():
            raise ValueError("Transition mechanism cannot be empty.")

        if any(
            edge.source_id == source_id and edge.target_id == target_id
            for edge in self.edges
        ):
            raise ValueError("This connection already exists.")

        # Adding source -> target would create a cycle if target
        # can already reach source.
        if self._has_path(target_id, source_id):
            raise ValueError("Connection would create a circular attack path.")

        self.edges.append(
            AttackEdge(
                source_id=source_id,
                target_id=target_id,
                transition_mechanism=mechanism.strip()
            )
        )

    def update_severity(self) -> str:
        """Set chain severity to the highest node severity."""

        if not self.nodes:
            self.severity = "INFO"
            return self.severity

        self.severity = max(
            (node.normalized_severity() for node in self.nodes),
            key=lambda value: SEVERITY_RANK[value]
        )

        return self.severity

    def get_attack_paths(self) -> List[List[str]]:
        """Return all root-to-leaf paths in the attack graph."""

        adjacency: Dict[str, List[str]] = {
            node.node_id: [] for node in self.nodes
        }

        targets = set()

        for edge in self.edges:
            adjacency[edge.source_id].append(edge.target_id)
            targets.add(edge.target_id)

        roots = [
            node_id for node_id in adjacency
            if node_id not in targets
        ]

        paths: List[List[str]] = []

        def explore(current: str, path: List[str]) -> None:
            next_nodes = adjacency[current]

            if not next_nodes:
                paths.append(path)
                return

            for next_node in next_nodes:
                explore(next_node, path + [next_node])

        for root in roots:
            explore(root, [root])

        # Include isolated nodes.
        connected_nodes = {
            node_id
            for node_id, children in adjacency.items()
            if children
        } | targets

        for node_id in adjacency:
            if node_id not in connected_nodes:
                paths.append([node_id])

        return paths

    def get_summary(self) -> dict:
        """Return a summary suitable for reporting and dashboards."""

        return {
            "chain_title": self.chain_title,
            "severity": self.update_severity(),
            "total_nodes": len(self.nodes),
            "total_connections": len(self.edges),
            "attack_paths": self.get_attack_paths(),
            "is_hypothetical": True,
        }
