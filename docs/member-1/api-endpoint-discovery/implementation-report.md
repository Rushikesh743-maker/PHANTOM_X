# PHANTOM-X | Member 1 — Feature 2: API Endpoint Discovery
## Implementation Report

- **Author**: Member 1 (Application Intelligence)
- **Module**: Application Intelligence & Security Discovery
- **Feature**: Feature 2 — API Endpoint Discovery
- **Status**: Completed & Verified
- **Date**: 2026-11-12

---

## 1. Executive Summary

Feature 2 (API Endpoint Discovery) implements an automated, secure, and multi-format API endpoint ingestion, normalization, validation, and inventory system. Building upon the foundational tenant-isolated Application Registration and Scope Policy infrastructure delivered in Feature 1, Feature 2 allows organizations to populate their authorized attack surface inventory through structured imports (OpenAPI/Swagger, Postman Collections, and HTTP Archives) and triggered discovery jobs.

Every discovered endpoint undergoes strict scope evaluation against the target application's active security policy, canonical path normalization, parameter and response schema deduplication, and forensic audit logging. Out-of-scope endpoints are rejected with explicit diagnostic reasons, ensuring that downstream scanning (Member 2) and orchestration (Member 4) operate exclusively within verified legal boundaries.

---

## 2. Architecture & Pipeline Overview

The Discovery pipeline follows a multi-stage ingestion, validation, normalization, and persistence model:

```
[Import Payload / Trigger Request]
               │
               ▼
   [Tenant & Auth Enforcement] ──► Rejects cross-tenant / unauthenticated calls
               │
               ▼
    [Scope & Expiry Guard]    ──► Rejects UNAPPROVED, INACTIVE, or EXPIRED apps
               │
               ▼
    [Multi-Format Parsers]     ──► Extracts Candidate Endpoints
    ├─ OpenAPI (v2, v3, v3.1)
    ├─ Postman (v2.0, v2.1)
    └─ HAR Traffic Logs
               │
               ▼
     [Scope Safety Filter]    ──► Filters by permitted paths, excluded paths,
               │                  allowed methods, and host constraints
               ▼
    [Endpoint Normalizer]     ──► Canonicalizes paths (e.g. /users/123 -> /users/{id})
               │
               ▼
  [Deduplication & Merger]    ──► Upserts on (application_id, method, normalized_path)
               │                  merging parameters, response codes, and evidence
               ▼
   [Persistence & Audit Log]  ──► Stores DiscoveredEndpoint & DiscoveryJob records
```

---

## 3. Detailed Component Implementation

### 3.1 Multi-Format Discovery Parsers

All parsers are implemented in `security-engine/discovery/parsers/` and mirrored in `backend/app/discovery/parsers/`:

1. **OpenAPI / Swagger Parser (`openapi_parser.py`)**:
   - Supports Swagger 2.0, OpenAPI 3.0.x, and OpenAPI 3.1.x in both JSON and YAML encodings.
   - Extracts server/base paths, operations, HTTP methods, operation IDs, summaries, and descriptions.
   - Parses path parameters, query parameters, header parameters, and cookie parameters.
   - Extracts request body schemas and declared HTTP response status codes.
   - Tags endpoints with `source="openapi"` and `provenance="documented"`.

2. **Postman Collection Parser (`postman_parser.py`)**:
   - Supports Postman Collection format v2.0 and v2.1.
   - Recursively traverses nested folders, tracking folder hierarchy as tags.
   - Replaces collection variable syntax (e.g., `{{baseUrl}}`, `{{userId}}`) with normalized path templates.
   - Extracts query parameters, raw/form request bodies, and headers.
   - Tags endpoints with `source="postman"` and `provenance="imported"`.

3. **HTTP Archive (HAR) Parser (`har_parser.py`)**:
   - Ingests standard `.har` network traffic dumps recorded during authorized application navigation.
   - Discards non-API static asset requests by evaluating MIME types (e.g., images, stylesheets, scripts, fonts) and file extensions (`.css`, `.js`, `.png`, `.jpg`, `.svg`, `.ico`, `.woff2`).
   - Extracts HTTP method, full request URL, path, observed query parameters, request headers, cookies, and actual HTTP response status codes.
   - Preserves original observed URLs and response codes as concrete empirical evidence.
   - Tags endpoints with `source="har"` and `provenance="observed"`.

### 3.2 Canonical Path Normalizer (`normalizer.py`)

- **Class**: `EndpointNormalizer`
- **Path Cleaning**: Normalizes leading/trailing slashes, strips query strings and fragments, and resolves redundant relative components (`/a/../b`).
- **Dynamic Parameter Canonicalization**:
  - Automatically identifies numeric IDs (`/accounts/12345` -> `/accounts/{id}`).
  - Automatically identifies UUIDs/GUIDs (`/orders/550e8400-e29b-41d4-a716-446655440000` -> `/orders/{id}`).
  - Preserves explicit OpenAPI/Postman template variables (`{user_id}`, `:accountId`).
