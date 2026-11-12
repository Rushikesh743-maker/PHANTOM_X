import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from urllib.parse import urlparse

try:
    from discovery.normalizer import EndpointNormalizer
except ImportError:
    try:
        from security_engine.discovery.normalizer import EndpointNormalizer
    except ImportError:
        from ..normalizer import EndpointNormalizer


class PostmanParser:
    """
    Parses Postman Collection files (v2.0.0 and v2.1.0).
    Recursively navigates folders and requests to extract endpoints,
    headers, query parameters, payload structures, and example response codes.
    """

    @classmethod
    def parse_collection(
        cls,
        content: str,
        default_base_url: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Parses Postman collection JSON content string.
        Returns a list of structured endpoint dictionaries.
        """
        if not content or not content.strip():
            raise ValueError("Postman collection content cannot be empty.")

        try:
            data = json.loads(content)
        except Exception as e:
            raise ValueError(f"Failed to parse Postman collection as JSON: {str(e)}")

        if not isinstance(data, dict):
            raise ValueError("Invalid Postman collection: root must be a JSON object.")

        if "item" not in data and "items" not in data:
            raise ValueError("Invalid Postman collection: missing 'item' array.")

        items = data.get("item", data.get("items", []))
        if not isinstance(items, list):
            raise ValueError("Invalid Postman collection: 'item' must be a list.")

        collection_auth = data.get("auth")
        discovered_endpoints: List[Dict[str, Any]] = []

        cls._traverse_items(
            items=items,
            collection_auth=collection_auth,
            default_base_url=default_base_url,
            results=discovered_endpoints
        )

        return EndpointNormalizer.deduplicate_endpoints(discovered_endpoints)

    @classmethod
    def _traverse_items(
        cls,
        items: List[Any],
        collection_auth: Optional[Dict[str, Any]],
        default_base_url: Optional[str],
        results: List[Dict[str, Any]]
    ):
        """Recursively traverses folders and request items."""
        for item in items:
            if not isinstance(item, dict):
                continue

            # Nested folder
            if "item" in item and isinstance(item["item"], list):
                cls._traverse_items(
                    items=item["item"],
                    collection_auth=item.get("auth", collection_auth),
                    default_base_url=default_base_url,
                    results=results
                )
                continue

            # Request item
            request_obj = item.get("request")
            if not request_obj:
                continue

            endpoint = cls._parse_request_item(
                item=item,
                request_obj=request_obj,
                inherited_auth=collection_auth,
                default_base_url=default_base_url
            )
            if endpoint:
                results.append(endpoint)

    @classmethod
    def _parse_request_item(
        cls,
        item: Dict[str, Any],
        request_obj: Any,
        inherited_auth: Optional[Dict[str, Any]],
        default_base_url: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """Parses a single Postman request item into a normalized endpoint dictionary."""
        # Method
        if isinstance(request_obj, dict):
            method = request_obj.get("method", "GET").upper().strip()
            url_obj = request_obj.get("url", "")
            headers_list = request_obj.get("header", [])
            body_obj = request_obj.get("body", {})
            req_auth = request_obj.get("auth", inherited_auth)
        elif isinstance(request_obj, str):
            method = "GET"
            url_obj = request_obj
            headers_list = []
            body_obj = {}
            req_auth = inherited_auth
        else:
            return None

        # Parse URL
        raw_url, path, query_params, base_url = cls._parse_url(url_obj, default_base_url)
        if not path:
            return None

        norm_path, path_params_from_route, _ = EndpointNormalizer.normalize_path(path)

        # Merge parameters
        all_params = list(path_params_from_route)
        for q in query_params:
            all_params.append({
                "name": q.get("key", "param"),
                "location": "query",
                "param_type": "string",
                "required": False,
                "example": q.get("value")
            })

        # Headers
        request_headers: Dict[str, str] = {}
        if isinstance(headers_list, list):
            for h in headers_list:
                if isinstance(h, dict) and h.get("key"):
                    request_headers[h["key"].lower()] = str(h.get("value", ""))

        # Request body
        request_body_schema, content_type = cls._parse_body(body_obj, request_headers)

        # Auth
        auth_required = req_auth is not None and req_auth.get("type", "noauth") != "noauth"
        if not auth_required and "authorization" in request_headers:
            auth_required = True

        # Example responses
        response_codes = cls._extract_example_responses(item.get("response", []))

        now_iso = datetime.now(timezone.utc).isoformat()

        return {
            "path": norm_path,
            "method": method,
            "auth_required": auth_required,
            "parameters": all_params,
            "response_codes": response_codes,
            "risk_level": "UNASSESSED",
            "raw_metadata": {
                "base_url": base_url,
                "original_path": path,
                "original_url": raw_url,
                "discovery_source": "POSTMAN",
                "evidence_classification": "IMPORTED",
                "request_name": item.get("name"),
                "description": item.get("description"),
                "content_type": content_type,
                "request_headers": request_headers,
                "request_body_schema": request_body_schema,
                "first_discovered_at": now_iso,
                "last_observed_at": now_iso,
            }
        }

    @classmethod
    def _parse_url(cls, url_obj: Any, default_base_url: Optional[str]) -> Tuple[str, str, List[Dict[str, Any]], str]:
        """Extracts raw URL, path, query parameters, and base URL from Postman URL representation."""
        query_params: List[Dict[str, Any]] = []

        if isinstance(url_obj, str):
            raw_url = url_obj
            parsed = urlparse(url_obj)
            path = parsed.path or "/"
            base_url = f"{parsed.scheme}://{parsed.netloc}".rstrip("/") if parsed.netloc else (default_base_url or "")
            return raw_url, path, query_params, base_url

        if isinstance(url_obj, dict):
            raw_url = url_obj.get("raw", "")
            raw_path_list = url_obj.get("path", [])
            query_list = url_obj.get("query", [])

            if isinstance(raw_path_list, list):
                clean_segments = [str(s).strip() for s in raw_path_list if str(s).strip()]
                path = "/" + "/".join(clean_segments)
            elif isinstance(raw_path_list, str):
                path = raw_path_list if raw_path_list.startswith("/") else f"/{raw_path_list}"
            else:
                path = "/"

            if isinstance(query_list, list):
                for q in query_list:
                    if isinstance(q, dict) and q.get("key"):
                        query_params.append(q)

            # Extract base_url from host/protocol if present
            protocol = url_obj.get("protocol", "https")
            host_list = url_obj.get("host", [])
            port = url_obj.get("port", "")
            if isinstance(host_list, list) and host_list:
                host_str = ".".join(str(h) for h in host_list)
                if port:
                    host_str = f"{host_str}:{port}"
                base_url = f"{protocol}://{host_str}".rstrip("/")
            elif raw_url and "://" in raw_url:
                parsed = urlparse(raw_url)
                base_url = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
            else:
                base_url = default_base_url.rstrip("/") if default_base_url else ""

            return raw_url, path, query_params, base_url

        return "", "", [], default_base_url or ""

    @classmethod
    def _parse_body(cls, body_obj: Dict[str, Any], headers: Dict[str, str]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Parses request body mode and schema details."""
        if not isinstance(body_obj, dict):
            return None, headers.get("content-type")

        mode = body_obj.get("mode", "")
        content_type = headers.get("content-type")

        if mode == "raw":
            raw_text = body_obj.get("raw", "")
            opts = body_obj.get("options", {}).get("raw", {})
            detected_lang = opts.get("language", "json")
            if not content_type:
                content_type = "application/json" if detected_lang == "json" else "text/plain"
            try:
                schema = json.loads(raw_text)
                return {"type": "object", "example": schema}, content_type
            except Exception:
                return {"type": "string", "example": raw_text[:200]}, content_type

        elif mode == "urlencoded":
            params = body_obj.get("urlencoded", [])
            return {"type": "urlencoded", "fields": params}, content_type or "application/x-www-form-urlencoded"

        elif mode == "formdata":
            params = body_obj.get("formdata", [])
            return {"type": "formdata", "fields": params}, content_type or "multipart/form-data"

        return None, content_type

    @classmethod
    def _extract_example_responses(cls, responses: List[Any]) -> List[int]:
        """Extracts status codes from saved example responses."""
        codes: List[int] = []
        if isinstance(responses, list):
            for resp in responses:
                if isinstance(resp, dict):
                    code = resp.get("code")
                    if code and str(code).isdigit():
                        codes.append(int(code))
        return sorted(list(set(codes))) if codes else [200]
