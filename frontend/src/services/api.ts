import axios, { AxiosError, AxiosInstance } from "axios";
import {
  ApplicationResponse,
  ApplicationCreate,
  ApplicationUpdate,
  ApplicationScopeDetail,
  ScanResponse,
  ScanCreate,
  ScanProgress,
  EndpointResponse,
  DiscoveryJobResponse,
  DiscoverySummaryResponse,
  DiscoveryImportRequest,
  DiscoveryTriggerRequest,
  VulnerabilityResponse,
  AttackChainResponse,
  EvidenceResponse,
  RegressionResult,
  AuditLogResponse,
  AuditOverviewResponse,
  AuditIntegrityVerificationResponse,
  ScanExecutionRecordResponse,
  ScopePermissionResponse,
  ScopePolicyCreate,
  ScopePolicyUpdate,
  ScopePolicyResponse,
  ScopeAuthorizeRequest,
  ScopeSuspendRequest,
  ScopeRevokeRequest,
  TestValidationRequest,
  TestValidationResult,
  BlockedExecutionResponse,
  TokenResponse,
  UserLogin,
  ReportDashboardMetrics,
  ReportListPagination,
  VulnerabilityReportDetail,
  VulnerabilityReportListItem,
  ReportStatusUpdateRequest,
  StatusHistoryItem,
  ApiResourceGroup,
  EndpointRelationshipResponse,
  InventoryOverviewStats,
  InventoryRebuildResponse,
} from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 10000,
});

// Request interceptor to attach JWT token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("phantom_token");
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Clear token on 401
      localStorage.removeItem("phantom_token");
    }
    return Promise.reject(error);
  }
);

// ============================================================================
// API Service Methods
// ============================================================================