- **Evidence Tracking**: Stores the original raw path and an aggregated list of distinct observed paths in `raw_metadata` (`original_path`, `observed_paths`).

### 3.3 Scope Safety Enforcement (`scope_filter.py`)

- **Class**: `ScopeFilter`
- **Application Expiry & Status Verification**:
  - Dynamically verifies that the target application has an `ACTIVE` scope policy and `AUTHORIZED` status.
  - Dynamically evaluates policy validity against the current UTC timestamp (`valid_until < datetime.now(timezone.utc)`), immediately failing expired applications with HTTP 403 Forbidden.
- **Path Prefix Matching**:
  - Evaluates candidate paths against `permitted_paths` (default `/` allows all under domain).
  - Evaluates candidate paths against `excluded_paths` (e.g., `/admin`, `/auth/logout`, `/internal/metrics`). Any match causes an immediate rejection.
- **Method Filtering**:
  - Verifies that the endpoint's HTTP method is included in `allowed_methods`.
- **Domain/Host Boundary**:
  - Compares request host against the application's target URL host and any explicitly declared target domain scopes. Rejects out-of-scope third-party origins.
- **Diagnostic Reporting**:
  - Returns a detailed dictionary of rejected endpoints accompanied by specific diagnostic reasons (`excluded_path_prefix`, `disallowed_http_method`, `out_of_scope_host`, `not_in_permitted_paths`).
- **Strictly Non-Destructive**:
  - All discovery operations are purely passive ingestion, document parsing, or read-only interrogation. No active exploitation, fuzzing payloads, or credential cracking is executed during discovery.

### 3.4 Deduplication & Merging Engine (`discovery_service.py`)

- **Composite Deduplication Key**: `(application_id, method.upper(), normalized_path)`
- **Persistence Strategy**:
  - If the endpoint does not exist in `discovered_endpoints`, it is inserted with initial parameter schemas, response status codes, and source metadata.
  - If the endpoint already exists:
    - Merges newly discovered parameters (combining path, query, header, and body definitions).
    - Unifies response status codes (e.g., merging `[200]` with `[404, 500]` into `[200, 404, 500]`).
    - Updates `last_seen_at` timestamp.
    - Appends unique path instances to `raw_metadata["observed_paths"]`.
    - Preserves primary provenance while recording multi-source corroboration in `raw_metadata["sources"]`.

### 3.5 Database & Migration Layer

1. **`DiscoveryJob` Model (`backend/app/models/endpoint.py`)**:
   - Table name: `discovery_jobs`
   - Fields: `id` (UUID), `application_id` (FK to applications.id), `source_type` (Enum), `status` (Enum: PENDING, RUNNING, COMPLETED, FAILED, CANCELLED), `endpoints_found` (Integer), `endpoints_in_scope` (Integer), `endpoints_out_of_scope` (Integer), `error_message` (Text), `diagnostic_summary` (JSON), `started_at` (DateTime), `completed_at` (DateTime), `created_at` (DateTime).
   - Relationship: Linked to `Application.discovery_jobs` with cascade deletion.
2. **`DiscoveredEndpoint` Model Enhancements**:
   - Fields: `application_id`, `path`, `method`, `source`, `risk_level`, `parameters`, `response_codes`, `requires_auth`, `raw_metadata`, `first_seen_at`, `last_seen_at`.
   - Indexing: `ix_discovered_endpoints_app_path_method` for rapid deduplication lookups.
3. **Alembic Migration**:
   - Migration `009_discovery_jobs.py` creates table `discovery_jobs`, indexes on `application_id` and `status`, and foreign key constraints.

### 3.6 REST API Endpoints (`backend/app/api/v1/endpoints/discovery.py`)

