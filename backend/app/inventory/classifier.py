import re
from typing import Dict, Any, List, Optional, Tuple


class ApiCategory:
    AUTH_IDENTITY = "AUTH_IDENTITY"
    USER_MANAGEMENT = "USER_MANAGEMENT"
    ACCOUNT_MANAGEMENT = "ACCOUNT_MANAGEMENT"
    ADMIN_OPERATIONS = "ADMIN_OPERATIONS"
    FILE_MANAGEMENT = "FILE_MANAGEMENT"
    PAYMENT_TRANSACTION = "PAYMENT_TRANSACTION"
    DATA_RETRIEVAL = "DATA_RETRIEVAL"
    DATA_MODIFICATION = "DATA_MODIFICATION"
    REPORTING_ANALYTICS = "REPORTING_ANALYTICS"
    UNCLASSIFIED = "UNCLASSIFIED"


CATEGORY_LABELS = {
    ApiCategory.AUTH_IDENTITY: "Authentication and Identity",
    ApiCategory.USER_MANAGEMENT: "User Management",
    ApiCategory.ACCOUNT_MANAGEMENT: "Account Management",
    ApiCategory.ADMIN_OPERATIONS: "Administrative Operations",
    ApiCategory.FILE_MANAGEMENT: "File and Document Management",
    ApiCategory.PAYMENT_TRANSACTION: "Payment and Transaction Operations",
    ApiCategory.DATA_RETRIEVAL: "Data Retrieval",
    ApiCategory.DATA_MODIFICATION: "Data Modification",
    ApiCategory.REPORTING_ANALYTICS: "Reporting and Analytics",
    ApiCategory.UNCLASSIFIED: "Other / Unclassified",
}


TAG_CATEGORY_MAPPING = {
    "auth": ApiCategory.AUTH_IDENTITY,
    "authentication": ApiCategory.AUTH_IDENTITY,
    "identity": ApiCategory.AUTH_IDENTITY,
    "oauth": ApiCategory.AUTH_IDENTITY,
    "login": ApiCategory.AUTH_IDENTITY,
    "users": ApiCategory.USER_MANAGEMENT,
    "user": ApiCategory.USER_MANAGEMENT,
    "user management": ApiCategory.USER_MANAGEMENT,
    "members": ApiCategory.USER_MANAGEMENT,
    "profiles": ApiCategory.USER_MANAGEMENT,
    "roles": ApiCategory.USER_MANAGEMENT,
    "accounts": ApiCategory.ACCOUNT_MANAGEMENT,
    "account": ApiCategory.ACCOUNT_MANAGEMENT,
    "organizations": ApiCategory.ACCOUNT_MANAGEMENT,
    "organization": ApiCategory.ACCOUNT_MANAGEMENT,
    "tenants": ApiCategory.ACCOUNT_MANAGEMENT,
    "tenant": ApiCategory.ACCOUNT_MANAGEMENT,
    "settings": ApiCategory.ACCOUNT_MANAGEMENT,
    "admin": ApiCategory.ADMIN_OPERATIONS,
    "administration": ApiCategory.ADMIN_OPERATIONS,
    "system": ApiCategory.ADMIN_OPERATIONS,
    "internal": ApiCategory.ADMIN_OPERATIONS,
    "files": ApiCategory.FILE_MANAGEMENT,
    "file": ApiCategory.FILE_MANAGEMENT,
    "documents": ApiCategory.FILE_MANAGEMENT,
    "uploads": ApiCategory.FILE_MANAGEMENT,
    "attachments": ApiCategory.FILE_MANAGEMENT,
    "media": ApiCategory.FILE_MANAGEMENT,
    "payments": ApiCategory.PAYMENT_TRANSACTION,
    "payment": ApiCategory.PAYMENT_TRANSACTION,
    "billing": ApiCategory.PAYMENT_TRANSACTION,
    "invoices": ApiCategory.PAYMENT_TRANSACTION,
    "subscriptions": ApiCategory.PAYMENT_TRANSACTION,
    "checkout": ApiCategory.PAYMENT_TRANSACTION,
    "orders": ApiCategory.PAYMENT_TRANSACTION,
    "transactions": ApiCategory.PAYMENT_TRANSACTION,
    "reports": ApiCategory.REPORTING_ANALYTICS,
    "reporting": ApiCategory.REPORTING_ANALYTICS,
    "analytics": ApiCategory.REPORTING_ANALYTICS,
    "metrics": ApiCategory.REPORTING_ANALYTICS,
    "telemetry": ApiCategory.REPORTING_ANALYTICS,
    "audit": ApiCategory.REPORTING_ANALYTICS,
}

