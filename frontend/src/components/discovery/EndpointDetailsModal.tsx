import React from "react";
import { X, Key, ShieldCheck, Globe, Calendar, FileCode, CheckCircle, Tag } from "lucide-react";
import { EndpointResponse } from "../../types";

interface EndpointDetailsModalProps {
  endpoint: EndpointResponse | null;
  isOpen: boolean;
  onClose: () => void;
}

export const EndpointDetailsModal: React.FC<EndpointDetailsModalProps> = ({
  endpoint,
  isOpen,
  onClose,
}) => {
  if (!isOpen || !endpoint) return null;

  const rawMeta = endpoint.raw_metadata || {};
  const methodColors: Record<string, string> = {
    GET: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
    POST: "bg-cyan-500/10 text-cyan-400 border-cyan-500/30",
    PUT: "bg-amber-500/10 text-amber-400 border-amber-500/30",
    PATCH: "bg-orange-500/10 text-orange-400 border-orange-500/30",
    DELETE: "bg-rose-500/10 text-rose-400 border-rose-500/30",
    OPTIONS: "bg-slate-500/10 text-slate-400 border-slate-500/30",
    HEAD: "bg-purple-500/10 text-purple-400 border-purple-500/30",
  };

  const badgeColor = methodColors[endpoint.method] || "bg-slate-800 text-slate-300 border-slate-700";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-phantom-900 border border-slate-800 rounded-xl w-full max-w-3xl overflow-hidden shadow-2xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/40">
          <div className="flex items-center gap-3">
            <span className={`px-2.5 py-1 text-xs font-mono font-bold rounded border ${badgeColor}`}>
              {endpoint.method}
            </span>
            <span className="font-mono text-sm font-semibold text-slate-100">{endpoint.path}</span>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-6 text-xs font-sans">
          {/* Metadata Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3 bg-slate-950/40 border border-slate-800/80 rounded-lg">
              <div className="text-[11px] text-slate-400 mb-1 flex items-center gap-1.5">
                <Globe className="w-3 h-3 text-cyan-400" />
                <span>Base URL</span>
              </div>
              <div className="font-mono text-slate-200 truncate">
                {rawMeta.base_url || "Configured Target"}
              </div>
            </div>

            <div className="p-3 bg-slate-950/40 border border-slate-800/80 rounded-lg">
              <div className="text-[11px] text-slate-400 mb-1 flex items-center gap-1.5">
                <Key className="w-3 h-3 text-amber-400" />
                <span>Authentication</span>
              </div>
              <div className="font-semibold">
                {endpoint.auth_required ? (
                  <span className="text-amber-400">Required</span>
                ) : (
                  <span className="text-emerald-400">Public</span>
                )}
              </div>
            </div>

            <div className="p-3 bg-slate-950/40 border border-slate-800/80 rounded-lg">
              <div className="text-[11px] text-slate-400 mb-1 flex items-center gap-1.5">
                <FileCode className="w-3 h-3 text-purple-400" />
                <span>Provenance Source</span>
              </div>
              <div className="font-mono text-cyan-300 font-semibold">
                {rawMeta.discovery_source || "SPECIFICATION"}
              </div>
            </div>

            <div className="p-3 bg-slate-950/40 border border-slate-800/80 rounded-lg">
              <div className="text-[11px] text-slate-400 mb-1 flex items-center gap-1.5">
                <Tag className="w-3 h-3 text-emerald-400" />
                <span>Evidence Type</span>
              </div>
              <div className="font-mono text-slate-200">
                {rawMeta.evidence_classification || "DOCUMENTED"}
              </div>
            </div>
          </div>

          {/* Original Path if normalized */}
          {rawMeta.original_path && rawMeta.original_path !== endpoint.path && (
            <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg font-mono text-[11px]">
              <span className="text-slate-400">Original Observed Path: </span>
              <span className="text-amber-300">{rawMeta.original_path}</span>
            </div>
          )}

          {/* Classification & Resource Card */}
          <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-lg space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="text-[11px] text-slate-500 font-mono">LOGICAL RESOURCE:</span>
                <span className="font-mono text-xs font-bold text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
                  /{rawMeta.resource_name || "root"}
                </span>
                {rawMeta.parent_resource_name && (
                  <span className="font-mono text-[11px] text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
                    child of /{rawMeta.parent_resource_name}
                  </span>
                )}
              </div>

              <div className="flex items-center gap-1.5 font-mono text-[11px]">
                <span className="text-slate-500">CATEGORY:</span>
                <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-200 font-semibold border border-slate-700">
                  {rawMeta.category_label || rawMeta.category || "Unclassified"}
                </span>
                {rawMeta.category_confidence !== undefined && (
                  <span className="text-cyan-400 font-semibold">
                    ({Math.round(rawMeta.category_confidence * 100)}%)
                  </span>
                )}
              </div>
            </div>

            {rawMeta.category_explanation && (
              <p className="text-[11px] text-slate-400 italic">
                Classification rationale: {rawMeta.category_explanation}
              </p>
            )}
          </div>

          {/* Parameters Section */}
          <div className="space-y-2">
            <h3 className="font-semibold text-slate-200 flex items-center gap-1.5">
              <span>Endpoint Parameters</span>
              <span className="text-[11px] text-slate-500 font-normal">
                ({endpoint.parameters?.length || 0})
              </span>
            </h3>

            {endpoint.parameters && endpoint.parameters.length > 0 ? (
              <div className="border border-slate-800 rounded-lg overflow-hidden bg-slate-950/40">
                <table className="w-full text-left font-mono text-[11px]">
                  <thead className="bg-slate-950/80 border-b border-slate-800 text-slate-400">
                    <tr>
                      <th className="p-2.5">NAME</th>
                      <th className="p-2.5">LOCATION</th>
                      <th className="p-2.5">TYPE</th>
                      <th className="p-2.5">REQUIRED</th>
                      <th className="p-2.5">EXAMPLE</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-300">
                    {endpoint.parameters.map((p: any, idx: number) => (
                      <tr key={idx} className="hover:bg-slate-900/40">
                        <td className="p-2.5 font-semibold text-cyan-300">{p.name}</td>
                        <td className="p-2.5 text-slate-400">{p.location || "query"}</td>
                        <td className="p-2.5 text-purple-300">{p.param_type || "string"}</td>
                        <td className="p-2.5">
                          {p.required ? (
                            <span className="text-rose-400 font-semibold">Yes</span>
                          ) : (
                            <span className="text-slate-500">No</span>
                          )}
                        </td>
                        <td className="p-2.5 text-slate-400 truncate max-w-[150px]">
                          {p.example !== undefined && p.example !== null ? String(p.example) : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="p-3 bg-slate-950/30 border border-slate-800/60 rounded-lg text-slate-500">
                No query or path parameters declared.
              </div>
            )}
          </div>

          {/* Response Status Codes */}
          <div className="space-y-2">
            <h3 className="font-semibold text-slate-200">Observed Response Codes</h3>
            <div className="flex flex-wrap gap-2">
              {endpoint.response_codes && endpoint.response_codes.length > 0 ? (
                endpoint.response_codes.map((code) => {
                  const is2xx = code >= 200 && code < 300;
                  const is4xx = code >= 400 && code < 500;
                  const color = is2xx
                    ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                    : is4xx
                    ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
                    : "bg-rose-500/10 text-rose-400 border-rose-500/30";
                  return (
                    <span
                      key={code}
                      className={`px-2 py-0.5 font-mono text-[11px] font-semibold rounded border ${color}`}
                    >
                      {code}
                    </span>
                  );
                })
              ) : (
                <span className="text-slate-500">No response status codes recorded</span>
              )}
            </div>
          </div>

          {/* Request Body Schema if present */}
          {rawMeta.request_body_schema && (
            <div className="space-y-2">
              <h3 className="font-semibold text-slate-200">Request Body Schema</h3>
              <pre className="p-3 bg-slate-950 border border-slate-800 rounded-lg font-mono text-[11px] text-cyan-300 overflow-x-auto max-h-48">
                {JSON.stringify(rawMeta.request_body_schema, null, 2)}
              </pre>
            </div>
          )}

          {/* Timestamps */}
          <div className="flex items-center gap-6 pt-3 border-t border-slate-800/80 text-[11px] text-slate-500">
            <div className="flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-slate-600" />
              <span>
                First Discovered:{" "}
                {rawMeta.first_discovered_at
                  ? new Date(rawMeta.first_discovered_at).toLocaleString()
                  : new Date(endpoint.created_at).toLocaleString()}
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-slate-600" />
              <span>
                Last Observed:{" "}
                {rawMeta.last_observed_at
                  ? new Date(rawMeta.last_observed_at).toLocaleString()
                  : new Date(endpoint.updated_at).toLocaleString()}
              </span>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-800 bg-slate-950/40 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

