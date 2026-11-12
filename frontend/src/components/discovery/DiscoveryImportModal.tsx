import React, { useState } from "react";
import { X, Upload, FileCode, CheckCircle2, AlertTriangle, Loader2 } from "lucide-react";
import { api } from "../../services/api";
import { ApplicationResponse, DiscoverySummaryResponse, DiscoverySourceType } from "../../types";

interface DiscoveryImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  selectedApp: ApplicationResponse | null;
  onImportSuccess: (summary: DiscoverySummaryResponse) => void;
}

export const DiscoveryImportModal: React.FC<DiscoveryImportModalProps> = ({
  isOpen,
  onClose,
  selectedApp,
  onImportSuccess,
}) => {
  const [sourceType, setSourceType] = useState<DiscoverySourceType>("OPENAPI");
  const [inputMode, setInputMode] = useState<"upload" | "paste">("upload");
  const [fileContent, setFileContent] = useState("");
  const [fileName, setFileName] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!isOpen || !selectedApp) return null;

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setFileName(file.name);
    setErrorMessage(null);

    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result as string;
      setFileContent(text || "");
    };
    reader.onerror = () => {
      setErrorMessage("Failed to read the selected file. Please try again.");
    };
    reader.readAsText(file);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fileContent.trim()) {
      setErrorMessage("Please select a file or paste specification content before importing.");
      return;
    }

    try {
      setIsSubmitting(true);
      setErrorMessage(null);

      let result: DiscoverySummaryResponse;
      const payload = {
        application_id: selectedApp.id,
        content: fileContent,
        filename: fileName || undefined,
      };

      if (sourceType === "POSTMAN") {
        result = await api.discovery.importPostman(payload);
      } else if (sourceType === "HAR") {
        result = await api.discovery.importHar(payload);
      } else {
        result = await api.discovery.importOpenApi(payload);
      }

      onImportSuccess(result);
      onClose();
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || "Failed to import and discover endpoints.";
      setErrorMessage(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-phantom-900 border border-slate-800 rounded-xl w-full max-w-2xl overflow-hidden shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <FileCode className="w-5 h-5 text-cyan-400" />
            <h2 className="text-base font-semibold text-slate-100">
              Import & Discover API Endpoints
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {/* Target App Info */}
          <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg text-xs space-y-1">
            <div className="text-slate-400">Target Application:</div>
            <div className="font-semibold text-slate-200 flex items-center gap-2">
              <span>{selectedApp.name}</span>
              <span className="text-slate-500 font-mono">({selectedApp.target_url})</span>
            </div>
          </div>

          {/* Source Type Selector */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-slate-300">Discovery Source Type</label>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => setSourceType("OPENAPI")}
                className={`px-3 py-2 text-xs font-medium rounded-lg border transition-all ${
                  sourceType === "OPENAPI"
                    ? "bg-cyan-500/10 border-cyan-500/50 text-cyan-300 shadow-sm"
                    : "bg-slate-950/40 border-slate-800 text-slate-400 hover:border-slate-700"
                }`}
              >
                OpenAPI / Swagger
              </button>
              <button
                type="button"
                onClick={() => setSourceType("POSTMAN")}
                className={`px-3 py-2 text-xs font-medium rounded-lg border transition-all ${
                  sourceType === "POSTMAN"
                    ? "bg-amber-500/10 border-amber-500/50 text-amber-300 shadow-sm"
                    : "bg-slate-950/40 border-slate-800 text-slate-400 hover:border-slate-700"
                }`}
              >
                Postman Collection
              </button>
              <button
                type="button"
                onClick={() => setSourceType("HAR")}
                className={`px-3 py-2 text-xs font-medium rounded-lg border transition-all ${
                  sourceType === "HAR"
                    ? "bg-purple-500/10 border-purple-500/50 text-purple-300 shadow-sm"
                    : "bg-slate-950/40 border-slate-800 text-slate-400 hover:border-slate-700"
                }`}
              >
                HAR Traffic Log
              </button>
            </div>
          </div>

          {/* Mode Switcher */}
          <div className="flex border-b border-slate-800 text-xs">
            <button
              type="button"
              onClick={() => setInputMode("upload")}
              className={`pb-2 px-3 font-medium transition-colors ${
                inputMode === "upload"
                  ? "border-b-2 border-cyan-500 text-cyan-400"
                  : "text-slate-400 hover:text-slate-300"
              }`}
            >
              Upload File
            </button>
            <button
              type="button"
              onClick={() => setInputMode("paste")}
              className={`pb-2 px-3 font-medium transition-colors ${
                inputMode === "paste"
                  ? "border-b-2 border-cyan-500 text-cyan-400"
                  : "text-slate-400 hover:text-slate-300"
              }`}
            >
              Paste Content
            </button>
          </div>

          {/* Upload Input Mode */}
          {inputMode === "upload" ? (
            <div className="space-y-2">
              <label
                htmlFor="spec-file-input"
                className="flex flex-col items-center justify-center p-6 border-2 border-dashed border-slate-800 hover:border-slate-700 rounded-xl bg-slate-950/30 cursor-pointer transition-colors"
              >
                <Upload className="w-8 h-8 text-slate-500 mb-2" />
                <span className="text-xs text-slate-300 font-medium">
                  {fileName ? fileName : "Click to select or drag and drop specification file"}
                </span>
                <span className="text-[11px] text-slate-500 mt-1">
                  Supports .json, .yaml, .yml, .har files
                </span>
                <input
                  id="spec-file-input"
                  type="file"
                  accept=".json,.yaml,.yml,.har"
                  onChange={handleFileUpload}
                  className="hidden"
                />
              </label>
              {fileContent && (
                <div className="text-[11px] text-emerald-400 flex items-center gap-1 font-mono">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>File loaded ({fileContent.length.toLocaleString()} characters)</span>
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-1">
              <textarea
                value={fileContent}
                onChange={(e) => setFileContent(e.target.value)}
                placeholder={
                  sourceType === "OPENAPI"
                    ? "Paste OpenAPI JSON or YAML here..."
                    : sourceType === "POSTMAN"
                    ? "Paste Postman Collection JSON here..."
                    : "Paste HTTP Archive (.har) JSON here..."
                }
                rows={8}
                className="w-full px-3 py-2 bg-slate-950/60 border border-slate-800 rounded-lg text-xs font-mono text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
              />
            </div>
          )}

          {/* Error Message */}
          {errorMessage && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg flex items-start gap-2.5 text-xs text-rose-300 animate-in fade-in">
              <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !fileContent.trim()}
              className="flex items-center gap-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-slate-950 font-semibold text-xs rounded-lg transition-colors"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Analyzing & Normalizing...</span>
                </>
              ) : (
                <span>Import & Discover</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

