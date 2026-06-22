import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { QueueItem, ScheduledJob } from "../types";
import type { Job } from "../hooks/useJobs";
import { useJobs } from "../hooks/useJobs";
import JobProgressModal from "../components/JobProgressModal";
import LaunchConfirmModal from "../components/LaunchConfirmModal";
import ScheduleModal from "../components/ScheduleModal";
import AddJdPanel from "../components/AddJdPanel";
import { FloatingOutline, useScrollSpy } from "../components/PageOutline";
import type { OutlineItem } from "../components/PageOutline";

export default function QueuePage() {
  const [queue, setQueue] = useState<QueueItem[] | null>(null);
  const [scheduled, setScheduled] = useState<ScheduledJob[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState<QueueItem | null>(null);
  const [viewingJobId, setViewingJobId] = useState<string | null>(null);
  const [scheduling, setScheduling] = useState(false);

  const fetchQueue = () =>
    api
      .get<QueueItem[]>("/tracking/queue")
      .then(setQueue)
      .catch((e) => setError(String(e)));

  const fetchScheduled = () =>
    api
      .get<ScheduledJob[]>("/jobs/scheduled")
      .then(setScheduled)
      .catch((e) => setError(String(e)));

  const {
    launchApply,
    launchApplyFromSource,
    relaunchApply,
    deleteQueued,
    launchEnrich,
    launchBatch,
    launchSchedule,
    runningJobForPath,
    getJob,
  } = useJobs(() => {
    fetchQueue();
    fetchScheduled();
  });

  useEffect(() => {
    setError(null);
    fetchQueue();
    fetchScheduled();
  }, []);

  const activeId = useScrollSpy(
    ["q-queued", "q-apply", "q-enrich"],
    [queue, scheduled]
  );

  const jdQueue = queue?.filter((q) => q.subfolder === "jobs") ?? [];
  const profileQueue = queue?.filter((q) => q.subfolder === "profiles") ?? [];
  const runningScheduled = scheduled?.filter((s) => s.status === "running") ?? [];

  const outline: OutlineItem[] = [
    { id: "q-queued", label: "Queued" },
    { id: "q-apply", label: "Apply" },
    { id: "q-enrich", label: "Enrich" },
  ];

  const confirmLaunch = async ({ skipDrive }: { skipDrive: boolean }) => {
    if (!confirming) return;
    const item = confirming;
    const jobId =
      item.subfolder === "profiles"
        ? await launchEnrich(item)
        : await launchApply(item, { skipDrive });
    setConfirming(null);
    setViewingJobId(jobId);
  };

  const processAll = async (type: "apply" | "enrich") => {
    const endpoint = type === "apply" ? "/jobs/apply-all" : "/jobs/enrich-all";
    const label = type === "apply" ? "Apply all JDs" : "Enrich all profiles";
    try {
      const jobId = await launchBatch(endpoint, label);
      setViewingJobId(jobId);
    } catch (e) {
      setError(String(e));
    }
  };

  if (error) return <div className="p-6 text-red-600">{error}</div>;

  const viewingJob = getJob(viewingJobId);

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <h1 className="text-xl font-semibold text-gray-900">Queue</h1>

      <div className="relative">
        <FloatingOutline items={outline} activeId={activeId} />
        <div className="space-y-6">
          {/* Queued section */}
          <div id="q-queued" className="scroll-mt-16">
            <ScheduledSection
              items={runningScheduled}
              loading={scheduled === null}
              onSchedule={() => setScheduling(true)}
              getJob={getJob}
              onView={setViewingJobId}
            />
          </div>

          {/* Apply section */}
          <div id="q-apply" className="scroll-mt-16 space-y-4">
            <AddJdPanel
              onSubmit={async (source, opts) => {
                const jobId = await launchApplyFromSource(source, opts);
                setViewingJobId(jobId);
                return jobId;
              }}
            />
            <QueueSection
              title="Apply"
              items={queue === null ? null : jdQueue}
              emptyText="No pending JDs in data/jobs/."
              actionLabel="Apply"
              onLaunch={setConfirming}
              onView={setViewingJobId}
              runningJobForPath={runningJobForPath}
              onRefresh={fetchQueue}
              onProcessAll={jdQueue.length > 0 ? () => processAll("apply") : undefined}
            />
          </div>

          {/* Enrich section */}
          <div id="q-enrich" className="scroll-mt-16">
            <QueueSection
              title="Enrich"
              items={queue === null ? null : profileQueue}
              emptyText="No pending profiles in data/profiles/."
              actionLabel="Enrich"
              onLaunch={setConfirming}
              onView={setViewingJobId}
              runningJobForPath={runningJobForPath}
              onRefresh={fetchQueue}
              onProcessAll={
                profileQueue.length > 0 ? () => processAll("enrich") : undefined
              }
            />
          </div>
        </div>
      </div>

      {confirming && (
        <LaunchConfirmModal
          item={confirming}
          onClose={() => setConfirming(null)}
          onConfirm={confirmLaunch}
        />
      )}

      {scheduling && (
        <ScheduleModal
          items={queue ?? []}
          onClose={() => setScheduling(false)}
          onConfirm={async (params) => {
            const jobId = await launchSchedule(params);
            setScheduling(false);
            setViewingJobId(jobId);
          }}
        />
      )}

      {viewingJob && (
        <JobProgressModal
          job={viewingJob}
          onClose={() => setViewingJobId(null)}
          onRelaunch={
            viewingJob.kind === "apply" && viewingJob.path
              ? async (allowOverwrite) => {
                  const id = await relaunchApply(viewingJob, {
                    skipDrive: false,
                    allowOverwrite,
                  });
                  setViewingJobId(id);
                }
              : undefined
          }
          onClearDelete={
            viewingJob.kind === "apply" && viewingJob.path
              ? async () => {
                  await deleteQueued(viewingJob.path!);
                  setViewingJobId(null);
                  fetchQueue();
                }
              : undefined
          }
        />
      )}
    </div>
  );
}

