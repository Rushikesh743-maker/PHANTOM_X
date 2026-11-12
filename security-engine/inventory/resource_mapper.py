import re
from typing import List, Dict, Any, Optional, Tuple, Set


COMMON_PREFIXES = {"api", "v1", "v2", "v3", "v4", "v5", "rest", "public", "internal", "private", "app", "service"}


class ResourceMapper:
    """
    Extracts logical resources and parent-child hierarchical relationships
    from API paths without false associations across unrelated paths.
    """

    @classmethod
    def extract_resource(cls, path: str) -> Tuple[str, Optional[str], float, str]:
        """
        Extracts (resource_name, parent_resource_name, confidence, evidence)
        from a normalized endpoint path.
        """
        clean_path = path.strip("/")
        if not clean_path:
            return ("root", None, 0.70, "Root API path")

        raw_segments = clean_path.split("/")

        # Strip standard API prefixes
        filtered_segments = []
        i = 0
        while i < len(raw_segments):
            seg = raw_segments[i]
            if not filtered_segments and seg.lower() in COMMON_PREFIXES:
                i += 1
                continue
            filtered_segments.append(seg)
            i += 1

        if not filtered_segments:
            return ("root", None, 0.70, "Root API path")

        # Identify non-parameter (literal resource) segments
        resource_segments = []
        for seg in filtered_segments:
            # Check if segment is dynamic parameter: {id}, :id, <id>, or all numeric
            if seg.startswith("{") and seg.endswith("}"):
                continue
            if seg.startswith(":") or (seg.startswith("<") and seg.endswith(">")):
                continue
            if seg.isdigit():
                continue
            resource_segments.append(seg.lower())

        if not resource_segments:
            # All segments were parameters
            return (filtered_segments[0].strip("{}:<>").lower() or "resource", None, 0.60, "Derived from parameter placeholder")

        if len(resource_segments) == 1:
            res_name = resource_segments[0]
            return (res_name, None, 0.95, f"Top-level REST resource /{res_name}")

        # Multiple resource segments indicate hierarchy
        primary_res = resource_segments[-1]
        parent_res = resource_segments[-2]
        evidence = f"Sub-resource /{primary_res} nested under parent /{parent_res}"
        return (primary_res, parent_res, 0.90, evidence)

    @classmethod
    def group_by_resource(cls, endpoints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Groups a list of endpoint dictionaries by their logical resource.
        """
        resource_map: Dict[str, Dict[str, Any]] = {}

        for ep in endpoints:
            path = ep.get("path", "/")
            method = ep.get("method", "GET").upper()
            ep_id = ep.get("id")
            source = ep.get("source", "openapi")
            params = ep.get("parameters", [])

            res_name, parent_res, conf, evidence = cls.extract_resource(path)

            if res_name not in resource_map:
                resource_map[res_name] = {
                    "name": res_name,
                    "parent_resource": parent_res,
                    "endpoint_ids": [],
                    "methods": set(),
                    "paths": set(),
                    "parameters": [],
                    "request_schemas": [],
                    "response_schemas": [],
                    "related_resources": set(),
                    "discovery_sources": set(),
                    "confidence": conf,
                    "evidence": evidence,
                }

            group = resource_map[res_name]
            if ep_id:
                group["endpoint_ids"].append(ep_id)
            group["methods"].add(method)
            group["paths"].add(path)
            group["discovery_sources"].add(source)

            if parent_res:
                group["related_resources"].add(parent_res)

            # Merge parameters
            existing_param_names = {p.get("name") for p in group["parameters"]}
            for p in params:
                if p.get("name") and p.get("name") not in existing_param_names:
                    group["parameters"].append(p)
                    existing_param_names.add(p.get("name"))

            # Collect schemas if available
            raw_meta = ep.get("raw_metadata", {})
            if raw_meta.get("request_body_schema"):
                group["request_schemas"].append(raw_meta["request_body_schema"])
            if raw_meta.get("response_schemas"):
                group["response_schemas"].append(raw_meta["response_schemas"])

        # Also register child resources in parent related_resources
        for res_name, data in resource_map.items():
            parent = data.get("parent_resource")
            if parent and parent in resource_map:
                resource_map[parent]["related_resources"].add(res_name)

        # Convert sets to sorted lists for serialization
        results = []
        for res_name, data in sorted(resource_map.items()):
            results.append({
                "name": data["name"],
                "parent_resource": data["parent_resource"],
                "endpoint_count": len(data["endpoint_ids"]),
                "endpoint_ids": data["endpoint_ids"],
                "methods": sorted(list(data["methods"])),
                "paths": sorted(list(data["paths"])),
                "parameters": data["parameters"],
                "request_schemas": data["request_schemas"],
                "response_schemas": data["response_schemas"],
                "related_resources": sorted(list(data["related_resources"])),
                "discovery_sources": sorted(list(data["discovery_sources"])),
                "confidence": data["confidence"],
                "evidence": data["evidence"],
            })

        return results

