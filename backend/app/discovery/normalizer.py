import re
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timezone


UUID_REGEX = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
NUMERIC_REGEX = re.compile(r"^\d+$")
OBJECTID_REGEX = re.compile(r"^[0-9a-fA-F]{24}$")
HASH_TOKEN_REGEX = re.compile(r"^[0-9a-fA-F]{32,64}$")
PARAM_COLON_REGEX = re.compile(r"^:([a-zA-Z_][a-zA-Z0-9_]*)$")
PARAM_ANGLE_REGEX = re.compile(r"^<([a-zA-Z_][a-zA-Z0-9_]*)>$")


class EndpointNormalizer:
    """
    Normalizes API endpoint paths, identifies path parameters,
    and deduplicates discovered endpoints without conflating distinct HTTP methods.
    """

    @classmethod
    def clean_path(cls, raw_path: str) -> str:
        """Strip query params, fragments, whitespace, and normalize slashes."""
        if not raw_path:
            return "/"
        # Strip query string and fragment
        path = raw_path.split("?")[0].split("#")[0].strip()
        # Ensure leading slash
        if not path.startswith("/"):
            path = "/" + path
        # Normalize double slashes
        path = re.sub(r"/+", "/", path)
        # Strip trailing slash unless it's root
        if len(path) > 1 and path.endswith("/"):
            path = path[:-1]
        return path

    @classmethod
    def normalize_path(cls, raw_path: str) -> Tuple[str, List[Dict[str, Any]], bool]:
        """
        Normalizes dynamic URL paths into canonical parameterized routes.
        Returns:
            (normalized_path, extracted_path_parameters, was_normalized)
        """
        clean = cls.clean_path(raw_path)
        if clean == "/":
            return "/", [], False

        segments = clean.split("/")[1:]  # skip leading empty segment
        normalized_segments: List[str] = []
        path_params: List[Dict[str, Any]] = []
        was_normalized = False

        for idx, segment in enumerate(segments):
            # Check existing OpenAPI style {param}
            if segment.startswith("{") and segment.endswith("}") and len(segment) > 2:
                param_name = segment[1:-1]
                normalized_segments.append(segment)
                path_params.append({
                    "name": param_name,
                    "location": "path",
                    "param_type": "string",
                    "required": True,
                    "example": None
                })
                continue

            # Check colon param :id
            colon_match = PARAM_COLON_REGEX.match(segment)
            if colon_match:
                param_name = colon_match.group(1)
                normalized_segments.append(f"{{{param_name}}}")
                path_params.append({
                    "name": param_name,
                    "location": "path",
                    "param_type": "string",
                    "required": True,
                    "example": None
                })
                was_normalized = True
                continue

            # Check angle bracket param <id>
            angle_match = PARAM_ANGLE_REGEX.match(segment)
            if angle_match:
                param_name = angle_match.group(1)
                normalized_segments.append(f"{{{param_name}}}")
                path_params.append({
                    "name": param_name,
                    "location": "path",
                    "param_type": "string",
                    "required": True,
                    "example": None
                })
                was_normalized = True
                continue

            # Check UUID
            if UUID_REGEX.match(segment):
                normalized_segments.append("{id}")
                path_params.append({
                    "name": "id",
                    "location": "path",
                    "param_type": "uuid",
                    "required": True,
                    "example": segment
                })
                was_normalized = True
                continue

            # Check Numeric ID
            if NUMERIC_REGEX.match(segment):
                normalized_segments.append("{id}")
                path_params.append({
                    "name": "id",
                    "location": "path",
                    "param_type": "integer",
                    "required": True,
                    "example": segment
                })
                was_normalized = True
                continue

            # Check MongoDB ObjectId
            if OBJECTID_REGEX.match(segment):
                normalized_segments.append("{id}")
                path_params.append({
                    "name": "id",
                    "location": "path",
                    "param_type": "string",
                    "required": True,
                    "example": segment
                })
                was_normalized = True
                continue

            # Check Token/Hash segment
            if HASH_TOKEN_REGEX.match(segment):
                param_name = "token"
                normalized_segments.append(f"{{{param_name}}}")
                path_params.append({
                    "name": param_name,
                    "location": "path",
                    "param_type": "string",
                    "required": True,
                    "example": segment[:8] + "..."
                })
                was_normalized = True
                continue

            # Literal segment
            normalized_segments.append(segment)

        normalized_path = "/" + "/".join(normalized_segments)
        return normalized_path, path_params, was_normalized

    @classmethod
    def deduplicate_endpoints(cls, endpoints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicates candidate endpoints by (method, normalized_path).
        Maintains distinct endpoints across different HTTP methods.
        Aggregates parameters, response status codes, and observed path evidence.
        """
        dedup_map: Dict[Tuple[str, str], Dict[str, Any]] = {}

        for ep in endpoints:
            method = ep.get("method", "GET").upper().strip()
            path = ep.get("path", "/").strip()
            key = (method, path)

            if key not in dedup_map:
                ep_copy = dict(ep)
                ep_copy["method"] = method
                ep_copy["path"] = path
                raw_meta = dict(ep_copy.get("raw_metadata", {}))
                orig_path = raw_meta.get("original_path", path)
                raw_meta["observed_paths"] = [orig_path]
                ep_copy["raw_metadata"] = raw_meta
                dedup_map[key] = ep_copy
            else:
                existing = dedup_map[key]
                # Merge response status codes
                existing_codes = set(existing.get("response_codes", []))
                for c in ep.get("response_codes", []):
                    existing_codes.add(int(c))
                existing["response_codes"] = sorted(list(existing_codes))

                # Merge parameters
                existing_params = {
                    (p.get("name"), p.get("location")): p
                    for p in existing.get("parameters", [])
                }
                for new_p in ep.get("parameters", []):
                    p_key = (new_p.get("name"), new_p.get("location"))
                    if p_key not in existing_params:
                        existing_params[p_key] = new_p
                existing["parameters"] = list(existing_params.values())

                # Merge observed paths
                raw_meta = existing.setdefault("raw_metadata", {})
                observed_paths = set(raw_meta.get("observed_paths", []))
                incoming_orig = ep.get("raw_metadata", {}).get("original_path")
                if incoming_orig:
                    observed_paths.add(incoming_orig)
                raw_meta["observed_paths"] = sorted(list(observed_paths))
                raw_meta["last_observed_at"] = datetime.now(timezone.utc).isoformat()

                # If any observation requires auth, mark auth_required True
                if ep.get("auth_required") is True:
                    existing["auth_required"] = True

        return list(dedup_map.values())
