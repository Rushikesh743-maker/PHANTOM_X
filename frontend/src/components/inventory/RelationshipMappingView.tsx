import React, { useState } from "react";
import {
  GitFork,
  ArrowRight,
  ShieldAlert,
  Key,
  Layers,
  Repeat,
  RefreshCw,
  Search,
  Filter,
} from "lucide-react";
import { EndpointRelationshipResponse } from "../../types";

interface RelationshipMappingViewProps {
  relationships: EndpointRelationshipResponse[];
  isLoading: boolean;
  onRebuild: () => void;
  isRebuilding: boolean;
  onSelectEndpoint: (endpointId: string) => void;
}

const TYPE_CONFIG: Record<string, { label: string; color: string; icon: React.FC<{ className?: string }> }> = {
  SAME_RESOURCE: { label: "Same Resource", color: "text-blue-400 bg-blue-500/10 border-blue-500/20", icon: Layers },
  PARENT_CHILD: { label: "Parent - Child", color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20", icon: GitFork },
  READ_WRITE: { label: "Read / Write", color: "text-purple-400 bg-purple-500/10 border-purple-500/20", icon: Repeat },
  AUTH_DEPENDENCY: { label: "Auth Dependency", color: "text-amber-400 bg-amber-500/10 border-amber-500/20", icon: Key },
  SHARED_PARAMETER: { label: "Shared Parameter", color: "text-cyan-400 bg-cyan-500/10 border-cyan-500/20", icon: Layers },
  WORKFLOW_CANDIDATE: { label: "Workflow Transition", color: "text-rose-400 bg-rose-500/10 border-rose-500/20", icon: ArrowRight },
};

export const RelationshipMappingView: React.FC<RelationshipMappingViewProps> = ({
  relationships,
  isLoading,
  onRebuild,
  isRebuilding,
  onSelectEndpoint,
}) => {
  const [selectedType, setSelectedType] = useState<string>("ALL");
  const [selectedProvenance, setSelectedProvenance] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState("");

  const filtered = relationships.filter((rel) => {
    if (selectedType !== "ALL" && rel.relationship_type !== selectedType) return false;
    if (selectedProvenance !== "ALL" && rel.provenance.toUpperCase() !== selectedProvenance) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const srcPath = (rel.source_endpoint_path || "").toLowerCase();
      const tgtPath = (rel.target_endpoint_path || "").toLowerCase();
      const exp = (rel.explanation || "").toLowerCase();
      if (!srcPath.includes(q) && !tgtPath.includes(q) && !exp.includes(q)) return false;
    }
    return true;
  });

  if (isLoading) {
    return (
      <div className="p-12 text-center text-slate-400 font-mono text-sm">
        Analyzing endpoint relationships and dependency graph...
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Controls Bar */}
      <div className="bg-slate-900/60 p-4 rounded-lg border border-slate-800 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <GitFork className="w-4 h-4 text-indigo-400" />
              <span>API Dependency & Relationship Graph ({relationships.length} Mapped)</span>
            </h3>
            <p className="text-xs text-slate-400">
              Correlated execution paths, auth requirements, and state transitions. Inferred relations are distinguished from proven facts.
            </p>
          </div>

          <button
            onClick={onRebuild}
            disabled={isRebuilding}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded text-xs font-mono transition-colors self-start sm:self-auto disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRebuilding ? "animate-spin text-cyan-400" : ""}`} />
            <span>{isRebuilding ? "Analyzing..." : "Re-Analyze Graph"}</span>
          </button>
        </div>

        {/* Filter Pills and Search */}
        <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-800/80">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-xs font-mono text-slate-500 mr-1 flex items-center gap-1">
              <Filter className="w-3 h-3" /> TYPE:
            </span>
            {["ALL", "SAME_RESOURCE", "PARENT_CHILD", "READ_WRITE", "AUTH_DEPENDENCY", "SHARED_PARAMETER", "WORKFLOW_CANDIDATE"].map(
              (type) => (
                <button
                  key={type}
                  onClick={() => setSelectedType(type)}
                  className={`px-2 py-0.5 rounded text-[11px] font-mono transition-colors ${
                    selectedType === type
                      ? "bg-cyan-500 text-slate-950 font-bold"
                      : "bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200"
                  }`}
                >
                  {type.replace("_", " ")}
                </button>
              )
            )}
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto">
            {/* Provenance selector */}
            <select
              value={selectedProvenance}
              onChange={(e) => setSelectedProvenance(e.target.value)}
              className="px-2 py-1 bg-slate-950 border border-slate-700 rounded text-xs text-slate-200 font-mono"
            >
              <option value="ALL">All Evidence Levels</option>
              <option value="DOCUMENTED">Documented</option>
              <option value="INFERRED">Inferred</option>
              <option value="OBSERVED">Observed</option>
            </select>

            <div className="relative">
              <Search className="w-3 h-3 text-slate-500 absolute left-2.5 top-2.5" />
              <input
                type="text"
                placeholder="Search graph..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-7 pr-3 py-1 bg-slate-950 border border-slate-700 rounded text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-mono w-44"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Relationships Flow Cards List */}
      {filtered.length === 0 ? (
        <div className="p-12 text-center bg-phantom-900/30 rounded-lg border border-slate-800">
          <GitFork className="w-8 h-8 text-slate-600 mx-auto mb-2" />
          <p className="text-xs text-slate-400 font-mono">No matching endpoint relationships found.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((rel) => {
            const config = TYPE_CONFIG[rel.relationship_type] || {
              label: rel.relationship_type,
              color: "text-slate-400 bg-slate-800",
              icon: GitFork,
            };
            const Icon = config.icon;
            const provUpper = rel.provenance.toUpperCase();

            return (
              <div
                key={rel.id}
                className="bg-phantom-900/40 border border-slate-800/80 rounded-lg p-4 space-y-3 hover:border-slate-700 transition-colors"
              >
                {/* Visual Connection Flow */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                  {/* Source Node */}
                  <div
                    onClick={() => onSelectEndpoint(rel.source_endpoint_id)}
                    className="flex-1 bg-slate-950/70 p-2.5 rounded border border-slate-800 hover:border-cyan-500/50 cursor-pointer transition-colors"
                  >
                    <span className="block text-[10px] font-mono text-slate-500">SOURCE ENDPOINT</span>
                    <div className="flex items-center gap-2 mt-1">
                      {rel.source_endpoint_method && (
                        <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400">
                          {rel.source_endpoint_method}
                        </span>
                      )}
                      <span className="font-mono text-xs text-slate-200 truncate">
                        {rel.source_endpoint_path || rel.source_endpoint_id}
                      </span>
                    </div>
                  </div>

                  {/* Transition Badge */}
                  <div className="flex flex-col items-center justify-center px-2 py-1 shrink-0">
                    <div className="flex items-center gap-1.5">
                      <Icon className="w-3.5 h-3.5 text-slate-400" />
                      <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${config.color}`}>
                        {config.label}
                      </span>
                      <ArrowRight className="w-4 h-4 text-slate-500" />
                    </div>
                    <span className="text-[10px] font-mono text-slate-400 mt-1">
                      {Math.round(rel.confidence * 100)}% Confidence
                    </span>
                  </div>

                  {/* Target Node */}
                  <div
                    onClick={() => onSelectEndpoint(rel.target_endpoint_id)}
                    className="flex-1 bg-slate-950/70 p-2.5 rounded border border-slate-800 hover:border-cyan-500/50 cursor-pointer transition-colors"
                  >
                    <span className="block text-[10px] font-mono text-slate-500">TARGET ENDPOINT</span>
                    <div className="flex items-center gap-2 mt-1">
                      {rel.target_endpoint_method && (
                        <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400">
                          {rel.target_endpoint_method}
                        </span>
                      )}
                      <span className="font-mono text-xs text-slate-200 truncate">
                        {rel.target_endpoint_path || rel.target_endpoint_id}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Footer Notes & Provenance */}
                <div className="flex flex-wrap items-center justify-between text-xs pt-2 border-t border-slate-800/60 text-slate-400 gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-slate-500 font-mono">EXPLANATION:</span>
                    <span>{rel.explanation}</span>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-slate-500 font-mono">SOURCE: {rel.evidence_source}</span>
                    <span
                      className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
                        provUpper === "DOCUMENTED"
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                          : provUpper === "OBSERVED"
                          ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                          : "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20"
                      }`}
                    >
                      {provUpper}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

