import React, { useState, useEffect, useCallback } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  Globe,
  Radar,
  Compass,
  ArrowLeft,
  Shield,
  Sliders,
  AlertCircle,
  Edit3,
  Trash2,
  Lock,
  Gauge,
  Clock,
  CheckCircle2,
} from "lucide-react";
import { PageHeader } from "../components/common/PageHeader";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { ApplicationEditModal, ApplicationDeleteDialog } from "../components/applications";
import { api } from "../services/api";
import { ApplicationResponse } from "../types";

export const ApplicationDetailsPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [app, setApp] = useState<ApplicationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);

  const fetchApp = useCallback(async () => {
    if (!id) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.applications.getById(id);
      setApp(data);
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || "Failed to load application details.";
      setError(typeof msg === "string" ? msg : JSON.stringify(msg));
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchApp();
  }, [fetchApp]);

  if (isLoading) return <LoadingSpinner />;

  if (error || !app) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-2 text-xs font-mono text-slate-500 mb-2">
          <Link to="/applications" className="hover:text-slate-300 flex items-center gap-1">
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Applications</span>
          </Link>
        </div>

        <div className="p-6 rounded-lg bg-phantom-900 border border-slate-800 text-center space-y-4">
          <div className="w-12 h-12 mx-auto rounded-full bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400">
            <AlertCircle className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-slate-200">Application Not Found</h3>
            <p className="text-xs text-slate-400 mt-1">{error || "The requested application does not exist or is not authorized for your organization."}</p>
          </div>
          <Link
            to="/applications"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono border border-slate-700"
          >
            <span>Return to Applications List</span>
          </Link>
        </div>
      </div>
    );
  }

  const isAuthorized = app.scope?.authorization_status === "AUTHORIZED";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between text-xs font-mono text-slate-500">
        <Link to="/applications" className="hover:text-slate-300 flex items-center gap-1 transition-colors">
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Applications</span>
        </Link>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsEditOpen(true)}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs border border-slate-700 transition-colors"
          >
            <Edit3 className="w-3 h-3" />
            <span>Edit Profile</span>
          </button>
          <button
            onClick={() => setIsDeleteOpen(true)}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 text-xs transition-colors"
          >
            <Trash2 className="w-3 h-3" />
            <span>Delete</span>
          </button>
        </div>
      </div>

      <PageHeader
        title={app.name}
        description={app.description || "Authorized target profiling and continuous security testing scope configuration."}
        actions={
          <div className="flex gap-2">
            <Link
              to={`/discovery?app_id=${app.id}`}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono border border-slate-700 transition-colors"
            >
              <Compass className="w-3.5 h-3.5" />
              <span>Explore APIs</span>
            </Link>
            <Link
              to={`/scans?app_id=${app.id}`}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-semibold text-xs transition-colors font-mono"
            >
              <Radar className="w-3.5 h-3.5" />
              <span>Launch Scan</span>
            </Link>
          </div>
        }
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Left Column: Target Profile */}
        <div className="bg-phantom-900 border border-slate-800 rounded-lg p-5 space-y-5">
          <div className="border-b border-slate-800 pb-3 flex items-center justify-between">
            <h3 className="text-xs font-mono font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <Globe className="w-3.5 h-3.5 text-cyan-400" /> Target Profile
            </h3>
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

          <div className="text-xs space-y-3 font-mono">
            <div>
              <span className="text-slate-500 block mb-0.5">TARGET BASE URL</span>
              <a
                href={app.target_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-cyan-400 hover:text-cyan-300 break-all underline decoration-cyan-500/40"
              >
                {app.target_url}
              </a>
            </div>

            <div>
              <span className="text-slate-500 block mb-0.5">ENVIRONMENT TIER</span>
              <span className="px-2 py-0.5 rounded text-[11px] bg-slate-800 text-slate-300 border border-slate-700">
                {(app.environment_name || "staging").toUpperCase()}
              </span>
            </div>

            <div>
              <span className="text-slate-500 block mb-0.5">RISK SCORE</span>
              <span className="text-cyan-400 font-bold text-sm">{app.risk_score} / 100</span>
            </div>

            <div>
              <span className="text-slate-500 block mb-0.5">APPLICATION ID</span>
              <span className="text-slate-400 text-[11px] select-all">{app.id}</span>
            </div>

            <div>
              <span className="text-slate-500 block mb-0.5">REGISTERED AT</span>
              <span className="text-slate-400">{new Date(app.created_at).toLocaleString()}</span>
            </div>
          </div>
        </div>

        {/* Right Column: Authorized Testing Scope Policy */}
        <div className="md:col-span-2 bg-phantom-900 border border-slate-800 rounded-lg p-5 space-y-5">
          <div className="border-b border-slate-800 pb-3 flex items-center justify-between">
            <h3 className="text-xs font-mono font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <Shield className="w-3.5 h-3.5 text-cyan-400" /> Authorized Testing Scope Policy
            </h3>
            {isAuthorized ? (
              <span className="px-2.5 py-0.5 rounded text-xs font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" /> AUTHORIZED
              </span>
            ) : (
              <span className="px-2.5 py-0.5 rounded text-xs font-mono bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center gap-1">
                <Lock className="w-3 h-3" /> PENDING AUTHORIZATION
              </span>
            )}
          </div>

          {app.scope ? (
            <div className="space-y-4 text-xs font-mono">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-3.5 rounded bg-slate-950/60 border border-slate-800">
                <div>
                  <span className="text-slate-500 block text-[11px] mb-0.5 flex items-center gap-1">
                    <Globe className="w-3 h-3" /> TARGET DOMAIN
                  </span>
                  <span className="text-slate-200 font-semibold">{app.scope.target_domain}</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[11px] mb-0.5 flex items-center gap-1">
                    <Gauge className="w-3 h-3" /> RATE LIMIT / CONCURRENCY
                  </span>
                  <span className="text-slate-200">
                    {app.scope.rate_limit_rps} RPS / {app.scope.max_concurrency} max
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[11px] mb-0.5 flex items-center gap-1">
                    <Clock className="w-3 h-3" /> MAX SCAN DURATION
                  </span>
                  <span className="text-slate-200">{app.scope.max_scan_duration_minutes} minutes</span>
                </div>
              </div>

              {/* Permitted and Excluded Paths */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="p-3 rounded bg-slate-950/40 border border-slate-800 space-y-2">
                  <span className="text-slate-400 font-semibold block text-[11px]">PERMITTED PATHS</span>
                  <div className="space-y-1">
                    {app.scope.permitted_paths?.map((p, idx) => (
                      <span
                        key={idx}
                        className="inline-block mr-1.5 mb-1 px-2 py-0.5 rounded text-[11px] bg-emerald-500/10 text-emerald-300 border border-emerald-500/20"
                      >
                        {p}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="p-3 rounded bg-slate-950/40 border border-slate-800 space-y-2">
                  <span className="text-slate-400 font-semibold block text-[11px]">EXCLUDED PATHS</span>
                  <div className="space-y-1">
                    {app.scope.excluded_paths && app.scope.excluded_paths.length > 0 ? (
                      app.scope.excluded_paths.map((p, idx) => (
                        <span
                          key={idx}
                          className="inline-block mr-1.5 mb-1 px-2 py-0.5 rounded text-[11px] bg-rose-500/10 text-rose-300 border border-rose-500/20"
                        >
                          {p}
                        </span>
                      ))
                    ) : (
                      <span className="text-slate-500 text-[11px]">None configured</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Methods and Governance */}
              <div>
                <span className="text-slate-500 block text-[11px] mb-1.5">PERMITTED HTTP METHODS</span>
                <div className="flex flex-wrap gap-1.5">
                  {app.scope.allowed_methods?.map((m) => (
                    <span
                      key={m}
                      className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300 border border-slate-700"
                    >
                      {m}
                    </span>
                  ))}
                </div>
              </div>

              {app.scope.authorized_by && (
                <div className="pt-3 border-t border-slate-800 text-[11px] text-slate-400 flex items-center justify-between">
                  <span>
                    Authorized By: <strong className="text-slate-200">{app.scope.authorized_by}</strong> (
                    {app.scope.authorizer_role || "Security Engineer"})
                  </span>
                  {app.scope.valid_until && (
                    <span className="text-slate-500">
                      Valid until: {new Date(app.scope.valid_until).toLocaleDateString()}
                    </span>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="p-4 rounded bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs">
              No scope policy is configured for this application target.
            </div>
          )}
        </div>
      </div>

      {/* Edit Modal */}
      <ApplicationEditModal
        app={app}
        isOpen={isEditOpen}
        onClose={() => setIsEditOpen(false)}
        onSuccess={(updated) => {
          setApp(updated);
        }}
      />

      {/* Delete Confirmation Dialog */}
      <ApplicationDeleteDialog
        app={app}
        isOpen={isDeleteOpen}
        onClose={() => setIsDeleteOpen(false)}
        onSuccess={() => {
          navigate("/applications");
        }}
      />
    </div>
  );
};
