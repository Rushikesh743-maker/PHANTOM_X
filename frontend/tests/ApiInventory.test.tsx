import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { ApiDiscoveryPage } from "../src/pages/ApiDiscoveryPage";
import { api } from "../src/services/api";
import {
  ApplicationResponse,
  EndpointResponse,
  InventoryOverviewStats,
  ApiResourceGroup,
  EndpointRelationshipResponse,
} from "../src/types";

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
    inventory: {
      listEndpoints: vi.fn(),
      listResources: vi.fn(),
      getResource: vi.fn(),
      listRelationships: vi.fn(),
      getStats: vi.fn(),
      rebuild: vi.fn(),
      exportUrl: vi.fn(),
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
  },
];

const mockEndpoints: EndpointResponse[] = [
  {
    id: "ep-1",
    application_id: "app-uuid-1",
    path: "/api/v1/auth/login",
    method: "POST",
    auth_required: false,
    parameters: [],
    response_codes: [200, 401],
    risk_level: "LOW",
    raw_metadata: {
      resource_name: "auth",
      parent_resource_name: null,
      category: "AUTH_IDENTITY",
      category_label: "Authentication & Identity",
      category_confidence: 0.95,
      category_explanation: "Path contains keyword 'auth/login' and method is POST",
      discovery_source: "OPENAPI",
      evidence_classification: "DOCUMENTED",
    },
    created_at: "2026-11-12T10:00:00Z",
    updated_at: "2026-11-12T10:00:00Z",
  },
  {
    id: "ep-2",
    application_id: "app-uuid-1",
    path: "/api/v1/users",
    method: "GET",
    auth_required: true,
    parameters: [{ name: "limit", location: "query", param_type: "integer", required: false }],
    response_codes: [200],
    risk_level: "LOW",
    raw_metadata: {
      resource_name: "users",
      parent_resource_name: null,
      category: "USER_MANAGEMENT",
      category_label: "User Management",
      category_confidence: 0.9,
      category_explanation: "Path references user collection",
      discovery_source: "OPENAPI",
      evidence_classification: "DOCUMENTED",
    },
    created_at: "2026-11-12T10:00:00Z",
    updated_at: "2026-11-12T10:00:00Z",
  },
  {
    id: "ep-3",
    application_id: "app-uuid-1",
    path: "/api/v1/users/{id}/accounts",
    method: "GET",
    auth_required: true,
    parameters: [{ name: "id", location: "path", param_type: "string", required: true }],
    response_codes: [200],
    risk_level: "MEDIUM",
    raw_metadata: {
      resource_name: "accounts",
      parent_resource_name: "users",
      category: "ACCOUNT_MANAGEMENT",
      category_label: "Account Management",
      category_confidence: 0.85,
      category_explanation: "Sub-resource managing financial accounts",
      discovery_source: "OPENAPI",
      evidence_classification: "DOCUMENTED",
    },
    created_at: "2026-11-12T10:00:00Z",
    updated_at: "2026-11-12T10:00:00Z",
  },
];

const mockStats: InventoryOverviewStats = {
  total_endpoints: 3,
  unique_resources: 2,
  method_distribution: {
    GET: 2,
    POST: 1,
  },
  category_distribution: {
    AUTH_IDENTITY: 1,
    USER_MANAGEMENT: 1,
    ACCOUNT_MANAGEMENT: 1,
  },
  source_distribution: {
    OPENAPI: 3,
  },
  documented_count: 3,
  observed_count: 0,
  imported_count: 3,
  inferred_relationships_count: 1,
  total_relationships_count: 2,
  unclassified_count: 0,
  incomplete_metadata_count: 0,
};

