import fnmatch
from typing import Dict, Any, List, Tuple
from urllib.parse import urlparse


class ScopeFilter:
    """
    Validates candidate discovered endpoints against an ApplicationScopePolicy.
    Filters out unauthorized domains, excluded paths, and disallowed HTTP methods.
    """

    @classmethod
    def evaluate_endpoints(
        cls,
        endpoints: List[Dict[str, Any]],
        scope_policy: Any
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Filters endpoints based on scope policy rules.
        Returns:
            (in_scope_endpoints, out_of_scope_reasons)
        """
        in_scope: List[Dict[str, Any]] = []
        out_of_scope: List[Dict[str, Any]] = []

        target_domain = getattr(scope_policy, "target_domain", "").strip().lower()
        permitted_paths = getattr(scope_policy, "permitted_paths", ["/*"]) or ["/*"]
        excluded_paths = getattr(scope_policy, "excluded_paths", []) or []
        allowed_methods = [
            m.upper().strip()
            for m in getattr(scope_policy, "allowed_methods", ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
        ]

        for ep in endpoints:
            method = ep.get("method", "GET").upper().strip()
            path = ep.get("path", "/").strip()
            raw_meta = ep.get("raw_metadata", {})
            ep_base_url = raw_meta.get("base_url", "")
            original_path = raw_meta.get("original_path", path)

            # 1. Target Domain Verification
            if ep_base_url and target_domain:
                parsed_base = urlparse(ep_base_url)
                ep_host = (parsed_base.hostname or ep_base_url).split(":")[0].strip().lower()
                if not cls._is_domain_authorized(ep_host, target_domain):
                    out_of_scope.append({
                        "method": method,
                        "path": path,
                        "original_path": original_path,
                        "reason": f"Domain '{ep_host}' is outside authorized domain '{target_domain}'",
                        "category": "DOMAIN_OUT_OF_SCOPE"
                    })
                    continue

            # 2. Allowed HTTP Methods
            if allowed_methods and method not in allowed_methods:
                out_of_scope.append({
                    "method": method,
                    "path": path,
                    "original_path": original_path,
                    "reason": f"HTTP method '{method}' is not in allowed testing methods: {allowed_methods}",
                    "category": "DISALLOWED_METHOD"
                })
                continue

            # 3. Excluded Paths Check (check both normalized path and original path)
            is_excluded = False
            for exc_pat in excluded_paths:
                if cls._match_path(path, exc_pat) or cls._match_path(original_path, exc_pat):
                    out_of_scope.append({
                        "method": method,
                        "path": path,
                        "original_path": original_path,
                        "reason": f"Endpoint matches excluded path pattern '{exc_pat}'",
                        "category": "EXCLUDED_PATH"
                    })
                    is_excluded = True
                    break
            if is_excluded:
                continue

            # 4. Permitted Paths Check
            is_permitted = False
            for perm_pat in permitted_paths:
                if cls._match_path(path, perm_pat) or cls._match_path(original_path, perm_pat):
                    is_permitted = True
                    break

            if not is_permitted:
                out_of_scope.append({
                    "method": method,
                    "path": path,
                    "original_path": original_path,
                    "reason": f"Endpoint does not match any permitted path patterns: {permitted_paths}",
                    "category": "NOT_PERMITTED_PATH"
                })
                continue

            # If all checks pass
            in_scope.append(ep)

        return in_scope, out_of_scope

    @classmethod
    def _is_domain_authorized(cls, host: str, authorized_domain: str) -> bool:
        """Checks if host matches or is a subdomain of authorized domain."""
        if not host or not authorized_domain:
            return True
        host = host.lower().strip()
        authorized_domain = authorized_domain.lower().strip()
        if host == authorized_domain:
            return True
        if host.endswith(f".{authorized_domain}"):
            return True
        # Localhost / IP matches
        if authorized_domain in ("localhost", "127.0.0.1") and host in ("localhost", "127.0.0.1"):
            return True
        return False

    @classmethod
    def _match_path(cls, path: str, pattern: str) -> bool:
        """Matches path against a glob pattern."""
        if not pattern:
            return False
        pattern = pattern.strip()
        if not pattern.startswith("/"):
            pattern = "/" + pattern
        if not path.startswith("/"):
            path = "/" + path
        return fnmatch.fnmatch(path, pattern)

