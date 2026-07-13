import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { CompletedItem, QueueItem } from "../types";
import { useJobs } from "../hooks/useJobs";
import JobProgressModal from "../components/JobProgressModal";
import LaunchConfirmModal from "../components/LaunchConfirmModal";

// Contacts: the enrich domain as entities — queued profile screenshots and
// completed contacts. Executions (runs) live on the Queue page.
export default function ContactsPage() {
  const [queue, setQueue] = useState<QueueItem[] | null>(null);
  const [completed, setCompleted] = useState<CompletedItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState<QueueItem | null>(null);
  const [viewingJobId, setViewingJobId] = useState<string | null>(null);

  const fetchQueue = () =>
    api
      .get<QueueItem[]>("/tracking/queue")
      .then((items) => setQueue(items.filter((q) => q.subfolder === "profiles")))
      .catch((e) => setError(String(e)));
  const fetchCompleted = (force: boolean) =>
    api
      .get<CompletedItem[]>(
        force ? "/tracking/completed?refresh=true" : "/tracking/completed"
      )
      .then((items) => setCompleted(items.filter((c) => c.type === "profile")))
      .catch((e) => setError(String(e)));

  const { launchEnrich, launchBatch, runningJobForPath, getJob } = useJobs(() => {
    fetchQueue();
    fetchCompleted(true);
  });

  useEffect(() => {
    setError(null);
    fetchQueue();
    fetchCompleted(false);
  }, []);

  const refresh = () => {
    setError(null);
    setQueue(null);
    setCompleted(null);
    fetchQueue();
    fetchCompleted(true);
  };

  const confirmLaunch = async () => {
    if (!confirming) return;
    const jobId = await launchEnrich(confirming);
    setConfirming(null);
    setViewingJobId(jobId);
  };

  const enrichAll = async () => {
    try {
      const jobId = await launchBatch("/jobs/enrich-all", "Enrich all profiles");
      setViewingJobId(jobId);
    } catch (e) {
      setError(String(e));
    }
  };

  if (error) return <div className="p-6 text-red-600">{error}</div>;

  const viewingJob = getJob(viewingJobId);
  const rows = completed === null ? null : [...completed].sort(byCompanyThenPerson);

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Contacts</h1>
        <button onClick={refresh} className="text-sm text-blue-600 hover:underline">
          Refresh
        </button>
      </div>

      {/* Pending profile inputs */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
            Pending — {queue?.length ?? "…"}
          </h2>
          {(queue?.length ?? 0) > 0 && (
            <button
              onClick={enrichAll}
              className="px-3 py-1 text-xs font-medium text-white bg-blue-600 rounded
                hover:bg-blue-700"
            >
              Enrich all
            </button>
          )}
        </div>
        {queue === null ? (
          <p className="text-gray-400 text-sm">Loading…</p>
        ) : queue.length === 0 ? (
          <p className="text-gray-400 text-sm">
            No pending profiles in data/profiles/.
          </p>
        ) : (
          <ul className="divide-y divide-gray-100 border border-gray-200 rounded-lg overflow-hidden">
            {queue.map((item) => {
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
                    <button
                      onClick={() => setViewingJobId(job.id)}
                      className="ml-4 shrink-0 px-3 py-1 text-xs font-medium text-blue-600
                        border border-blue-200 rounded hover:bg-blue-50"
                    >
                      Running…
                    </button>
                  ) : (
                    <button
                      onClick={() => setConfirming(item)}
                      className="ml-4 shrink-0 px-3 py-1 text-xs font-medium text-white
                        bg-blue-600 rounded hover:bg-blue-700"
                    >
                      Enrich
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </section>

      {/* Completed contacts */}
      <section>
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
          Contacts {rows && `— ${rows.length}`}
        </h2>
        {rows === null ? (
          <p className="text-gray-400 text-sm">Loading…</p>
        ) : rows.length === 0 ? (
          <p className="text-gray-400 text-sm">No enriched contacts yet.</p>
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
                        onClick={() =>
                          setConfirming({
                            name: item.name,
                            path: item.path,
                            subfolder: "profiles",
                            extension: item.name.split(".").pop() ?? "pdf",
                          })
                        }
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

      {confirming && (
        <LaunchConfirmModal
          item={confirming}
          onClose={() => setConfirming(null)}
          onConfirm={confirmLaunch}
        />
      )}

      {viewingJob && (
        <JobProgressModal job={viewingJob} onClose={() => setViewingJobId(null)} />
      )}
    </div>
  );
}

// Company ascending, then person ascending.
const byCompanyThenPerson = (a: CompletedItem, b: CompletedItem) =>
  (a.company || a.folder_name).localeCompare(b.company || b.folder_name) ||
  (a.person || "").localeCompare(b.person || "");
