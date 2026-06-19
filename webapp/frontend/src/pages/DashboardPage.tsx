import { useEffect, useState } from "react";
import { api } from "../api/client";
import { APP_STATUSES } from "../types";
import type { AppStatus, CompletedItem, ConfigSchema, QueueItem } from "../types";
import { useJobs } from "../hooks/useJobs";
import JobProgressModal from "../components/JobProgressModal";
import LaunchConfirmModal from "../components/LaunchConfirmModal";
import { FloatingOutline, useScrollSpy } from "../components/PageOutline";
import type { OutlineItem } from "../components/PageOutline";

type Tab = "apply" | "enrich";

export default function DashboardPage() {
  const [completed, setCompleted] = useState<CompletedItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("apply");
  const [confirming, setConfirming] = useState<QueueItem | null>(null);
  const [rerunningApp, setRerunningApp] = useState<CompletedItem | null>(null);
  const [modelOptions, setModelOptions] = useState<string[]>([]);
  const [viewingJobId, setViewingJobId] = useState<string | null>(null);

  const fetchCompleted = (force: boolean) =>
    api
      .get<CompletedItem[]>(force ? "/tracking/completed?refresh=true" : "/tracking/completed")
      .then(setCompleted)
      .catch((e) => setError(String(e)));

  const { launchApply, launchApplyRerun, launchEnrich, getJob } = useJobs(() =>
    fetchCompleted(true)
  );

  // Patch local state on success instead of refetching: the backend cache is
  // invalidated by the PATCH, so any later natural fetch stays consistent.
  const setAppStatus = async (item: CompletedItem, status: AppStatus) => {
    await api.patch(
      `/tracking/applications/${encodeURIComponent(item.folder_name)}/status`,
      { status }
    );
    setCompleted((prev) =>
      prev === null
        ? prev
        : prev.map((c) =>
            c.folder_name === item.folder_name ? { ...c, app_status: status } : c
          )
    );
  };

  const appLabel = (item: CompletedItem) =>
    item.company ? `${item.company} — ${item.title || ""}`.trim() : item.folder_name;

  const confirmRerun = async ({
    skipDrive,
    model,
  }: {
    skipDrive: boolean;
    model?: string;
  }) => {
    if (!rerunningApp) return;
    const jobId = await launchApplyRerun(rerunningApp.folder_name, appLabel(rerunningApp), {
      skipDrive,
      model,
    });
    setRerunningApp(null);
    setViewingJobId(jobId);
  };

  useEffect(() => {
    setError(null);
    fetchCompleted(false);
    // Model options for the per-run override on re-run (same static list as Config).
    api
      .get<ConfigSchema>("/config")
      .then((s) => setModelOptions(s.CLAUDE_MODEL?.options ?? []))
      .catch(() => setModelOptions([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Sidebar + scroll-spy mirror the table's per-status sections (apply tab only).
  const jdStatusGroups =
    tab === "apply"
      ? STATUS_ORDER.filter((s) =>
          (completed ?? []).some(
            (c) => c.type === "jd" && (c.app_status ?? "GENERATED") === s
          )
        )
      : [];
  const sectionIds =
    jdStatusGroups.length > 0
      ? jdStatusGroups.map((s) => `db-status-${s}`)
      : ["db-completed"];
  const activeId = useScrollSpy(sectionIds, [tab, completed]);

  const refresh = () => {
    setError(null);
    setCompleted(null);
    fetchCompleted(true);
  };

  const jdCompleted = completed?.filter((c) => c.type === "jd") ?? [];
  const profileCompleted = completed?.filter((c) => c.type === "profile") ?? [];

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

  if (error) return <div className="p-6 text-red-600">{error}</div>;

  const viewingJob = getJob(viewingJobId);

  const outline: OutlineItem[] =
    tab === "apply" && jdStatusGroups.length > 0
      ? jdStatusGroups.map((s) => ({ id: `db-status-${s}`, label: statusLabel(s) }))
      : [
          {
            id: "db-completed",
            label: tab === "apply" ? "Completed Applications" : "Completed Profiles",
          },
        ];

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Dashboard</h1>
        <button onClick={refresh} className="text-sm text-blue-600 hover:underline">
          Refresh
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200">
        {(["apply", "enrich"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium -mb-px border-b-2 transition-colors ${
              tab === t
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t === "apply" ? "Applications" : "Profiles"}
          </button>
        ))}
      </div>

      <div className="relative">
        <FloatingOutline items={outline} activeId={activeId} />
        <div id="db-completed" className="scroll-mt-16">
          {tab === "apply" ? (
            <CompletedAppsTable
              items={completed === null ? null : jdCompleted}
              onRerun={setRerunningApp}
              onStatusChange={setAppStatus}
            />
          ) : (
            <CompletedProfilesTable
              items={completed === null ? null : profileCompleted}
              onRerun={(item) =>
                setConfirming({
                  name: item.name,
                  path: item.path,
                  subfolder: "profiles",
                  extension: item.name.split(".").pop()!,
                })
              }
            />
          )}
        </div>
      </div>

      {confirming && (
        <LaunchConfirmModal
          item={confirming}
          onClose={() => setConfirming(null)}
          onConfirm={confirmLaunch}
        />
      )}

      {rerunningApp && (
        <LaunchConfirmModal
          item={{
            name: appLabel(rerunningApp),
            path: rerunningApp.folder_name,
            subfolder: "jobs",
            extension: "pdf",
          }}
          onClose={() => setRerunningApp(null)}
          onConfirm={confirmRerun}
          modelOptions={modelOptions}
        />
      )}

      {viewingJob && (
        <JobProgressModal job={viewingJob} onClose={() => setViewingJobId(null)} />
      )}
    </div>
  );
}

// ── Completed applications table ───────────────────────────────────────────────

// Tint per status; applied to both the read-only badge and the select control.
const STATUS_STYLES: Record<AppStatus, string> = {
  GENERATED: "bg-white text-gray-500 border-gray-200",
  APPLIED: "bg-green-100 text-green-800 border-green-200",
  IGNORED: "bg-gray-100 text-gray-600 border-gray-200",
  INTERVIEWING: "bg-blue-100 text-blue-800 border-blue-200",
  REJECTED: "bg-red-100 text-red-700 border-red-200",
  OFFER: "bg-purple-100 text-purple-800 border-purple-200",
  ACCEPTED: "bg-emerald-100 text-emerald-800 border-emerald-200",
  WITHDRAWN: "bg-amber-100 text-amber-800 border-amber-200",
};

const statusLabel = (s: AppStatus) => s.charAt(0) + s.slice(1).toLowerCase();

function StatusCell({
  item,
  onChange,
}: {
  item: CompletedItem;
  onChange: (item: CompletedItem, status: AppStatus) => Promise<void>;
}) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const status: AppStatus = item.app_status ?? "GENERATED";

  if (!item.status_writable) {
    return (
      <span
        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${STATUS_STYLES[status]}`}
        title="Status is read-only without a local applications mirror"
      >
        {statusLabel(status)}
      </span>
    );
  }

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
    <div>
      <select
        value={status}
        disabled={saving}
        onChange={(e) => change(e.target.value as AppStatus)}
        className={`px-1.5 py-0.5 text-xs font-medium rounded border cursor-pointer
          focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50
          ${STATUS_STYLES[status]}`}
        title="Set application status"
      >
        {APP_STATUSES.map((s) => (
          <option key={s} value={s}>
            {statusLabel(s)}
          </option>
        ))}
      </select>
      {error && (
        <p className="mt-1 text-xs text-red-600" title={error}>
          Save failed
        </p>
      )}
    </div>
  );
}

// Section order for the dashboard: Generated first, Ignored last.
const STATUS_ORDER: AppStatus[] = [
  "GENERATED",
  "APPLIED",
  "INTERVIEWING",
  "OFFER",
  "ACCEPTED",
  "REJECTED",
  "WITHDRAWN",
  "IGNORED",
];

// Within a section: company ascending, then role ascending.
const byCompanyThenRole = (a: CompletedItem, b: CompletedItem) =>
  (a.company || a.folder_name).localeCompare(b.company || b.folder_name) ||
  (a.title || "").localeCompare(b.title || "");

// Profiles: company ascending, then person ascending.
const byCompanyThenPerson = (a: CompletedItem, b: CompletedItem) =>
  (a.company || a.folder_name).localeCompare(b.company || b.folder_name) ||
  (a.person || "").localeCompare(b.person || "");

function AppRow({
  item,
  onRerun,
  onStatusChange,
}: {
  item: CompletedItem;
  onRerun: (item: CompletedItem) => void;
  onStatusChange: (item: CompletedItem, status: AppStatus) => Promise<void>;
}) {
  return (
    <tr className="bg-white hover:bg-gray-50">
      <td className="px-4 py-2 align-top whitespace-nowrap text-gray-500 tabular-nums">
        {item.date || "—"}
      </td>
      <td className="px-4 py-2 align-top font-medium text-gray-900">
        {item.company || item.folder_name}
      </td>
      <td className="px-4 py-2 align-top text-gray-700">{item.title || "—"}</td>
      <td className="px-4 py-2 align-top">
        <StatusCell item={item} onChange={onStatusChange} />
      </td>
      <td className="px-4 py-2 align-top text-right whitespace-nowrap">
        {item.status === "error" && (
          <span className="text-red-500 mr-1" title="Incomplete artifacts">
            ⚠
          </span>
        )}
        {item.drive?.web_link && (
          <a
            href={item.drive.web_link}
            target="_blank"
            rel="noreferrer"
            className="text-blue-600 hover:underline text-xs mr-2"
          >
            Drive
          </a>
        )}
        <button
          onClick={() => onRerun(item)}
          className="px-2 py-0.5 text-xs font-medium text-gray-700 border
            border-gray-200 rounded hover:bg-gray-50"
          title="Re-run apply with the current config, reusing this JD"
        >
          Re-run
        </button>
      </td>
    </tr>
  );
}

function CompletedAppsTable({
  items,
  onRerun,
  onStatusChange,
}: {
  items: CompletedItem[] | null;
  onRerun: (item: CompletedItem) => void;
  onStatusChange: (item: CompletedItem, status: AppStatus) => Promise<void>;
}) {
  const groups =
    items === null
      ? null
      : STATUS_ORDER.map((status) => ({
          status,
          rows: items
            .filter((i) => (i.app_status ?? "GENERATED") === status)
            .sort(byCompanyThenRole),
        })).filter((g) => g.rows.length > 0);

  return (
    <section>
      <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
        Completed Applications {items && `— ${items.length}`}
      </h2>

      {groups === null ? (
        <p className="text-gray-400 text-sm">Loading…</p>
      ) : groups.length === 0 ? (
        <p className="text-gray-400 text-sm">No completed applications yet.</p>
      ) : (
        <div className="border border-gray-200 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                <th className="px-4 py-2 w-28">Date</th>
                <th className="px-4 py-2">Company</th>
                <th className="px-4 py-2">Title</th>
                <th className="px-4 py-2 w-32">Status</th>
                <th className="px-4 py-2 w-32 text-right"></th>
              </tr>
            </thead>
            {groups.map((g) => (
              <tbody key={g.status} className="divide-y divide-gray-100 border-t border-gray-200">
                <tr id={`db-status-${g.status}`} className="scroll-mt-16">
                  <td colSpan={5} className="px-4 py-1.5 bg-gray-50/70">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs
                        font-medium border ${STATUS_STYLES[g.status]}`}
                    >
                      {statusLabel(g.status)}
                    </span>
                    <span className="ml-2 text-xs text-gray-400">{g.rows.length}</span>
                  </td>
                </tr>
                {g.rows.map((item) => (
                  <AppRow
                    key={item.folder_name}
                    item={item}
                    onRerun={onRerun}
                    onStatusChange={onStatusChange}
                  />
                ))}
              </tbody>
            ))}
          </table>
        </div>
      )}
    </section>
  );
}

