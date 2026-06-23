import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { ProfilesInfo, ProfileEntry } from "../types";

type Action = "none" | "create" | "duplicate" | "register";

/**
 * Profiles management: list profiles, switch the active one, and create / duplicate /
 * register / delete profiles. The bundled `example` (Tila Mer) is read-only — it can
 * be duplicated but never edited or deleted. Mounted on the Config page.
 */
export default function ProfilesPanel() {
  const [info, setInfo] = useState<ProfilesInfo | null>(null);
  const [action, setAction] = useState<Action>("none");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form fields.
  const [name, setName] = useState("");
  const [source, setSource] = useState("example");
  const [location, setLocation] = useState("");

  const load = () =>
    api
      .get<ProfilesInfo>("/profiles")
      .then(setInfo)
      .catch((e) => setError(String(e)));

  useEffect(() => {
    load();
  }, []);

  const entries: ProfileEntry[] =
    info?.entries ??
    (info?.profiles ?? []).map((n) => ({
      name: n,
      active: n === info?.active,
      read_only: false,
      external: false,
    }));

  const reset = () => {
    setAction("none");
    setName("");
    setSource("example");
    setLocation("");
    setError(null);
  };

  const run = async (fn: () => Promise<ProfilesInfo>) => {
    setBusy(true);
    setError(null);
    try {
      setInfo(await fn());
      reset();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const switchTo = (n: string) =>
    run(async () => {
      const next = await api.put<ProfilesInfo>("/profiles/active", { name: n });
      // Content, applicant identity, and template change across the app — reload.
      window.location.reload();
      return next;
    });

  const create = () => run(() => api.post<ProfilesInfo>("/profiles", { name }));
  const duplicate = () =>
    run(() => api.post<ProfilesInfo>("/profiles/duplicate", { source, name }));
  const register = () =>
    run(() => api.post<ProfilesInfo>("/profiles/register", { name, location }));
  const remove = (n: string) => {
    if (!window.confirm(`Delete profile "${n}"? This cannot be undone.`)) return;
    run(() => api.del<ProfilesInfo>(`/profiles/${n}`));
  };

  return (
    <div className="mb-6 border border-gray-200 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-900">Profiles</h2>
        <div className="flex gap-1.5">
          <ActionButton on={() => setAction("create")} active={action === "create"}>
            New
          </ActionButton>
          <ActionButton
            on={() => setAction("duplicate")}
            active={action === "duplicate"}
          >
            Duplicate
          </ActionButton>
          <ActionButton on={() => setAction("register")} active={action === "register"}>
            Register folder
          </ActionButton>
        </div>
      </div>

      <p className="text-xs text-gray-500 mb-3">
        Each profile holds its own content, reference docs, and applicant identity. The{" "}
        <span className="font-medium">example</span> profile is read-only — duplicate it
        to make an editable copy.
      </p>

      <ul className="divide-y divide-gray-100">
        {entries.map((e) => (
          <li key={e.name} className="flex items-center justify-between py-2">
            <div className="flex items-center gap-2">
              <button
                onClick={() => switchTo(e.name)}
                disabled={busy || e.active}
                title={e.active ? "Already active" : `Switch to ${e.name}`}
                className="text-xs px-2 py-1 rounded text-blue-700 hover:bg-blue-50
                  disabled:text-gray-400 disabled:hover:bg-transparent disabled:cursor-default"
              >
                Switch
              </button>
              <span className="text-sm font-medium capitalize text-gray-800">
                {e.name}
              </span>
              {e.active && <Badge tone="blue">Active</Badge>}
              {e.read_only && <Badge tone="gray">Example</Badge>}
              {e.read_only && <Badge tone="gray">read-only</Badge>}
              {e.external && <Badge tone="amber">External</Badge>}
            </div>
            <div className="flex items-center gap-1.5">
              {!e.active && !e.read_only && (
                <button
                  onClick={() => remove(e.name)}
                  disabled={busy}
                  className="text-xs px-2 py-1 rounded text-red-600 hover:bg-red-50 disabled:opacity-40"
                >
                  Delete
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>

      {action !== "none" && (
        <div className="mt-3 p-3 bg-gray-50 rounded border border-gray-200 space-y-2">
          {action === "duplicate" && (
            <Field label="Copy from">
              <select
                value={source}
                onChange={(ev) => setSource(ev.target.value)}
                className="w-full px-2 py-1 text-sm border border-gray-300 rounded bg-white"
              >
                {entries.map((e) => (
                  <option key={e.name} value={e.name}>
                    {e.name}
                  </option>
                ))}
              </select>
            </Field>
          )}
          <Field label="New profile name">
            <input
              value={name}
              onChange={(ev) => setName(ev.target.value)}
              placeholder="e.g. my_profile (lowercase, letters/digits/underscores)"
              className="w-full px-2 py-1 text-sm border border-gray-300 rounded font-mono"
            />
          </Field>
          {action === "register" && (
            <Field label="Existing folder path">
              <input
                value={location}
                onChange={(ev) => setLocation(ev.target.value)}
                placeholder="/path/to/your/profile"
                className="w-full px-2 py-1 text-sm border border-gray-300 rounded font-mono"
              />
            </Field>
          )}
          <div className="flex items-center gap-2 pt-1">
            <button
              onClick={
                action === "create"
                  ? create
                  : action === "duplicate"
                    ? duplicate
                    : register
              }
              disabled={busy || !name || (action === "register" && !location)}
              className="px-3 py-1 rounded bg-blue-600 text-white text-xs font-medium
                hover:bg-blue-700 disabled:opacity-40"
            >
              {busy
                ? "Working…"
                : action === "create"
                  ? "Create"
                  : action === "duplicate"
                    ? "Duplicate"
                    : "Register"}
            </button>
            <button
              onClick={reset}
              disabled={busy}
              className="px-3 py-1 rounded text-xs text-gray-600 hover:bg-gray-100"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
    </div>
  );
}

function ActionButton({
  on,
  active,
  children,
}: {
  on: () => void;
  active: boolean;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={on}
      className={`text-xs px-2 py-1 rounded font-medium ${
        active ? "bg-blue-600 text-white" : "text-gray-600 hover:bg-gray-100"
      }`}
    >
      {children}
    </button>
  );
}

function Badge({
  tone,
  children,
}: {
  tone: "blue" | "gray" | "amber";
  children: React.ReactNode;
}) {
  const tones = {
    blue: "bg-blue-100 text-blue-800",
    gray: "bg-gray-100 text-gray-600",
    amber: "bg-amber-100 text-amber-800",
  };
  return (
    <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${tones[tone]}`}>
      {children}
    </span>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      {children}
    </div>
  );
}
