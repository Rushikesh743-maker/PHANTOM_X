import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { ApplicationsPage } from "../src/pages/ApplicationsPage";
import {
  ApplicationRegistrationModal,
  ApplicationEditModal,
  ApplicationDeleteDialog,
  ApplicationCard,
} from "../src/components/applications";
import { api } from "../src/services/api";
import { ApplicationResponse } from "../src/types";

// Mock API service methods
vi.mock("../src/services/api", () => ({
  api: {
    applications: {
      list: vi.fn(),
      getById: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
      getScope: vi.fn(),
    },
  },
}));

const mockApps: ApplicationResponse[] = [
  {
    id: "app-uuid-1",
    organization_id: "org-uuid-1",
    name: "FinTech Core Banking",
    description: "Core banking backend microservice",
    target_url: "https://banking.fintech.local:8443",
    environment_name: "staging",
    risk_score: 12.5,
    status: "ACTIVE",
    created_at: "2026-11-10T12:00:00Z",
    updated_at: "2026-11-10T12:00:00Z",
    scope: {
      id: "scope-uuid-1",
      organization_id: "org-uuid-1",
      application_id: "app-uuid-1",
      target_domain: "banking.fintech.local",
      base_url: "https://banking.fintech.local:8443",
      permitted_paths: ["/api/v1/*", "/checkout/*"],
      excluded_paths: ["/admin/*", "/logout"],
      scope_status: "ACTIVE",
      authorization_status: "AUTHORIZED",
      authorized_by: "secops@fintech.local",
      authorizer_role: "Security Engineer",
      rate_limit_rps: 20,
      max_concurrency: 3,
      max_scan_duration_minutes: 90,
      allowed_methods: ["GET", "POST", "PUT"],
      restricted_endpoint_patterns: ["*/purge*"],
      require_synthetic_auth: true,
      allow_destructive: false,
    },
  },
  {
    id: "app-uuid-2",
    organization_id: "org-uuid-1",
    name: "Mobile Banking Gateway",
    description: "Customer facing mobile application gateway",
    target_url: "https://mobile-gw.fintech.local",
    environment_name: "development",
    risk_score: 0.0,
    status: "ACTIVE",
    created_at: "2026-11-11T10:00:00Z",
    updated_at: "2026-11-11T10:00:00Z",
    scope: {
      id: "scope-uuid-2",
      organization_id: "org-uuid-1",
      application_id: "app-uuid-2",
      target_domain: "mobile-gw.fintech.local",
      base_url: "https://mobile-gw.fintech.local",
      permitted_paths: ["/*"],
      excluded_paths: ["/admin/*"],
      scope_status: "DRAFT",
      authorization_status: "PENDING",
      rate_limit_rps: 10,
      max_concurrency: 2,
      max_scan_duration_minutes: 60,
      allowed_methods: ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
      restricted_endpoint_patterns: [],
      require_synthetic_auth: true,
      allow_destructive: false,
    },
  },
];