PATH_KEYWORD_RULES: List[Tuple[str, List[str], float]] = [
    (
        ApiCategory.AUTH_IDENTITY,
        [
            r"\bauth\b", r"\blogin\b", r"\blogout\b", r"\boauth\b", r"\btoken\b",
            r"\bsignup\b", r"\bsignin\b", r"\bpassword\b", r"\bsession\b",
            r"\bregister\b", r"\bmfa\b", r"\b2fa\b", r"\bsso\b", r"\bjwt\b",
            r"\bverify-email\b", r"\breset-password\b"
        ],
        0.85
    ),
    (
        ApiCategory.ADMIN_OPERATIONS,
        [
            r"\badmin\b", r"\badministration\b", r"\bsuperadmin\b", r"\bsysadmin\b",
            r"\bmaintenance\b", r"\bmanage\b", r"\bhealthcheck\b", r"\bdiagnostics\b"
        ],
        0.85
    ),
    (
        ApiCategory.PAYMENT_TRANSACTION,
        [
            r"\bpayment\b", r"\bpayments\b", r"\bbill\b", r"\bbilling\b",
            r"\binvoice\b", r"\binvoices\b", r"\bcheckout\b", r"\btransaction\b",
            r"\btransactions\b", r"\bsubscription\b", r"\bsubscriptions\b",
            r"\bstripe\b", r"\bpaypal\b", r"\bcharge\b", r"\bwallet\b"
        ],
        0.85
    ),
    (
        ApiCategory.FILE_MANAGEMENT,
        [
            r"\bfile\b", r"\bfiles\b", r"\bdocument\b", r"\bdocuments\b",
            r"\bupload\b", r"\buploads\b", r"\bdownload\b", r"\bdownloads\b",
            r"\battachment\b", r"\battachments\b", r"\bmedia\b", r"\basset\b",
            r"\bassets\b", r"\bblob\b"
        ],
        0.85
    ),
    (
        ApiCategory.REPORTING_ANALYTICS,
        [
            r"\breport\b", r"\breports\b", r"\banalytic\b", r"\banalytics\b",
            r"\bmetric\b", r"\bmetrics\b", r"\btelemetry\b", r"\baudit-log\b",
            r"\baudit-logs\b", r"\binsight\b", r"\binsights\b", r"\bdashboard\b"
        ],
        0.85
    ),
    (
        ApiCategory.USER_MANAGEMENT,
        [
            r"\buser\b", r"\busers\b", r"\bmember\b", r"\bmembers\b",
            r"\bprofile\b", r"\bprofiles\b", r"\binvitation\b", r"\binvitations\b",
            r"\brole\b", r"\broles\b", r"\bpermission\b", r"\bpermissions\b"
        ],
        0.80
    ),
    (
        ApiCategory.ACCOUNT_MANAGEMENT,
        [
            r"\baccount\b", r"\baccounts\b", r"\borganization\b", r"\borganizations\b",
            r"\borg\b", r"\borgs\b", r"\btenant\b", r"\btenants\b", r"\bworkspace\b",
            r"\bworkspaces\b", r"\bsetting\b", r"\bsettings\b", r"\bpreference\b"
        ],
        0.80
    ),
    (
        ApiCategory.DATA_RETRIEVAL,
        [
            r"\bsearch\b", r"\bquery\b", r"\bfilter\b", r"\bexport\b",
            r"\bfetch\b", r"\bfind\b", r"\bcatalog\b", r"\bbrowse\b"
        ],
        0.75
    ),
    (
        ApiCategory.DATA_MODIFICATION,
        [
            r"\bbulk\b", r"\bbatch\b", r"\bsync\b", r"\bimport\b",
            r"\bmutate\b", r"\bpatch\b"
        ],
        0.75
    ),
]


