import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qsl

try:
    from discovery.normalizer import EndpointNormalizer
except ImportError:
    try:
        from security_engine.discovery.normalizer import EndpointNormalizer
    except ImportError:
        from ..normalizer import EndpointNormalizer


STATIC_EXTENSIONS = {
    ".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".woff", ".woff2", ".ttf", ".eot", ".map", ".mp4", ".mp3", ".webp"
}

STATIC_MIME_PREFIXES = (
    "text/css", "image/", "font/", "video/", "audio/",
    "application/javascript", "text/javascript"
)


class HarDiscoveryParser:
    """
    Parses HTTP Archive (.har) logs containing recorded application traffic.
    Filters static asset noise, extracts API endpoints, request/response headers,
    status codes, and identifies observed authentication credentials.
    """

    @classmethod
    def parse_har_log(
        cls,
        content: str,
        default_base_url: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Parses raw HAR file JSON string.
        Returns a list of structured endpoint dictionaries.
        """
        if not content or not content.strip():
            raise ValueError("HAR content cannot be empty.")

        try:
            data = json.loads(content)
        except Exception as e:
            raise ValueError(f"Failed to parse HAR content as JSON: {str(e)}")

        if not isinstance(data, dict):
            raise ValueError("Invalid HAR content: root must be a JSON object.")

        log_obj = data.get("log")
        if not isinstance(log_obj, dict):
            raise ValueError("Invalid HAR format: missing 'log' object.")

        entries = log_obj.get("entries", [])
        if not isinstance(entries, list):
            raise ValueError("Invalid HAR format: 'entries' must be an array.")

        discovered_endpoints: List[Dict[str, Any]] = []

        for entry in entries:
            if not isinstance(entry, dict):
                continue

            req = entry.get("request", {})
            resp = entry.get("response", {})
            raw_url = req.get("url", "")
            method = req.get("method", "GET").upper().strip()

            if not raw_url:
                continue

            parsed_url = urlparse(raw_url)
            path = parsed_url.path or "/"

            # Filter static assets
            if cls._is_static_asset(path, resp):
                continue

            norm_path, path_params_from_route, _ = EndpointNormalizer.normalize_path(path)

            # Query parameters
            all_params = list(path_params_from_route)
            query_tuples = parse_qsl(parsed_url.query, keep_blank_values=True)
            for k, v in query_tuples:
                all_params.append({
                    "name": k,
                    "location": "query",
                    "param_type": "string",
                    "required": False,
                    "example": v
                })

            # Headers
            req_headers = {
                h.get("name", "").lower(): h.get("value", "")
                for h in req.get("headers", [])
                if isinstance(h, dict) and h.get("name")
            }

            resp_status = resp.get("status", 200)
            status_codes = [int(resp_status)] if resp_status else [200]

            # Auth check
            auth_required = bool(
                "authorization" in req_headers
                or "x-api-key" in req_headers
                or "cookie" in req_headers
                or resp_status == 401
            )

            # Body schema
            post_data = req.get("postData", {})
            req_body_text = post_data.get("text", "")
            req_mime = post_data.get("mimeType", req_headers.get("content-type"))
            body_schema = None
            if req_body_text:
                try:
                    body_schema = {"type": "object", "example": json.loads(req_body_text)}
                except Exception:
                    body_schema = {"type": "string", "example": req_body_text[:200]}

            # Response schema
            resp_content = resp.get("content", {})
            resp_text = resp_content.get("text", "")
            resp_mime = resp_content.get("mimeType", "")
            resp_schema = {}
            if resp_text and "application/json" in resp_mime:
                try:
                    resp_schema[str(resp_status)] = {"type": "object", "example": json.loads(resp_text)}
                except Exception:
                    pass

            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}".rstrip("/") if parsed_url.netloc else (default_base_url or "")
            now_iso = datetime.now(timezone.utc).isoformat()

            discovered_endpoints.append({
                "path": norm_path,
                "method": method,
                "auth_required": auth_required,
                "parameters": all_params,
                "response_codes": status_codes,
                "risk_level": "UNASSESSED",
                "raw_metadata": {
                    "base_url": base_url,
                    "original_path": path,
                    "original_url": raw_url,
                    "discovery_source": "HAR",
                    "evidence_classification": "OBSERVED",
                    "content_type": req_mime,
                    "request_headers": req_headers,
                    "request_body_schema": body_schema,
                    "response_schemas": resp_schema,
                    "first_discovered_at": now_iso,
                    "last_observed_at": now_iso,
                    "traffic_timing_ms": entry.get("time", 0.0)
                }
            })

        return EndpointNormalizer.deduplicate_endpoints(discovered_endpoints)

    @classmethod
    def _is_static_asset(cls, path: str, response: Dict[str, Any]) -> bool:
        """Determines if a request path or response content represents a static non-API asset."""
        lower_path = path.lower()
        for ext in STATIC_EXTENSIONS:
            if lower_path.endswith(ext):
                return True

        # Check response content-type
        content = response.get("content", {})
        mime = content.get("mimeType", "").lower()
        if any(mime.startswith(prefix) for prefix in STATIC_MIME_PREFIXES):
            return True

        return False
