import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { ApiDiscoveryPage } from "../src/pages/ApiDiscoveryPage";
import { DiscoveryImportModal, EndpointDetailsModal } from "../src/components/discovery";
import { api } from "../src/services/api";
import { ApplicationResponse, EndpointResponse, DiscoverySummaryResponse } from "../src/types";

// Mock API service
vi.mock("../src/services/api", () => ({
  api: {
    applications: {
      list: vi.fn(),
      getById: vi.fn(),
    },
    discovery: {
      listEndpoints: vi.fn(),
      getEndpoint: vi.fn(),
      deleteEndpoint: vi.fn(),
      trigger: vi.fn(),
      importOpenApi: vi.fn(),
      importPostman: vi.fn(),
      importHar: vi.fn(),
    },
  },
}));

const mockApplications: ApplicationResponse[] = [
  {
    id: "app-uuid-1",
    organization_id: "org-uuid-1",
    name: "FinTech Core Banking",
    description: "Core banking and accounts API",
    target_url: "https://api.fintech.local",
    environment_name: "staging",
    risk_score: 10.0,
    status: "ACTIVE",
    created_at: "2026-11-10T12:00:00Z",
    updated_at: "2026-11-10T12:00:00Z",
    scope: {
      id: "scope-uuid-1",
      organization_id: "org-uuid-1",
      application_id: "app-uuid-1",
      target_domain: "api.fintech.local",
      base_url: "https://api.fintech.local",
      permitted_paths: ["/api/v1/*"],
      excluded_paths: ["/api/v1/admin/*"],
      scope_status: "ACTIVE",
      authorization_status: "AUTHORIZED",
      rate_limit_rps: 50,
      max_concurrency: 3,
      max_scan_duration_minutes: 60,
      allowed_methods: ["GET", "POST", "PUT"],
      restricted_endpoint_patterns: [],
      require_synthetic_auth: true,
      allow_destructive: false,
    },
  },
  {
    id: "app-uuid-2",
    organization_id: "org-uuid-1",
    name: "HealthCare Portal",
    description: "Patient records API",
    target_url: "https://api.healthcare.local",
    environment_name: "production",
    risk_score: 5.0,
    status: "ACTIVE",
    created_at: "2026-11-11T12:00:00Z",
    updated_at: "2026-11-11T12:00:00Z",
  },
];

const mockEndpoints: EndpointResponse[] = [
  {
    id: "ep-uuid-1",
    application_id: "app-uuid-1",
    path: "/api/v1/accounts",
    method: "GET",
    auth_required: true,
    parameters: [
      { name: "status", location: "query", param_type: "string", required: false },
      { name: "limit", location: "query", param_type: "integer", required: false },
    ],
    response_codes: [200, 401],
    risk_level: "UNASSESSED",
    raw_metadata: {
      discovery_source: "OPENAPI",
      evidence_classification: "DOCUMENTED",
      base_url: "https://api.fintech.local",
    },
    created_at: "2026-11-12T10:00:00Z",
    updated_at: "2026-11-12T10:00:00Z",
  },
  {
    id: "ep-uuid-2",
    application_id: "app-uuid-1",
    path: "/api/v1/accounts",
    method: "POST",
    auth_required: true,
    parameters: [],
    response_codes: [201, 400],
    risk_level: "UNASSESSED",
    raw_metadata: {
      discovery_source: "OPENAPI",
      evidence_classification: "DOCUMENTED",
      base_url: "https://api.fintech.local",
    },
    created_at: "2026-11-12T10:00:00Z",
    updated_at: "2026-11-12T10:00:00Z",
  },
  {
    id: "ep-uuid-3",
    application_id: "app-uuid-1",
    path: "/api/v1/users/{id}",
    method: "GET",
    auth_required: false,
    parameters: [
      { name: "id", location: "path", param_type: "string", required: true },
    ],
    response_codes: [200],
    risk_level: "UNASSESSED",
    raw_metadata: {
      discovery_source: "HAR",
      evidence_classification: "OBSERVED",
      base_url: "https://api.fintech.local",
      original_path: "/api/v1/users/42",
    },
    created_at: "2026-11-12T10:15:00Z",
    updated_at: "2026-11-12T10:15:00Z",
  },
];

