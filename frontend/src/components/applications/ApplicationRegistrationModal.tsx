import React, { useState } from "react";
import { Shield, AlertCircle, CheckCircle2, Globe, Sliders, Lock } from "lucide-react";
import { Modal } from "../common/Modal";
import { api } from "../../services/api";
import { ApplicationCreate, ApplicationResponse } from "../../types";

interface ApplicationRegistrationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (app: ApplicationResponse) => void;
}

const ALL_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"];

export const ApplicationRegistrationModal: React.FC<ApplicationRegistrationModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [name, setName] = useState("");
  const [targetUrl, setTargetUrl] = useState("");
  const [description, setDescription] = useState("");
  const [environmentName, setEnvironmentName] = useState("staging");

  // Scope parameters
  const [permittedPaths, setPermittedPaths] = useState("/*");
  const [excludedPaths, setExcludedPaths] = useState("/admin/*, /logout, /auth/reset-password");
  const [rateLimitRps, setRateLimitRps] = useState(10);
  const [maxConcurrency, setMaxConcurrency] = useState(2);
  const [maxScanDuration, setMaxScanDuration] = useState(60);
  const [allowedMethods, setAllowedMethods] = useState<string[]>([
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "HEAD",
    "OPTIONS",
  ]);
  const [restrictedPatterns, setRestrictedPatterns] = useState("*/delete-account*, */purge*, */reset*");
  const [confirmAuth, setConfirmAuth] = useState(false);
  const [authNotes, setAuthNotes] = useState("");

  // States
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [apiError, setApiError] = useState<string | null>(null);

  const resetForm = () => {
    setName("");
    setTargetUrl("");
    setDescription("");
    setEnvironmentName("staging");
    setPermittedPaths("/*");
    setExcludedPaths("/admin/*, /logout, /auth/reset-password");
    setRateLimitRps(10);
    setMaxConcurrency(2);
    setMaxScanDuration(60);
    setAllowedMethods(["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]);
    setRestrictedPatterns("*/delete-account*, */purge*, */reset*");
    setConfirmAuth(false);
    setAuthNotes("");
    setErrors({});
    setApiError(null);
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

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

    if (!confirmAuth) {
      errs.confirmAuth = "You must explicitly confirm authorization for security testing on this target.";
    }

    if (allowedMethods.length === 0) {
      errs.methods = "At least one HTTP method must be permitted in the scope.";
    }

    if (rateLimitRps < 1 || rateLimitRps > 100) {
      errs.rateLimit = "Rate limit must be between 1 and 100 requests per second.";
    }

    if (maxConcurrency < 1 || maxConcurrency > 20) {
      errs.concurrency = "Max concurrency must be between 1 and 20.";
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
    setApiError(null);

    if (!validate()) {
      return;
    }

    setIsSubmitting(true);
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

      const payload: ApplicationCreate = {
        name: name.trim(),
        target_url: targetUrl.trim(),
        description: description.trim() || undefined,
        environment_name: environmentName,
        permitted_paths: permittedList.length > 0 ? permittedList : ["/*"],
        excluded_paths: excludedList,
        rate_limit_rps: rateLimitRps,
        max_concurrency: maxConcurrency,
        max_scan_duration_minutes: maxScanDuration,
        allowed_methods: allowedMethods,
        restricted_endpoint_patterns: restrictedList,
        confirm_authorization: confirmAuth,
        authorization_notes: authNotes.trim() || undefined,
      };

      const created = await api.applications.create(payload);
      resetForm();
      onSuccess(created);
      onClose();
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || "Failed to register application. Please try again.";
      setApiError(typeof msg === "string" ? msg : JSON.stringify(msg));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Register Target Application"
      footer={
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={handleClose}
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
                <span>Registering Target...</span>
              </>
            ) : (
              <>
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Confirm & Register</span>
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

        {/* Basic Application Information */}
        <div className="space-y-4">
          <div className="border-b border-slate-800 pb-2">
            <h4 className="text-xs font-mono font-semibold text-cyan-400 uppercase tracking-wider flex items-center gap-1.5">
              <Globe className="w-3.5 h-3.5" /> Target Profiling
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
              placeholder="e.g. Core Banking API Staging"
              className={`w-full px-3 py-2 bg-phantom-950 border rounded text-sm text-slate-100 placeholder-slate-600 focus:outline-none ${
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
                placeholder="https://staging.target.internal:8443"
                className={`w-full px-3 py-2 bg-phantom-950 border rounded text-sm text-slate-100 placeholder-slate-600 focus:outline-none font-mono ${
                  errors.targetUrl ? "border-rose-500" : "border-slate-800 focus:border-cyan-500"
                }`}
              />
              {errors.targetUrl && <p className="text-rose-400 text-[11px] font-mono mt-1">{errors.targetUrl}</p>}
            </div>

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
          </div>

          <div>
            <label className="block text-xs font-mono text-slate-400 mb-1">DESCRIPTION (OPTIONAL)</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Application purpose, tech stack, and testing objectives..."
              rows={2}
              className="w-full px-3 py-2 bg-phantom-950 border border-slate-800 rounded text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-cyan-500"
            />
          </div>
        </div>

        {/* Authorized Testing Scope Definition */}
        <div className="space-y-4 pt-2">
          <div className="border-b border-slate-800 pb-2">
            <h4 className="text-xs font-mono font-semibold text-cyan-400 uppercase tracking-wider flex items-center gap-1.5">
              <Sliders className="w-3.5 h-3.5" /> Authorized Testing Scope
            </h4>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-mono text-slate-400 mb-1">
                PERMITTED PATHS (COMMA-SEPARATED)
              </label>
              <input
                type="text"
                value={permittedPaths}
                onChange={(e) => setPermittedPaths(e.target.value)}
                placeholder="/*, /api/v1/*, /checkout/*"
                className="w-full px-3 py-2 bg-phantom-950 border border-slate-800 rounded text-sm text-slate-100 placeholder-slate-600 font-mono focus:outline-none focus:border-cyan-500"
              />
              <span className="text-[10px] text-slate-500 font-mono">Glob patterns allowed to be tested</span>
            </div>

            <div>
              <label className="block text-xs font-mono text-slate-400 mb-1">
                EXCLUDED PATHS (COMMA-SEPARATED)
              </label>
              <input
                type="text"
                value={excludedPaths}
                onChange={(e) => setExcludedPaths(e.target.value)}
                placeholder="/admin/*, /logout, /auth/reset-password"
                className="w-full px-3 py-2 bg-phantom-950 border border-slate-800 rounded text-sm text-slate-100 placeholder-slate-600 font-mono focus:outline-none focus:border-cyan-500"
              />
              <span className="text-[10px] text-slate-500 font-mono">Strictly prohibited from test requests</span>
            </div>
          </div>

          {/* Safety & Performance Limits */}
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
              {errors.rateLimit && <p className="text-rose-400 text-[10px] font-mono">{errors.rateLimit}</p>}
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
              {errors.concurrency && <p className="text-rose-400 text-[10px] font-mono">{errors.concurrency}</p>}
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

          {/* Allowed HTTP Methods */}
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
              placeholder="*/delete-account*, */purge*, */reset*"
              className="w-full px-3 py-2 bg-phantom-950 border border-slate-800 rounded text-sm text-slate-100 placeholder-slate-600 font-mono focus:outline-none focus:border-cyan-500"
            />
          </div>
        </div>

        {/* Explicit Testing Authorization Confirmation */}
        <div className="pt-2">
          <div className="p-3.5 rounded bg-slate-950/80 border border-slate-800 space-y-3">
            <div className="flex items-start gap-2.5">
              <input
                id="auth-checkbox"
                type="checkbox"
                checked={confirmAuth}
                onChange={(e) => setConfirmAuth(e.target.checked)}
                className="mt-1 h-4 w-4 rounded border-slate-700 bg-slate-900 text-cyan-600 focus:ring-cyan-500"
              />
              <label htmlFor="auth-checkbox" className="text-xs text-slate-300 leading-relaxed cursor-pointer">
                <span className="font-semibold text-slate-100 block mb-0.5 flex items-center gap-1.5">
                  <Lock className="w-3.5 h-3.5 text-cyan-400" /> Explicit Testing Scope Authorization
                </span>
                I confirm and certify that our organization owns or has explicit written authorization to conduct
                security testing against this target application URL and within the configured scope boundaries.
              </label>
            </div>
            {errors.confirmAuth && (
              <p className="text-rose-400 text-[11px] font-mono pl-6">{errors.confirmAuth}</p>
            )}

            <div>
              <input
                type="text"
                value={authNotes}
                onChange={(e) => setAuthNotes(e.target.value)}
                placeholder="Authorization reference, ticket ID, or approval rationale..."
                className="w-full px-3 py-1.5 bg-phantom-900 border border-slate-800 rounded text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500"
              />
            </div>
          </div>
        </div>
      </form>
    </Modal>
  );
};

