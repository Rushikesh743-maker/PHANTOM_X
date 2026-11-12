# PHANTOM-X | Member 1 — Feature 2: API Endpoint Discovery
## API Specification & Reference

- **Author**: Member 1 (Application Intelligence)
- **Module**: Application Intelligence & Security Discovery
- **Feature**: Feature 2 — API Endpoint Discovery
- **Status**: Active & Verified
- **Base Route**: `/api/v1/discovery`

---

## 1. Authentication & Tenant Isolation

All Discovery API routes require standard JWT Bearer token authentication:
```http
Authorization: Bearer <access_token>
```
The authenticated user's `organization_id` is extracted via dependency injection (`get_current_user`). Any request attempting to query, trigger, import, or delete endpoints for an application belonging to a different tenant organization returns `404 Not Found` to prevent metadata leakage.

---

## 2. API Endpoints Reference

### 2.1 Trigger Discovery Job
Dispatches an asynchronous discovery job using document parsing, passive traffic analysis, or the AI Discovery Agent.

- **Method**: `POST`
- **Path**: `/api/v1/discovery/trigger`
- **Request Headers**:
  - `Content-Type: application/json`
  - `Authorization: Bearer <token>`
- **Request Body** (`DiscoveryTriggerRequest`):
  ```json
  {
    "application_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "source_type": "openapi",
    "raw_payload": "{\"openapi\": \"3.0.0\", ...}",
    "scope_override": {},
    "parameters": {
      "include_observed": true
    }
  }
  ```
- **Responses**:
  - `200 OK`: Job created and initiated.
    ```json
    {
      "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "application_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "source_type": "openapi",
      "status": "COMPLETED",
      "endpoints_found": 12,
      "endpoints_in_scope": 10,
      "endpoints_out_of_scope": 2,
      "error_message": null,
      "diagnostic_summary": {
        "rejected_endpoints": [
          {"path": "/admin/delete", "method": "POST", "reason": "excluded_path_prefix"}
        ]
      },
      "started_at": "2026-11-12T14:30:00Z",
      "completed_at": "2026-11-12T14:30:01Z",
      "created_at": "2026-11-12T14:30:00Z"
    }
    ```
  - `400 Bad Request`: Invalid payload or missing parameters.
  - `403 Forbidden`: Application testing scope is inactive, unauthorized, or expired.
  - `404 Not Found`: Application does not exist or belongs to another tenant.

---

### 2.2 Import OpenAPI Specification
Ingests Swagger 2.0 or OpenAPI 3.0/3.1 specifications in JSON or YAML format.

- **Method**: `POST`
- **Path**: `/api/v1/discovery/import/openapi`
- **Request Body** (`DiscoveryImportRequest`):
  ```json
  {
    "application_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "raw_content": "openapi: 3.0.0\ninfo:\n  title: Sample API\n  version: 1.0.0\npaths:\n  /api/v1/users:\n    get:\n      responses:\n        '200':\n          description: OK",
    "file_format": "yaml",
    "options": {}
  }
  ```
- **Responses**:
  - `200 OK`:
    ```json
    {
      "job_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "application_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "status": "COMPLETED",
      "total_discovered": 1,
      "in_scope_count": 1,
      "out_of_scope_count": 0,
      "rejected_endpoints": [],
      "sample_endpoints": [
        {
          "id": "e0a39745-9851-4f15-81fa-f4d0d8eb230a",
          "application_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
          "path": "/api/v1/users",
          "method": "GET",
          "source": "openapi",
          "risk_level": "LOW",
          "parameters": [],
          "response_codes": [200],
          "requires_auth": false,
          "raw_metadata": {"provenance": "documented", "original_path": "/api/v1/users"},
          "first_seen_at": "2026-11-12T14:30:00Z",
          "last_seen_at": "2026-11-12T14:30:00Z"
        }
      ]
    }
    ```
  - `403 Forbidden`: Application expired or unauthorized.
  - `422 Unprocessable Entity`: Corrupted or invalid OpenAPI structure.

---

### 2.3 Import Postman Collection
Ingests Postman Collection v2.0 or v2.1 in JSON format.

- **Method**: `POST`
- **Path**: `/api/v1/discovery/import/postman`
- **Request Body** (`DiscoveryImportRequest`):
  ```json
  {
    "application_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "raw_content": "{\"info\": {\"name\": \"My Collection\", \"schema\": \"https://schema.getpostman.com/json/collection/v2.1.0/collection.json\"}, \"item\": [...]}",
    "file_format": "json"
  }
  ```