const mockResources: ApiResourceGroup[] = [
  {
    name: "users",
    parent_resource: null,
    endpoint_count: 2,
    endpoint_ids: ["ep-2", "ep-3"],
    methods: ["GET"],
    paths: ["/api/v1/users", "/api/v1/users/{id}/accounts"],
    parameters: [],
    request_schemas: [],
    response_schemas: [],
    related_resources: ["accounts"],
    discovery_sources: ["OPENAPI"],
    confidence: 1.0,
    evidence: "Extracted from OpenAPI path patterns",
  },
  {
    name: "auth",
    parent_resource: null,
    endpoint_count: 1,
    endpoint_ids: ["ep-1"],
    methods: ["POST"],
    paths: ["/api/v1/auth/login"],
    parameters: [],
    request_schemas: [],
    response_schemas: [],
    related_resources: [],
    discovery_sources: ["OPENAPI"],
    confidence: 1.0,
    evidence: "Extracted from OpenAPI path patterns",
  },
];

const mockRelationships: EndpointRelationshipResponse[] = [
  {
    id: "rel-1",
    application_id: "app-uuid-1",
    source_endpoint_id: "ep-1",
    target_endpoint_id: "ep-2",
    source_endpoint_path: "/api/v1/auth/login",
    source_endpoint_method: "POST",
    target_endpoint_path: "/api/v1/users",
    target_endpoint_method: "GET",
    relationship_type: "AUTH_DEPENDENCY",
    evidence_source: "AUTHENTICATION_PREREQUISITE",
    confidence: 0.9,
    explanation: "Target endpoint requires authentication supplied by login",
    provenance: "INFERRED",
    raw_metadata: {},
    created_at: "2026-11-12T10:30:00Z",
  },
  {
    id: "rel-2",
    application_id: "app-uuid-1",
    source_endpoint_id: "ep-2",
    target_endpoint_id: "ep-3",
    source_endpoint_path: "/api/v1/users",
    source_endpoint_method: "GET",
    target_endpoint_path: "/api/v1/users/{id}/accounts",
    target_endpoint_method: "GET",
    relationship_type: "PARENT_CHILD",
    evidence_source: "PATH_HIERARCHY",
    confidence: 0.95,
    explanation: "Target is sub-resource under parent resource users",
    provenance: "DOCUMENTED",
    raw_metadata: {},
    created_at: "2026-11-12T10:30:00Z",
  },
];

