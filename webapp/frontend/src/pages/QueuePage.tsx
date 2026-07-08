import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { QueueItem, RunRecord, ScheduledJob } from "../types";
import type { Job } from "../hooks/useJobs";
import { useJobs } from "../hooks/useJobs";
import JobProgressModal from "../components/JobProgressModal";
import ScheduleModal from "../components/ScheduleModal";

// Queue = executions. Entities live on Applications/Contacts; this page shows
// the persisted run history (with logs, surviving restarts) and scheduling.
const POLL_MS = 5000;

const KIND_LABELS: Record<RunRecord["kind"], string> = {
  build: "Build",
  enrich: "Enrich",
  batch: "Batch",
  schedule: "Schedule",
  apply: "Apply",
};

const STATUS_STYLES: Record<RunRecord["status"], string> = {
  running: "bg-blue-100 text-blue-800 border-blue-200",
  completed: "bg-green-100 text-green-800 border-green-200",
  failed: "bg-red-100 text-red-700 border-red-200",
};

function formatTs(ts?: string | null): string {
  if (!ts) return "—";
  const d = new Date(ts);
  return isNaN(d.getTime()) ? ts : d.toLocaleString();
}

function RunRow({ run }: { run: RunRecord }) {
  const [expanded, setExpanded] = useState(false);
  const [log, setLog] = useState<string | null>(null);
  const [logError, setLogError] = useState<string | null>(null);

  const toggle = async () => {
    const next = !expanded;
    setExpanded(next);
    if (next && log === null && run.has_log) {
      try {
        const r = await api.get<{ log: string }>(`/jobs/${run.run_id}/log`);
        setLog(r.log);
      } catch (e) {
        setLogError(String(e instanceof Error ? e.message : e));
      }
    }
  };

  return (
    <li className="bg-white">
      <button
        onClick={toggle}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-50"
      >
        <span
          className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium
            border shrink-0 ${STATUS_STYLES[run.status]}`}
        >
          {run.status}
        </span>
        <span className="text-xs text-gray-400 shrink-0 w-16">
          {KIND_LABELS[run.kind] ?? run.kind}
        </span>
        <span className="text-sm font-medium text-gray-900 truncate">
          {run.label || run.run_id}
        </span>
        <span className="ml-auto text-xs text-gray-400 shrink-0 tabular-nums">
          {formatTs(run.started_at)}
        </span>
        <span className="text-gray-300 shrink-0">{expanded ? "▴" : "▾"}</span>
      </button>
      {expanded && (
        <div className="px-4 pb-3 space-y-2">
          {run.error && <p className="text-xs text-red-600">{run.error}</p>}
          {run.has_log ? (
            log === null && !logError ? (
              <p className="text-xs text-gray-400">Loading log…</p>
            ) : logError ? (
              <p className="text-xs text-red-600">{logError}</p>
            ) : (
              <pre
                className="text-xs text-gray-700 bg-gray-50 border border-gray-200 rounded
                  p-3 max-h-64 overflow-auto whitespace-pre-wrap"
              >
                {log}
              </pre>
            )
          ) : (
            <p className="text-xs text-gray-400">No stored log for this run.</p>
          )}
        </div>
      )}
    </li>
  );
}

export default function QueuePage() {
  const [runs, setRuns] = useState<RunRecord[] | null>(null);
  const [scheduled, setScheduled] = useState<ScheduledJob[] | null>(null);
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [scheduling, setScheduling] = useState(false);
  const [viewingJobId, setViewingJobId] = useState<string | null>(null);

  const fetchRuns = useCallback(
    () =>
      api
        .get<RunRecord[]>("/jobs")
        .then(setRuns)
        .catch((e) => setError(String(e))),
    []
  );
  const fetchScheduled = () =>
    api
      .get<ScheduledJob[]>("/jobs/scheduled")
      .then(setScheduled)
      .catch((e) => setError(String(e)));
  const fetchQueue = () =>
    api
      .get<QueueItem[]>("/tracking/queue")
      .then(setQueue)
      .catch(() => setQueue([]));

  const { launchSchedule, getJob } = useJobs(() => {
    fetchRuns();
    fetchScheduled();
  });

  useEffect(() => {
    setError(null);
    fetchRuns();
    fetchScheduled();
    fetchQueue();
  }, [fetchRuns]);

  // Poll while anything is running so live runs settle into the history.
  useEffect(() => {
    if (!runs?.some((r) => r.status === "running")) return;
    const t = setInterval(fetchRuns, POLL_MS);
    return () => clearInterval(t);
  }, [runs, fetchRuns]);

  if (error) return <div className="p-6 text-red-600">{error}</div>;

  const viewingJob = getJob(viewingJobId);
  const runningScheduled = scheduled?.filter((s) => s.status === "running") ?? [];

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Queue</h1>
        <button
          onClick={() => {
            setError(null);
            fetchRuns();
            fetchScheduled();
          }}
          className="text-sm text-blue-600 hover:underline"
        >
          Refresh
        </button>
      </div>

      {/* Scheduled batches */}
      <ScheduledSection
        items={runningScheduled}
        loading={scheduled === null}
        onSchedule={() => setScheduling(true)}
        getJob={getJob}
        onView={setViewingJobId}
      />

      {/* Run history */}
      <section>
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
          Runs {runs && `— ${runs.length}`}
        </h2>
        {runs === null ? (
          <p className="text-gray-400 text-sm">Loading…</p>
        ) : runs.length === 0 ? (
          <p className="text-gray-400 text-sm">
            No runs yet — build an application from the Applications page.
          </p>
        ) : (
          <ul className="divide-y divide-gray-100 border border-gray-200 rounded-lg overflow-hidden">
            {runs.map((run) => (
              <RunRow key={run.run_id} run={run} />
            ))}
          </ul>
        )}
      </section>

      {scheduling && (
        <ScheduleModal
          items={queue}
          onClose={() => setScheduling(false)}
          onConfirm={async (params) => {
            const jobId = await launchSchedule(params);
            setScheduling(false);
            setViewingJobId(jobId);
            fetchRuns();
          }}
        />
      )}

      {viewingJob && (
        <JobProgressModal job={viewingJob} onClose={() => setViewingJobId(null)} />
      )}
    </div>
  );
}

// ── Scheduled batches ──────────────────────────────────────────────────────────

function ScheduledSection({
  items,
  loading,
  onSchedule,
  getJob,
  onView,
}: {
  items: ScheduledJob[];
  loading: boolean;
  onSchedule: () => void;
  getJob: (id: string | null) => Job | undefined;
  onView: (jobId: string) => void;
}) {
  const totalItems = items.reduce((n, s) => n + s.paths.length, 0);

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
          Scheduled {!loading && `— ${totalItems} item${totalItems !== 1 ? "s" : ""}`}
        </h2>
        <button
          onClick={onSchedule}
          className="px-3 py-1 text-xs font-medium text-white bg-indigo-600 rounded
            hover:bg-indigo-700"
        >
          Schedule
        </button>
      </div>

      {loading ? (
        <p className="text-gray-400 text-sm">Loading…</p>
      ) : items.length === 0 ? (
        <p className="text-gray-400 text-sm">No scheduled jobs running.</p>
      ) : (
        <div className="space-y-3">
          {items.map((sched) => {
            const job = getJob(sched.job_id);
            return (
              <div
                key={sched.job_id}
                className="border border-gray-200 rounded-lg overflow-hidden"
              >
                <div className="flex items-center justify-between px-4 py-2 bg-gray-50 border-b border-gray-200">
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-block w-2 h-2 rounded-full shrink-0 ${
                        sched.status === "running"
                          ? "bg-blue-500 animate-pulse"
                          : "bg-gray-400"
                      }`}
                    />
                    <span className="text-xs font-medium text-gray-700">
                      Schedule — {sched.count} item{sched.count !== 1 ? "s" : ""}
                    </span>
                    <span className="text-xs text-gray-400">
                      {sched.mode} · {sched.concurrency}× · {sched.interval_minutes}m
                      gap
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500">
                      starts {new Date(sched.start_at).toLocaleString()}
                    </span>
                    {job && (
                      <button
                        onClick={() => onView(sched.job_id)}
                        className="px-2 py-0.5 text-xs font-medium text-blue-600 border
                          border-blue-200 rounded hover:bg-blue-50"
                      >
                        View
                      </button>
                    )}
                  </div>
                </div>
                <ul className="divide-y divide-gray-100">
                  {sched.paths.map((path) => {
                    const name = path.split("/").pop() ?? path;
                    const expectedTime = sched.expected_times[path];
                    return (
                      <li
                        key={path}
                        className="flex items-center justify-between px-4 py-2 bg-white"
                      >
                        <span className="text-sm text-gray-800 truncate">{name}</span>
                        {expectedTime && (
                          <span className="text-xs text-gray-400 shrink-0 ml-4">
                            ~
                            {new Date(expectedTime).toLocaleTimeString([], {
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </span>
                        )}
                      </li>
                    );
                  })}
                </ul>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