- **Responses**:
  - `200 OK`: `DiscoverySummaryResponse`
  - `422 Unprocessable Entity`: Invalid Postman JSON schema.

---

### 2.4 Import HAR Traffic Log
Ingests HTTP Archive (`.har`) recorded traffic, discarding static assets and capturing live response evidence.

- **Method**: `POST`
- **Path**: `/api/v1/discovery/import/har`
- **Request Body** (`DiscoveryImportRequest`):
  ```json
  {
    "application_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "raw_content": "{\"log\": {\"entries\": [...]}}",
    "file_format": "json"
  }
  ```
- **Responses**:
  - `200 OK`: `DiscoverySummaryResponse`
  - `422 Unprocessable Entity`: Invalid HAR log structure.

---

### 2.5 List Discovered Endpoints
Lists normalized endpoints for an application with filtering, sorting, and pagination.

- **Method**: `GET`
- **Path**: `/api/v1/discovery/endpoints`
- **Query Parameters**:
  - `app_id` (UUID, optional): Filter by application.
  - `method` (string, optional): Filter by HTTP verb (`GET`, `POST`, etc.).
  - `path` (string, optional): Substring filter on endpoint path.
  - `search` (string, optional): General text search across path and metadata.
  - `risk_level` (string, optional): Filter by risk level (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
  - `source` (string, optional): Filter by source (`openapi`, `postman`, `har`, `passive`).
  - `skip` (integer, default `0`): Pagination offset.
  - `limit` (integer, default `100`, max `500`): Maximum records to return.
- **Responses**:
  - `200 OK`: Array of `EndpointResponse` objects.

---

### 2.6 Get Endpoint by ID
Retrieves complete details for a single discovered endpoint.

- **Method**: `GET`
- **Path**: `/api/v1/discovery/endpoints/{id}`
- **Responses**:
  - `200 OK`: `EndpointResponse` object.
  - `404 Not Found`: Endpoint does not exist or belongs to another tenant.

---

### 2.7 Delete Discovered Endpoint
Removes a specific endpoint from the active attack surface inventory.

- **Method**: `DELETE`
- **Path**: `/api/v1/discovery/endpoints/{id}`
- **Responses**:
  - `200 OK`:
    ```json
    {
      "message": "Endpoint successfully deleted",
      "id": "e0a39745-9851-4f15-81fa-f4d0d8eb230a"
    }
    ```
  - `404 Not Found`: Endpoint does not exist or unauthorized.

---

### 2.8 List Discovery Jobs
Lists execution history for discovery jobs.

- **Method**: `GET`
- **Path**: `/api/v1/discovery/jobs`
- **Query Parameters**:
  - `app_id` (UUID, optional): Filter by application.
  - `status` (string, optional): Filter by status (`PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`).
  - `skip` (integer, default `0`).
  - `limit` (integer, default `50`).
- **Responses**:
  - `200 OK`: Array of `DiscoveryJobResponse` objects.

---

### 2.9 Get Discovery Job by ID
- **Method**: `GET`
- **Path**: `/api/v1/discovery/jobs/{job_id}`
- **Responses**:
  - `200 OK`: `DiscoveryJobResponse`
  - `404 Not Found`: Job does not exist or belongs to another tenant.

---

### 2.10 Cancel Discovery Job
- **Method**: `POST`
- **Path**: `/api/v1/discovery/jobs/{job_id}/cancel`
- **Responses**:
  - `200 OK`: Updated `DiscoveryJobResponse` with status `CANCELLED`.
  - `404 Not Found`: Job does not exist or unauthorized.

---

## 3. Scope Safety Violation Diagnostic Schema

When endpoints are filtered out during ingestion or triggering, the API returns a structured diagnostic report in `rejected_endpoints`:

```json
{
  "path": "/admin/delete-database",
  "method": "POST",
  "reason": "excluded_path_prefix"
}
```

Standard reason codes include:
- `excluded_path_prefix`: Matches one of the application's configured `excluded_paths`.
- `disallowed_http_method`: The HTTP verb is omitted from `allowed_methods`.
- `out_of_scope_host`: Target URL host does not match permitted host patterns.
- `not_in_permitted_paths`: Path does not fall under any prefix in `permitted_paths`.