describe("Feature 3: API Inventory & Mapping UI Components", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.applications.list).mockResolvedValue(mockApplications);
    vi.mocked(api.discovery.listEndpoints).mockResolvedValue(mockEndpoints);
    vi.mocked(api.inventory.getStats).mockResolvedValue(mockStats);
    vi.mocked(api.inventory.listResources).mockResolvedValue(mockResources);
    vi.mocked(api.inventory.listRelationships).mockResolvedValue(mockRelationships);
  });

  it("renders tabbed navigation with counts and active indicator", async () => {
    render(
      <BrowserRouter>
        <ApiDiscoveryPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("/api/v1/auth/login")).toBeInTheDocument();
    });

    expect(screen.getByText("Endpoint Inventory")).toBeInTheDocument();
    expect(screen.getByText("Overview Analytics")).toBeInTheDocument();
    expect(screen.getByText("Resource Mapping")).toBeInTheDocument();
    expect(screen.getByText("Relationship Graph")).toBeInTheDocument();

    // Check count badges
    expect(screen.getAllByText("3").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("2").length).toBeGreaterThanOrEqual(1);
  });

  it("displays categorized endpoints with category labels and confidence in inventory tab", async () => {
    render(
      <BrowserRouter>
        <ApiDiscoveryPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("/api/v1/auth/login")).toBeInTheDocument();
      expect(screen.getByText("/api/v1/users")).toBeInTheDocument();
      expect(screen.getByText("/api/v1/users/{id}/accounts")).toBeInTheDocument();
    });

    // Verify category labels rendered
    expect(screen.getAllByText("Auth & Identity").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("User Management").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Account Management").length).toBeGreaterThanOrEqual(1);

    // Verify confidence percentages
    expect(screen.getByText("95%")).toBeInTheDocument();
    expect(screen.getByText("90%")).toBeInTheDocument();
  });

  it("switches to Overview Analytics tab and renders statistical breakdown", async () => {
    render(
      <BrowserRouter>
        <ApiDiscoveryPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("/api/v1/auth/login")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Overview Analytics"));

    await waitFor(() => {
      expect(screen.getByText("API Inventory Overview")).toBeInTheDocument();
      expect(screen.getByText("TOTAL ENDPOINTS")).toBeInTheDocument();
      expect(screen.getByText("UNIQUE RESOURCES")).toBeInTheDocument();
      expect(screen.getByText("MAPPED RELATIONSHIPS")).toBeInTheDocument();
      expect(screen.getByText("Category Distribution")).toBeInTheDocument();
    });
  });

  it("switches to Resource Mapping tab and renders hierarchical tree", async () => {
    render(
      <BrowserRouter>
        <ApiDiscoveryPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("/api/v1/auth/login")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Resource Mapping"));

    await waitFor(() => {
      expect(screen.getByText("API Resource Hierarchy (2 Logical Entities)")).toBeInTheDocument();
      expect(screen.getByText("/users")).toBeInTheDocument();
      expect(screen.getByText("/auth")).toBeInTheDocument();
      expect(screen.getByText("2 endpoints")).toBeInTheDocument();
    });
  });

  it("switches to Relationship Graph tab and displays dependency flows with provenance", async () => {
    render(
      <BrowserRouter>
        <ApiDiscoveryPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("/api/v1/auth/login")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Relationship Graph"));

    await waitFor(() => {
      expect(screen.getByText("Auth Dependency")).toBeInTheDocument();
      expect(screen.getByText("Parent - Child")).toBeInTheDocument();
      expect(screen.getByText("INFERRED")).toBeInTheDocument();
      expect(screen.getByText("DOCUMENTED")).toBeInTheDocument();
      expect(
        screen.getByText("Target endpoint requires authentication supplied by login")
      ).toBeInTheDocument();
    });
  });

  it("triggers Rebuild Mappings and refreshes inventory data", async () => {
    vi.mocked(api.inventory.rebuild).mockResolvedValue({
      application_id: "app-uuid-1",
      endpoints_classified: 3,
      relationships_created: 2,
      unique_resources: 2,
      message: "Successfully rebuilt inventory",
    });

    render(
      <BrowserRouter>
        <ApiDiscoveryPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("/api/v1/auth/login")).toBeInTheDocument();
      expect(screen.getByText("Rebuild Mappings")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Rebuild Mappings"));

    await waitFor(() => {
      expect(api.inventory.rebuild).toHaveBeenCalledWith("app-uuid-1");
      expect(screen.getByText(/Inventory rebuilt successfully/i)).toBeInTheDocument();
    });
  });

  it("filters endpoints by category dropdown in inventory tab", async () => {
    render(
      <BrowserRouter>
        <ApiDiscoveryPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("/api/v1/auth/login")).toBeInTheDocument();
    });

    // Select Auth & Identity category
    const select = screen.getByLabelText(/Category:/i);
    fireEvent.change(select, { target: { value: "AUTH_IDENTITY" } });

    await waitFor(() => {
      expect(screen.getByText("/api/v1/auth/login")).toBeInTheDocument();
      expect(screen.queryByText("/api/v1/users/{id}/accounts")).not.toBeInTheDocument();
    });
  });

  it("inspects endpoint from details button and shows classification card", async () => {
    render(
      <BrowserRouter>
        <ApiDiscoveryPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("/api/v1/auth/login")).toBeInTheDocument();
    });

    // Find and click inspect button (eye icon)
    const inspectButtons = screen.getAllByTitle("Inspect endpoint specifications");
    fireEvent.click(inspectButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("LOGICAL RESOURCE:")).toBeInTheDocument();
      expect(screen.getAllByText("/auth").length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText("Authentication & Identity").length).toBeGreaterThanOrEqual(1);
      expect(
        screen.getByText(/Path contains keyword 'auth\/login' and method is POST/i)
      ).toBeInTheDocument();
    });
  });
});
