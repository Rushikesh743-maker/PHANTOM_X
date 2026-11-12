import React, { useState, useEffect, useCallback } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  Compass,
  Play,
  Upload,
  Key,
  Globe,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  Trash2,
  Eye,
  RefreshCw,
  Search,
  Filter,
  X,
  Layers,
  BarChart3,
  FolderTree,
  GitFork,
  Download,
  FileSpreadsheet,
  FileJson,
} from "lucide-react";
import { PageHeader } from "../components/common/PageHeader";
import { EmptyState } from "../components/common/EmptyState";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { DiscoveryImportModal, EndpointDetailsModal } from "../components/discovery";
import {
  InventoryOverviewView,
  ResourceMappingView,
  RelationshipMappingView,
} from "../components/inventory";
import { api } from "../services/api";
import {
  ApplicationResponse,
  EndpointResponse,
  DiscoverySummaryResponse,
  InventoryOverviewStats,
  ApiResourceGroup,
  EndpointRelationshipResponse,
} from "../types";

type InventoryTab = "inventory" | "overview" | "resources" | "relationships";

const CATEGORY_LABELS: Record<string, string> = {
  AUTH_IDENTITY: "Auth & Identity",
  USER_MANAGEMENT: "User Management",
  ACCOUNT_MANAGEMENT: "Account Management",
  ADMIN_OPERATIONS: "Admin Operations",
  FILE_MANAGEMENT: "Files & Documents",
  PAYMENT_TRANSACTION: "Payments & Billing",
  DATA_RETRIEVAL: "Data Retrieval",
  DATA_MODIFICATION: "Data Modification",
  REPORTING_ANALYTICS: "Reporting & Analytics",
  UNCLASSIFIED: "Unclassified",
};

