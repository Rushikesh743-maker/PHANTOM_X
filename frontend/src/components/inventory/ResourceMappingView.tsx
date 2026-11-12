import React, { useState } from "react";
import {
  Layers,
  ChevronDown,
  ChevronRight,
  GitBranch,
  Shield,
  FileCode,
  Tag,
  ExternalLink,
} from "lucide-react";
import { ApiResourceGroup, EndpointResponse } from "../../types";

interface ResourceMappingViewProps {
  resources: ApiResourceGroup[];
  isLoading: boolean;
  onSelectEndpoint: (endpointId: string) => void;
  endpoints?: EndpointResponse[];
}

export const ResourceMappingView: React.FC<ResourceMappingViewProps> = ({
  resources,
  isLoading,
  onSelectEndpoint,
  endpoints = [],
}) => {
  const [expandedResources, setExpandedResources] = useState<Record<string, boolean>>({});
  const [filterQuery, setFilterQuery] = useState("");

  const toggleExpand = (name: string) => {
    setExpandedResources((prev) => ({ ...prev, [name]: !prev[name] }));
  };

  const filteredResources = resources.filter(
    (r) =>
      r.name.toLowerCase().includes(filterQuery.toLowerCase()) ||
      (r.parent_resource && r.parent_resource.toLowerCase().includes(filterQuery.toLowerCase()))
  );

  const epMap = new Map(endpoints.map((e) => [e.id, e]));

  if (isLoading) {
    return (
      <div className="p-12 text-center text-slate-400 font-mono text-sm">
        Loading API resource hierarchy...
      </div>
    );
  }

  if (resources.length === 0) {
    return (
      <div className="p-12 text-center bg-phantom-900/30 rounded-lg border border-slate-800">
        <Layers className="w-10 h-10 text-slate-600 mx-auto mb-3" />
        <h4 className="text-slate-200 font-semibold mb-1">No API Resources Mapped</h4>
        <p className="text-xs text-slate-500 max-w-md mx-auto">
          Endpoints have not been discovered yet or mapping has not been generated for this application.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Search Header */}
      <div className="flex items-center justify-between gap-4 bg-slate-900/60 p-4 rounded-lg border border-slate-800">
        <div className="flex items-center gap-2">
          <Layers className="w-5 h-5 text-emerald-400" />
          <div>
            <h3 className="text-sm font-semibold text-slate-200">
              API Resource Hierarchy ({resources.length} Logical Entities)
            </h3>
            <p className="text-xs text-slate-400">
              Endpoints clustered into bounded domains with parent-child entity dependencies.
            </p>
          </div>
        </div>
        <input
          type="text"
          placeholder="Filter resources..."
          value={filterQuery}
          onChange={(e) => setFilterQuery(e.target.value)}
          className="px-3 py-1.5 bg-slate-950 border border-slate-700 rounded text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500 font-mono w-64"
        />
      </div>

      {/* Resource Cards */}
      <div className="space-y-3">
        {filteredResources.map((res) => {
          const isExpanded = !!expandedResources[res.name];
          return (
            <div
              key={res.name}
              className="bg-phantom-900/40 border border-slate-800/80 rounded-lg overflow-hidden transition-colors hover:border-slate-700"
            >
              {/* Card Header */}
              <div
                onClick={() => toggleExpand(res.name)}
                className="p-4 flex items-center justify-between cursor-pointer select-none"
              >
                <div className="flex items-center gap-3">
                  <button className="text-slate-500 hover:text-slate-300">
                    {isExpanded ? (
                      <ChevronDown className="w-4 h-4" />
                    ) : (
                      <ChevronRight className="w-4 h-4" />
                    )}
                  </button>
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-sm text-cyan-300">
                      /{res.name}
                    </span>
                    {res.parent_resource && (
                      <span className="flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                        <GitBranch className="w-3 h-3" />
                        <span>child of /{res.parent_resource}</span>
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  {/* Methods strip */}
                  <div className="flex gap-1">
                    {res.methods.map((m) => {
                      const colorMap: Record<string, string> = {
                        GET: "text-blue-400 bg-blue-500/10",
                        POST: "text-emerald-400 bg-emerald-500/10",
                        PUT: "text-amber-400 bg-amber-500/10",
                        DELETE: "text-rose-400 bg-rose-500/10",
                        PATCH: "text-purple-400 bg-purple-500/10",
                      };
                      return (
                        <span
                          key={m}
                          className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded ${
                            colorMap[m] || "text-slate-400 bg-slate-800"
                          }`}
                        >
                          {m}
                        </span>
                      );
                    })}
                  </div>

                  <span className="text-xs font-mono text-slate-400 bg-slate-800 px-2 py-0.5 rounded">
                    {res.endpoint_count} {res.endpoint_count === 1 ? "endpoint" : "endpoints"}
                  </span>
                </div>
              </div>

              {/* Expanded Details */}
              {isExpanded && (
                <div className="px-4 pb-4 pt-1 border-t border-slate-800/60 space-y-3 bg-slate-950/40">
                  {/* Evidence & Related */}
                  <div className="flex flex-wrap items-center justify-between text-xs text-slate-400 gap-2 pt-2">
                    <div className="flex items-center gap-2">
                      <span className="text-slate-500 font-mono">EVIDENCE:</span>
                      <span>{res.evidence}</span>
                      <span className="text-[10px] font-mono text-emerald-400 px-1.5 py-0.5 rounded bg-emerald-500/10">
                        {Math.round(res.confidence * 100)}% CONFIDENCE
                      </span>
                    </div>

                    {res.related_resources.length > 0 && (
                      <div className="flex items-center gap-1.5">
                        <span className="text-slate-500 font-mono">CONNECTED ENTITIES:</span>
                        {res.related_resources.map((rr) => (
                          <span
                            key={rr}
                            className="font-mono text-[11px] text-cyan-400 bg-cyan-500/10 px-1.5 py-0.5 rounded border border-cyan-500/20"
                          >
                            /{rr}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Endpoint Routes Table */}
                  <div className="border border-slate-800 rounded overflow-hidden">
                    <table className="w-full text-left text-xs font-mono">
                      <thead className="bg-slate-900/80 text-slate-400">
                        <tr>
                          <th className="py-2 px-3">METHOD</th>
                          <th className="py-2 px-3">CANONICAL PATH</th>
                          <th className="py-2 px-3">PARAMETERS</th>
                          <th className="py-2 px-3 text-right">ACTION</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60">
                        {res.endpoint_ids.map((id) => {
                          const ep = epMap.get(id);
                          if (!ep) {
                            return (
                              <tr key={id} className="hover:bg-slate-900/40">
                                <td colSpan={4} className="py-2 px-3 text-slate-500">
                                  Endpoint {id}
                                </td>
                              </tr>
                            );
                          }

                          const colorMap: Record<string, string> = {
                            GET: "text-blue-400 bg-blue-500/10",
                            POST: "text-emerald-400 bg-emerald-500/10",
                            PUT: "text-amber-400 bg-amber-500/10",
                            DELETE: "text-rose-400 bg-rose-500/10",
                            PATCH: "text-purple-400 bg-purple-500/10",
                          };

                          return (
                            <tr key={id} className="hover:bg-slate-900/40 transition-colors">
                              <td className="py-2 px-3">
                                <span
                                  className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                                    colorMap[ep.method] || "text-slate-400 bg-slate-800"
                                  }`}
                                >
                                  {ep.method}
                                </span>
                              </td>
                              <td className="py-2 px-3 text-slate-200">{ep.path}</td>
                              <td className="py-2 px-3 text-slate-400">
                                {ep.parameters && ep.parameters.length > 0 ? (
                                  <span className="text-slate-300">
                                    {ep.parameters.map((p: any) => p.name).join(", ")}
                                  </span>
                                ) : (
                                  <span className="text-slate-600">none</span>
                                )}
                              </td>
                              <td className="py-2 px-3 text-right">
                                <button
                                  onClick={() => onSelectEndpoint(ep.id)}
                                  className="text-cyan-400 hover:text-cyan-300 text-[11px] inline-flex items-center gap-1"
                                >
                                  <span>Inspect</span>
                                  <ExternalLink className="w-3 h-3" />
                                </button>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