| Method | Path | Description | Security / Scope Guard |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/discovery/trigger` | Triggers a discovery job via source or AI agent | Requires active tenant, authorized active scope |
| `POST` | `/api/v1/discovery/import/openapi` | Ingests OpenAPI 2/3 JSON or YAML | Validates tenant, scope, normalizes & upserts |
| `POST` | `/api/v1/discovery/import/postman` | Ingests Postman Collection v2.x JSON | Validates tenant, scope, normalizes & upserts |
| `POST` | `/api/v1/discovery/import/har` | Ingests HAR traffic logs | Validates tenant, filters static assets, upserts |
| `GET` | `/api/v1/discovery/endpoints` | Lists discovered endpoints with filters | Tenant-isolated; filters by app, method, path, risk |
| `GET` | `/api/v1/discovery/endpoints/{id}` | Retrieves detailed endpoint record | Tenant-isolated verification |
| `DELETE`| `/api/v1/discovery/endpoints/{id}` | Removes endpoint from inventory | Tenant-isolated verification & audit logged |
| `GET` | `/api/v1/discovery/jobs` | Lists historical discovery jobs | Tenant-isolated by application ownership |
| `GET` | `/api/v1/discovery/jobs/{job_id}` | Retrieves discovery job status & summary | Tenant-isolated verification |
| `POST` | `/api/v1/discovery/jobs/{job_id}/cancel` | Cancels an in-progress discovery job | Tenant-isolated verification |

---

## 4. Frontend Architecture & User Interface

The discovery interface is implemented across modern React components in `frontend/src/`:

1. **`ApiDiscoveryPage.tsx`**:
   - **Target Application Selector**: Dynamically lists authorized applications belonging to the user's tenant organization. Automatically selects the first active application.
   - **Scope Status Banner**: Displays active authorization status, permitted path count, excluded paths, and maximum RPS constraints.
   - **Discovery Action Bar**: Houses the "Import Specification / Traffic" button and "Trigger Discovery" button.
   - **Execution & Inventory Summary**: Displays live metrics cards showing Total Discovered Endpoints, Endpoints In Scope, Ingestion Jobs Executed, and Scope Exclusion Rate.
   - **Inventory Filtering & Search**: Instant client-side search by path, filter pills for HTTP methods (`ALL`, `GET`, `POST`, `PUT`, `DELETE`, `PATCH`), and source tags (`ALL`, `OPENAPI`, `POSTMAN`, `HAR`, `PASSIVE`).
   - **Endpoint Inventory Table**: Displays method badges, normalized paths, source tags, authorization requirements, response status codes, and inspect/delete actions.
   - **Zero Mock Fallback**: Strictly consumes live backend APIs via `frontend/src/services/api.ts`. Displays empty state banners and actionable error notices when API calls fail or return no data.

2. **`DiscoveryImportModal.tsx`**:
   - Supports tabbed selection between OpenAPI/Swagger, Postman Collection, and HAR Traffic Log.
   - Provides both drag-and-drop file upload and raw text paste modes.
   - Validates JSON/YAML format before submission.
   - Displays real-time ingestion progress and detailed post-import summaries (discovered, in-scope, out-of-scope).

3. **`EndpointDetailsModal.tsx`**:
   - Comprehensive endpoint inspector modal displaying:
     - Method, normalized path, original path, and risk level.
     - Parameter schema table (name, location, type, required status, description).
     - Response status codes badge strip.
     - Raw metadata inspector (JSON view) showing observed path evidence and headers.

---

## 5. Files Created and Modified

### Created Files:
- `backend/app/discovery/__init__.py`
- `backend/app/discovery/normalizer.py`
- `backend/app/discovery/scope_filter.py`
- `backend/app/discovery/parsers/__init__.py`
- `backend/app/discovery/parsers/openapi_parser.py`
- `backend/app/discovery/parsers/postman_parser.py`
- `backend/app/discovery/parsers/har_parser.py`
- `security-engine/discovery/__init__.py`
- `security-engine/discovery/normalizer.py`
- `security-engine/discovery/scope_filter.py`
- `security-engine/discovery/parsers/__init__.py`
- `security-engine/discovery/parsers/openapi_parser.py`
- `security-engine/discovery/parsers/postman_parser.py`
- `security-engine/discovery/parsers/har_parser.py`
- `backend/migrations/versions/009_discovery_jobs.py`
- `backend/tests/test_feature_02_api_endpoint_discovery.py`
- `frontend/src/components/discovery/DiscoveryImportModal.tsx`
- `frontend/src/components/discovery/EndpointDetailsModal.tsx`
- `frontend/src/components/discovery/index.ts`
- `frontend/tests/ApiDiscovery.test.tsx`
- `docs/member-1/api-endpoint-discovery/implementation-report.md`
- `docs/member-1/api-endpoint-discovery/testing-report.md`
- `docs/member-1/api-endpoint-discovery/api-documentation.md`
- `docs/member-1/api-endpoint-discovery/discovery-architecture.md`

### Modified Files:
- `backend/app/models/endpoint.py` (added `DiscoveryJob` model and relationship)
- `backend/app/models/application.py` (added `discovery_jobs` relationship)
- `backend/app/models/__init__.py` (exported `DiscoveryJob`)
- `shared/contracts/models.py` (added discovery schemas and `raw_metadata` field)
- `shared/contracts/__init__.py` (exported discovery schemas)
- `backend/app/services/discovery_service.py` (full implementation of discovery operations)
- `backend/app/services/__init__.py` (exported `DiscoveryService`)
- `backend/app/api/v1/endpoints/discovery.py` (full implementation of API endpoints)
- `ai-engine/agents/discovery_agent/agent.py` (adapted to accept parameters and return discovery results)
- `frontend/src/types/index.ts` (added discovery type contracts)
- `frontend/src/services/api.ts` (connected discovery API methods)
- `frontend/src/pages/ApiDiscoveryPage.tsx` (redesigned with full feature set)
- `docs/member-1/member_1.md` (appended Feature 2 execution log)

