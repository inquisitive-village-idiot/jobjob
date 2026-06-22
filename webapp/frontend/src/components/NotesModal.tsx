import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { AppNote, CompletedItem } from "../types";

interface Props {
  item: CompletedItem;
  onClose: () => void;
  // Notify the parent of the new note count so the row badge stays in sync.
  onCountChange?: (folderName: string, count: number) => void;
}

function formatTs(ts: string): string {
  const d = new Date(ts);
  return isNaN(d.getTime()) ? ts : d.toLocaleString();
}

// Changelog of an application's status transitions (auto-logged) and free-text notes.
export default function NotesModal({ item, onClose, onCountChange }: Props) {
  const [notes, setNotes] = useState<AppNote[] | null>(null);
  const [draft, setDraft] = useState("");
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const folder = encodeURIComponent(item.folder_name);

  useEffect(() => {
    api
      .get<{ notes: AppNote[] }>(`/tracking/applications/${folder}/notes`)
      .then((r) => setNotes(r.notes))
      .catch((e) => setError(String(e instanceof Error ? e.message : e)));
  }, [folder]);

  const add = async () => {
    const text = draft.trim();
    if (!text) return;
    setAdding(true);
    setError(null);
    try {
      const r = await api.post<{ notes: AppNote[] }>(
        `/tracking/applications/${folder}/notes`,
        { text }
      );
      setNotes(r.notes);
      setDraft("");
      onCountChange?.(item.folder_name, r.notes.length);
    } catch (e) {
      setError(String(e instanceof Error ? e.message : e));
    } finally {
      setAdding(false);
    }
  };

  const label = item.company
    ? `${item.company} — ${item.title || ""}`.trim()
    : item.folder_name;

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 flex flex-col max-h-[90vh]">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 shrink-0">
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-gray-900 truncate">Notes</h2>
            <p className="text-xs text-gray-500 truncate">{label}</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        {/* Changelog trail */}
        <div className="p-5 overflow-y-auto flex-1 space-y-3">
          {notes === null && !error ? (
            <p className="text-sm text-gray-400">Loading…</p>
          ) : notes && notes.length === 0 ? (
            <p className="text-sm text-gray-400">No history yet.</p>
          ) : (
            <ul className="space-y-2">
              {notes?.map((n, i) => (
                <li key={i} className="flex gap-2 text-sm">
                  <span
                    className={`shrink-0 mt-0.5 inline-flex items-center px-1.5 py-0.5 rounded text-xs
                      font-medium border ${
                        n.kind === "status"
                          ? "bg-blue-50 text-blue-700 border-blue-200"
                          : "bg-gray-50 text-gray-600 border-gray-200"
                      }`}
                  >
                    {n.kind === "status" ? "Status" : "Note"}
                  </span>
                  <div className="min-w-0">
                    <p className="text-gray-800 whitespace-pre-wrap break-words">
                      {n.text}
                    </p>
                    <p className="text-xs text-gray-400">{formatTs(n.ts)}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Add note */}
        <div className="px-5 py-4 border-t border-gray-200 shrink-0 space-y-2">
          {error && <p className="text-sm text-red-600">{error}</p>}
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Add a note (e.g. recruiter call, follow-up date)…"
            rows={2}
            disabled={!item.status_writable}
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded resize-y
              focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50"
          />
          <div className="flex justify-end gap-2">
            <button
              onClick={onClose}
              className="px-4 py-1.5 text-sm text-gray-700 bg-gray-100 rounded hover:bg-gray-200"
            >
              Close
            </button>
            <button
              onClick={add}
              disabled={adding || !draft.trim() || !item.status_writable}
              className="px-4 py-1.5 text-sm font-medium text-white bg-blue-600 rounded
                hover:bg-blue-700 disabled:opacity-50"
            >
              {adding ? "Adding…" : "Add note"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
