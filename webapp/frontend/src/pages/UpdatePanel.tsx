import { useEffect, useState } from "react";
import { api } from "../api/client";

interface UpdateStatus {
  current_version: string;
  current_release_date: string | null;
  latest_version: string | null;
  latest_release_date: string | null;
  last_checked: string | null;
  check_error: string | null;
  install_method: "pipx" | "pip" | "source";
  update_available: boolean;
  can_update: boolean;
}

interface ApplyResult {
  ok: boolean;
  method: string;
  message: string;
  command?: string;
  stdout?: string;
  stderr?: string;
}

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString();
}

function fmtDateTime(iso: string | null): string {
  if (!iso) return "Never";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

export default function UpdatePanel() {
  const [status, setStatus] = useState<UpdateStatus | null>(null);
  const [checking, setChecking] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ApplyResult | null>(null);

  useEffect(() => {
    api
      .get<UpdateStatus>("/update/status")
      .then(setStatus)
      .catch((e) => setError(String(e)));
  }, []);

  const check = async () => {
    setChecking(true);
    setError(null);
    setResult(null);
    try {
      setStatus(await api.post<UpdateStatus>("/update/check", {}));
    } catch (e) {
      setError(String(e));
    } finally {
      setChecking(false);
    }
  };

  const update = async () => {
    setUpdating(true);
    setError(null);
    setResult(null);
    try {
      const res = await api.post<ApplyResult>("/update/apply", {});
      setResult(res);
      if (res.ok) setStatus(await api.get<UpdateStatus>("/update/status"));
    } catch (e) {
      setError(String(e));
    } finally {
      setUpdating(false);
    }
  };

  return (
    <section className="border border-gray-200 rounded-lg p-4 mb-8">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wide">
          Updates
        </h2>
        <div className="flex items-center gap-2">
          <button
            onClick={check}
            disabled={checking || updating}
            className="px-3 py-1.5 rounded border border-gray-300 text-sm font-medium
              text-gray-700 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {checking ? "Checking…" : "Check for updates"}
          </button>
          {status?.can_update && (
            <button
              onClick={update}
              disabled={updating || checking}
              className="px-3 py-1.5 rounded bg-blue-600 text-white text-sm font-medium
                hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {updating ? "Updating…" : `Update to ${status.latest_version}`}
            </button>
          )}
        </div>
      </div>

      {!status && !error && <p className="text-sm text-gray-400">Loading…</p>}
      {error && <p className="text-sm text-red-600 mb-2">{error}</p>}

      {status && (
        <>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm max-w-lg">
            <dt className="text-gray-500">Current version</dt>
            <dd className="text-gray-900 font-mono">
              {status.current_version}
              <span className="text-gray-400 font-sans">
                {" "}
                (released {fmtDate(status.current_release_date)})
              </span>
            </dd>

            <dt className="text-gray-500">Latest version</dt>
            <dd className="text-gray-900 font-mono">
              {status.latest_version ?? "—"}
              {status.latest_version && (
                <span className="text-gray-400 font-sans">
                  {" "}
                  (released {fmtDate(status.latest_release_date)})
                </span>
              )}
            </dd>

            <dt className="text-gray-500">Last checked</dt>
            <dd className="text-gray-900">{fmtDateTime(status.last_checked)}</dd>
          </dl>

          <div className="mt-3 text-sm">
            {status.check_error ? (
              <p className="text-yellow-700">
                Last check failed: {status.check_error}
              </p>
            ) : status.update_available ? (
              status.can_update ? (
                <p className="text-blue-700">
                  An update is available.
                </p>
              ) : (
                <p className="text-gray-500">
                  Version {status.latest_version} is available. This is a source
                  checkout — update with <code>git pull</code> rather than the
                  in-app installer.
                </p>
              )
            ) : (
              <p className="text-green-700">You&apos;re on the latest version.</p>
            )}
          </div>

          {result && (
            <div
              className={`mt-3 text-sm rounded border p-2 ${
                result.ok
                  ? "bg-green-50 border-green-200 text-green-800"
                  : "bg-red-50 border-red-200 text-red-800"
              }`}
            >
              <p className="font-medium">{result.message}</p>
              {result.command && (
                <p className="text-xs font-mono mt-1 opacity-70">{result.command}</p>
              )}
              {(result.stderr || result.stdout) && (
                <pre className="text-xs mt-2 whitespace-pre-wrap max-h-40 overflow-y-auto">
                  {result.stderr || result.stdout}
                </pre>
              )}
            </div>
          )}
        </>
      )}
    </section>
  );
}