// ── Completed profiles table ───────────────────────────────────────────────────

function CompletedProfilesTable({
  items,
  onRerun,
}: {
  items: CompletedItem[] | null;
  onRerun: (item: CompletedItem) => void;
}) {
  const rows = items === null ? null : [...items].sort(byCompanyThenPerson);
  return (
    <section>
      <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
        Completed Profiles {items && `— ${items.length}`}
      </h2>

      {rows === null ? (
        <p className="text-gray-400 text-sm">Loading…</p>
      ) : rows.length === 0 ? (
        <p className="text-gray-400 text-sm">No completed profiles yet.</p>
      ) : (
        <div className="border border-gray-200 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                <th className="px-4 py-2 w-28">Created</th>
                <th className="px-4 py-2 w-28">Processed</th>
                <th className="px-4 py-2">Company</th>
                <th className="px-4 py-2">Person</th>
                <th className="px-4 py-2 w-32 text-right"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 border-t border-gray-200">
              {rows.map((item) => (
                <tr key={item.path} className="bg-white hover:bg-gray-50">
                  <td className="px-4 py-2 align-top whitespace-nowrap text-gray-500 tabular-nums">
                    {item.date_created || "—"}
                  </td>
                  <td className="px-4 py-2 align-top whitespace-nowrap text-gray-500 tabular-nums">
                    {item.date_processed || "—"}
                  </td>
                  <td className="px-4 py-2 align-top font-medium text-gray-900">
                    {item.company || item.folder_name}
                  </td>
                  <td className="px-4 py-2 align-top text-gray-700">
                    {item.person || "—"}
                  </td>
                  <td className="px-4 py-2 align-top text-right whitespace-nowrap">
                    {item.drive?.web_link && (
                      <a
                        href={item.drive.web_link}
                        target="_blank"
                        rel="noreferrer"
                        className="text-blue-600 hover:underline text-xs mr-2"
                      >
                        Sheet
                      </a>
                    )}
                    <button
                      onClick={() => onRerun(item)}
                      className="px-2 py-0.5 text-xs font-medium text-gray-700 border
                        border-gray-200 rounded hover:bg-gray-50"
                      title="Re-run enrich for this profile"
                    >
                      Re-run
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
