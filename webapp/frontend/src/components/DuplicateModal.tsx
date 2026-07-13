import { useState } from "react";
import { api } from "../api/client";
import type { CompletedItem } from "../types";

interface Props {
  // The application the modal was opened from — the default "survivor" when
  // merging (it keeps its entity_id/status/root execution — design D3).
  item: CompletedItem;
  // Other applications sharing the same duplicate_group.
  candidates: CompletedItem[];
  onClose: () => void;
  // Parent refetches the completed list after a merge/delete resolves it.
  onResolved: () => void;
}

const appLabel = (item: CompletedItem) =>
  item.company ? `${item.company} — ${item.title || ""}`.trim() : item.folder_name;

// Resolve a flagged possible-duplicate pair (application-identity, phase 6c):
// merge one into the other, or delete one outright. Never automatic (design
// D3) — every resolution here is an explicit click.
export default function DuplicateModal({
  item,
  candidates,
  onClose,
  onResolved,
}: Props) {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const withBusy = async (key: string, fn: () => Promise<void>) => {
    setBusy(key);
    setError(null);
    try {
      await fn();
      onResolved();
      onClose();
    } catch (e) {
      setError(String(e instanceof Error ? e.message : e));
    } finally {
      setBusy(null);
    }
  };

  const mergeInto = (other: CompletedItem) =>
    withBusy(`merge:${other.folder_name}`, async () => {
      await api.post(
        `/tracking/applications/${encodeURIComponent(item.folder_name)}/merge`,
        { loser_folder_name: other.folder_name }
      );
    });

  const deleteOther = (other: CompletedItem) =>
    withBusy(`delete:${other.folder_name}`, async () => {
      if (!confirm(`Delete "${appLabel(other)}" outright? This cannot be undone.`)) {
        throw new Error("cancelled");
      }
      await api.del(
        `/tracking/applications/${encodeURIComponent(other.folder_name)}/duplicate`
      );
    });

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 flex flex-col max-h-[90vh]">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 shrink-0">
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-gray-900 truncate">
              Possible duplicate
            </h2>
            <p className="text-xs text-gray-500 truncate">{appLabel(item)}</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        <div className="p-5 overflow-y-auto flex-1 space-y-3">
          <p className="text-xs text-gray-500">
            These share the same normalized company + role. Nothing merges automatically
            — choose an action for each, or leave them as they are.
          </p>
          {error && error !== "cancelled" && (
            <p className="text-sm text-red-600">{error}</p>
          )}
          <ul className="space-y-3">
            {candidates.map((other) => (
              <li
                key={other.folder_name}
                className="border border-gray-200 rounded-lg p-3 space-y-2"
              >
                <p className="text-sm font-medium text-gray-800 truncate">
                  {appLabel(other)}
                </p>
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => mergeInto(other)}
                    disabled={busy !== null}
                    className="px-2 py-0.5 text-xs font-medium text-white bg-blue-600 rounded
                      hover:bg-blue-700 disabled:opacity-50"
                    title={`Re-parent this one's executions + notes into "${appLabel(
                      item
                    )}", then remove this folder`}
                  >
                    {busy === `merge:${other.folder_name}`
                      ? "Merging…"
                      : `Merge into "${appLabel(item)}"`}
                  </button>
                  <button
                    onClick={() => deleteOther(other)}
                    disabled={busy !== null}
                    className="px-2 py-0.5 text-xs font-medium text-red-700 bg-red-50 border
                      border-red-200 rounded hover:bg-red-100 disabled:opacity-50"
                  >
                    {busy === `delete:${other.folder_name}` ? "Deleting…" : "Delete"}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <div className="px-5 py-4 border-t border-gray-200 shrink-0 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 text-sm text-gray-700 bg-gray-100 rounded hover:bg-gray-200"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
