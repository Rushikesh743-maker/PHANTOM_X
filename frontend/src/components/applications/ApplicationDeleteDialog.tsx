import React, { useState } from "react";
import { AlertTriangle, Trash2 } from "lucide-react";
import { Modal } from "../common/Modal";
import { api } from "../../services/api";
import { ApplicationResponse } from "../../types";

interface ApplicationDeleteDialogProps {
  app: ApplicationResponse | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (deletedId: string) => void;
}

export const ApplicationDeleteDialog: React.FC<ApplicationDeleteDialogProps> = ({
  app,
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!app) return null;

  const handleDelete = async () => {
    setIsDeleting(true);
    setError(null);
    try {
      await api.applications.delete(app.id);
      onSuccess(app.id);
      onClose();
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || "Failed to delete application.";
      setError(typeof msg === "string" ? msg : JSON.stringify(msg));
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Delete Application Target"
      footer={
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={isDeleting}
            className="px-3 py-1.5 rounded border border-slate-800 hover:bg-slate-800 text-slate-300 text-xs font-mono transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleDelete}
            disabled={isDeleting}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-white font-semibold text-xs font-mono transition-colors"
          >
            {isDeleting ? (
              <>
                <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Deleting...</span>
              </>
            ) : (
              <>
                <Trash2 className="w-3.5 h-3.5" />
                <span>Confirm Deletion</span>
              </>
            )}
          </button>
        </div>
      }
    >
      <div className="space-y-4 text-slate-200">
        {error && (
          <div className="p-3 rounded bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs font-mono">
            {error}
          </div>
        )}

        <div className="flex items-start gap-3 p-3.5 rounded bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
          <AlertTriangle className="w-5 h-5 shrink-0 text-rose-400" />
          <div className="space-y-1">
            <p className="font-semibold text-rose-200">Warning: Irreversible Action</p>
            <p className="text-slate-300 leading-relaxed">
              You are about to delete <strong className="text-white font-mono">{app.name}</strong> (
              <span className="font-mono text-slate-400">{app.target_url}</span>).
            </p>
            <p className="text-slate-400 text-[11px]">
              This will remove all associated testing scope policies, registered environments, and
              endpoint discovery associations. Historical scans and evidence records will be unlinked.
            </p>
          </div>
        </div>

        <p className="text-xs text-slate-400">
          Please confirm you want to proceed with deleting this target application.
        </p>
      </div>
    </Modal>
  );
};

