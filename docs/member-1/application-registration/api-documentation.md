# Member 1 — Feature 1: Application Registration | API Documentation

## 1. Overview & General Principles

- **Base Path**: `/api/v1/applications`
- **Module**: Member 1 — Application Intelligence & Scope Safety
- **Content Type**: `application/json`
- **Security Scheme**: HTTP Bearer JWT Authentication (`Authorization: Bearer <jwt_token>`)
- **Tenant Scope**: All operations are strictly sandboxed to the caller's `organization_id` derived directly from the authenticated JWT token.

---

## 2. Endpoints Summary

| Method | Endpoint | Description | Status Codes |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/applications/` | Register target application & scope policy | `201`, `400`, `401`, `409`, `422` |
| `GET` | `/api/v1/applications/` | List organization applications with search & filter | `200`, `401` |
| `GET` | `/api/v1/applications/{app_id}` | Retrieve application details & scope policy | `200`, `401`, `404` |
| `PUT` | `/api/v1/applications/{app_id}` | Update application details & scope policy | `200`, `400`, `401`, `404`, `409` |
| `PATCH` | `/api/v1/applications/{app_id}` | Partially update application & scope policy | `200`, `400`, `401`, `404`, `409` |
| `DELETE` | `/api/v1/applications/{app_id}` | Delete application, environments, & scope policy | `204`, `401`, `404` |
| `GET` | `/api/v1/applications/{app_id}/scope` | Retrieve authorized testing scope boundaries | `200`, `401`, `404` |

---

## 3. Detailed Endpoint Specifications

### 3.1 Register Application
`POST /api/v1/applications/`

Registers a new target application, provisions its environment, creates its authorized scope policy, and records an audit log event.

#### Headers
- `Authorization: Bearer <token>` (Required)
- `Content-Type: application/json`

#### Request Body (`ApplicationCreate`)
```json
{
  "name": "E-Commerce Core API",
  "description": "Production staging gateway for store services",
  "target_url": "https://staging-api.example.com",
  "environment_name": "staging",
  "permitted_paths": [
    "/api/v1/*",
    "/health"
  ],
  "excluded_paths": [
    "/api/v1/admin/*",
    "/api/v1/auth/reset-password"
  ],
  "allowed_methods": ["GET", "POST", "PUT", "PATCH", "DELETE"],
  "max_requests_per_second": 25,
  "safe_mode_enabled": true,
  "confirm_authorization": true
}
```

#### Field Validation Rules
- `name`: string, 1–255 characters, required. Must be unique within the organization.
- `description`: string, optional.
- `target_url`: string, required. Must be a valid URL with scheme `http` or `https`, non-empty host, and port between 1–65535.
- `environment_name`: string (`development`, `staging`, `production`, `sandbox`), defaults to `staging`.
- `permitted_paths`: list of strings. If omitted, defaults to `["/*"]`.
- `excluded_paths`: list of strings. Defaults to `[]`.
- `allowed_methods`: list of strings. Must belong to standard HTTP methods (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `HEAD`, `OPTIONS`).
- `max_requests_per_second`: integer, 1–1000, defaults to 50.
- `safe_mode_enabled`: boolean, defaults to `true`.
- `confirm_authorization`: boolean, **must be true**.

#### Response (`201 Created`)
```json
{
  "id": "e4b17697-3bb2-4f27-a026-646e7f27efaa",
  "organization_id": "90e6ba0e-faee-4613-a447-fdf05b5fdb33",
  "name": "E-Commerce Core API",
  "description": "Production staging gateway for store services",
  "target_url": "https://staging-api.example.com",
  "status": "ACTIVE",
  "risk_score": 0.0,
  "environment_name": "staging",
  "scope": {
    "target_domains": ["staging-api.example.com"],
    "permitted_paths": ["/api/v1/*", "/health"],
    "excluded_paths": ["/api/v1/admin/*", "/api/v1/auth/reset-password"],
    "allowed_methods": ["GET", "POST", "PUT", "PATCH", "DELETE"],
    "max_requests_per_second": 25,
    "require_synthetic_auth": true,
    "allow_destructive": false,
    "safe_mode_enabled": true,
    "scope_status": "ACTIVE",
    "authorization_status": "AUTHORIZED",
    "valid_until_utc": null
  },
  "created_at": "2026-11-12T13:45:00Z",
  "updated_at": "2026-11-12T13:45:00Z"
}
```

---

### 3.2 List Applications
`GET /api/v1/applications/`

Lists registered applications for the caller's organization.

#### Query Parameters
- `skip`: integer, default `0`.
- `limit`: integer, default `100`, max `500`.
- `search`: string, optional. Filters by case-insensitive name or target URL.
- `status`: string, optional. Filters by application status (`ACTIVE`, `INACTIVE`, `ARCHIVED`).

#### Response (`200 OK`)
```json
[
  {
    "id": "e4b17697-3bb2-4f27-a026-646e7f27efaa",
    "organization_id": "90e6ba0e-faee-4613-a447-fdf05b5fdb33",
    "name": "E-Commerce Core API",
    "description": "Production staging gateway for store services",
    "target_url": "https://staging-api.example.com",
    "status": "ACTIVE",
    "risk_score": 0.0,
    "environment_name": "staging",
    "scope": {
      "target_domains": ["staging-api.example.com"],
      "permitted_paths": ["/api/v1/*", "/health"],
      "excluded_paths": ["/api/v1/admin/*"],
      "allowed_methods": ["GET", "POST", "PUT"],
      "max_requests_per_second": 25,
      "require_synthetic_auth": true,
      "allow_destructive": false,
      "safe_mode_enabled": true,
      "scope_status": "ACTIVE",
      "authorization_status": "AUTHORIZED",
      "valid_until_utc": null
    },
    "created_at": "2026-11-12T13:45:00Z",
    "updated_at": "2026-11-12T13:45:00Z"
  }
]
```

---

### 3.3 Get Application Details
`GET /api/v1/applications/{application_id}`

Retrieves details, environments, and scope policy for an application.

#### Path Parameters
- `application_id`: UUID string.

#### Response (`200 OK`)
Returns the complete `ApplicationResponse` object.

#### Error Responses
- `404 Not Found`: If application ID does not exist or belongs to another organization.

---

### 3.4 Update Application
`PUT /api/v1/applications/{application_id}`
`PATCH /api/v1/applications/{application_id}`

Updates application metadata, target URL, and scope policy parameters.

#### Request Body (`ApplicationUpdate`)
```json
{
  "name": "E-Commerce Core API (v2)",
  "description": "Updated description",
  "target_url": "https://staging-v2.example.com",
  "status": "ACTIVE",
  "environment_name": "staging",
  "permitted_paths": ["/api/v2/*"],
  "excluded_paths": ["/api/v2/admin/*"],
  "allowed_methods": ["GET", "POST", "PUT"],
  "max_requests_per_second": 40,
  "safe_mode_enabled": true
}
```

#### Response (`200 OK`)
Returns the updated `ApplicationResponse` object.

---

### 3.5 Delete Application
`DELETE /api/v1/applications/{application_id}`

Irreversibly deletes the application and cascades deletion of its environments and scope policies. Associated `audit_logs` entries are permanently preserved.

#### Response (`204 No Content`)
Empty body.

#### Error Responses
- `404 Not Found`: If application does not exist or belongs to another organization.

---

### 3.6 Get Application Scope
`GET /api/v1/applications/{application_id}/scope`

Retrieves testing scope boundaries, rate limits, and authorization flags. Designed for direct consumption by Feature 2 Discovery and subsequent scanner modules.

#### Response (`200 OK`)
```json
{
  "target_domains": ["staging-api.example.com"],
  "permitted_paths": ["/api/v1/*"],
  "excluded_paths": ["/api/v1/admin/*"],
  "allowed_methods": ["GET", "POST", "PUT"],
  "max_requests_per_second": 25,
  "require_synthetic_auth": true,
  "allow_destructive": false,
  "safe_mode_enabled": true,
  "scope_status": "ACTIVE",
  "authorization_status": "AUTHORIZED",
  "valid_until_utc": null
}
```

---

## 4. Standard Error Responses

### Missing Fields (`422 Unprocessable Content`)
```json
{
  "detail": [
    {
      "loc": ["body", "target_url"],
      "msg": "Field required",
      "type": "missing"
    }
  ]
}
```

### Invalid Target URL (`400 Bad Request`)
```json
{
  "detail": "Invalid target URL: scheme must be http or https"
}
```

### Missing Explicit Authorization (`400 Bad Request`)
```json
{
  "detail": "Explicit testing authorization confirmation is required to register an application target."
}
```

### Name Conflict within Organization (`409 Conflict`)
```json
{
  "detail": "Application with this name already exists in your organization"
}
```

### Cross-Tenant Access (`404 Not Found`)
```json
{
  "detail": "Application not found"
}
```
*(Returns 404 rather than 403 to prevent attackers from discovering other tenant IDs).*

