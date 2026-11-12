# Feature 3: API Inventory & Mapping — API Documentation

**Member 1: Application Intelligence**  
**Module:** PHANTOM-X Application Intelligence  
**Feature:** Feature 3 — API Inventory & Mapping  
**Date:** November 12, 2026  
**Status:** Completed & Active  

---

## 1. Overview of Inventory Endpoints

The API Inventory & Mapping module provides RESTful APIs for inspecting categorized endpoints, querying hierarchical domain resource groups, retrieving dependency graphs, triggering rebuild operations, and exporting inventory data.

Base Path: `/api/v1/inventory` (Alias: `/api/v1/discovery/inventory`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/endpoints` | List categorized endpoints with multi-dimensional filtering and search |
| `GET` | `/resources` | List hierarchical resource groupings for an application |
| `GET` | `/resources/{resource_name}` | Retrieve details for a specific resource group |
| `GET` | `/relationships` | Query endpoint relationship dependencies and provenance |
| `GET` | `/stats` | Retrieve aggregated attack surface metrics and distributions |
| `POST` | `/rebuild` | Trigger full re-classification and relationship reconstruction |
| `GET` | `/export` | Export application inventory in structured JSON or CSV format |

---

## 2. Endpoint Specifications

### 2.1 GET `/api/v1/inventory/endpoints`
List discovered endpoints enriched with logical resource tags, category classifications, confidence scores, and rationales.

**Query Parameters:**
- `app_id` (string, required): Application UUID.
- `resource` (string, optional): Filter by logical resource name (e.g., `users`).
- `category` (string, optional): Filter by API category (`AUTH_IDENTITY`, `USER_MANAGEMENT`, etc.).
- `method` (string, optional): Filter by HTTP method (`GET`, `POST`, `PUT`, `DELETE`, etc.).
- `source` (string, optional): Filter by discovery source (`OPENAPI`, `POSTMAN`, `HAR`).
- `search` (string, optional): Case-insensitive substring match on path, method, or resource.
- `unclassified_only` (boolean, optional, default: `false`): Filter for unclassified endpoints.
- `incomplete_metadata_only` (boolean, optional, default: `false`): Filter endpoints lacking parameters/schemas.
- `skip` (integer, optional, default: `0`): Pagination offset.
- `limit` (integer, optional, default: `100`): Maximum items to return.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Response (200 OK):**
```json
[
  {
    "id": "ep-uuid-1",
    "application_id": "app-uuid-1",
    "path": "/api/v1/users",
    "method": "GET",
    "auth_required": true,
    "parameters": [
      {
        "name": "limit",
        "location": "query",
        "param_type": "integer",
        "required": false
      }
    ],
    "response_codes": [200, 401],
    "risk_level": "LOW",
    "raw_metadata": {
      "resource_name": "users",
      "parent_resource_name": null,
      "category": "USER_MANAGEMENT",
      "category_label": "User Management",
      "category_confidence": 0.9,
      "category_explanation": "Matched user management keyword heuristics and GET operation",
      "category_provenance": "rule-based",
      "discovery_source": "OPENAPI",
      "evidence_classification": "DOCUMENTED"
    },
    "created_at": "2026-11-12T10:00:00Z",
    "updated_at": "2026-11-12T10:00:00Z"
  }
]
```

---

### 2.2 GET `/api/v1/inventory/resources`
List all domain resource entities clustered from discovered endpoints.

**Query Parameters:**
- `app_id` (string, required): Application UUID.

**Response (200 OK):**
```json
[
  {
    "name": "users",
    "parent_resource": null,
    "endpoint_count": 2,
    "endpoint_ids": ["ep-uuid-1", "ep-uuid-2"],
    "methods": ["GET", "POST"],
    "paths": ["/api/v1/users", "/api/v1/users/{id}"],
    "parameters": [
      { "name": "id", "location": "path", "param_type": "string", "required": true }
    ],
    "request_schemas": [
      { "type": "object", "properties": { "name": { "type": "string" } } }
    ],
    "response_schemas": [],
    "related_resources": ["accounts"],
    "discovery_sources": ["OPENAPI"],
    "confidence": 1.0,
    "evidence": "Extracted from OpenAPI path patterns"
  }
]
```

---

### 2.3 GET `/api/v1/inventory/resources/{resource_name}`
Retrieve details for a single logical resource.

**Path Parameters:**
- `resource_name` (string, required): Target resource name (e.g. `users`).

**Query Parameters:**
- `app_id` (string, required): Application UUID.

**Response (200 OK):**
Returns single `ApiResourceGroup` object.
Returns `404 Not Found` if resource does not exist in the application's inventory.

---

### 2.4 GET `/api/v1/inventory/relationships`
Retrieve mapped dependencies between endpoints.

**Query Parameters:**
- `app_id` (string, required): Application UUID.
- `endpoint_id` (string, optional): Filter relationships involving this endpoint.
- `relationship_type` (string, optional): Filter by type (`SAME_RESOURCE`, `PARENT_CHILD`, `READ_WRITE`, `AUTH_DEPENDENCY`, etc.).
- `provenance` (string, optional): Filter by provenance (`OBSERVED`, `DOCUMENTED`, `INFERRED`).
- `skip` (integer, optional, default: `0`): Pagination offset.
- `limit` (integer, optional, default: `200`): Maximum relationships to return.

**Response (200 OK):**
```json
[
  {
    "id": "rel-uuid-1",
    "application_id": "app-uuid-1",
    "source_endpoint_id": "ep-uuid-login",
    "target_endpoint_id": "ep-uuid-users",
    "source_endpoint_path": "/api/v1/auth/login",
    "source_endpoint_method": "POST",
    "target_endpoint_path": "/api/v1/users",
    "target_endpoint_method": "GET",
    "relationship_type": "AUTH_DEPENDENCY",
    "evidence_source": "AUTHENTICATION_PREREQUISITE",
    "confidence": 0.9,
    "explanation": "Target endpoint requires authentication supplied by login",
    "provenance": "INFERRED",
    "raw_metadata": {},
    "created_at": "2026-11-12T10:30:00Z"
  }
]
```

---

### 2.5 GET `/api/v1/inventory/stats`
Computes real-time overview metrics and distributions.

**Query Parameters:**
- `app_id` (string, required): Application UUID.

**Response (200 OK):**
```json
{
  "total_endpoints": 3,
  "unique_resources": 2,
  "method_distribution": {
    "GET": 2,
    "POST": 1
  },
  "category_distribution": {
    "AUTH_IDENTITY": 1,
    "USER_MANAGEMENT": 1,
    "ACCOUNT_MANAGEMENT": 1
  },
  "source_distribution": {
    "OPENAPI": 3
  },
  "documented_count": 3,
  "observed_count": 0,
  "imported_count": 3,
  "inferred_relationships_count": 1,
  "total_relationships_count": 2,
  "unclassified_count": 0,
  "incomplete_metadata_count": 0
}
```

---

### 2.6 POST `/api/v1/inventory/rebuild`
Re-runs the classifier, resource mapper, and relationship builder across all endpoints for the application.

**Query Parameters:**
- `app_id` (string, required): Application UUID.

**Response (200 OK):**
```json
{
  "application_id": "app-uuid-1",
  "endpoints_classified": 3,
  "relationships_created": 2,
  "unique_resources": 2,
  "message": "Successfully classified 3 endpoints and generated 2 relationships across 2 resources."
}
```

---

### 2.7 GET `/api/v1/inventory/export`
Exports inventory in structured format.

**Query Parameters:**
- `app_id` (string, required): Application UUID.
- `format` (string, optional, default: `json`): Export format (`json` or `csv`).

**Response Headers (JSON):**
```
Content-Type: application/json
Content-Disposition: attachment; filename=api_inventory_app-uuid-1.json
```

**Response Headers (CSV):**
```
Content-Type: text/csv; charset=utf-8
Content-Disposition: attachment; filename=api_inventory_app-uuid-1.csv
```
*Note: Any cell starting with `=, +, -, @` is sanitized with a prepended `'` to block spreadsheet formula injection.*

---

## 3. Error Responses

| Status Code | Reason | Example Response Body |
| :---: | :--- | :--- |
| **401 Unauthorized** | Missing or expired JWT bearer token | `{"detail": "Could not validate credentials"}` |
| **403 Forbidden** | Target application is suspended, expired, or out of scope | `{"detail": "Application scope authorization has expired"}` |
| **404 Not Found** | Target application does not exist or belongs to another tenant | `{"detail": "Application not found or unauthorized"}` |
| **422 Unprocessable Content** | Missing required parameters or invalid parameter types | `{"detail": [{"loc": ["query", "app_id"], "msg": "Field required"}]}` |