// ── Queued / Scheduled section ─────────────────────────────────────────────────

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
          Queued {!loading && `— ${totalItems} item${totalItems !== 1 ? "s" : ""}`}
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

// ── Queue section ──────────────────────────────────────────────────────────────

function Spinner() {
  return (
    <span
      className="inline-block w-3.5 h-3.5 border-2 border-gray-300 border-t-blue-600
        rounded-full animate-spin"
      aria-hidden
    />
  );
}

function QueueSection({
  title,
  items,
  emptyText,
  actionLabel,
  onLaunch,
  onView,
  runningJobForPath,
  onRefresh,
  onProcessAll,
}: {
  title: string;
  items: QueueItem[] | null;
  emptyText: string;
  actionLabel: string;
  onLaunch: (item: QueueItem) => void;
  onView: (jobId: string) => void;
  runningJobForPath: (path: string) => Job | undefined;
  onRefresh: () => void;
  onProcessAll?: () => void;
}) {
  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
          {title} — {items?.length ?? "…"}
        </h2>
        <div className="flex items-center gap-2">
          <button
            onClick={onRefresh}
            className="px-3 py-1 text-xs font-medium text-gray-600 border border-gray-200
              rounded hover:bg-gray-50"
          >
            Refresh
          </button>
          {onProcessAll && (
            <button
              onClick={onProcessAll}
              className="px-3 py-1 text-xs font-medium text-white bg-blue-600 rounded
                hover:bg-blue-700"
            >
              {actionLabel} All
            </button>
          )}
        </div>
      </div>

      {items === null ? (
        <p className="text-gray-400 text-sm">Loading…</p>
      ) : items.length === 0 ? (
        <p className="text-gray-400 text-sm">{emptyText}</p>
      ) : (
        <ul className="divide-y divide-gray-100 border border-gray-200 rounded-lg overflow-hidden">
          {items.map((item) => {
            const job = runningJobForPath(item.path);
            return (
              <li
                key={item.path}
                className="flex items-center justify-between px-4 py-3 bg-white hover:bg-gray-50"
              >
                <span className="text-sm font-medium text-gray-900 truncate">
                  {item.name}
                </span>
                {job ? (
                  <div className="ml-4 shrink-0 flex items-center gap-2">
                    <span className="flex items-center gap-1.5 text-xs text-gray-500">
                      <Spinner />
                      Running…
                    </span>
                    <button
                      onClick={() => onView(job.id)}
                      className="px-3 py-1 text-xs font-medium text-blue-600 border
                        border-blue-200 rounded hover:bg-blue-50"
                    >
                      View
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => onLaunch(item)}
                    className="ml-4 shrink-0 px-3 py-1 text-xs font-medium text-white
                      bg-blue-600 rounded hover:bg-blue-700"
                  >
                    {actionLabel}
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
