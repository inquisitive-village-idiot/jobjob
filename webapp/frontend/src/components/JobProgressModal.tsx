import { useEffect, useRef } from "react";
import type { Job } from "../hooks/useJobs";

interface Props {
  job: Job;
  onClose: () => void;
  // Re-run apply for this job's source JD (override = acknowledge overwrite).
  onRelaunch?: (allowOverwrite: boolean) => void;
  // Delete the queued JD and dismiss (clear a failed job).
  onClearDelete?: () => void;
}

interface TokenUsage {
  input_tokens?: number;
  output_tokens?: number;
  cache_read_input_tokens?: number;
  cache_creation_input_tokens?: number;
}

function levelColor(level: string): string {
  switch (level) {
    case "ERROR":
    case "CRITICAL":
      return "text-red-400";
    case "WARNING":
      return "text-yellow-400";
    case "INFO":
      return "text-green-400";
    default:
      return "text-gray-400";
  }
}

/**
 * Reopenable view of a job's live progress. Closing it only hides the view —
 * the job keeps running (its EventSource is owned by useJobs at the page level).
 */
export default function JobProgressModal({
  job,
  onClose,
  onRelaunch,
  onClearDelete,
}: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [job.lines]);

  const usage = (job.result?.token_usage as TokenUsage | undefined) ?? null;
  const model = job.result?.model as string | undefined;
  const title =
    job.kind === "batch"
      ? job.label
      : // NOTE: UI-only rename — the pipeline is "Build" in copy; API/CLI names unchanged (full rename is a future change).
        `${job.kind === "enrich" ? "Enrich" : "Build"} — ${job.label}`;

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-gray-900 truncate">{title}</h2>
            {job.kind === "batch" && job.count != null && (
              <p className="text-xs text-gray-500 mt-0.5">
                {job.count} item{job.count !== 1 ? "s" : ""}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl leading-none shrink-0"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        <div className="p-5 space-y-2">
          <div className="bg-gray-900 rounded-lg p-4 h-64 overflow-y-auto font-mono text-xs">
            {job.lines.map((line, i) => (
              <div key={i} className="flex gap-2">
                <span className={`shrink-0 ${levelColor(line.level)}`}>
                  [{line.level.slice(0, 4)}]
                </span>
                <span className="text-gray-200 break-all">{line.message}</span>
              </div>
            ))}
            {job.status === "running" && (
              <div className="text-gray-500 animate-pulse">▌</div>
            )}
            <div ref={bottomRef} />
          </div>

          {job.status !== "running" && (
            <div
              className={`flex items-center gap-2 px-3 py-2 rounded text-sm font-medium ${
                job.status === "completed"
                  ? "bg-green-50 text-green-800"
                  : "bg-red-50 text-red-800"
              }`}
            >
              <span>{job.status === "completed" ? "✓ Completed" : "✗ Failed"}</span>
              {job.finalMessage && (
                <span className="font-normal">{job.finalMessage}</span>
              )}
            </div>
          )}

          {job.status === "failed" && (onRelaunch || onClearDelete) && (
            <div className="space-y-2">
              {job.overwriteConflict && (
                <p className="text-xs text-amber-700 bg-amber-50 rounded px-3 py-2">
                  An application already exists for
                  {job.folderName ? ` "${job.folderName}"` : " this role"}. Relaunching
                  with override will overwrite it (previous versions remain in Google
                  Docs history).
                </p>
              )}
              <div className="flex flex-wrap gap-2">
                {onRelaunch && job.overwriteConflict && (
                  <button
                    onClick={() => onRelaunch(true)}
                    className="px-3 py-1.5 text-sm font-medium text-white bg-amber-600
                      rounded hover:bg-amber-700"
                  >
                    Relaunch with override
                  </button>
                )}
                {onRelaunch && (
                  <button
                    onClick={() => onRelaunch(false)}
                    className="px-3 py-1.5 text-sm font-medium text-gray-700 border
                      border-gray-300 rounded hover:bg-gray-50"
                  >
                    Retry
                  </button>
                )}
                {onClearDelete && (
                  <button
                    onClick={onClearDelete}
                    className="px-3 py-1.5 text-sm font-medium text-red-700 border
                      border-red-200 rounded hover:bg-red-50"
                  >
                    Clear &amp; delete JD
                  </button>
                )}
              </div>
            </div>
          )}

          {model && (
            <div className="bg-gray-50 rounded-lg px-4 py-2 text-xs text-gray-600">
              <span className="font-medium text-gray-700">Model:</span>{" "}
              <span className="font-mono">{model}</span>
            </div>
          )}

          {usage && (
            <div className="bg-gray-50 rounded-lg px-4 py-3 text-xs text-gray-600 space-y-1">
              <p className="font-medium text-gray-700">Token usage</p>
              <p>Input: {usage.input_tokens?.toLocaleString()}</p>
              <p>Output: {usage.output_tokens?.toLocaleString()}</p>
              {(usage.cache_read_input_tokens ?? 0) > 0 && (
                <p>Cache read: {usage.cache_read_input_tokens?.toLocaleString()}</p>
              )}
            </div>
          )}
        </div>

        <div className="flex items-center justify-between px-5 py-4 border-t border-gray-200">
          <span className="text-xs text-gray-400">
            {job.status === "running"
              ? "Running in the background — you can close this and keep working."
              : "Finished."}
          </span>
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
