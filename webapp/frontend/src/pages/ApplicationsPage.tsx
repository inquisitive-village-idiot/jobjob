import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api/client";
import { APP_STATUSES } from "../types";
import type {
  AppStatus,
  CompletedItem,
  ConfigSchema,
  QueueItem,
  RunRecord,
} from "../types";
import { useJobs } from "../hooks/useJobs";
import AddJdPanel from "../components/AddJdPanel";
import AtsReportModal from "../components/AtsReportModal";
import JobProgressModal from "../components/JobProgressModal";
import LaunchConfirmModal from "../components/LaunchConfirmModal";
import NotesModal from "../components/NotesModal";
import RowActions from "../components/RowActions";
import SourceEditModal from "../components/SourceEditModal";
import type { RowAction } from "../components/RowActions";

// Live BUILDING refresh interval — mirrors QueuePage's POLL_MS.
const POLL_MS = 5000;

// One application record — from the input dir while queued, from the output
// mirror once built (the confirmed two-source model). State is a column.
type Row =
  | { key: string; state: "QUEUED"; queued: QueueItem; built?: undefined }
  | { key: string; state: AppStatus; built: CompletedItem; queued?: undefined };

type StateFilter = "ALL" | "QUEUED" | "BUILDING" | AppStatus;
type SortMode = "company" | "fit" | "ats";

// Tint per state; QUEUED joins the stored statuses. BUILDING is derived
// (never stored) — see isRowBuilding below.
const STATE_STYLES: Record<string, string> = {
  QUEUED: "bg-sky-100 text-sky-800 border-sky-200",
  BUILDING: "bg-blue-100 text-blue-800 border-blue-200",
  BUILT: "bg-white text-gray-500 border-gray-200",
  APPLIED: "bg-green-100 text-green-800 border-green-200",
  IGNORED: "bg-gray-100 text-gray-600 border-gray-200",
  INTERVIEWING: "bg-blue-100 text-blue-800 border-blue-200",
  REJECTED: "bg-red-100 text-red-700 border-red-200",
  OFFER: "bg-purple-100 text-purple-800 border-purple-200",
  ACCEPTED: "bg-emerald-100 text-emerald-800 border-emerald-200",
  WITHDRAWN: "bg-amber-100 text-amber-800 border-amber-200",
};

const stateLabel = (s: string) =>
  s === "BUILT" ? "Built" : s.charAt(0) + s.slice(1).toLowerCase();

// Pipeline order for the filter chips.
const STATE_ORDER: string[] = ["QUEUED", "BUILT", ...APP_STATUSES.slice(1)];

const rowCompany = (r: Row) =>
  r.built ? r.built.company || r.built.folder_name : r.queued.name;

const byCompany = (a: Row, b: Row) =>
  rowCompany(a).localeCompare(rowCompany(b)) ||
  (a.built?.title || "").localeCompare(b.built?.title || "");

// Score-descending; rows without a score sort last. Ties fall back to company.
const byScoreDesc =
  (score: (r: Row) => number | null | undefined) => (a: Row, b: Row) => {
    const sa = score(a) ?? -1;
    const sb = score(b) ?? -1;
    return sb - sa || byCompany(a, b);
  };

const SORTS: Record<SortMode, (a: Row, b: Row) => number> = {
  company: byCompany,
  fit: byScoreDesc((r) => r.built?.fit?.role_fit),
  ats: byScoreDesc((r) => r.built?.ats_coverage),
};

const BAND_STYLES: Record<string, string> = {
  Strong: "bg-green-100 text-green-800 border-green-200",
  Moderate: "bg-amber-100 text-amber-800 border-amber-200",
  Weak: "bg-red-100 text-red-700 border-red-200",
};

