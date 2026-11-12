import React, { useState, useEffect } from "react";
import { AlertCircle, CheckCircle2, Globe, Sliders } from "lucide-react";
import { Modal } from "../common/Modal";
import { api } from "../../services/api";
import { ApplicationResponse, ApplicationUpdate } from "../../types";

interface ApplicationEditModalProps {
  app: ApplicationResponse | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (updated: ApplicationResponse) => void;
}

const ALL_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"];

export const ApplicationEditModal: React.FC<ApplicationEditModalProps> = ({
  app,
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [name, setName] = useState("");
  const [targetUrl, setTargetUrl] = useState("");
  const [description, setDescription] = useState("");
  const [environmentName, setEnvironmentName] = useState("staging");
  const [status, setStatus] = useState("ACTIVE");

  // Scope parameters
  const [permittedPaths, setPermittedPaths] = useState("/*");
  const [excludedPaths, setExcludedPaths] = useState("");
  const [rateLimitRps, setRateLimitRps] = useState(10);
  const [maxConcurrency, setMaxConcurrency] = useState(2);
  const [maxScanDuration, setMaxScanDuration] = useState(60);
  const [allowedMethods, setAllowedMethods] = useState<string[]>(ALL_METHODS);
  const [restrictedPatterns, setRestrictedPatterns] = useState("");

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [apiError, setApiError] = useState<string | null>(null);

  useEffect(() => {
    if (app) {
      setName(app.name || "");
      setTargetUrl(app.target_url || "");
      setDescription(app.description || "");
      setEnvironmentName(app.environment_name || "staging");
      setStatus(app.status || "ACTIVE");

      if (app.scope) {
        setPermittedPaths((app.scope.permitted_paths || ["/*"]).join(", "));
        setExcludedPaths((app.scope.excluded_paths || []).join(", "));
        setRateLimitRps(app.scope.rate_limit_rps || 10);
        setMaxConcurrency(app.scope.max_concurrency || 2);
        setMaxScanDuration(app.scope.max_scan_duration_minutes || 60);
        setAllowedMethods(app.scope.allowed_methods || ALL_METHODS);
        setRestrictedPatterns((app.scope.restricted_endpoint_patterns || []).join(", "));
      } else {
        setPermittedPaths("/*");
        setExcludedPaths("/admin/*, /logout, /auth/reset-password");
        setRateLimitRps(10);
        setMaxConcurrency(2);
        setMaxScanDuration(60);
        setAllowedMethods(ALL_METHODS);
        setRestrictedPatterns("*/delete-account*, */purge*, */reset*");
      }
      setErrors({});
      setApiError(null);
    }
  }, [app]);

  const validate = (): boolean => {
    const errs: Record<string, string> = {};

    if (!name.trim()) {
      errs.name = "Application name is required.";
    } else if (name.trim().length < 2) {
      errs.name = "Application name must be at least 2 characters.";
    } else if (name.trim().length > 100) {
      errs.name = "Application name cannot exceed 100 characters.";
    }

    if (!targetUrl.trim()) {
      errs.targetUrl = "Target URL is required.";
    } else {
      try {
        const parsed = new URL(targetUrl.trim());
        if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
          errs.targetUrl = "Target URL must use HTTP or HTTPS protocol.";
        }
      } catch {
        errs.targetUrl = "Please enter a valid URL (e.g., https://staging.example.com).";
      }
    }

    if (allowedMethods.length === 0) {
      errs.methods = "At least one HTTP method must be permitted in the scope.";
    }

    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const toggleMethod = (method: string) => {
    if (allowedMethods.includes(method)) {
      setAllowedMethods(allowedMethods.filter((m) => m !== method));
    } else {
      setAllowedMethods([...allowedMethods, method]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!app || !validate()) return;

    setIsSubmitting(true);
    setApiError(null);

    try {
      const permittedList = permittedPaths
        .split(",")
        .map((p) => p.trim())
        .filter(Boolean);
      const excludedList = excludedPaths
        .split(",")
        .map((p) => p.trim())
        .filter(Boolean);
      const restrictedList = restrictedPatterns
        .split(",")
        .map((p) => p.trim())
        .filter(Boolean);

      const payload: ApplicationUpdate = {
        name: name.trim(),
        target_url: targetUrl.trim(),
        description: description.trim() || undefined,
        environment_name: environmentName,
        status: status,
        permitted_paths: permittedList.length > 0 ? permittedList : ["/*"],
        excluded_paths: excludedList,
        rate_limit_rps: rateLimitRps,
        max_concurrency: maxConcurrency,
        max_scan_duration_minutes: maxScanDuration,
        allowed_methods: allowedMethods,
        restricted_endpoint_patterns: restrictedList,
      };

      const updated = await api.applications.update(app.id, payload);
      onSuccess(updated);
      onClose();
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || "Failed to update application.";
      setApiError(typeof msg === "string" ? msg : JSON.stringify(msg));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Edit Application Profile & Scope"
      footer={
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="px-3 py-1.5 rounded border border-slate-800 hover:bg-slate-800 text-slate-300 text-xs font-mono transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="inline-flex items-center gap-2 px-4 py-1.5 rounded bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-slate-950 font-semibold text-xs transition-colors font-mono"
          >
            {isSubmitting ? (
              <>
                <span className="w-3.5 h-3.5 border-2 border-slate-950 border-t-transparent rounded-full animate-spin" />
                <span>Saving Changes...</span>
              </>
            ) : (
              <>
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Save Changes</span>
              </>
            )}
          </button>
        </div>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-5 text-slate-200">
        {apiError && (
          <div className="p-3 rounded bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-start gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <div className="flex-1 break-words">{apiError}</div>
          </div>
        )}

        {/* Profiling */}
        <div className="space-y-4">
          <div className="border-b border-slate-800 pb-2">
            <h4 className="text-xs font-mono font-semibold text-cyan-400 uppercase tracking-wider flex items-center gap-1.5">
              <Globe className="w-3.5 h-3.5" /> Application Profiling
            </h4>
          </div>

          <div>
            <label className="block text-xs font-mono text-slate-400 mb-1">
              APPLICATION NAME <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className={`w-full px-3 py-2 bg-phantom-950 border rounded text-sm text-slate-100 focus:outline-none ${
                errors.name ? "border-rose-500" : "border-slate-800 focus:border-cyan-500"
              }`}
            />
            {errors.name && <p className="text-rose-400 text-[11px] font-mono mt-1">{errors.name}</p>}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="md:col-span-2">
              <label className="block text-xs font-mono text-slate-400 mb-1">
                TARGET BASE URL <span className="text-rose-400">*</span>
              </label>
              <input
                type="url"
                value={targetUrl}
                onChange={(e) => setTargetUrl(e.target.value)}
                className={`w-full px-3 py-2 bg-phantom-950 border rounded text-sm text-slate-100 font-mono focus:outline-none ${
                  errors.targetUrl ? "border-rose-500" : "border-slate-800 focus:border-cyan-500"
                }`}
              />
              {errors.targetUrl && <p className="text-rose-400 text-[11px] font-mono mt-1">{errors.targetUrl}</p>}
            </div>

            <div>
              <label className="block text-xs font-mono text-slate-400 mb-1">STATUS</label>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                className="w-full px-3 py-2 bg-phantom-950 border border-slate-800 rounded text-sm text-slate-100 focus:outline-none focus:border-cyan-500 font-mono"
              >
                <option value="ACTIVE">ACTIVE</option>
                <option value="INACTIVE">INACTIVE</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-mono text-slate-400 mb-1">ENVIRONMENT TIER</label>
              <select
                value={environmentName}
                onChange={(e) => setEnvironmentName(e.target.value)}
                className="w-full px-3 py-2 bg-phantom-950 border border-slate-800 rounded text-sm text-slate-100 focus:outline-none focus:border-cyan-500 font-mono"
              >
                <option value="staging">Staging</option>
                <option value="development">Development</option>
                <option value="sandbox">Sandbox</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-mono text-slate-400 mb-1">DESCRIPTION</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={2}
                className="w-full px-3 py-2 bg-phantom-950 border border-slate-800 rounded text-sm text-slate-100 focus:outline-none focus:border-cyan-500"
              />
            </div>
          </div>
        </div>

        {/* Scope Controls */}
        <div className="space-y-4 pt-2">
          <div className="border-b border-slate-800 pb-2">
            <h4 className="text-xs font-mono font-semibold text-cyan-400 uppercase tracking-wider flex items-center gap-1.5">
              <Sliders className="w-3.5 h-3.5" /> Scope & Safety Controls
            </h4>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-mono text-slate-400 mb-1">PERMITTED PATHS</label>
              <input
                type="text"
                value={permittedPaths}
                onChange={(e) => setPermittedPaths(e.target.value)}
                className="w-full px-3 py-2 bg-phantom-950 border border-slate-800 rounded text-sm text-slate-100 font-mono focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div>
              <label className="block text-xs font-mono text-slate-400 mb-1">EXCLUDED PATHS</label>
              <input
                type="text"
                value={excludedPaths}
                onChange={(e) => setExcludedPaths(e.target.value)}
                className="w-full px-3 py-2 bg-phantom-950 border border-slate-800 rounded text-sm text-slate-100 font-mono focus:outline-none focus:border-cyan-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-mono text-slate-400 mb-1">RATE LIMIT (RPS)</label>
              <input
                type="number"
                min={1}
                max={100}
                value={rateLimitRps}
                onChange={(e) => setRateLimitRps(parseInt(e.target.value) || 10)}
                className="w-full px-3 py-2 bg-phantom-950 border border-slate-800 rounded text-sm text-slate-100 font-mono focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div>
              <label className="block text-xs font-mono text-slate-400 mb-1">CONCURRENCY</label>
              <input
                type="number"
                min={1}
                max={20}
                value={maxConcurrency}
                onChange={(e) => setMaxConcurrency(parseInt(e.target.value) || 2)}
                className="w-full px-3 py-2 bg-phantom-950 border border-slate-800 rounded text-sm text-slate-100 font-mono focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div>
              <label className="block text-xs font-mono text-slate-400 mb-1">MAX DURATION (MIN)</label>
              <input
                type="number"
                min={5}
                max={720}
                value={maxScanDuration}
                onChange={(e) => setMaxScanDuration(parseInt(e.target.value) || 60)}
                className="w-full px-3 py-2 bg-phantom-950 border border-slate-800 rounded text-sm text-slate-100 font-mono focus:outline-none focus:border-cyan-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-mono text-slate-400 mb-1.5">ALLOWED HTTP METHODS</label>
            <div className="flex flex-wrap gap-2">
              {ALL_METHODS.map((method) => {
                const isSelected = allowedMethods.includes(method);
                return (
                  <button
                    key={method}
                    type="button"
                    onClick={() => toggleMethod(method)}
                    className={`px-2.5 py-1 rounded text-xs font-mono border transition-colors ${
                      isSelected
                        ? "bg-cyan-500/20 text-cyan-300 border-cyan-500/40"
                        : "bg-slate-900 text-slate-500 border-slate-800 hover:border-slate-700"
                    }`}
                  >
                    {method}
                  </button>
                );
              })}
            </div>
            {errors.methods && <p className="text-rose-400 text-[11px] font-mono mt-1">{errors.methods}</p>}
          </div>

          <div>
            <label className="block text-xs font-mono text-slate-400 mb-1">RESTRICTED ENDPOINT PATTERNS</label>
            <input
              type="text"
              value={restrictedPatterns}
              onChange={(e) => setRestrictedPatterns(e.target.value)}
              className="w-full px-3 py-2 bg-phantom-950 border border-slate-800 rounded text-sm text-slate-100 font-mono focus:outline-none focus:border-cyan-500"
            />
          </div>
        </div>
      </form>
    </Modal>
  );
};

