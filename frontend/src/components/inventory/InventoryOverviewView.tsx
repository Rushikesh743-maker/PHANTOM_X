import React from "react";
import {
  Layers,
  Database,
  GitFork,
  AlertCircle,
  CheckCircle2,
  RefreshCw,
  Download,
  Share2,
} from "lucide-react";
import { InventoryOverviewStats } from "../../types";

interface InventoryOverviewViewProps {
  stats: InventoryOverviewStats | null;
  isLoading: boolean;
  onRebuild: () => void;
  isRebuilding: boolean;
  onExport: (format: "json" | "csv") => void;
}

const CATEGORY_NAMES: Record<string, string> = {
  AUTH_IDENTITY: "Authentication & Identity",
  USER_MANAGEMENT: "User Management",
  ACCOUNT_MANAGEMENT: "Account Management",
  ADMIN_OPERATIONS: "Admin Operations",
  FILE_MANAGEMENT: "File & Documents",
  PAYMENT_TRANSACTION: "Payments & Billing",
  DATA_RETRIEVAL: "Data Retrieval",
  DATA_MODIFICATION: "Data Modification",
  REPORTING_ANALYTICS: "Reporting & Analytics",
  UNCLASSIFIED: "Unclassified / Other",
};

export const InventoryOverviewView: React.FC<InventoryOverviewViewProps> = ({
  stats,
  isLoading,
  onRebuild,
  isRebuilding,
  onExport,
}) => {
  if (isLoading || !stats) {
    return (
      <div className="p-12 text-center">
        <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin mx-auto mb-3" />
        <p className="text-slate-400 font-mono text-sm">Computing API inventory analytics...</p>
      </div>
    );
  }

  const total = stats.total_endpoints || 1;

  return (
    <div className="space-y-6">
      {/* Top Controls Banner */}
      <div className="flex items-center justify-between bg-slate-900/60 p-4 rounded-lg border border-slate-800">
        <div>
          <h3 className="text-base font-semibold text-slate-100">API Inventory Overview</h3>
          <p className="text-xs text-slate-400">
            Real-time attack surface categorization, resource clustering, and dependency graph.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onRebuild}
            disabled={isRebuilding}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded text-xs font-mono transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRebuilding ? "animate-spin text-cyan-400" : ""}`} />
            <span>{isRebuilding ? "Rebuilding..." : "Rebuild Mappings"}</span>
          </button>
          <button
            onClick={() => onExport("json")}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded text-xs font-mono transition-colors"
          >
            <Download className="w-3.5 h-3.5 text-cyan-400" />
            <span>Export JSON</span>
          </button>
          <button
            onClick={() => onExport("csv")}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded text-xs font-mono transition-colors"
          >
            <Download className="w-3.5 h-3.5 text-emerald-400" />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-phantom-900/50 border border-slate-800/80 rounded-lg p-4">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2 font-mono">
            <span>TOTAL ENDPOINTS</span>
            <Database className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-slate-100">{stats.total_endpoints}</div>
          <div className="text-[11px] text-slate-500 mt-1 font-mono">
            {stats.documented_count} documented • {stats.observed_count} observed
          </div>
        </div>

        <div className="bg-phantom-900/50 border border-slate-800/80 rounded-lg p-4">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2 font-mono">
            <span>UNIQUE RESOURCES</span>
            <Layers className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-slate-100">{stats.unique_resources}</div>
          <div className="text-[11px] text-slate-500 mt-1 font-mono">Logical domain entities</div>
        </div>

        <div className="bg-phantom-900/50 border border-slate-800/80 rounded-lg p-4">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2 font-mono">
            <span>MAPPED RELATIONSHIPS</span>
            <GitFork className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-slate-100">{stats.total_relationships_count}</div>
          <div className="text-[11px] text-slate-500 mt-1 font-mono">
            {stats.inferred_relationships_count} inferred • {stats.total_relationships_count - stats.inferred_relationships_count} documented
          </div>
        </div>

        <div className="bg-phantom-900/50 border border-slate-800/80 rounded-lg p-4">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2 font-mono">
            <span>CLASSIFICATION HEALTH</span>
            {stats.unclassified_count > 0 ? (
              <AlertCircle className="w-4 h-4 text-amber-400" />
            ) : (
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            )}
          </div>
          <div className="text-2xl font-bold font-mono text-slate-100">
            {Math.round(((stats.total_endpoints - stats.unclassified_count) / total) * 100)}%
          </div>
          <div className="text-[11px] text-slate-500 mt-1 font-mono">
            {stats.unclassified_count} unclassified • {stats.incomplete_metadata_count} partial metadata
          </div>
        </div>
      </div>

      {/* Distributions Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Category Breakdown */}
        <div className="bg-phantom-900/40 border border-slate-800/80 rounded-lg p-5">
          <h4 className="text-sm font-semibold text-slate-200 mb-4 flex items-center gap-2">
            <Share2 className="w-4 h-4 text-cyan-400" />
            <span>Category Distribution</span>
          </h4>
          <div className="space-y-3">
            {Object.entries(stats.category_distribution || {}).map(([cat, count]) => {
              const pct = Math.round((count / total) * 100);
              const label = CATEGORY_NAMES[cat] || cat;
              return (
                <div key={cat} className="space-y-1">
                  <div className="flex justify-between text-xs font-mono">
                    <span className="text-slate-300">{label}</span>
                    <span className="text-slate-400">
                      {count} ({pct}%)
                    </span>
                  </div>
                  <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        cat === "UNCLASSIFIED"
                          ? "bg-amber-500/60"
                          : cat === "AUTH_IDENTITY"
                          ? "bg-purple-500"
                          : cat === "USER_MANAGEMENT"
                          ? "bg-cyan-500"
                          : "bg-emerald-500"
                      }`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* HTTP Methods & Sources */}
        <div className="space-y-6">
          {/* HTTP Methods */}
          <div className="bg-phantom-900/40 border border-slate-800/80 rounded-lg p-5">
            <h4 className="text-sm font-semibold text-slate-200 mb-4">HTTP Method Coverage</h4>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {Object.entries(stats.method_distribution || {}).map(([method, count]) => {
                const colorMap: Record<string, string> = {
                  GET: "text-blue-400 bg-blue-500/10 border-blue-500/20",
                  POST: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
                  PUT: "text-amber-400 bg-amber-500/10 border-amber-500/20",
                  DELETE: "text-rose-400 bg-rose-500/10 border-rose-500/20",
                  PATCH: "text-purple-400 bg-purple-500/10 border-purple-500/20",
                };
                const style = colorMap[method] || "text-slate-400 bg-slate-800 border-slate-700";
                return (
                  <div key={method} className={`p-3 rounded border text-center font-mono ${style}`}>
                    <div className="text-xs font-bold">{method}</div>
                    <div className="text-lg font-bold mt-1 text-slate-100">{count}</div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Discovery Sources */}
          <div className="bg-phantom-900/40 border border-slate-800/80 rounded-lg p-5">
            <h4 className="text-sm font-semibold text-slate-200 mb-4">Discovery Source Provenance</h4>
            <div className="grid grid-cols-3 gap-3 font-mono text-center">
              <div className="p-3 bg-slate-900/80 rounded border border-slate-800">
                <span className="text-xs text-slate-400">DOCUMENTED</span>
                <div className="text-lg font-bold text-cyan-400 mt-1">{stats.documented_count}</div>
              </div>
              <div className="p-3 bg-slate-900/80 rounded border border-slate-800">
                <span className="text-xs text-slate-400">OBSERVED (HAR)</span>
                <div className="text-lg font-bold text-emerald-400 mt-1">{stats.observed_count}</div>
              </div>
              <div className="p-3 bg-slate-900/80 rounded border border-slate-800">
                <span className="text-xs text-slate-400">IMPORTED (POSTMAN)</span>
                <div className="text-lg font-bold text-amber-400 mt-1">{stats.imported_count}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

