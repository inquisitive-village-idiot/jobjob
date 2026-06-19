import { useState } from "react";
import type { QueueItem } from "../types";

interface ScheduleParams {
  mode: "sync" | "async";
  concurrency: number;
  interval_minutes: number;
  start_at: string;
  paths: string[];
}

interface Props {
  items: QueueItem[];
  onClose: () => void;
  onConfirm: (params: ScheduleParams) => Promise<void>;
}

function nowLocalIso(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/**
 * Modal for configuring and launching a scheduled batch run over selected queue items.
 * Shows all unprocessed items (both apply and enrich), all checked by default.
 */
export default function ScheduleModal({ items, onClose, onConfirm }: Props) {
  const [mode, setMode] = useState<"sync" | "async">("sync");
  const [concurrency, setConcurrency] = useState(2);
  const [intervalMinutes, setIntervalMinutes] = useState(0);
  const [startAt, setStartAt] = useState(nowLocalIso);
  const [selected, setSelected] = useState<Set<string>>(
    () => new Set(items.map((i) => i.path))
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const allChecked = selected.size === items.length;
  const noneChecked = selected.size === 0;

  const toggle = (path: string) =>
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(path) ? next.delete(path) : next.add(path);
      return next;
    });

  const selectAll = () => setSelected(new Set(items.map((i) => i.path)));
  const deselectAll = () => setSelected(new Set());

  const submit = async () => {
    if (noneChecked) return;
    setError(null);
    setSubmitting(true);
    try {
      // Convert local datetime string to ISO with local timezone offset.
      const localDate = new Date(startAt);
      const isoStart = isNaN(localDate.getTime())
        ? new Date().toISOString()
        : localDate.toISOString();

      await onConfirm({
        mode,
        concurrency: mode === "async" ? Math.max(1, concurrency) : 1,
        interval_minutes: Math.max(0, intervalMinutes),
        start_at: isoStart,
        paths: items.filter((i) => selected.has(i.path)).map((i) => i.path),
      });
    } catch (e) {
      setError(String(e));
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 shrink-0">
          <h2 className="text-base font-semibold text-gray-900">Schedule Jobs</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        {/* Body */}
        <div className="p-5 space-y-4 overflow-y-auto flex-1">
          {/* Mode */}
          <div>
            <label className="block text-xs font-medium text-gray-600 uppercase tracking-wide mb-1">
              Execution mode
            </label>
            <div className="flex gap-3">
              {(["sync", "async"] as const).map((m) => (
                <label key={m} className="flex items-center gap-1.5 text-sm text-gray-700 cursor-pointer">
                  <input
                    type="radio"
                    name="mode"
                    value={m}
                    checked={mode === m}
                    onChange={() => setMode(m)}
                  />
                  {m === "sync" ? "Sync (sequential)" : "Async (concurrent)"}
                </label>
              ))}
            </div>
          </div>

          {/* Concurrency — only relevant in async mode */}
          {mode === "async" && (
            <div>
              <label className="block text-xs font-medium text-gray-600 uppercase tracking-wide mb-1">
                Concurrency
              </label>
              <input
                type="number"
                min={1}
                value={concurrency}
                onChange={(e) => setConcurrency(Math.max(1, Number(e.target.value)))}
                className="w-24 border border-gray-300 rounded px-3 py-1.5 text-sm"
              />
              <span className="ml-2 text-xs text-gray-500">jobs running at once</span>
            </div>
          )}

          {/* Interval */}
          <div>
            <label className="block text-xs font-medium text-gray-600 uppercase tracking-wide mb-1">
              Interval between jobs
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min={0}
                value={intervalMinutes}
                onChange={(e) => setIntervalMinutes(Math.max(0, Number(e.target.value)))}
                className="w-24 border border-gray-300 rounded px-3 py-1.5 text-sm"
              />
              <span className="text-xs text-gray-500">minutes</span>
            </div>
          </div>

          {/* Start time */}
          <div>
            <label className="block text-xs font-medium text-gray-600 uppercase tracking-wide mb-1">
              Scheduled start
            </label>
            <input
              type="datetime-local"
              value={startAt}
              onChange={(e) => setStartAt(e.target.value)}
              className="border border-gray-300 rounded px-3 py-1.5 text-sm"
            />
          </div>

          {/* Item checklist */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-gray-600 uppercase tracking-wide">
                Items to run — {selected.size}/{items.length}
              </span>
              <div className="flex gap-2">
                <button
                  onClick={selectAll}
                  disabled={allChecked}
                  className="text-xs text-blue-600 hover:underline disabled:text-gray-400"
                >
                  Select all
                </button>
                <span className="text-gray-300">|</span>
                <button
                  onClick={deselectAll}
                  disabled={noneChecked}
                  className="text-xs text-blue-600 hover:underline disabled:text-gray-400"
                >
                  Deselect all
                </button>
              </div>
            </div>
            {items.length === 0 ? (
              <p className="text-sm text-gray-400">No unprocessed items in queue.</p>
            ) : (
              <ul className="divide-y divide-gray-100 border border-gray-200 rounded-lg overflow-hidden max-h-48 overflow-y-auto">
                {items.map((item) => (
                  <li key={item.path}>
                    <label className="flex items-center gap-3 px-3 py-2 hover:bg-gray-50 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={selected.has(item.path)}
                        onChange={() => toggle(item.path)}
                        className="rounded shrink-0"
                      />
                      <span className="text-sm text-gray-900 truncate flex-1">{item.name}</span>
                      <span className="text-xs text-gray-400 shrink-0">
                        {item.subfolder === "profiles" ? "Enrich" : "Apply"}
                      </span>
                    </label>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 px-5 py-4 border-t border-gray-200 shrink-0">
          <button
            onClick={onClose}
            className="px-4 py-1.5 text-sm text-gray-700 bg-gray-100 rounded hover:bg-gray-200"
          >
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={submitting || noneChecked}
            className="px-4 py-1.5 text-sm font-medium text-white bg-blue-600 rounded
              hover:bg-blue-700 disabled:opacity-50"
          >
            {submitting
              ? "Scheduling…"
              : `Schedule ${selected.size} job${selected.size !== 1 ? "s" : ""}`}
          </button>
        </div>
      </div>
    </div>
  );
}