class ApiClassifier:
    """
    Classifies API endpoints into domain categories using source-declared tags,
    path structures, HTTP methods, and operational context with confidence scoring.
    """

    @classmethod
    def classify(
        cls,
        path: str,
        method: str,
        tags: Optional[List[str]] = None,
        operation_id: Optional[str] = None,
        description: Optional[str] = None,
        parameters: Optional[List[Dict[str, Any]]] = None,
        raw_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates an endpoint and returns a classification dictionary:
        {
            "category": str,
            "category_label": str,
            "confidence": float,
            "explanation": str,
            "provenance": "source-declared" | "rule-based" | "ai-assisted"
        }
        """
        raw_metadata = raw_metadata or {}
        tags = tags or raw_metadata.get("tags", [])
        operation_id = operation_id or raw_metadata.get("operation_id")
        description = description or raw_metadata.get("description")
        method_upper = (method or "GET").upper()
        clean_path = path.lower().replace("-", " ").replace("_", " ").replace("/", " ")

        # 1. Source-declared tags check (highest confidence)
        if tags:
            for tag in tags:
                tag_lower = tag.lower().strip()
                if tag_lower in TAG_CATEGORY_MAPPING:
                    cat = TAG_CATEGORY_MAPPING[tag_lower]
                    return {
                        "category": cat,
                        "category_label": CATEGORY_LABELS[cat],
                        "confidence": 0.95,
                        "explanation": f"Source-declared in specification tag '{tag}'",
                        "provenance": "source-declared"
                    }

        # 2. Rule-based path and operation ID pattern matching
        op_text = f"{clean_path} {(operation_id or '').lower()} {(description or '').lower()}"

        for cat, patterns, base_conf in PATH_KEYWORD_RULES:
            matched_keywords = []
            for pat in patterns:
                if re.search(pat, op_text):
                    clean_keyword = pat.replace(r"\b", "").strip()
                    matched_keywords.append(clean_keyword)

            if matched_keywords:
                # Adjust confidence if operation_id corroborated
                conf = base_conf
                if operation_id and any(kw in operation_id.lower() for kw in matched_keywords):
                    conf = min(0.90, base_conf + 0.05)

                kw_str = ", ".join(f"'{k}'" for k in matched_keywords[:3])
                return {
                    "category": cat,
                    "category_label": CATEGORY_LABELS[cat],
                    "confidence": round(conf, 2),
                    "explanation": f"Matched pattern keywords {kw_str} in path or operation",
                    "provenance": "rule-based"
                }

        # 3. Fallback heuristic based on HTTP method and path purpose
        if method_upper in ("GET", "HEAD") and any(w in clean_path for w in ["list", "search", "all", "items"]):
            return {
                "category": ApiCategory.DATA_RETRIEVAL,
                "category_label": CATEGORY_LABELS[ApiCategory.DATA_RETRIEVAL],
                "confidence": 0.70,
                "explanation": f"HTTP {method_upper} read operation on data collection",
                "provenance": "rule-based"
            }

        if method_upper in ("POST", "PUT", "PATCH", "DELETE") and any(w in clean_path for w in ["bulk", "update", "batch", "import"]):
            return {
                "category": ApiCategory.DATA_MODIFICATION,
                "category_label": CATEGORY_LABELS[ApiCategory.DATA_MODIFICATION],
                "confidence": 0.70,
                "explanation": f"HTTP {method_upper} write/mutation operation on data entity",
                "provenance": "rule-based"
            }

        # 4. Strictly unclassified when no evidence exists
        return {
            "category": ApiCategory.UNCLASSIFIED,
            "category_label": CATEGORY_LABELS[ApiCategory.UNCLASSIFIED],
            "confidence": 0.0,
            "explanation": "No category keywords, operation patterns, or specification tags matched",
            "provenance": "rule-based"
        }

