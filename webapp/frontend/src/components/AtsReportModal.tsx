import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { AtsReport, CompletedItem } from "../types";

interface Props {
  item: CompletedItem;
  onClose: () => void;
}

function Section({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div>
      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
        {title}
      </h3>
      <ul className="list-disc list-inside space-y-0.5">
        {items.map((text, i) => (
          <li key={i} className="text-sm text-gray-800">
            {text}
          </li>
        ))}
      </ul>
    </div>
  );
}

// Per-application ATS report, fetched live from the standalone re-check
// endpoint (#53): saved artifacts + one Docs read of the *current* resume.
// The re-check button supports the edit-in-Drive → re-check loop without
// re-running the apply pipeline.
export default function AtsReportModal({ item, onClose }: Props) {
  const [report, setReport] = useState<AtsReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const folder = encodeURIComponent(item.folder_name);

  const fetchReport = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setReport(await api.get<AtsReport>(`/tracking/applications/${folder}/ats`));
    } catch (e) {
      // A 409 means the saved artifacts predate the ATS assessment — surface
      // the endpoint's explanation instead of a report.
      setReport(null);
      setError(String(e instanceof Error ? e.message : e));
    } finally {
      setLoading(false);
    }
  }, [folder]);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  const label = item.company
    ? `${item.company} — ${item.title || ""}`.trim()
    : item.folder_name;
  const failedChecks = report?.checks.filter((c) => !c.passed) ?? [];

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 flex flex-col max-h-[90vh]">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 shrink-0">
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-gray-900 truncate">
              ATS Report
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

        <div className="p-5 overflow-y-auto flex-1 space-y-4">
          {loading && !report ? (
            <p className="text-sm text-gray-400">Checking…</p>
          ) : error ? (
            <p className="text-sm text-red-600">{error}</p>
          ) : report?.skipped ? (
            <p className="text-sm text-gray-600">
              No ATS assessment — no resume document was generated for this application
              (Drive skipped).
            </p>
          ) : report ? (
            <>
              <p className="text-sm text-gray-900">
                Keyword coverage:{" "}
                <span className="font-semibold tabular-nums">
                  {report.coverage_score === null
                    ? "—"
                    : report.coverage_score.toFixed(2)}
                </span>
              </p>
              <Section title="Present in resume" items={report.present} />
              <Section title="Missing (evidenced)" items={report.missing_evidenced} />
              <Section
                title="Missing (unevidenced)"
                items={report.missing_unevidenced}
              />
              <Section title="Unmapped requirements" items={report.unmapped} />
              <Section title="Recommendations" items={report.recommendations} />
              <Section
                title="Skills-file candidates"
                items={report.skills_file_candidates}
              />
              <Section title="Up-skill targets" items={report.upskill_targets} />
              <Section title="Fit vs. ATS gaps" items={report.fit_gaps} />
              {failedChecks.length > 0 ? (
                <Section
                  title="Parseability warnings"
                  items={failedChecks.map((c) => `${c.name}: ${c.reason}`)}
                />
              ) : (
                <p className="text-sm text-gray-600">
                  Parseability: all checks passed.
                </p>
              )}
            </>
          ) : null}
        </div>

        <div className="flex items-center justify-between px-5 py-4 border-t border-gray-200 shrink-0">
          <p className="text-xs text-gray-400">
            Edit the resume in Drive, then re-check — no AI calls.
          </p>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-1.5 text-sm text-gray-700 bg-gray-100 rounded hover:bg-gray-200"
            >
              Close
            </button>
            <button
              onClick={fetchReport}
              disabled={loading}
              className="px-4 py-1.5 text-sm font-medium text-white bg-blue-600 rounded
                hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? "Checking…" : "Re-check"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