// Compact per-row insight: band badge + whichever scores exist.
function InsightChip({ item }: { item: CompletedItem }) {
  const band = item.fit?.band;
  const scores = [
    typeof item.fit?.role_fit === "number" && `role ${item.fit.role_fit.toFixed(2)}`,
    typeof item.ats_coverage === "number" && `ATS ${item.ats_coverage.toFixed(2)}`,
  ].filter(Boolean);
  if (!band && scores.length === 0) return <span className="text-gray-300">—</span>;
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap">
      {band && (
        <span
          className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium
            border ${BAND_STYLES[band] ?? "bg-gray-50 text-gray-600 border-gray-200"}`}
        >
          {band}
        </span>
      )}
      {scores.length > 0 && (
        <span className="text-xs text-gray-500 tabular-nums">{scores.join(" · ")}</span>
      )}
    </span>
  );
}

// Id-preferring join (application-identity, phase 1): prefer entity_id
// equality (survives a folder rename since the run happened), falling back
// to folder_name when either side lacks an id — mirrors
// services/tracking_service.run_matches_application; keep in sync.
const runMatchesApplication = (r: RunRecord, item: CompletedItem): boolean =>
  r.entity_id && item.entity_id
    ? r.entity_id === item.entity_id
    : r.folder_name === item.folder_name;

// Latest run touching this row; the list from /jobs is newest-first.
const latestRunFor = (row: Row, runs: RunRecord[]): RunRecord | undefined =>
  runs.find((r) =>
    row.built ? runMatchesApplication(r, row.built) : r.paths.includes(row.queued.path)
  );

// Run kinds that represent document generation — a running run of one of
// these means the row is actively being (re)built. Excludes apply (autofill)
// and enrich, which don't touch the résumé/cover letter.
const BUILDING_KINDS: ReadonlySet<RunRecord["kind"]> = new Set([
  "build",
  "batch",
  "schedule",
]);

// Derived (never stored) live BUILDING flag: true when the row's latest
// matching run (by the join above) is a document-generation run still in
// progress, regardless of which page/session launched it. Exported as a
// small pure helper for reviewability — this repo has no JS test runner
// (module-local, not exported, to keep Fast Refresh's single-export rule happy).
function isRowBuilding(row: Row, runs: RunRecord[]): boolean {
  const run = latestRunFor(row, runs);
  return !!run && run.status === "running" && BUILDING_KINDS.has(run.kind);
}

function StateCell({
  row,
  building,
  onChange,
  onViewBuilding,
}: {
  row: Row;
  building?: RunRecord;
  onChange: (item: CompletedItem, status: AppStatus) => Promise<void>;
  onViewBuilding: (runId: string) => void;
}) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!row.built || !row.built.status_writable) {
    const state = building ? "BUILDING" : row.state;
    return (
      <span
        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium
          border ${STATE_STYLES[state] ?? STATE_STYLES.BUILT}`}
        title={
          building
            ? "A build is running for this application."
            : row.built
              ? "Status and notes need a local applications mirror — set APPLICATIONS_OUTPUT_DIR in Settings to enable them."
              : "Queued — not built yet."
        }
      >
        {stateLabel(state)}
      </span>
    );
  }

  const item = row.built;
  const status: AppStatus = item.app_status ?? "BUILT";
  const change = async (next: AppStatus) => {
    setSaving(true);
    setError(null);
    try {
      await onChange(item, next);
    } catch (e) {
      setError(String(e instanceof Error ? e.message : e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex items-center gap-1.5">
      <div>
        <select
          value={status}
          disabled={saving}
          onChange={(e) => change(e.target.value as AppStatus)}
          className={`px-1.5 py-0.5 text-xs font-medium rounded border cursor-pointer
            focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50
            ${STATE_STYLES[status]}`}
          title="Set application status"
        >
          {APP_STATUSES.map((s) => (
            <option key={s} value={s}>
              {stateLabel(s)}
            </option>
          ))}
        </select>
        {error && (
          <p className="mt-1 text-xs text-red-600" title={error}>
            Save failed
          </p>
        )}
      </div>
      {building && (
        <button
          onClick={() => onViewBuilding(building.run_id)}
          className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium
            border whitespace-nowrap hover:opacity-80 ${STATE_STYLES.BUILDING}`}
          title="A build is running for this application — view live progress"
        >
          Building…
        </button>
      )}
    </div>
  );
}

export default function ApplicationsPage() {
  const [queue, setQueue] = useState<QueueItem[] | null>(null);
  const [completed, setCompleted] = useState<CompletedItem[] | null>(null);
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<StateFilter>("ALL");
  const [sortMode, setSortMode] = useState<SortMode>("company");
  const [building, setBuilding] = useState<QueueItem | null>(null);
  const [rebuilding, setRebuilding] = useState<CompletedItem | null>(null);
  const [notesApp, setNotesApp] = useState<CompletedItem | null>(null);
  const [atsApp, setAtsApp] = useState<CompletedItem | null>(null);
  const [sourceApp, setSourceApp] = useState<CompletedItem | null>(null);
  const [modelOptions, setModelOptions] = useState<string[]>([]);
  const [viewingJobId, setViewingJobId] = useState<string | null>(null);

  const fetchQueue = () =>
    api
      .get<QueueItem[]>("/tracking/queue")
      .then((items) => setQueue(items.filter((q) => q.subfolder === "jobs")))
      .catch((e) => setError(String(e)));
  const fetchCompleted = (force: boolean) =>
    api
      .get<CompletedItem[]>(
        force ? "/tracking/completed?refresh=true" : "/tracking/completed"
      )
      .then((items) => setCompleted(items.filter((c) => c.type === "jd")))
      .catch((e) => setError(String(e)));
  const fetchRuns = () =>
    api
      .get<RunRecord[]>("/jobs")
      .then(setRuns)
      .catch(() => setRuns([]));

  const {
    launchApply,
    launchApplyFromSource,
    launchApplyRerun,
    launchAutofill,
    launchBatch,
    relaunchApply,
    deleteQueued,
    runningJobForPath,
    getJob,
  } = useJobs(() => {
    fetchQueue();
    fetchCompleted(true);
    fetchRuns();
  });

  useEffect(() => {
    setError(null);
    fetchQueue();
    fetchCompleted(false);
    fetchRuns();
    api
      .get<ConfigSchema>("/config")
      .then((s) => setModelOptions(s.CLAUDE_MODEL?.options ?? []))
      .catch(() => setModelOptions([]));
  }, []);

  // Live BUILDING state: poll the run listing (mirrors QueuePage's
  // POLL_MS/interval) so BUILDING appears/clears without a manual reload,
  // regardless of which page/session launched the run. A ref (not the `runs`
  // state) tracks the previous tick so the interval closure stays current.
  const runsRef = useRef<RunRecord[]>(runs);
  useEffect(() => {
    runsRef.current = runs;
  }, [runs]);

  useEffect(() => {
    const buildingIds = (list: RunRecord[]) =>
      new Set(
        list
          .filter((r) => r.status === "running" && BUILDING_KINDS.has(r.kind))
          .map((r) => r.run_id)
      );
    const t = setInterval(() => {
      api
        .get<RunRecord[]>("/jobs")
        .then((next) => {
          const wasBuilding = buildingIds(runsRef.current);
          // A previously-building run reached a terminal state — refresh
          // queue/completed so its row moves to the built state. Avoid a
          // forced rescan on every tick; only on this transition.
          const settled = [...wasBuilding].some((id) => !buildingIds(next).has(id));
          setRuns(next);
          if (settled) {
            fetchQueue();
            fetchCompleted(true);
          }
        })
        .catch(() => {});
    }, POLL_MS);
    return () => clearInterval(t);
  }, []);

  const setAppStatus = async (item: CompletedItem, status: AppStatus) => {
    await api.patch(
      `/tracking/applications/${encodeURIComponent(item.folder_name)}/status`,
      { status }
    );
    const changed = (item.app_status ?? "BUILT") !== status;
    setCompleted((prev) =>
      prev === null
        ? prev
        : prev.map((c) =>
            c.folder_name === item.folder_name
              ? {
                  ...c,
                  app_status: status,
                  note_count: (c.note_count ?? 0) + (changed ? 1 : 0),
                }
              : c
          )
    );
  };

  const setNoteCount = (folderName: string, count: number) =>
    setCompleted((prev) =>
      prev === null
        ? prev
        : prev.map((c) =>
            c.folder_name === folderName ? { ...c, note_count: count } : c
          )
    );

  const appLabel = (item: CompletedItem) =>
    item.company ? `${item.company} — ${item.title || ""}`.trim() : item.folder_name;

  const rows: Row[] | null = useMemo(() => {
    if (queue === null || completed === null) return null;
    return [
      ...queue.map(
        (q): Row => ({ key: `queued:${q.path}`, state: "QUEUED", queued: q })
      ),
      ...completed.map(
        (c): Row => ({
          key: `built:${c.folder_name}`,
          state: c.app_status ?? "BUILT",
          built: c,
        })
      ),
    ];
  }, [queue, completed]);

  // BUILDING is derived, not a stored state — it slots into the pipeline
  // right after QUEUED and only appears while at least one row is building.
  const anyBuilding = useMemo(
    () => (rows ?? []).some((r) => isRowBuilding(r, runs)),
    [rows, runs]
  );

  const presentStates = useMemo(() => {
    const order = [STATE_ORDER[0], "BUILDING", ...STATE_ORDER.slice(1)];
    return order.filter((s) =>
      s === "BUILDING" ? anyBuilding : (rows ?? []).some((r) => r.state === s)
    );
  }, [rows, anyBuilding]);

  const visible = (rows ?? [])
    .filter((r) => {
      if (filter === "ALL") return true;
      if (filter === "BUILDING") return isRowBuilding(r, runs);
      if (filter === "QUEUED") return r.state === "QUEUED";
      return r.state === filter;
    })
    .sort(SORTS[sortMode]);

  const refresh = () => {
    setError(null);
    setQueue(null);
    setCompleted(null);
    fetchQueue();
    fetchCompleted(true);
    fetchRuns();
  };

  const confirmBuild = async ({ skipDrive }: { skipDrive: boolean }) => {
    if (!building) return;
    const jobId = await launchApply(building, { skipDrive });
    setBuilding(null);
    setViewingJobId(jobId);
  };

  const confirmRebuild = async ({
    skipDrive,
    model,
  }: {
    skipDrive: boolean;
    model?: string;
  }) => {
    if (!rebuilding) return;
    const jobId = await launchApplyRerun(rebuilding.folder_name, appLabel(rebuilding), {
      skipDrive,
      model,
    });
    setRebuilding(null);
    setViewingJobId(jobId);
  };

  const buildAll = async () => {
    try {
      const jobId = await launchBatch("/jobs/build-all", "Build all JDs");
      setViewingJobId(jobId);
    } catch (e) {
      setError(String(e));
    }
  };

  const rowActions = (row: Row): RowAction[] => {
    if (row.queued) {
      const item = row.queued;
      return [
        { label: "Build", onClick: () => setBuilding(item) },
        {
          label: "Delete",
          onClick: async () => {
            await deleteQueued(item.path);
            fetchQueue();
          },
          title: "Remove the queued JD file",
        },
      ];
    }
    const item = row.built;
    const actions: RowAction[] = [
      { label: "Re-build", onClick: () => setRebuilding(item) },
      item.posting_url
        ? {
            label: "Apply",
            onClick: async () => {
              try {
                const jobId = await launchAutofill({
                  folder_name: item.folder_name,
                  entity_id: item.entity_id,
                });
                setViewingJobId(jobId);
              } catch (e) {
                setError(String(e));
              }
            },
            title: "Autofill (Playwright): fill contact basics, then finish by hand.",
          }
        : {
            label: "Apply",
            disabled: true,
            title: "Needs a posting URL — attach one via Edit source before applying.",
          },
    ];
    if (item.status_writable) {
      actions.push(
        { label: "ATS report", onClick: () => setAtsApp(item) },
        {
          label: `Notes${item.note_count ? ` (${item.note_count})` : ""}`,
          onClick: () => setNotesApp(item),
        },
        { label: "Edit source", onClick: () => setSourceApp(item) }
      );
    }
    if (item.drive?.web_link) {
      actions.push({ label: "Drive", href: item.drive.web_link });
    }
    return actions;
  };

  if (error) return <div className="p-6 text-red-600">{error}</div>;

  const viewingJob = getJob(viewingJobId);

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Applications</h1>
        <button onClick={refresh} className="text-sm text-blue-600 hover:underline">
          Refresh
        </button>
      </div>

      <AddJdPanel
        onSubmit={async (source, opts) => {
          const jobId = await launchApplyFromSource(source, opts);
          setViewingJobId(jobId);
          return jobId;
        }}
      />

      <section>
        <div className="flex items-center justify-between mb-3 gap-4">
          <div className="flex items-center gap-1.5 flex-wrap">
            {(["ALL", ...presentStates] as StateFilter[]).map((s) => (
              <button
                key={s}
                onClick={() => setFilter(s)}
                className={`px-2 py-0.5 rounded-full text-xs font-medium border transition-colors ${
                  filter === s
                    ? "bg-blue-600 text-white border-blue-600"
                    : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
                }`}
              >
                {s === "ALL" ? `All${rows ? ` — ${rows.length}` : ""}` : stateLabel(s)}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <label className="text-xs text-gray-500">
              Sort{" "}
              <select
                value={sortMode}
                onChange={(e) => setSortMode(e.target.value as SortMode)}
                className="px-1.5 py-0.5 text-xs border border-gray-200 rounded
                  focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="company">Company</option>
                <option value="fit">Role fit</option>
                <option value="ats">ATS coverage</option>
              </select>
            </label>
            {(queue?.length ?? 0) > 0 && (
              <button
                onClick={buildAll}
                className="px-3 py-1 text-xs font-medium text-white bg-blue-600 rounded
                  hover:bg-blue-700"
              >
                Build all
              </button>
            )}
          </div>
        </div>

        {rows === null ? (
          <p className="text-gray-400 text-sm">Loading…</p>
        ) : visible.length === 0 ? (
          <p className="text-gray-400 text-sm">
            No applications yet — add a job posting above.
          </p>
        ) : (
          <div className="border border-gray-200 rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                  <th className="px-4 py-2 w-28">Date</th>
                  <th className="px-4 py-2">Company</th>
                  <th className="px-4 py-2">Title</th>
                  <th className="px-4 py-2 w-40">Fit</th>
                  <th className="px-4 py-2 w-32">State</th>
                  <th className="px-4 py-2 w-28 text-right"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 border-t border-gray-200">
                {visible.map((row) => {
                  const liveJob = row.queued
                    ? runningJobForPath(row.queued.path)
                    : undefined;
                  const lastRun = latestRunFor(row, runs);
                  const buildingRun = isRowBuilding(row, runs) ? lastRun : undefined;
                  return (
                    <tr key={row.key} className="bg-white hover:bg-gray-50">
                      <td className="px-4 py-2 align-top whitespace-nowrap text-gray-500 tabular-nums">
                        {row.built?.date || "—"}
                      </td>
                      <td className="px-4 py-2 align-top font-medium text-gray-900">
                        {rowCompany(row)}
                        {row.built?.entity_id && (
                          <p className="font-mono font-normal text-[10px] text-gray-300">
                            {row.built.entity_id.slice(0, 8)}
                          </p>
                        )}
                      </td>
                      <td className="px-4 py-2 align-top text-gray-700">
                        {row.built?.title || "—"}
                      </td>
                      <td className="px-4 py-2 align-top">
                        {row.built ? (
                          <InsightChip item={row.built} />
                        ) : (
                          <span className="text-gray-300">—</span>
                        )}
                      </td>
                      <td className="px-4 py-2 align-top">
                        <StateCell
                          row={row}
                          building={buildingRun}
                          onChange={setAppStatus}
                          onViewBuilding={setViewingJobId}
                        />
                      </td>
                      <td className="px-4 py-2 align-top text-right whitespace-nowrap">
                        {row.built?.status === "error" && (
                          <span
                            className="text-red-500 mr-1"
                            title="Incomplete artifacts"
                          >
                            ⚠
                          </span>
                        )}
                        {lastRun?.status === "failed" && !liveJob && (
                          <a
                            href="#queue"
                            className="inline-flex items-center px-1.5 py-0.5 mr-2 rounded
                              text-xs font-medium border bg-red-50 text-red-700
                              border-red-200 hover:bg-red-100"
                            title={lastRun.error ?? "The last run failed — see Queue."}
                          >
                            ⚠ failed
                          </a>
                        )}
                        {liveJob ? (
                          <button
                            onClick={() => setViewingJobId(liveJob.id)}
                            className="px-2 py-0.5 text-xs font-medium text-blue-600 border
                              border-blue-200 rounded hover:bg-blue-50"
                          >
                            Building…
                          </button>
                        ) : (
                          <RowActions actions={rowActions(row)} />
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {building && (
        <LaunchConfirmModal
          item={building}
          onClose={() => setBuilding(null)}
          onConfirm={confirmBuild}
        />
      )}

      {rebuilding && (
        <LaunchConfirmModal
          item={{
            name: appLabel(rebuilding),
            path: rebuilding.folder_name,
            subfolder: "jobs",
            extension: "pdf",
          }}
          onClose={() => setRebuilding(null)}
          onConfirm={confirmRebuild}
          modelOptions={modelOptions}
        />
      )}

      {viewingJob && (
        <JobProgressModal
          job={viewingJob}
          onClose={() => setViewingJobId(null)}
          onRelaunch={
            viewingJob.kind === "build" && viewingJob.path
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
            viewingJob.kind === "build" && viewingJob.path
              ? async () => {
                  await deleteQueued(viewingJob.path!);
                  setViewingJobId(null);
                  fetchQueue();
                }
              : undefined
          }
        />
      )}

      {notesApp && (
        <NotesModal
          item={notesApp}
          onClose={() => setNotesApp(null)}
          onCountChange={setNoteCount}
        />
      )}

      {atsApp && <AtsReportModal item={atsApp} onClose={() => setAtsApp(null)} />}

      {sourceApp && (
        <SourceEditModal item={sourceApp} onClose={() => setSourceApp(null)} />
      )}
    </div>
  );
}
