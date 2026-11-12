import React, { useState } from "react";
import {
  Search,
  Download,
  Filter,
  Eye,
  Trash2,
  Lock,
  Unlock,
  ShieldCheck,
  AlertTriangle,
} from "lucide-react";
import { EndpointResponse } from "../../types";

interface EndpointInventoryViewProps {
  endpoints: EndpointResponse[];
  isLoading: boolean;
  onSelectEndpoint: (endpointId: string) => void;
  onDeleteEndpoint: (endpointId: string) => void;
  onExport: (format: "json" | "csv") => void;
}

const CATEGORY_NAMES: Record<string, string> = {
  AUTH_IDENTITY: "Auth & Identity",
  USER_MANAGEMENT: "User Management",
  ACCOUNT_MANAGEMENT: "Account Management",
  ADMIN_OPERATIONS: "Admin Operations",
  FILE_MANAGEMENT: "File & Documents",
  PAYMENT_TRANSACTION: "Payments & Billing",
  DATA_RETRIEVAL: "Data Retrieval",
  DATA_MODIFICATION: "Data Modification",
  REPORTING_ANALYTICS: "Reporting & Analytics",
  UNCLASSIFIED: "Unclassified",
};

export const EndpointInventoryView: React.FC<EndpointInventoryViewProps> = ({
  endpoints,
  isLoading,
  onSelectEndpoint,
  onDeleteEndpoint,
  onExport,
}) => {
  const [search, setSearch] = useState("");
  const [selectedMethod, setSelectedMethod] = useState("ALL");
  const [selectedCategory, setSelectedCategory] = useState("ALL");
  const [selectedSource, setSelectedSource] = useState("ALL");
  const [unclassifiedOnly, setUnclassifiedOnly] = useState(false);

  const filtered = endpoints.filter((ep) => {
    const meta = ep.raw_metadata || {};
    const cat = meta.category || "UNCLASSIFIED";

    if (selectedMethod !== "ALL" && ep.method !== selectedMethod) return false;
    if (selectedCategory !== "ALL" && cat !== selectedCategory) return false;
    if (unclassifiedOnly && cat !== "UNCLASSIFIED") return false;

    if (selectedSource !== "ALL") {
      const src = (meta.discovery_source || "").toUpperCase();
      if (src !== selectedSource) return false;
    }

    if (search) {
      const q = search.toLowerCase();
      const pathMatch = ep.path.toLowerCase().includes(q);
      const resMatch = (meta.resource_name || "").toLowerCase().includes(q);
      const descMatch = (meta.description || "").toLowerCase().includes(q);
      const opMatch = (meta.operation_id || "").toLowerCase().includes(q);
      if (!pathMatch && !resMatch && !descMatch && !opMatch) return false;
    }

    return true;
  });

  const getMethodBadge = (method: string) => {
    const colorMap: Record<string, string> = {
      GET: "text-blue-400 bg-blue-500/10 border-blue-500/20",
      POST: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
      PUT: "text-amber-400 bg-amber-500/10 border-amber-500/20",
      DELETE: "text-rose-400 bg-rose-500/10 border-rose-500/20",
      PATCH: "text-purple-400 bg-purple-500/10 border-purple-500/20",
    };
    return (
      <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${colorMap[method] || "text-slate-400 bg-slate-800"}`}>
        {method}
      </span>
    );
  };

  const getCategoryBadge = (meta: Record<string, any>) => {
    const cat = meta.category || "UNCLASSIFIED";
    const conf = meta.category_confidence !== undefined ? Math.round(meta.category_confidence * 100) : 0;
    const label = CATEGORY_NAMES[cat] || cat;

    if (cat === "UNCLASSIFIED") {
      return (
        <span className="inline-flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
          <AlertTriangle className="w-3 h-3" />
          <span>Unclassified</span>
        </span>
      );
    }

    return (
      <span className="inline-flex items-center gap-1.5 text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
        <span className="text-cyan-400 font-semibold">{conf}%</span>
        <span>{label}</span>
      </span>
    );
  };

  return (
    <div className="space-y-4">
      {/* Controls Bar */}
      <div className="bg-slate-900/60 p-4 rounded-lg border border-slate-800 space-y-3">
        {/* Row 1: Search and Export */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search by path, resource, operation ID, or description..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 bg-slate-950 border border-slate-700 rounded text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-mono"
            />
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => onExport("json")}
              className="flex items-center gap-1 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded text-xs font-mono transition-colors"
            >
              <Download className="w-3.5 h-3.5 text-cyan-400" />
              <span>JSON</span>
            </button>
            <button
              onClick={() => onExport("csv")}
              className="flex items-center gap-1 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded text-xs font-mono transition-colors"
            >
              <Download className="w-3.5 h-3.5 text-emerald-400" />
              <span>CSV</span>
            </button>
          </div>
        </div>

        {/* Row 2: Method Pills and Category Filter */}
        <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-800/80">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-xs font-mono text-slate-500 mr-1">METHOD:</span>
            {["ALL", "GET", "POST", "PUT", "DELETE", "PATCH"].map((m) => (
              <button
                key={m}
                onClick={() => setSelectedMethod(m)}
                className={`px-2 py-0.5 rounded text-[11px] font-mono transition-colors ${
                  selectedMethod === m
                    ? "bg-cyan-500 text-slate-950 font-bold"
                    : "bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200"
                }`}
              >
                {m}
              </button>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Category Dropdown */}
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="px-2 py-1 bg-slate-950 border border-slate-700 rounded text-xs text-slate-200 font-mono"
            >
              <option value="ALL">All Categories</option>
              {Object.entries(CATEGORY_NAMES).map(([key, name]) => (
                <option key={key} value={key}>
                  {name}
                </option>
              ))}
            </select>

            {/* Source Dropdown */}
            <select
              value={selectedSource}
              onChange={(e) => setSelectedSource(e.target.value)}
              className="px-2 py-1 bg-slate-950 border border-slate-700 rounded text-xs text-slate-200 font-mono"
            >
              <option value="ALL">All Sources</option>
              <option value="OPENAPI">OpenAPI</option>
              <option value="POSTMAN">Postman</option>
              <option value="HAR">HAR Traffic</option>
              <option value="PASSIVE">Passive</option>
            </select>

            {/* Unclassified Toggle */}
            <label className="flex items-center gap-1.5 text-xs text-slate-400 cursor-pointer select-none font-mono">
              <input
                type="checkbox"
                checked={unclassifiedOnly}
                onChange={(e) => setUnclassifiedOnly(e.target.checked)}
                className="rounded bg-slate-950 border-slate-700 text-cyan-500 focus:ring-0"
              />
              <span>Unclassified Only</span>
            </label>
          </div>
        </div>
      </div>

      {/* Inventory Table */}
      <div className="bg-phantom-900/40 border border-slate-800/80 rounded-lg overflow-hidden">
        <div className="p-3 bg-slate-900/90 border-b border-slate-800 flex items-center justify-between text-xs font-mono text-slate-400">
          <span>SHOWING {filtered.length} OF {endpoints.length} ENDPOINTS</span>
        </div>

        {isLoading ? (
          <div className="p-12 text-center text-slate-400 font-mono text-sm">
            Loading endpoints inventory...
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center text-slate-500 font-mono text-sm">
            No endpoints match current filters.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-3">METHOD</th>
                  <th className="py-2.5 px-3">ENDPOINT PATH</th>
                  <th className="py-2.5 px-3">RESOURCE</th>
                  <th className="py-2.5 px-3">CLASSIFICATION</th>
                  <th className="py-2.5 px-3">AUTH</th>
                  <th className="py-2.5 px-3">SOURCE</th>
                  <th className="py-2.5 px-3 text-right">ACTIONS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filtered.map((ep) => {
                  const meta = ep.raw_metadata || {};
                  const resName = meta.resource_name || "root";
                  const src = (meta.discovery_source || "openapi").toUpperCase();

                  return (
                    <tr key={ep.id} className="hover:bg-slate-900/40 transition-colors">
                      <td className="py-2.5 px-3">{getMethodBadge(ep.method)}</td>
                      <td className="py-2.5 px-3 text-slate-200 font-medium">{ep.path}</td>
                      <td className="py-2.5 px-3">
                        <span className="text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
                          /{resName}
                        </span>
                      </td>
                      <td className="py-2.5 px-3">{getCategoryBadge(meta)}</td>
                      <td className="py-2.5 px-3">
                        {ep.auth_required ? (
                          <span className="text-emerald-400 inline-flex items-center gap-1" title="Authentication required">
                            <Lock className="w-3.5 h-3.5" />
                          </span>
                        ) : (
                          <span className="text-slate-500 inline-flex items-center gap-1" title="Public / Unauthenticated">
                            <Unlock className="w-3.5 h-3.5" />
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 px-3">
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                          {src}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => onSelectEndpoint(ep.id)}
                            title="Inspect complete metadata and schemas"
                            className="p-1 rounded text-slate-400 hover:text-cyan-400 hover:bg-slate-800 transition-colors"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => onDeleteEndpoint(ep.id)}
                            title="Delete endpoint from inventory"
                            className="p-1 rounded text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition-colors"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

