import { useState } from "react";
import type { QueueItem } from "../types";

interface Props {
  item: QueueItem;
  onClose: () => void;
  onConfirm: (opts: { skipDrive: boolean; model?: string }) => Promise<void> | void;
  /** When provided, show a per-run model override selector (empty = use current config). */
  modelOptions?: string[];
}

/**
 * Confirmation dialog shown before launching a single apply/enrich job. Once
 * confirmed, the job is tracked at the page level (see useJobs) and its live
 * progress is shown in JobProgressModal.
 */
export default function LaunchConfirmModal({
  item,
  onClose,
  onConfirm,
  modelOptions,
}: Props) {
  const isEnrich = item.subfolder === "profiles";
  const [skipDrive, setSkipDrive] = useState(false);
  const [model, setModel] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [launching, setLaunching] = useState(false);

  const confirm = async () => {
    setError(null);
    setLaunching(true);
    try {
      await onConfirm({ skipDrive, model: model || undefined });
    } catch (e) {
      setError(String(e));
      setLaunching(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
          <h2 className="text-base font-semibold text-gray-900">
            {/* NOTE: UI-only rename — the pipeline is "Build" in copy; API/CLI names unchanged (full rename is a future change). */}
            {isEnrich ? "Enrich profile" : "Build application"}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        <div className="p-5 space-y-4">
          <div className="bg-gray-50 rounded-lg px-4 py-3">
            <p className="text-sm font-mono text-gray-700 truncate">{item.name}</p>
            <p className="text-xs text-gray-400 mt-0.5">{item.path}</p>
          </div>

          {!isEnrich && (
            <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
              <input
                type="checkbox"
                checked={skipDrive}
                onChange={(e) => setSkipDrive(e.target.checked)}
                className="rounded"
              />
              Skip Google Drive (local artifacts only)
            </label>
          )}

          {modelOptions && modelOptions.length > 0 && (
            <label className="block text-sm text-gray-700">
              <span className="block mb-1">Model (this run only)</span>
              <select
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded
                  focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono bg-white"
              >
                <option value="">Use current config</option>
                {modelOptions.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </label>
          )}

          <div className="bg-yellow-50 border border-yellow-200 rounded-lg px-4 py-3 text-sm text-yellow-800">
            This will use Anthropic API credits
            {!isEnrich && !skipDrive && " and Google Drive quota"}.
            {!isEnrich && (
              <>
                {" "}
                Estimated cost: <strong>up to $2.00</strong> per run.
              </>
            )}
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}
        </div>

        <div className="flex justify-end gap-2 px-5 py-4 border-t border-gray-200">
          <button
            onClick={onClose}
            className="px-4 py-1.5 text-sm text-gray-700 bg-gray-100 rounded hover:bg-gray-200"
          >
            Cancel
          </button>
          <button
            onClick={confirm}
            disabled={launching}
            className="px-4 py-1.5 text-sm font-medium text-white bg-blue-600 rounded
              hover:bg-blue-700 disabled:opacity-50"
          >
            {launching ? "Launching…" : "Launch"}
          </button>
        </div>
      </div>
    </div>
  );
}