describe("Feature 2: API Endpoint Discovery UI Components", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders page header and target application selector with registered apps", async () => {
    vi.mocked(api.applications.list).mockResolvedValue(mockApplications);
    vi.mocked(api.discovery.listEndpoints).mockResolvedValue(mockEndpoints);

    render(
      <BrowserRouter>
        <ApiDiscoveryPage />
      </BrowserRouter>
    );

    // Verify header
    expect(screen.getByText("API Endpoint Inventory & Discovery")).toBeInTheDocument();

    // Verify applications loaded in selector
    await waitFor(() => {
      expect(screen.getByText(/FinTech Core Banking/i)).toBeInTheDocument();
    });

    // Verify target url displayed
    expect(screen.getByText("https://api.fintech.local")).toBeInTheDocument();
  });

  it("renders discovered endpoints table with methods, paths, and sources", async () => {
    vi.mocked(api.applications.list).mockResolvedValue(mockApplications);
    vi.mocked(api.discovery.listEndpoints).mockResolvedValue(mockEndpoints);

    render(
      <BrowserRouter>
        <ApiDiscoveryPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("/api/v1/users/{id}")).toBeInTheDocument();
    });

    // Check method badges
    expect(screen.getAllByText("GET").length).toBeGreaterThan(0);
    expect(screen.getAllByText("POST").length).toBeGreaterThan(0);

    // Check source badges (in filter bar and table rows)
    expect(screen.getAllByText("OPENAPI").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("HAR").length).toBeGreaterThanOrEqual(1);

    // Check auth status
    expect(screen.getAllByText("Required").length).toBe(2);
    expect(screen.getByText("Public")).toBeInTheDocument();
  });

  it("triggers automated discovery when Trigger Discovery button is clicked", async () => {
    vi.mocked(api.applications.list).mockResolvedValue(mockApplications);
    vi.mocked(api.discovery.listEndpoints).mockResolvedValue(mockEndpoints);
    const mockSummary: DiscoverySummaryResponse = {
      job_id: "job-123",
      application_id: "app-uuid-1",
      status: "COMPLETED",
      source_type: "SPECIFICATION",
      endpoints_found: 3,
      endpoints_in_scope: 3,
      endpoints_out_of_scope: 0,
      out_of_scope_reasons: [],
      message: "Successfully discovered 3 authorized endpoints.",
    };
    vi.mocked(api.discovery.trigger).mockResolvedValue(mockSummary);

    render(
      <BrowserRouter>
        <ApiDiscoveryPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Trigger Discovery")).toBeInTheDocument();
    });

    const triggerBtn = screen.getByText("Trigger Discovery");
    fireEvent.click(triggerBtn);

    await waitFor(() => {
      expect(api.discovery.trigger).toHaveBeenCalledWith("app-uuid-1");
      expect(screen.getByText(/Discovery Execution Completed/i)).toBeInTheDocument();
    });
  });

  it("opens discovery import modal on Import Spec / Traffic click", async () => {
    vi.mocked(api.applications.list).mockResolvedValue(mockApplications);
    vi.mocked(api.discovery.listEndpoints).mockResolvedValue(mockEndpoints);

    render(
      <BrowserRouter>
        <ApiDiscoveryPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Import Spec / Traffic")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Import Spec / Traffic"));

    await waitFor(() => {
      expect(screen.getByText("Import & Discover API Endpoints")).toBeInTheDocument();
      expect(screen.getByText("OpenAPI / Swagger")).toBeInTheDocument();
      expect(screen.getByText("Postman Collection")).toBeInTheDocument();
      expect(screen.getByText("HAR Traffic Log")).toBeInTheDocument();
    });
  });

  it("validates empty content in import modal", async () => {
    const handleClose = vi.fn();
    const handleSuccess = vi.fn();

    render(
      <DiscoveryImportModal
        isOpen={true}
        onClose={handleClose}
        selectedApp={mockApplications[0]}
        onImportSuccess={handleSuccess}
      />
    );

    const submitBtn = screen.getByRole("button", { name: /import & discover/i });
    // Button is disabled when file content is empty
    expect(submitBtn).toBeDisabled();
  });

  it("submits pasted OpenAPI content and handles successful import", async () => {
    const handleClose = vi.fn();
    const handleSuccess = vi.fn();
    const mockSummary: DiscoverySummaryResponse = {
      job_id: "job-456",
      application_id: "app-uuid-1",
      status: "COMPLETED",
      source_type: "OPENAPI",
      endpoints_found: 2,
      endpoints_in_scope: 2,
      endpoints_out_of_scope: 0,
      out_of_scope_reasons: [],
      message: "Imported 2 endpoints.",
    };
    vi.mocked(api.discovery.importOpenApi).mockResolvedValue(mockSummary);

    render(
      <DiscoveryImportModal
        isOpen={true}
        onClose={handleClose}
        selectedApp={mockApplications[0]}
        onImportSuccess={handleSuccess}
      />
    );

    // Switch to paste mode
    fireEvent.click(screen.getByText("Paste Content"));

    const textarea = screen.getByPlaceholderText(/Paste OpenAPI JSON or YAML here/i);
    fireEvent.change(textarea, { target: { value: '{"openapi":"3.0.0","paths":{}}' } });

    const submitBtn = screen.getByText("Import & Discover");
    expect(submitBtn).not.toBeDisabled();
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(api.discovery.importOpenApi).toHaveBeenCalledWith({
        application_id: "app-uuid-1",
        content: '{"openapi":"3.0.0","paths":{}}',
        filename: undefined,
      });
      expect(handleSuccess).toHaveBeenCalledWith(mockSummary);
      expect(handleClose).toHaveBeenCalled();
    });
  });

  it("filters endpoints by search query and HTTP method", async () => {
    vi.mocked(api.applications.list).mockResolvedValue(mockApplications);
    vi.mocked(api.discovery.listEndpoints).mockResolvedValue(mockEndpoints);

    render(
      <BrowserRouter>
        <ApiDiscoveryPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("/api/v1/users/{id}")).toBeInTheDocument();
    });

    // Search for "users"
    const searchInput = screen.getByPlaceholderText(/Filter by endpoint path/i);
    fireEvent.change(searchInput, { target: { value: "users" } });

    // Should display only users endpoint
    expect(screen.getByText("/api/v1/users/{id}")).toBeInTheDocument();
    expect(screen.queryByText("/api/v1/accounts")).not.toBeInTheDocument();

    // Clear search
    fireEvent.change(searchInput, { target: { value: "" } });

    // Filter by POST method
    const postFilterBtn = screen.getByRole("button", { name: "POST" });
    fireEvent.click(postFilterBtn);

    expect(screen.getByText("/api/v1/accounts")).toBeInTheDocument();
    expect(screen.queryByText("/api/v1/users/{id}")).not.toBeInTheDocument();
  });

  it("renders empty state when no endpoints exist for selected application", async () => {
    vi.mocked(api.applications.list).mockResolvedValue(mockApplications);
    vi.mocked(api.discovery.listEndpoints).mockResolvedValue([]);

    render(
      <BrowserRouter>
        <ApiDiscoveryPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("No Endpoints Discovered")).toBeInTheDocument();
      expect(screen.getByText("Import API Specification")).toBeInTheDocument();
    });
  });

  it("renders EndpointDetailsModal when endpoint inspect is clicked", async () => {
    const handleClose = vi.fn();

    render(
      <EndpointDetailsModal
        isOpen={true}
        endpoint={mockEndpoints[0]}
        onClose={handleClose}
      />
    );

    expect(screen.getByText("/api/v1/accounts")).toBeInTheDocument();
    expect(screen.getByText("Endpoint Parameters")).toBeInTheDocument();
    expect(screen.getByText("status")).toBeInTheDocument();
    expect(screen.getByText("limit")).toBeInTheDocument();
    expect(screen.getByText("DOCUMENTED")).toBeInTheDocument();
  });
});