describe("Feature 1: Application Registration UI Components", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ============================================================================
  // 1. APPLICATION LISTING
  // ============================================================================
  it("renders applications list with cards, badges, and target URLs", async () => {
    vi.mocked(api.applications.list).mockResolvedValueOnce(mockApps);

    render(
      <BrowserRouter>
        <ApplicationsPage />
      </BrowserRouter>
    );

    // Initial loading indicator
    expect(screen.getByText("Loading security intelligence...")).toBeInTheDocument();

    // Wait for apps to load
    await waitFor(() => {
      expect(screen.getByText("FinTech Core Banking")).toBeInTheDocument();
      expect(screen.getByText("Mobile Banking Gateway")).toBeInTheDocument();
    });

    expect(screen.getByText("https://banking.fintech.local:8443")).toBeInTheDocument();
    expect(screen.getByText("AUTHORIZED")).toBeInTheDocument();
    expect(screen.getByText("PENDING AUTH")).toBeInTheDocument();
    expect(screen.getByText("Register Application")).toBeInTheDocument();
  });

  // ============================================================================
  // 2. LOADING AND EMPTY STATES
  // ============================================================================
  it("displays empty state when no applications are registered", async () => {
    vi.mocked(api.applications.list).mockResolvedValueOnce([]);

    render(
      <BrowserRouter>
        <ApplicationsPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("No Applications Registered")).toBeInTheDocument();
    });

    expect(
      screen.getByText(/Register your first authorized target application to establish safety policy boundaries/)
    ).toBeInTheDocument();
    expect(screen.getByText("Register Target Application")).toBeInTheDocument();
  });

  // ============================================================================
  // 3. REGISTRATION FORM VALIDATION
  // ============================================================================
  it("validates required fields, target URL format, and explicit authorization checkbox", async () => {
    render(
      <ApplicationRegistrationModal
        isOpen={true}
        onClose={vi.fn()}
        onSuccess={vi.fn()}
      />
    );

    expect(screen.getByText("Register Target Application")).toBeInTheDocument();

    const submitBtn = screen.getByText("Confirm & Register");

    // Click submit with empty form
    fireEvent.click(submitBtn);

    // Assert validation errors appear
    expect(screen.getByText("Application name is required.")).toBeInTheDocument();
    expect(screen.getByText("Target URL is required.")).toBeInTheDocument();
    expect(
      screen.getByText("You must explicitly confirm authorization for security testing on this target.")
    ).toBeInTheDocument();

    // Fill invalid URL
    const urlInput = screen.getByPlaceholderText("https://staging.target.internal:8443");
    fireEvent.change(urlInput, { target: { value: "invalid-url-without-scheme" } });
    fireEvent.click(submitBtn);

    expect(screen.getByText("Please enter a valid URL (e.g., https://staging.example.com).")).toBeInTheDocument();

    // Verify API was not called
    expect(api.applications.create).not.toHaveBeenCalled();
  });

  // ============================================================================
  // 4. SUCCESSFUL REGISTRATION WORKFLOW
  // ============================================================================
  it("submits valid application registration with scope configuration and authorization confirmation", async () => {
    const handleSuccess = vi.fn();
    const handleClose = vi.fn();

    const createdApp: ApplicationResponse = {
      id: "new-app-1",
      organization_id: "org-1",
      name: "Staging Inventory Service",
      description: "Inventory management endpoints",
      target_url: "https://inventory-staging.local",
      environment_name: "staging",
      risk_score: 0.0,
      status: "ACTIVE",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    vi.mocked(api.applications.create).mockResolvedValueOnce(createdApp);

    render(
      <ApplicationRegistrationModal
        isOpen={true}
        onClose={handleClose}
        onSuccess={handleSuccess}
      />
    );

    // Fill form
    fireEvent.change(screen.getByPlaceholderText("e.g. Core Banking API Staging"), {
      target: { value: "Staging Inventory Service" },
    });
    fireEvent.change(screen.getByPlaceholderText("https://staging.target.internal:8443"), {
      target: { value: "https://inventory-staging.local" },
    });
    fireEvent.change(screen.getByPlaceholderText("Application purpose, tech stack, and testing objectives..."), {
      target: { value: "Inventory management endpoints" },
    });
    fireEvent.change(screen.getByPlaceholderText("/*, /api/v1/*, /checkout/*"), {
      target: { value: "/api/v1/*, /health" },
    });
    fireEvent.change(screen.getByPlaceholderText("/admin/*, /logout, /auth/reset-password"), {
      target: { value: "/admin/*" },
    });

    // Check authorization confirmation
    const authCheckbox = screen.getByRole("checkbox");
    fireEvent.click(authCheckbox);

    // Submit
    fireEvent.click(screen.getByText("Confirm & Register"));

    await waitFor(() => {
      expect(api.applications.create).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "Staging Inventory Service",
          target_url: "https://inventory-staging.local",
          description: "Inventory management endpoints",
          permitted_paths: ["/api/v1/*", "/health"],
          excluded_paths: ["/admin/*"],
          confirm_authorization: true,
        })
      );
    });

    expect(handleSuccess).toHaveBeenCalledWith(createdApp);
    expect(handleClose).toHaveBeenCalled();
  });

  // ============================================================================
  // 5. API ERROR HANDLING
  // ============================================================================
  it("displays API error messages returned from the backend (e.g. 409 conflict)", async () => {
    vi.mocked(api.applications.create).mockRejectedValueOnce({
      response: {
        data: {
          detail: "An application named 'Duplicate App' is already registered in your organization.",
        },
      },
    });

    render(
      <ApplicationRegistrationModal
        isOpen={true}
        onClose={vi.fn()}
        onSuccess={vi.fn()}
      />
    );

    fireEvent.change(screen.getByPlaceholderText("e.g. Core Banking API Staging"), {
      target: { value: "Duplicate App" },
    });
    fireEvent.change(screen.getByPlaceholderText("https://staging.target.internal:8443"), {
      target: { value: "https://app.fintech.local" },
    });
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByText("Confirm & Register"));

    await waitFor(() => {
      expect(
        screen.getByText("An application named 'Duplicate App' is already registered in your organization.")
      ).toBeInTheDocument();
    });
  });

  // ============================================================================
  // 6. APPLICATION CARD ACTIONS: EDIT & DELETE
  // ============================================================================
  it("renders ApplicationCard and triggers edit and delete callbacks", () => {
    const handleEdit = vi.fn();
    const handleDelete = vi.fn();

    render(
      <BrowserRouter>
        <ApplicationCard
          app={mockApps[0]}
          onEdit={handleEdit}
          onDelete={handleDelete}
        />
      </BrowserRouter>
    );

    expect(screen.getByText("FinTech Core Banking")).toBeInTheDocument();
    expect(screen.getByText("Limit: 20 RPS")).toBeInTheDocument();

    // Click edit button
    const editBtn = screen.getByRole("button", { name: "Edit FinTech Core Banking" });
    fireEvent.click(editBtn);
    expect(handleEdit).toHaveBeenCalledWith(mockApps[0]);

    // Click delete button
    const deleteBtn = screen.getByRole("button", { name: "Delete FinTech Core Banking" });
    fireEvent.click(deleteBtn);
    expect(handleDelete).toHaveBeenCalledWith(mockApps[0]);
  });

  // ============================================================================
  // 7. APPLICATION DELETE DIALOG
  // ============================================================================
  it("confirms and executes application deletion via API", async () => {
    const handleSuccess = vi.fn();
    const handleClose = vi.fn();
    vi.mocked(api.applications.delete).mockResolvedValueOnce();

    render(
      <ApplicationDeleteDialog
        app={mockApps[0]}
        isOpen={true}
        onClose={handleClose}
        onSuccess={handleSuccess}
      />
    );

    expect(screen.getByText("Delete Application Target")).toBeInTheDocument();
    expect(screen.getByText(/Warning: Irreversible Action/)).toBeInTheDocument();

    // Confirm deletion
    const confirmBtn = screen.getByText("Confirm Deletion");
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(api.applications.delete).toHaveBeenCalledWith(mockApps[0].id);
      expect(handleSuccess).toHaveBeenCalledWith(mockApps[0].id);
      expect(handleClose).toHaveBeenCalled();
    });
  });

  // ============================================================================
  // 8. APPLICATION EDIT MODAL
  // ============================================================================
  it("pre-fills and saves updated application profile and scope", async () => {
    const handleSuccess = vi.fn();
    const handleClose = vi.fn();

    const updatedApp: ApplicationResponse = {
      ...mockApps[0],
      name: "Updated Core Banking Name",
    };
    vi.mocked(api.applications.update).mockResolvedValueOnce(updatedApp);

    render(
      <ApplicationEditModal
        app={mockApps[0]}
        isOpen={true}
        onClose={handleClose}
        onSuccess={handleSuccess}
      />
    );

    expect(screen.getByText("Edit Application Profile & Scope")).toBeInTheDocument();

    const nameInput = screen.getByDisplayValue("FinTech Core Banking");
    fireEvent.change(nameInput, { target: { value: "Updated Core Banking Name" } });

    fireEvent.click(screen.getByText("Save Changes"));

    await waitFor(() => {
      expect(api.applications.update).toHaveBeenCalledWith(
        mockApps[0].id,
        expect.objectContaining({
          name: "Updated Core Banking Name",
        })
      );
      expect(handleSuccess).toHaveBeenCalledWith(updatedApp);
      expect(handleClose).toHaveBeenCalled();
    });
  });
});
