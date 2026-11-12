import json
import yaml
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from urllib.parse import urlparse

try:
    from discovery.normalizer import EndpointNormalizer
except ImportError:
    try:
        from security_engine.discovery.normalizer import EndpointNormalizer
    except ImportError:
        from ..normalizer import EndpointNormalizer


class OpenApiParser:
    """
    Parses OpenAPI (v3.0, v3.1) and Swagger (v2.0) specifications in JSON or YAML format.
    Extracts structured endpoint definitions, parameters, request/response schemas,
    and security requirements.
    """

    SUPPORTED_METHODS = {"get", "post", "put", "delete", "patch", "options", "head"}

    @classmethod
    def parse_specification(
        cls,
        content: str,
        default_base_url: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Parses raw OpenAPI/Swagger string content (JSON or YAML).
        Returns a list of structured endpoint dictionaries.
        """
        if not content or not content.strip():
            raise ValueError("OpenAPI specification content cannot be empty.")

        # Try JSON first, fallback to YAML
        try:
            data = json.loads(content)
        except Exception:
            try:
                data = yaml.safe_load(content)
            except Exception as e:
                raise ValueError(f"Failed to parse OpenAPI content as JSON or YAML: {str(e)}")

        if not isinstance(data, dict):
            raise ValueError("Invalid OpenAPI specification: root must be a JSON/YAML object.")

        # Determine version
        is_swagger_v2 = "swagger" in data and str(data["swagger"]).startswith("2")
        is_openapi_v3 = "openapi" in data and str(data["openapi"]).startswith("3")

        if not is_swagger_v2 and not is_openapi_v3 and "paths" not in data:
            raise ValueError("Invalid specification: missing 'openapi', 'swagger', or 'paths' declaration.")

        # Extract base URL
        base_url = cls._extract_base_url(data, is_swagger_v2, default_base_url)

        paths = data.get("paths", {})
        if not isinstance(paths, dict):
            raise ValueError("Invalid OpenAPI specification: 'paths' must be an object.")

        discovered_endpoints: List[Dict[str, Any]] = []
        global_security = data.get("security", [])

        for path_key, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            # Shared path-level parameters
            path_level_params = path_item.get("parameters", [])

            for method_key, operation in path_item.items():
                if method_key.lower() not in cls.SUPPORTED_METHODS:
                    continue
                if not isinstance(operation, dict):
                    continue

                method = method_key.upper()
                norm_path, path_params_from_path, _ = EndpointNormalizer.normalize_path(path_key)

                # Collect parameters
                all_params = cls._extract_parameters(
                    operation.get("parameters", []),
                    path_level_params,
                    path_params_from_path
                )

                # Collect response status codes
                response_codes = cls._extract_response_codes(operation.get("responses", {}))

                # Determine authentication requirement
                op_security = operation.get("security", None)
                if op_security is not None:
                    auth_required = len(op_security) > 0
                else:
                    auth_required = len(global_security) > 0

                # Extract request body schema and content types
                request_body_schema, content_type = cls._extract_request_body(operation, is_swagger_v2)

                # Extract response schemas
                response_schemas = cls._extract_response_schemas(operation.get("responses", {}))

                now_iso = datetime.now(timezone.utc).isoformat()

                endpoint_record = {
                    "path": norm_path,
                    "method": method,
                    "auth_required": auth_required,
                    "parameters": all_params,
                    "response_codes": response_codes,
                    "risk_level": "UNASSESSED",
                    "raw_metadata": {
                        "base_url": base_url,
                        "original_path": path_key,
                        "discovery_source": "OPENAPI",
                        "evidence_classification": "DOCUMENTED",
                        "operation_id": operation.get("operationId"),
                        "summary": operation.get("summary"),
                        "description": operation.get("description"),
                        "tags": operation.get("tags", []),
                        "content_type": content_type,
                        "request_body_schema": request_body_schema,
                        "response_schemas": response_schemas,
                        "first_discovered_at": now_iso,
                        "last_observed_at": now_iso,
                    }
                }
                discovered_endpoints.append(endpoint_record)

        return EndpointNormalizer.deduplicate_endpoints(discovered_endpoints)

    @classmethod
    def _extract_base_url(cls, data: Dict[str, Any], is_v2: bool, default_url: Optional[str]) -> str:
        """Extracts base URL from OpenAPI v3 servers or Swagger v2 host/basePath."""
        if is_v2:
            host = data.get("host")
            base_path = data.get("basePath", "")
            schemes = data.get("schemes", ["https"])
            scheme = schemes[0] if schemes else "https"
            if host:
                return f"{scheme}://{host}{base_path}".rstrip("/")
        else:
            servers = data.get("servers", [])
            if servers and isinstance(servers, list) and isinstance(servers[0], dict):
                url = servers[0].get("url", "")
                if url:
                    return url.rstrip("/")

        return default_url.rstrip("/") if default_url else ""

    @classmethod
    def _extract_parameters(
        cls,
        op_params: List[Any],
        path_params: List[Any],
        path_params_from_route: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Merges and extracts parameters across operation, path-level, and path syntax."""
        merged: Dict[Tuple[str, str], Dict[str, Any]] = {}

        # Add path params discovered from syntax
        for p in path_params_from_route:
            merged[(p["name"], p["location"])] = p

        for p in path_params + op_params:
            if not isinstance(p, dict):
                continue
            name = p.get("name")
            location = p.get("in", "query")
            if not name:
                continue

            schema = p.get("schema", {})
            param_type = schema.get("type", p.get("type", "string"))
            required = p.get("required", location == "path")
            example = p.get("example") or schema.get("example")

            merged[(name, location)] = {
                "name": name,
                "location": location,
                "param_type": param_type,
                "required": required,
                "example": example
            }

        return list(merged.values())

    @classmethod
    def _extract_response_codes(cls, responses: Dict[str, Any]) -> List[int]:
        """Extracts numeric HTTP status codes from response mapping."""
        codes: List[int] = []
        if not isinstance(responses, dict):
            return [200]

        for code_key in responses.keys():
            if str(code_key).isdigit():
                codes.append(int(code_key))
            elif str(code_key).lower() == "default":
                codes.append(200)

        return sorted(list(set(codes))) if codes else [200]

    @classmethod
    def _extract_request_body(cls, operation: Dict[str, Any], is_v2: bool) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Extracts request body schema and primary content type."""
        if is_v2:
            for p in operation.get("parameters", []):
                if isinstance(p, dict) and p.get("in") == "body":
                    return p.get("schema"), "application/json"
            return None, None

        # OpenAPI 3.x
        req_body = operation.get("requestBody")
        if isinstance(req_body, dict):
            content = req_body.get("content", {})
            if isinstance(content, dict):
                for mime_type, media_obj in content.items():
                    if isinstance(media_obj, dict):
                        return media_obj.get("schema"), mime_type
        return None, None

    @classmethod
    def _extract_response_schemas(cls, responses: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts schema descriptors per response status code."""
        schemas: Dict[str, Any] = {}
        if not isinstance(responses, dict):
            return schemas

        for code_key, resp_obj in responses.items():
            if not isinstance(resp_obj, dict):
                continue
            # v3 content
            content = resp_obj.get("content", {})
            if isinstance(content, dict):
                for mime, media in content.items():
                    if isinstance(media, dict) and "schema" in media:
                        schemas[str(code_key)] = media.get("schema")
                        break
            elif "schema" in resp_obj:
                schemas[str(code_key)] = resp_obj.get("schema")

        return schemas