export const api = {
  // Authentication
  auth: {
    login: async (credentials: UserLogin): Promise<TokenResponse> => {
      const { data } = await apiClient.post<TokenResponse>("/auth/login", credentials);
      return data;
    },
    getMe: async () => {
      const { data } = await apiClient.get("/auth/me");
      return data;
    },
  },

  // Applications
  applications: {
    list: async (params?: { search?: string; status?: string; skip?: number; limit?: number }): Promise<ApplicationResponse[]> => {
      const { data } = await apiClient.get<ApplicationResponse[]>("/applications/", { params });
      return data;
    },
    getById: async (id: string): Promise<ApplicationResponse> => {
      const { data } = await apiClient.get<ApplicationResponse>(`/applications/${id}`);
      return data;
    },
    create: async (app: ApplicationCreate): Promise<ApplicationResponse> => {
      const { data } = await apiClient.post<ApplicationResponse>("/applications/", app);
      return data;
    },
    update: async (id: string, app: ApplicationUpdate): Promise<ApplicationResponse> => {
      const { data } = await apiClient.put<ApplicationResponse>(`/applications/${id}`, app);
      return data;
    },
    delete: async (id: string): Promise<void> => {
      await apiClient.delete(`/applications/${id}`);
    },
    getScope: async (id: string): Promise<ApplicationScopeDetail> => {
      const { data } = await apiClient.get<ApplicationScopeDetail>(`/applications/${id}/scope`);
      return data;
    },
  },

  // Scans
  scans: {
    list: async (appId?: string): Promise<ScanResponse[]> => {
      const params = appId ? { app_id: appId } : {};
      const { data } = await apiClient.get<ScanResponse[]>("/scans/", { params });
      return data;
    },
    getById: async (id: string): Promise<ScanResponse> => {
      const { data } = await apiClient.get<ScanResponse>(`/scans/${id}`);
      return data;
    },
    getProgress: async (id: string): Promise<ScanProgress> => {
      const { data } = await apiClient.get<ScanProgress>(`/scans/${id}/progress`);
      return data;
    },
    launch: async (scan: ScanCreate): Promise<ScanResponse> => {
      const { data } = await apiClient.post<ScanResponse>("/scans/", scan);
      return data;
    },
    abort: async (id: string): Promise<ScanResponse> => {
      const { data } = await apiClient.post<ScanResponse>(`/scans/${id}/abort`);
      return data;
    },
  },

  // Discovery
  discovery: {
    listEndpoints: async (filters?: {
      app_id?: string;
      method?: string;
      path?: string;
      search?: string;
      risk_level?: string;
      source?: string;
      skip?: number;
      limit?: number;
    }): Promise<EndpointResponse[]> => {
      const { data } = await apiClient.get<EndpointResponse[]>("/discovery/endpoints", { params: filters });
      return data;
    },
    getEndpoint: async (id: string): Promise<EndpointResponse> => {
      const { data } = await apiClient.get<EndpointResponse>(`/discovery/endpoints/${id}`);
      return data;
    },
    deleteEndpoint: async (id: string): Promise<void> => {
      await apiClient.delete(`/discovery/endpoints/${id}`);
    },
    trigger: async (appId: string, sourceType?: string, specContent?: string): Promise<DiscoverySummaryResponse> => {
      const payload: DiscoveryTriggerRequest = {
        application_id: appId,
        source_type: sourceType || "SPECIFICATION",
        spec_content: specContent
      };
      const { data } = await apiClient.post<DiscoverySummaryResponse>("/discovery/trigger", payload);
      return data;
    },
    importOpenApi: async (payload: { application_id: string; content: string; filename?: string }): Promise<DiscoverySummaryResponse> => {
      const { data } = await apiClient.post<DiscoverySummaryResponse>("/discovery/import/openapi", payload);
      return data;
    },
    importPostman: async (payload: { application_id: string; content: string; filename?: string }): Promise<DiscoverySummaryResponse> => {
      const { data } = await apiClient.post<DiscoverySummaryResponse>("/discovery/import/postman", payload);
      return data;
    },
    importHar: async (payload: { application_id: string; content: string; filename?: string }): Promise<DiscoverySummaryResponse> => {
      const { data } = await apiClient.post<DiscoverySummaryResponse>("/discovery/import/har", payload);
      return data;
    },
    listJobs: async (appId?: string): Promise<DiscoveryJobResponse[]> => {
      const params = appId ? { app_id: appId } : {};
      const { data } = await apiClient.get<DiscoveryJobResponse[]>("/discovery/jobs", { params });
      return data;
    },
    getJob: async (jobId: string): Promise<DiscoveryJobResponse> => {
      const { data } = await apiClient.get<DiscoveryJobResponse>(`/discovery/jobs/${jobId}`);
      return data;
    },
    cancelJob: async (jobId: string): Promise<DiscoveryJobResponse> => {
      const { data } = await apiClient.post<DiscoveryJobResponse>(`/discovery/jobs/${jobId}/cancel`);
      return data;
    },
  },

  // API Inventory & Mapping
  inventory: {
    listEndpoints: async (
      appId: string,
      filters?: {
        resource?: string;
        category?: string;
        method?: string;
        source?: string;
        search?: string;
        unclassified_only?: boolean;
        incomplete_metadata_only?: boolean;
        skip?: number;
        limit?: number;
      }
    ): Promise<EndpointResponse[]> => {
      const { data } = await apiClient.get<EndpointResponse[]>("/inventory/endpoints", {
        params: { app_id: appId, ...filters },
      });
      return data;
    },
    listResources: async (appId: string): Promise<ApiResourceGroup[]> => {
      const { data } = await apiClient.get<ApiResourceGroup[]>("/inventory/resources", {
        params: { app_id: appId },
      });
      return data;
    },
    getResource: async (resourceName: string, appId: string): Promise<ApiResourceGroup> => {
      const { data } = await apiClient.get<ApiResourceGroup>(`/inventory/resources/${resourceName}`, {
        params: { app_id: appId },
      });
      return data;
    },
    listRelationships: async (
      appId: string,
      filters?: {
        endpoint_id?: string;
        relationship_type?: string;
        provenance?: string;
        skip?: number;
        limit?: number;
      }
    ): Promise<EndpointRelationshipResponse[]> => {
      const { data } = await apiClient.get<EndpointRelationshipResponse[]>("/inventory/relationships", {
        params: { app_id: appId, ...filters },
      });
      return data;
    },
    getStats: async (appId: string): Promise<InventoryOverviewStats> => {
      const { data } = await apiClient.get<InventoryOverviewStats>("/inventory/stats", {
        params: { app_id: appId },
      });
      return data;
    },
    rebuild: async (appId: string): Promise<InventoryRebuildResponse> => {
      const { data } = await apiClient.post<InventoryRebuildResponse>("/inventory/rebuild", null, {
        params: { app_id: appId },
      });
      return data;
    },
    exportUrl: (appId: string, format: "json" | "csv" = "json"): string => {
      return `/api/v1/inventory/export?app_id=${appId}&format=${format}`;
    },
  },

  // Vulnerabilities
  vulnerabilities: {
    list: async (filters?: { app_id?: string; severity?: string }): Promise<VulnerabilityResponse[]> => {
      const { data } = await apiClient.get<VulnerabilityResponse[]>("/vulnerabilities/", { params: filters });
      return data;
    },
    getById: async (id: string): Promise<VulnerabilityResponse> => {
      const { data } = await apiClient.get<VulnerabilityResponse>(`/vulnerabilities/${id}`);
      return data;
    },
    updateStatus: async (id: string, status: string): Promise<VulnerabilityResponse> => {
      const { data } = await apiClient.patch<VulnerabilityResponse>(`/vulnerabilities/${id}/status`, null, {
        params: { new_status: status },
      });
      return data;
    },
  },

  // Attack Chains
  attackChains: {
    list: async (appId?: string): Promise<AttackChainResponse[]> => {
      const params = appId ? { app_id: appId } : {};
      const { data } = await apiClient.get<AttackChainResponse[]>("/attack-chains/", { params });
      return data;
    },
    getById: async (id: string): Promise<AttackChainResponse> => {
      const { data } = await apiClient.get<AttackChainResponse>(`/attack-chains/${id}`);
      return data;
    },
  },

  // Evidence
  evidence: {
    list: async (vulnId?: string): Promise<EvidenceResponse[]> => {
      const params = vulnId ? { vuln_id: vulnId } : {};
      const { data } = await apiClient.get<EvidenceResponse[]>("/evidence/", { params });
      return data;
    },
    getById: async (id: string): Promise<EvidenceResponse> => {
      const { data } = await apiClient.get<EvidenceResponse>(`/evidence/${id}`);
      return data;
    },
  },

  // Regression
  regression: {
    list: async (appId?: string): Promise<RegressionResult[]> => {
      const params = appId ? { app_id: appId } : {};
      const { data } = await apiClient.get<RegressionResult[]>("/regression/", { params });
      return data;
    },
    trigger: async (vulnId: string, appId: string): Promise<RegressionResult> => {
      const { data } = await apiClient.post<RegressionResult>("/regression/run", {
        vulnerability_id: vulnId,
        application_id: appId,
      });
      return data;
    },
  },

  // Reports (Feature 21: Vulnerability Reports)
  reports: {
    getMetrics: async (appId?: string): Promise<ReportDashboardMetrics> => {
      const params = appId ? { application_id: appId } : {};
      const { data } = await apiClient.get<ReportDashboardMetrics>("/reports/metrics", { params });
      return data;
    },
    getSummary: async (appId?: string) => {
      const params = appId ? { app_id: appId } : {};
      const { data } = await apiClient.get("/reports/summary", { params });
      return data;
    },
    listReports: async (params?: {
      search?: string;
      severity?: string;
      status?: string;
      application_id?: string;
      scan_id?: string;
      start_date?: string;
      end_date?: string;
      page?: number;
      limit?: number;
    }): Promise<ReportListPagination> => {
      const { data } = await apiClient.get<ReportListPagination>("/reports", { params });
      return data;
    },
    getReport: async (reportId: string): Promise<VulnerabilityReportDetail> => {
      const { data } = await apiClient.get<VulnerabilityReportDetail>(`/reports/${encodeURIComponent(reportId)}`);
      return data;
    },
    generateReport: async (vulnId: string): Promise<VulnerabilityReportDetail> => {
      const { data } = await apiClient.post<VulnerabilityReportDetail>(`/reports/generate/${vulnId}`);
      return data;
    },
    generateAllForScan: async (scanId: string): Promise<VulnerabilityReportDetail[]> => {
      const { data } = await apiClient.post<VulnerabilityReportDetail[]>(`/reports/scan/${scanId}/generate-all`);
      return data;
    },
    updateStatus: async (
      reportId: string,
      payload: ReportStatusUpdateRequest
    ): Promise<VulnerabilityReportDetail> => {
      const { data } = await apiClient.patch<VulnerabilityReportDetail>(
        `/reports/${encodeURIComponent(reportId)}/status`,
        payload
      );
      return data;
    },
    getStatusHistory: async (reportId: string): Promise<StatusHistoryItem[]> => {
      const { data } = await apiClient.get<StatusHistoryItem[]>(
        `/reports/${encodeURIComponent(reportId)}/history`
      );
      return data;
    },
    exportReport: async (reportId: string, format: "pdf" | "json"): Promise<Blob | any> => {
      const response = await apiClient.get(`/reports/${encodeURIComponent(reportId)}/export`, {
        params: { format },
        responseType: format === "pdf" ? "blob" : "json",
      });
      return response.data;
    },
  },

  // Settings & Safety
  settings: {
    getSafetyPolicy: async () => {
      const { data } = await apiClient.get("/settings/safety-policy");
      return data;
    },
    listScopePermissions: async (appId?: string): Promise<ScopePermissionResponse[]> => {
      const params = appId ? { app_id: appId } : {};
      const { data } = await apiClient.get<ScopePermissionResponse[]>("/settings/scope", { params });
      return data;
    },
    listAuditLogs: async (params?: Record<string, any>): Promise<AuditLogResponse[]> => {
      const { data } = await apiClient.get<AuditLogResponse[]>("/settings/audit-logs", { params });
      return data;
    },
    getAuditOverview: async (): Promise<AuditOverviewResponse> => {
      const { data } = await apiClient.get<AuditOverviewResponse>("/settings/audit-logs/overview");
      return data;
    },
    verifyAuditIntegrity: async (): Promise<AuditIntegrityVerificationResponse> => {
      const { data } = await apiClient.get<AuditIntegrityVerificationResponse>("/settings/audit-logs/verify-integrity");
      return data;
    },
    getAuditEvent: async (id: string): Promise<AuditLogResponse> => {
      const { data } = await apiClient.get<AuditLogResponse>(`/settings/audit-logs/${id}`);
      return data;
    },
    exportAuditLogs: async (): Promise<any[]> => {
      const { data } = await apiClient.get<any[]>("/settings/audit-logs/export");
      return data;
    },
    listExecutionHistory: async (params?: Record<string, any>): Promise<ScanExecutionRecordResponse[]> => {
      const { data } = await apiClient.get<ScanExecutionRecordResponse[]>("/settings/execution-history", { params });
      return data;
    },
    getScanExecutionHistory: async (scanId: string): Promise<ScanExecutionRecordResponse> => {
      const { data } = await apiClient.get<ScanExecutionRecordResponse>(`/settings/execution-history/${scanId}`);
      return data;
    },
    // Feature 26: Scope, Permission & Safety Management
    listScopes: async (orgId?: string): Promise<ScopePolicyResponse[]> => {
      const params = orgId ? { org_id: orgId } : {};
      const { data } = await apiClient.get<ScopePolicyResponse[]>("/settings/scopes", { params });
      return data;
    },
    getScope: async (appId: string): Promise<ScopePolicyResponse> => {
      const { data } = await apiClient.get<ScopePolicyResponse>(`/settings/scopes/${appId}`);
      return data;
    },
    createOrUpdateScope: async (appId: string, payload: ScopePolicyCreate): Promise<ScopePolicyResponse> => {
      const { data } = await apiClient.post<ScopePolicyResponse>(`/settings/scopes/${appId}`, payload);
      return data;
    },
    updateScope: async (appId: string, payload: ScopePolicyUpdate): Promise<ScopePolicyResponse> => {
      const { data } = await apiClient.put<ScopePolicyResponse>(`/settings/scopes/${appId}`, payload);
      return data;
    },
    authorizeScope: async (appId: string, payload: ScopeAuthorizeRequest): Promise<ScopePolicyResponse> => {
      const { data } = await apiClient.post<ScopePolicyResponse>(`/settings/scopes/${appId}/authorize`, payload);
      return data;
    },
    suspendScope: async (appId: string, payload: ScopeSuspendRequest): Promise<ScopePolicyResponse> => {
      const { data } = await apiClient.post<ScopePolicyResponse>(`/settings/scopes/${appId}/suspend`, payload);
      return data;
    },
    revokeScope: async (appId: string, payload: ScopeRevokeRequest): Promise<ScopePolicyResponse> => {
      const { data } = await apiClient.post<ScopePolicyResponse>(`/settings/scopes/${appId}/revoke`, payload);
      return data;
    },
    validateTest: async (payload: TestValidationRequest): Promise<TestValidationResult> => {
      const { data } = await apiClient.post<TestValidationResult>("/settings/validate-test", payload);
      return data;
    },
    listBlockedExecutions: async (appId?: string): Promise<BlockedExecutionResponse[]> => {
      const params = appId ? { app_id: appId } : {};
      const { data } = await apiClient.get<BlockedExecutionResponse[]>("/settings/blocked-executions", { params });
      return data;
    },
  },

  // Health
  health: async () => {
    const { data } = await apiClient.get("/health");
    return data;
  },
};

