import React from "react";
import { Link } from "react-router-dom";
import { Globe, Shield, ExternalLink, Edit3, Trash2, Gauge, Compass } from "lucide-react";
import { ApplicationResponse } from "../../types";

interface ApplicationCardProps {
  app: ApplicationResponse;
  onEdit: (app: ApplicationResponse) => void;
  onDelete: (app: ApplicationResponse) => void;
}

export const ApplicationCard: React.FC<ApplicationCardProps> = ({ app, onEdit, onDelete }) => {
  const isAuthorized = app.scope?.authorization_status === "AUTHORIZED";

  return (
    <div
      data-testid={`application-card-${app.id}`}
      className="bg-phantom-900 border border-slate-800 hover:border-slate-700/80 rounded-lg p-5 flex flex-col justify-between transition-all shadow-sm"
    >
      <div>
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <h3 className="text-base font-semibold text-slate-100 truncate" title={app.name}>
              {app.name}
            </h3>
            {app.environment_name && (
              <span className="inline-block mt-1 px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-400 border border-slate-700">
                {app.environment_name.toUpperCase()}
              </span>
            )}
          </div>

          <div className="flex items-center gap-1.5 shrink-0">
            {/* Scope Status Badge */}
            {isAuthorized ? (
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                <Shield className="w-3 h-3" /> AUTHORIZED
              </span>
            ) : (
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center gap-1">
                <Shield className="w-3 h-3" /> PENDING AUTH
              </span>
            )}

            {/* Status */}
            <span
              className={`px-2 py-0.5 rounded text-[10px] font-mono border ${
                app.status === "ACTIVE"
                  ? "bg-cyan-500/10 text-cyan-400 border-cyan-500/20"
                  : "bg-slate-800 text-slate-400 border-slate-700"
              }`}
            >
              {app.status}
            </span>
          </div>
        </div>

        {/* Target URL */}
        <div className="flex items-center gap-2 text-xs text-slate-400 font-mono mt-3 break-all">
          <Globe className="w-3.5 h-3.5 shrink-0 text-cyan-500" />
          <a
            href={app.target_url}
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-cyan-300 transition-colors flex items-center gap-1"
          >
            <span>{app.target_url}</span>
            <ExternalLink className="w-3 h-3 shrink-0 opacity-60" />
          </a>
        </div>

        {/* Description */}
        {app.description && (
          <p className="text-xs text-slate-400 mt-2.5 line-clamp-2 leading-relaxed">{app.description}</p>
        )}

        {/* Scope metrics */}
        {app.scope && (
          <div className="mt-3.5 pt-2.5 border-t border-slate-800/60 grid grid-cols-2 gap-2 text-[11px] font-mono text-slate-400">
            <div className="flex items-center gap-1 text-slate-400">
              <Gauge className="w-3 h-3 text-slate-500" />
              <span>Limit: {app.scope.rate_limit_rps} RPS</span>
            </div>
            <div className="text-right text-slate-500">
              <span>{app.scope.permitted_paths?.length || 1} paths in scope</span>
            </div>
          </div>
        )}
      </div>

      {/* Footer Actions */}
      <div className="mt-5 pt-3 border-t border-slate-800/80 flex items-center justify-between">
        <span className="text-xs font-mono text-slate-500">
          Risk: <span className="font-bold text-cyan-400">{app.risk_score}</span>
        </span>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => onEdit(app)}
            aria-label={`Edit ${app.name}`}
            className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
            title="Edit Application & Scope"
          >
            <Edit3 className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            onClick={() => onDelete(app)}
            aria-label={`Delete ${app.name}`}
            className="p-1.5 rounded hover:bg-rose-500/10 text-slate-400 hover:text-rose-400 transition-colors"
            title="Delete Application"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
          <Link
            to={`/applications/${app.id}`}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-cyan-400 hover:text-cyan-300 text-xs font-mono transition-colors border border-slate-700/60"
          >
            <span>Details</span>
            <ExternalLink className="w-3 h-3" />
          </Link>
        </div>
      </div>
    </div>
  );
};