export const ApiDiscoveryPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const urlAppId = searchParams.get("app_id");

  const [activeTab, setActiveTab] = useState<InventoryTab>("inventory");
  const [applications, setApplications] = useState<ApplicationResponse[]>([]);
  const [selectedAppId, setSelectedAppId] = useState<string>("");
  const [endpoints, setEndpoints] = useState<EndpointResponse[]>([]);
  const [stats, setStats] = useState<InventoryOverviewStats | null>(null);
  const [resources, setResources] = useState<ApiResourceGroup[]>([]);
  const [relationships, setRelationships] = useState<EndpointRelationshipResponse[]>([]);

  const [isLoadingApps, setIsLoadingApps] = useState(true);
  const [isLoadingEndpoints, setIsLoadingEndpoints] = useState(false);
  const [isLoadingInventory, setIsLoadingInventory] = useState(false);
  const [isTriggering, setIsTriggering] = useState(false);
  const [isRebuilding, setIsRebuilding] = useState(false);

  // Filters & Search for Endpoint Inventory Tab
  const [search, setSearch] = useState("");
  const [selectedMethod, setSelectedMethod] = useState("ALL");
  const [selectedSource, setSelectedSource] = useState("ALL");
  const [selectedCategory, setSelectedCategory] = useState("ALL");
  const [unclassifiedOnly, setUnclassifiedOnly] = useState(false);

  // Modals & Feedback
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [selectedEndpoint, setSelectedEndpoint] = useState<EndpointResponse | null>(null);
  const [executionSummary, setExecutionSummary] = useState<DiscoverySummaryResponse | null>(null);
  const [rebuildNotification, setRebuildNotification] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Fetch applications list
  const fetchApplications = useCallback(async () => {
    try {
      setIsLoadingApps(true);
      setErrorMessage(null);
      const data = await api.applications.list();
      setApplications(data);

      if (data.length > 0) {
        if (urlAppId && data.some((a) => a.id === urlAppId)) {
          setSelectedAppId(urlAppId);
        } else if (!selectedAppId) {
          setSelectedAppId(data[0].id);
        }
      }
    } catch (err: any) {
      setErrorMessage("Failed to load registered applications. Please ensure backend services are active.");
    } finally {
      setIsLoadingApps(false);
    }
  }, [urlAppId, selectedAppId]);

  useEffect(() => {
    fetchApplications();
  }, [fetchApplications]);

  // Fetch endpoints for selected app
  const fetchEndpoints = useCallback(async () => {
    if (!selectedAppId) {
      setEndpoints([]);
      return;
    }

    try {
      setIsLoadingEndpoints(true);
      setErrorMessage(null);
      const data = await api.discovery.listEndpoints({ app_id: selectedAppId });
      setEndpoints(data);
    } catch (err: any) {
      setErrorMessage("Failed to load discovered endpoints for the selected application.");
      setEndpoints([]);
    } finally {
      setIsLoadingEndpoints(false);
    }
  }, [selectedAppId]);

  // Fetch inventory mapping data (stats, resources, relationships)
  const fetchInventoryData = useCallback(async () => {
    if (!selectedAppId || !api.inventory) {
      setStats(null);
      setResources([]);
      setRelationships([]);
      return;
    }

    try {
      setIsLoadingInventory(true);
      const [statsData, resData, relData] = await Promise.all([
        api.inventory.getStats ? api.inventory.getStats(selectedAppId).catch(() => null) : Promise.resolve(null),
        api.inventory.listResources ? api.inventory.listResources(selectedAppId).catch(() => []) : Promise.resolve([]),
        api.inventory.listRelationships ? api.inventory.listRelationships(selectedAppId).catch(() => []) : Promise.resolve([]),
      ]);
      setStats(statsData);
      setResources(resData || []);
      setRelationships(relData || []);
    } catch (err: any) {
      console.warn("Could not load inventory mapping data:", err);
    } finally {
      setIsLoadingInventory(false);
    }
  }, [selectedAppId]);

  useEffect(() => {
    fetchEndpoints();
    fetchInventoryData();
  }, [fetchEndpoints, fetchInventoryData]);

  const selectedApp = applications.find((a) => a.id === selectedAppId) || null;

  // Trigger automated discovery
  const handleTriggerDiscovery = async () => {
    if (!selectedApp) return;

    try {
      setIsTriggering(true);
      setErrorMessage(null);
      const summary = await api.discovery.trigger(selectedApp.id);
      setExecutionSummary(summary);
      await Promise.all([fetchEndpoints(), fetchInventoryData()]);
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || "Discovery execution failed.";
      setErrorMessage(msg);
    } finally {
      setIsTriggering(false);
    }
  };

  // Rebuild inventory mappings (categorization, resources, relationships)
  const handleRebuildMappings = async () => {
    if (!selectedAppId || !api.inventory?.rebuild) return;

    try {
      setIsRebuilding(true);
      setErrorMessage(null);
      setRebuildNotification(null);
      const res = await api.inventory.rebuild(selectedAppId);
      const classifiedCount = res.endpoints_classified ?? (res as any).classified_endpoints_count ?? 0;
      const relsCount = res.relationships_created ?? (res as any).created_relationships_count ?? 0;
      setRebuildNotification(
        `Inventory rebuilt successfully: classified ${classifiedCount} endpoints, created ${relsCount} relationship dependencies.`
      );
      await Promise.all([fetchEndpoints(), fetchInventoryData()]);
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || "Failed to rebuild API inventory mappings.";
      setErrorMessage(msg);
    } finally {
      setIsRebuilding(false);
    }
  };

  // Export inventory in JSON or CSV
  const handleExport = async (format: "json" | "csv") => {
    if (!selectedAppId) return;

    try {
      const token = localStorage.getItem("access_token");
      const response = await fetch(`/api/v1/inventory/export?app_id=${selectedAppId}&format=${format}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!response.ok) {
        throw new Error(`Export failed with HTTP status ${response.status}`);
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `api-inventory-${selectedAppId.slice(0, 8)}.${format}`);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      setErrorMessage("Export error: " + (err.message || "Unable to download export file."));
    }
  };

  // Delete an individual endpoint
  const handleDeleteEndpoint = async (endpointId: string) => {
    if (!window.confirm("Are you sure you want to remove this endpoint from the discovered inventory?")) {
      return;
    }

    try {
      await api.discovery.deleteEndpoint(endpointId);
      setEndpoints((prev) => prev.filter((e) => e.id !== endpointId));
      fetchInventoryData();
    } catch (err: any) {
      setErrorMessage("Failed to delete endpoint.");
    }
  };

  // Inspect endpoint by ID (used by sub-views)
  const handleInspectEndpointById = (endpointId: string) => {
    const ep = endpoints.find((e) => e.id === endpointId);
    if (ep) {
      setSelectedEndpoint(ep);
    }
  };

  // Client-side filtering for Endpoint Inventory Tab
  const filteredEndpoints = endpoints.filter((ep) => {
    const rawMeta = ep.raw_metadata || {};
    const cat = rawMeta.category || "UNCLASSIFIED";

    const matchesSearch =
      ep.path.toLowerCase().includes(search.toLowerCase()) ||
      ep.method.toLowerCase().includes(search.toLowerCase()) ||
      (rawMeta.resource_name || "").toLowerCase().includes(search.toLowerCase()) ||
      (cat || "").toLowerCase().includes(search.toLowerCase());

    const matchesMethod = selectedMethod === "ALL" || ep.method.toUpperCase() === selectedMethod;

    const epSource = (rawMeta.discovery_source || "").toUpperCase();
    const matchesSource = selectedSource === "ALL" || epSource === selectedSource;

    const matchesCategory = selectedCategory === "ALL" || cat === selectedCategory;

    const matchesUnclassified = !unclassifiedOnly || cat === "UNCLASSIFIED";

    return matchesSearch && matchesMethod && matchesSource && matchesCategory && matchesUnclassified;
  });

  const methodBadgeColors: Record<string, string> = {
    GET: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
    POST: "bg-cyan-500/10 text-cyan-400 border-cyan-500/30",
    PUT: "bg-amber-500/10 text-amber-400 border-amber-500/30",
    PATCH: "bg-orange-500/10 text-orange-400 border-orange-500/30",
    DELETE: "bg-rose-500/10 text-rose-400 border-rose-500/30",
    OPTIONS: "bg-slate-500/10 text-slate-400 border-slate-500/30",
    HEAD: "bg-purple-500/10 text-purple-400 border-purple-500/30",
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="API Endpoint Inventory & Discovery"
        description="Autonomous surface reconnaissance, OpenAPI/Swagger parsing, Postman collection extraction, HAR traffic analysis, and API relationship mapping."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            {/* Export Actions */}
            <div className="flex items-center rounded-lg border border-slate-700 bg-slate-900 overflow-hidden">
              <button
                onClick={() => handleExport("json")}
                disabled={!selectedApp || endpoints.length === 0}
                title="Export inventory as JSON"
                className="inline-flex items-center gap-1.5 px-2.5 py-1.5 hover:bg-slate-800 disabled:opacity-50 text-slate-300 text-xs transition-colors"
              >
                <Download className="w-3.5 h-3.5 text-cyan-400" />
                <span>JSON</span>
              </button>
              <div className="w-[1px] h-4 bg-slate-700" />
              <button
                onClick={() => handleExport("csv")}
                disabled={!selectedApp || endpoints.length === 0}
                title="Export inventory as CSV"
                className="inline-flex items-center gap-1.5 px-2.5 py-1.5 hover:bg-slate-800 disabled:opacity-50 text-slate-300 text-xs transition-colors"
              >
                <span>CSV</span>
              </button>
            </div>

            {/* Rebuild Mappings */}
            <button
              onClick={handleRebuildMappings}
              disabled={!selectedApp || isRebuilding || endpoints.length === 0}
              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-indigo-700/50 bg-indigo-950/40 hover:bg-indigo-900/50 disabled:opacity-50 text-indigo-200 font-medium text-xs transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-indigo-400 ${isRebuilding ? "animate-spin" : ""}`} />
              <span>{isRebuilding ? "Rebuilding..." : "Rebuild Mappings"}</span>
            </button>

            {/* Import Spec / Traffic */}
            <button
              onClick={() => setIsImportModalOpen(true)}
              disabled={!selectedApp}
              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-900 hover:bg-slate-800 disabled:opacity-50 text-slate-200 font-medium text-xs transition-colors"
            >
              <Upload className="w-3.5 h-3.5 text-cyan-400" />
              <span>Import Spec / Traffic</span>
            </button>

            {/* Trigger Discovery */}
            <button
              onClick={handleTriggerDiscovery}
              disabled={!selectedApp || isTriggering}
              className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-slate-950 font-semibold text-xs transition-colors shadow-sm"
            >
              <Play className={`w-3.5 h-3.5 ${isTriggering ? "animate-spin" : ""}`} />
              <span>{isTriggering ? "Discovering..." : "Trigger Discovery"}</span>
            </button>
          </div>
        }
      />

      {/* Error Banner */}
      {errorMessage && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-lg flex items-start justify-between text-xs text-rose-300">
          <div className="flex items-start gap-2.5">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <span>{errorMessage}</span>
          </div>
          <button
            onClick={() => setErrorMessage(null)}
            className="text-rose-400 hover:text-rose-200 p-0.5"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Rebuild Notification Banner */}
      {rebuildNotification && (
        <div className="p-4 bg-indigo-950/40 border border-indigo-700/50 rounded-lg flex items-start justify-between text-xs text-indigo-300">
          <div className="flex items-start gap-2.5">
            <CheckCircle2 className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
            <span>{rebuildNotification}</span>
          </div>
          <button
            onClick={() => setRebuildNotification(null)}
            className="text-indigo-400 hover:text-indigo-200 p-0.5"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Target Application Selector Bar */}
      <div className="p-4 bg-phantom-900 border border-slate-800 rounded-xl space-y-3">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3 w-full sm:w-auto">
            <label className="text-xs font-semibold text-slate-300 shrink-0 flex items-center gap-1.5">
              <Globe className="w-3.5 h-3.5 text-cyan-400" />
              <span>Target Application:</span>
            </label>
            {isLoadingApps ? (
              <div className="text-xs text-slate-400">Loading applications...</div>
            ) : applications.length === 0 ? (
              <div className="text-xs text-amber-400 flex items-center gap-2">
                <span>No applications registered.</span>
                <Link to="/applications" className="text-cyan-400 underline font-semibold">
                  Register Target Application
                </Link>
              </div>
            ) : (
              <select
                value={selectedAppId}
                onChange={(e) => setSelectedAppId(e.target.value)}
                className="w-full sm:w-72 px-3 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-xs font-medium text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                {applications.map((app) => (
                  <option key={app.id} value={app.id}>
                    {app.name} ({app.environment_name || "staging"})
                  </option>
                ))}
              </select>
            )}
          </div>

          {selectedApp && (
            <div className="flex items-center gap-3 text-xs">
              <span className="text-slate-400 font-mono text-[11px] truncate max-w-xs">
                {selectedApp.target_url}
              </span>
              <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                <ShieldCheck className="w-3 h-3" />
                <span>Authorized Scope</span>
              </span>
              <button
                onClick={() => {
                  fetchEndpoints();
                  fetchInventoryData();
                }}
                title="Refresh endpoints and inventory"
                className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Execution Summary Alert */}
      {executionSummary && (
        <div className="p-4 bg-cyan-950/30 border border-cyan-800/40 rounded-xl flex items-start justify-between text-xs text-slate-300">
          <div className="space-y-1">
            <div className="font-semibold text-cyan-300 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-cyan-400" />
              <span>Discovery Execution Completed ({executionSummary.source_type})</span>
            </div>
            <p className="text-slate-400">{executionSummary.message}</p>
            <div className="flex items-center gap-4 text-[11px] pt-1 text-slate-400">
              <span>
                Found: <strong className="text-slate-200">{executionSummary.endpoints_found}</strong>
              </span>
              <span>
                In Scope:{" "}
                <strong className="text-emerald-400">{executionSummary.endpoints_in_scope}</strong>
              </span>
              <span>
                Out of Scope:{" "}
                <strong className="text-amber-400">{executionSummary.endpoints_out_of_scope}</strong>
              </span>
            </div>
          </div>
          <button
            onClick={() => setExecutionSummary(null)}
            className="text-slate-400 hover:text-slate-200 p-1"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="flex items-center gap-1 border-b border-slate-800 pb-2">
        <button
          onClick={() => setActiveTab("inventory")}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            activeTab === "inventory"
              ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 font-semibold"
              : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          <span>Endpoint Inventory</span>
          <span className="px-1.5 py-0.2 rounded-full bg-slate-800 text-[10px] text-slate-300">
            {endpoints.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab("overview")}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            activeTab === "overview"
              ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 font-semibold"
              : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
          }`}
        >
          <BarChart3 className="w-3.5 h-3.5" />
          <span>Overview Analytics</span>
        </button>

        <button
          onClick={() => setActiveTab("resources")}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            activeTab === "resources"
              ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 font-semibold"
              : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
          }`}
        >
          <FolderTree className="w-3.5 h-3.5" />
          <span>Resource Mapping</span>
          <span className="px-1.5 py-0.2 rounded-full bg-slate-800 text-[10px] text-slate-300">
            {resources.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab("relationships")}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            activeTab === "relationships"
              ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 font-semibold"
              : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
          }`}
        >
          <GitFork className="w-3.5 h-3.5" />
          <span>Relationship Graph</span>
          <span className="px-1.5 py-0.2 rounded-full bg-slate-800 text-[10px] text-slate-300">
            {relationships.length}
          </span>
        </button>
      </div>

      {/* Main Tab Content */}
      {isLoadingApps || isLoadingEndpoints ? (
        <LoadingSpinner />
      ) : applications.length === 0 ? (
        <EmptyState
          icon={Compass}
          title="No Applications Available"
          description="Register a target application to define its authorized boundary and discover endpoints."
          action={
            <Link
              to="/applications"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-semibold text-xs transition-colors"
            >
              <span>Register Target Application</span>
            </Link>
          }
        />
      ) : activeTab === "overview" ? (
        <InventoryOverviewView
          stats={stats}
          isLoading={isLoadingInventory}
          onRebuild={handleRebuildMappings}
          isRebuilding={isRebuilding}
          onExport={handleExport}
        />
      ) : activeTab === "resources" ? (
        <ResourceMappingView
          resources={resources}
          isLoading={isLoadingInventory}
          onSelectEndpoint={handleInspectEndpointById}
          endpoints={endpoints}
        />
      ) : activeTab === "relationships" ? (
        <RelationshipMappingView
          relationships={relationships}
          isLoading={isLoadingInventory}
          onRebuild={handleRebuildMappings}
          isRebuilding={isRebuilding}
          onSelectEndpoint={handleInspectEndpointById}
        />
      ) : (
        /* Endpoint Inventory Tab */
        <div className="space-y-4">
          {/* Search & Filter Bar */}
          <div className="flex flex-col gap-3">
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
              <div className="relative flex-1">
                <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Filter by endpoint path, method, or query..."
                  className="w-full pl-9 pr-4 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                />
              </div>

              {/* Method Filter */}
              <div className="flex items-center gap-1 overflow-x-auto pb-1 sm:pb-0">
                {["ALL", "GET", "POST", "PUT", "PATCH", "DELETE"].map((m) => (
                  <button
                    key={m}
                    onClick={() => setSelectedMethod(m)}
                    className={`px-2.5 py-1 text-[11px] font-mono font-medium rounded-lg border transition-all ${
                      selectedMethod === m
                        ? "bg-cyan-500/10 border-cyan-500/40 text-cyan-300 font-bold"
                        : "bg-slate-900/60 border-slate-800 text-slate-400 hover:text-slate-300"
                    }`}
                  >
                    {m}
                  </button>
                ))}
              </div>

              {/* Source Filter */}
              <div className="flex items-center gap-1">
                {["ALL", "OPENAPI", "POSTMAN", "HAR"].map((s) => (
                  <button
                    key={s}
                    onClick={() => setSelectedSource(s)}
                    className={`px-2.5 py-1 text-[11px] font-medium rounded-lg border transition-all ${
                      selectedSource === s
                        ? "bg-purple-500/10 border-purple-500/40 text-purple-300 font-bold"
                        : "bg-slate-900/60 border-slate-800 text-slate-400 hover:text-slate-300"
                    }`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>

            {/* Secondary Filter Row: Category & Unclassified Toggle */}
            <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
              <div className="flex items-center gap-2">
                <label
                  htmlFor="inventory-category-select"
                  className="text-[11px] text-slate-400 flex items-center gap-1 font-mono"
                >
                  <Filter className="w-3 h-3 text-cyan-400" />
                  <span>Category:</span>
                </label>
                <select
                  id="inventory-category-select"
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  className="bg-slate-900 border border-slate-800 rounded px-2.5 py-1 text-[11px] text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
                >
                  <option value="ALL">All Categories</option>
                  {Object.entries(CATEGORY_LABELS).map(([catKey, catLabel]) => (
                    <option key={catKey} value={catKey}>
                      {catLabel}
                    </option>
                  ))}
                </select>

                <label className="inline-flex items-center gap-1.5 text-[11px] text-slate-400 cursor-pointer ml-3 font-mono">
                  <input
                    type="checkbox"
                    checked={unclassifiedOnly}
                    onChange={(e) => setUnclassifiedOnly(e.target.checked)}
                    className="rounded bg-slate-900 border-slate-800 text-cyan-500 focus:ring-0 w-3.5 h-3.5"
                  />
                  <span>Unclassified Only</span>
                </label>
              </div>

              <div className="text-[11px] text-slate-500 font-mono">
                Matching: <strong className="text-slate-300">{filteredEndpoints.length}</strong> of{" "}
                <strong className="text-slate-300">{endpoints.length}</strong> endpoints
              </div>
            </div>
          </div>

          {filteredEndpoints.length === 0 ? (
            <EmptyState
              icon={Compass}
              title="No Endpoints Discovered"
              description={
                search || selectedMethod !== "ALL" || selectedSource !== "ALL" || selectedCategory !== "ALL"
                  ? "No endpoints match the current search and filter criteria."
                  : "No endpoints have been discovered for this application yet. Import an OpenAPI specification, Postman collection, or HAR traffic log to discover attack surfaces."
              }
              action={
                <button
                  onClick={() => setIsImportModalOpen(true)}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-semibold text-xs transition-colors"
                >
                  <Upload className="w-3.5 h-3.5" />
                  <span>Import API Specification</span>
                </button>
              }
            />
          ) : (
            <div className="bg-phantom-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-slate-950/80 border-b border-slate-800 text-slate-400">
                    <tr>
                      <th className="p-3 w-20">METHOD</th>
                      <th className="p-3">ENDPOINT PATH</th>
                      <th className="p-3 w-36">CATEGORY</th>
                      <th className="p-3 w-24">SOURCE</th>
                      <th className="p-3 w-24">AUTH</th>
                      <th className="p-3 w-28">RESPONSES</th>
                      <th className="p-3 w-24">DISCOVERED</th>
                      <th className="p-3 w-20 text-right">ACTIONS</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {filteredEndpoints.map((ep) => {
                      const mColor = methodBadgeColors[ep.method] || "bg-slate-800 text-slate-400";
                      const rawMeta = ep.raw_metadata || {};
                      const category = rawMeta.category || "UNCLASSIFIED";
                      const resource = rawMeta.resource_name;

                      return (
                        <tr key={ep.id} className="hover:bg-slate-800/30 transition-colors">
                          <td className="p-3">
                            <span className={`px-2 py-0.5 rounded border text-[11px] font-bold ${mColor}`}>
                              {ep.method}
                            </span>
                          </td>
                          <td className="p-3">
                            <div className="flex flex-col gap-0.5">
                              <div className="flex items-center gap-2">
                                <span className="font-semibold text-slate-200">{ep.path}</span>
                                {rawMeta.original_path && rawMeta.original_path !== ep.path && (
                                  <span className="text-[10px] text-slate-500 font-normal">
                                    (obs: {rawMeta.original_path})
                                  </span>
                                )}
                              </div>
                              {resource && (
                                <div className="text-[10px] text-slate-500 font-mono">
                                  resource: <span className="text-cyan-400 font-medium">/{resource}</span>
                                  {rawMeta.parent_resource_name && (
                                    <span className="text-slate-600"> (parent: /{rawMeta.parent_resource_name})</span>
                                  )}
                                </div>
                              )}
                            </div>
                          </td>
                          <td className="p-3">
                            <div className="flex items-center gap-1.5">
                              <span className="px-2 py-0.5 rounded bg-slate-800/80 border border-slate-700/60 text-slate-300 text-[10px] font-sans font-medium">
                                {CATEGORY_LABELS[category] || category}
                              </span>
                              {rawMeta.category_confidence !== undefined && (
                                <span
                                  className="text-[10px] text-cyan-400 font-mono"
                                  title={`Confidence: ${Math.round(rawMeta.category_confidence * 100)}%`}
                                >
                                  {Math.round(rawMeta.category_confidence * 100)}%
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="p-3">
                            <span className="px-2 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/30 text-[10px] font-sans font-medium">
                              {rawMeta.discovery_source || "SPEC"}
                            </span>
                          </td>
                          <td className="p-3 font-sans">
                            {ep.auth_required ? (
                              <span className="text-amber-400 flex items-center gap-1 font-medium">
                                <Key className="w-3 h-3" />
                                <span>Required</span>
                              </span>
                            ) : (
                              <span className="text-emerald-400 flex items-center gap-1 font-medium">
                                <ShieldCheck className="w-3 h-3" />
                                <span>Public</span>
                              </span>
                            )}
                          </td>
                          <td className="p-3">
                            <div className="flex flex-wrap gap-1">
                              {ep.response_codes && ep.response_codes.length > 0 ? (
                                ep.response_codes.slice(0, 3).map((c) => (
                                  <span
                                    key={c}
                                    className="px-1.5 py-0.2 rounded bg-slate-800 text-slate-300 text-[10px]"
                                  >
                                    {c}
                                  </span>
                                ))
                              ) : (
                                <span className="text-slate-500 text-[10px]">200</span>
                              )}
                            </div>
                          </td>
                          <td className="p-3 text-slate-500 text-[11px] font-sans">
                            {new Date(ep.created_at).toLocaleDateString()}
                          </td>
                          <td className="p-3 text-right">
                            <div className="flex items-center justify-end gap-1.5">
                              <button
                                onClick={() => setSelectedEndpoint(ep)}
                                title="Inspect endpoint specifications"
                                className="p-1.5 text-slate-400 hover:text-cyan-400 hover:bg-slate-800 rounded transition-colors"
                              >
                                <Eye className="w-3.5 h-3.5" />
                              </button>
                              <button
                                onClick={() => handleDeleteEndpoint(ep.id)}
                                title="Remove from inventory"
                                className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded transition-colors"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Table Footer */}
              <div className="px-4 py-3 bg-slate-950/60 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400 font-sans">
                <div>
                  Showing <strong>{filteredEndpoints.length}</strong> of{" "}
                  <strong>{endpoints.length}</strong> discovered endpoints
                </div>
                {selectedApp && (
                  <div className="font-mono text-[11px] text-slate-500">
                    Scope rate limit: {selectedApp.scope?.rate_limit_rps || 50} RPS
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Import Modal */}
      <DiscoveryImportModal
        isOpen={isImportModalOpen}
        onClose={() => setIsImportModalOpen(false)}
        selectedApp={selectedApp}
        onImportSuccess={(summary) => {
          setExecutionSummary(summary);
          fetchEndpoints();
          fetchInventoryData();
        }}
      />

      {/* Endpoint Details Modal */}
      <EndpointDetailsModal
        endpoint={selectedEndpoint}
        isOpen={selectedEndpoint !== null}
        onClose={() => setSelectedEndpoint(null)}
      />
    </div>
  );
};
