import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { CompletedItem, ExecutionRecord } from "../types";

interface Props {
  item: CompletedItem;
  onClose: () => void;
  // Notify the parent of the new archived-execution count so the row badge
  // stays in sync (mirrors NotesModal's onCountChange).
  onCountChange?: (folderName: string, count: number) => void;
}

function formatTs(ts: string): string {
  // Timestamps are "YYYY-MM-DDTHH.MM.SS" (dots, not colons — Drive/filesystem
  // safe); swap back to colons so Date can parse it for display.
  const iso = ts.replace(/T(\d{2})\.(\d{2})\.(\d{2})$/, "T$1:$2:$3");
  const d = new Date(iso);
  return isNaN(d.getTime()) ? ts : d.toLocaleString();
}

// View/promote/note/lock/purge an application's archived (superseded)
// executions — application-identity phase 6b. The primary (root) execution
// is not listed here; it's what the rest of the app already shows.
export default function ExecutionsModal({ item, onClose, onCountChange }: Props) {
  const [executions, setExecutions] = useState<ExecutionRecord[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyTs, setBusyTs] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});

  const folder = encodeURIComponent(item.folder_name);
  const base = `/tracking/applications/${folder}/executions`;

  const load = () =>
    api
      .get<{ executions: ExecutionRecord[] }>(base)
      .then((r) => {
        setExecutions(r.executions);
        setDrafts(
          Object.fromEntries(r.executions.map((e) => [e.timestamp, e.note ?? ""]))
        );
        onCountChange?.(item.folder_name, r.executions.length);
      })
      .catch((e) => setError(String(e instanceof Error ? e.message : e)));

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [folder]);

  const withBusy = async (ts: string, fn: () => Promise<void>) => {
    setBusyTs(ts);
    setError(null);
    try {
      await fn();
    } catch (e) {
      setError(String(e instanceof Error ? e.message : e));
    } finally {
      setBusyTs(null);
    }
  };

  const promote = (ts: string) =>
    withBusy(ts, async () => {
      const r = await api.post<{ executions: ExecutionRecord[] }>(
        `${base}/${ts}/promote`,
        {}
      );
      setExecutions(r.executions);
      setDrafts(
        Object.fromEntries(r.executions.map((e) => [e.timestamp, e.note ?? ""]))
      );
      onCountChange?.(item.folder_name, r.executions.length);
    });

  const saveNote = (ts: string) =>
    withBusy(ts, async () => {
      const text = drafts[ts] ?? "";
      const updated = await api.patch<ExecutionRecord>(`${base}/${ts}`, { note: text });
      setExecutions((prev) =>
        (prev ?? []).map((e) => (e.timestamp === ts ? updated : e))
      );
    });

  const toggleLock = (ts: string, locked: boolean) =>
    withBusy(ts, async () => {
      const updated = await api.patch<ExecutionRecord>(`${base}/${ts}`, { locked });
      setExecutions((prev) =>
        (prev ?? []).map((e) => (e.timestamp === ts ? updated : e))
      );
    });

  const purgeAll = () =>
    withBusy("__purge__", async () => {
      const r = await api.del<{ purged: string[] }>(base);
      const purgedSet = new Set(r.purged);
      const remaining = (executions ?? []).filter((e) => !purgedSet.has(e.timestamp));
      setExecutions(remaining);
      onCountChange?.(item.folder_name, remaining.length);
    });

  const label = item.company
    ? `${item.company} — ${item.title || ""}`.trim()
    : item.folder_name;

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl mx-4 flex flex-col max-h-[90vh]">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 shrink-0">
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-gray-900 truncate">
              Archived executions
            </h2>
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

        <div className="p-5 overflow-y-auto flex-1 space-y-3">
          {error && <p className="text-sm text-red-600">{error}</p>}
          {executions === null && !error ? (
            <p className="text-sm text-gray-400">Loading…</p>
          ) : executions && executions.length === 0 ? (
            <p className="text-sm text-gray-400">
              No archived executions — only re-builds that chose "archive instead of
              overwrite" create one.
            </p>
          ) : (
            <ul className="space-y-3">
              {executions?.map((e) => (
                <li
                  key={e.timestamp}
                  className="border border-gray-200 rounded-lg p-3 space-y-2"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-800">
                        {formatTs(e.timestamp)}
                      </p>
                      {e.locked && (
                        <span
                          className="inline-flex items-center px-1.5 py-0.5 rounded text-xs
                            font-medium border bg-amber-50 text-amber-700 border-amber-200"
                          title="Locked — exempt from purge"
                        >
                          Locked
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <button
                        onClick={() => toggleLock(e.timestamp, !e.locked)}
                        disabled={busyTs === e.timestamp}
                        className="px-2 py-0.5 text-xs font-medium text-gray-700 border
                          border-gray-200 rounded hover:bg-gray-50 disabled:opacity-50"
                      >
                        {e.locked ? "Unlock" : "Lock"}
                      </button>
                      <button
                        onClick={() => promote(e.timestamp)}
                        disabled={busyTs === e.timestamp}
                        className="px-2 py-0.5 text-xs font-medium text-white bg-blue-600
                          rounded hover:bg-blue-700 disabled:opacity-50"
                        title="Make this execution primary"
                      >
                        Promote
                      </button>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <input
                      value={drafts[e.timestamp] ?? ""}
                      onChange={(ev) =>
                        setDrafts((d) => ({ ...d, [e.timestamp]: ev.target.value }))
                      }
                      placeholder="Why we kept this run…"
                      className="flex-1 px-2 py-1 text-sm border border-gray-300 rounded
                        focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <button
                      onClick={() => saveNote(e.timestamp)}
                      disabled={
                        busyTs === e.timestamp ||
                        (drafts[e.timestamp] ?? "") === (e.note ?? "")
                      }
                      className="px-2 py-1 text-xs font-medium text-gray-700 bg-gray-100
                        rounded hover:bg-gray-200 disabled:opacity-50"
                    >
                      Save note
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="px-5 py-4 border-t border-gray-200 shrink-0 flex justify-between gap-2">
          <button
            onClick={purgeAll}
            disabled={
              busyTs !== null || !executions || executions.every((e) => e.locked)
            }
            className="px-3 py-1.5 text-sm font-medium text-red-700 bg-red-50 border
              border-red-200 rounded hover:bg-red-100 disabled:opacity-50"
            title="Delete every unlocked archived execution for this application"
          >
            Purge unlocked
          </button>
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
