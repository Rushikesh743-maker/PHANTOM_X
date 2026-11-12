import React, { useState, useEffect, useCallback } from "react";
import { Server, Plus, AlertCircle, CheckCircle2, RefreshCw } from "lucide-react";
import { PageHeader } from "../components/common/PageHeader";
import { SearchFilterBar } from "../components/common/SearchFilterBar";
import { EmptyState } from "../components/common/EmptyState";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import {
  ApplicationRegistrationModal,
  ApplicationEditModal,
  ApplicationDeleteDialog,
  ApplicationCard,
} from "../components/applications";
import { api } from "../services/api";
import { ApplicationResponse } from "../types";

export const ApplicationsPage: React.FC = () => {
  const [apps, setApps] = useState<ApplicationResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successToast, setSuccessToast] = useState<string | null>(null);

  // Modals state
  const [isRegisterOpen, setIsRegisterOpen] = useState(false);
  const [editingApp, setEditingApp] = useState<ApplicationResponse | null>(null);
  const [deletingApp, setDeletingApp] = useState<ApplicationResponse | null>(null);

  const fetchApps = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const data = await api.applications.list({
        search: search.trim() || undefined,
        status: statusFilter !== "ALL" ? statusFilter : undefined,
      });
      setApps(data);
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || "Unable to load target applications from backend.";
      setErrorMessage(typeof msg === "string" ? msg : JSON.stringify(msg));
    } finally {
      setIsLoading(false);
    }
  }, [search, statusFilter]);

  useEffect(() => {
    fetchApps();
  }, [fetchApps]);

  const showSuccess = (msg: string) => {
    setSuccessToast(msg);
    setTimeout(() => {
      setSuccessToast(null);
    }, 4500);
  };

  const handleRegisterSuccess = (newApp: ApplicationResponse) => {
    showSuccess(`Target application "${newApp.name}" registered successfully with authorized testing scope.`);
    fetchApps();
  };

  const handleEditSuccess = (updatedApp: ApplicationResponse) => {
    showSuccess(`Application "${updatedApp.name}" updated successfully.`);
    fetchApps();
  };

  const handleDeleteSuccess = (deletedId: string) => {
    showSuccess("Application target and its associated scope policies removed successfully.");
    setApps((prev) => prev.filter((a) => a.id !== deletedId));
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Target Applications"
        description="Register, profile, and enforce authorized security testing boundaries for target applications and APIs."
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={fetchApps}
              className="p-1.5 rounded border border-slate-800 hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
              title="Refresh applications"
              aria-label="Refresh applications"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
            </button>
            <button
              onClick={() => setIsRegisterOpen(true)}
              className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-semibold text-xs transition-colors font-mono"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Register Application</span>
            </button>
          </div>
        }
      />

      {/* Success Notification Banner */}
      {successToast && (
        <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs flex items-center justify-between font-mono animate-fadeIn">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
            <span>{successToast}</span>
          </div>
          <button
            onClick={() => setSuccessToast(null)}
            className="text-emerald-500 hover:text-emerald-300 text-xs ml-4"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Error Notification Banner */}
      {errorMessage && (
        <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center justify-between font-mono">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
            <span>{errorMessage}</span>
          </div>
          <button
            onClick={fetchApps}
            className="px-2.5 py-1 rounded bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/40 text-xs font-semibold ml-4"
          >
            Retry
          </button>
        </div>
      )}

      {/* Search and Filter Controls */}
      <div className="flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
        <div className="flex-1">
          <SearchFilterBar
            searchQuery={search}
            onSearchChange={setSearch}
            placeholder="Search applications by name, target URL, or description..."
          />
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-slate-500">STATUS:</span>
          {["ALL", "ACTIVE", "INACTIVE"].map((status) => (
            <button
              key={status}
              type="button"
              onClick={() => setStatusFilter(status)}
              className={`px-2.5 py-1 rounded text-xs font-mono border transition-colors ${
                statusFilter === status
                  ? "bg-cyan-500/20 text-cyan-300 border-cyan-500/40"
                  : "bg-slate-900 text-slate-400 border-slate-800 hover:border-slate-700"
              }`}
            >
              {status}
            </button>
          ))}
        </div>
      </div>

      {/* Main Content Area */}
      {isLoading ? (
        <LoadingSpinner />
      ) : apps.length === 0 ? (
        <EmptyState
          icon={Server}
          title={search ? "No Applications Match Search" : "No Applications Registered"}
          description={
            search
              ? `No target applications found matching "${search}". Try clearing your search query.`
              : "Register your first authorized target application to establish safety policy boundaries, map endpoints, and model a Behavioral Digital Twin."
          }
          action={
            search ? (
              <button
                onClick={() => setSearch("")}
                className="px-3 py-1.5 rounded border border-slate-800 hover:bg-slate-800 text-slate-300 font-mono text-xs transition-colors"
              >
                Clear Search Filter
              </button>
            ) : (
              <button
                onClick={() => setIsRegisterOpen(true)}
                className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-semibold text-xs transition-colors font-mono"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Register Target Application</span>
              </button>
            )
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {apps.map((app) => (
            <ApplicationCard
              key={app.id}
              app={app}
              onEdit={(target) => setEditingApp(target)}
              onDelete={(target) => setDeletingApp(target)}
            />
          ))}
        </div>
      )}

      {/* Registration Modal */}
      <ApplicationRegistrationModal
        isOpen={isRegisterOpen}
        onClose={() => setIsRegisterOpen(false)}
        onSuccess={handleRegisterSuccess}
      />

      {/* Edit Modal */}
      <ApplicationEditModal
        app={editingApp}
        isOpen={!!editingApp}
        onClose={() => setEditingApp(null)}
        onSuccess={handleEditSuccess}
      />

      {/* Delete Confirmation Dialog */}
      <ApplicationDeleteDialog
        app={deletingApp}
        isOpen={!!deletingApp}
        onClose={() => setDeletingApp(null)}
        onSuccess={handleDeleteSuccess}
      />
    </div>
  );
};
