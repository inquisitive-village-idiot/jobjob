import { useEffect, useState } from "react";
import { api } from "../api/client";
import type {
  ConfigSchema,
  ProfileEntry,
  ProfileResources,
  ProfilesInfo,
} from "../types";
import {
  SectionHeader,
  scrollToSection,
  useScrollSpy,
} from "../components/PageOutline";
import type { OutlineItem } from "../components/PageOutline";
import UpdatePanel from "./UpdatePanel";
import ProfilesPanel from "./ProfilesPanel";

const slug = (group: string) => group.toLowerCase().replace(/\s+/g, "-");

const APP_HINT = "This jobjob instance — machine-local (config/.env), never committed.";
const PROFILE_HINT =
  "This profile — committed to its resources repo (config/.profile).";
const READ_ONLY_HINT =
  "This is the bundled example profile and is read-only — duplicate it to make an editable copy.";

// Read-only display of a profile's on-disk location and the file counts of its
// resource directories (content/reference/prompt). The dir names themselves are
// edited via the "Directories" config fields (under the whole-profile Edit toggle).
function ProfileResourcesPanel({ name }: { name: string }) {
  const [data, setData] = useState<ProfileResources | null>(null);

  useEffect(() => {
    setData(null);
    api
      .get<ProfileResources>(`/profiles/${encodeURIComponent(name)}/resources`)
      .then(setData)
      .catch(() => setData(null));
  }, [name]);

  if (!data) return null;
  return (
    <div className="mb-6 border border-gray-200 rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-900 mb-1">
        Location &amp; directories
      </h3>
      <p className="text-xs text-gray-500 mb-3 break-all font-mono">{data.location}</p>
      <div className="flex flex-wrap gap-2">
        {data.resources.map((r) => (
          <span
            key={r.name}
            title={r.path}
            className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs
              border ${
                r.exists
                  ? "bg-gray-50 text-gray-700 border-gray-200"
                  : "bg-yellow-50 text-yellow-700 border-yellow-200"
              }`}
          >
            <span className="font-medium">{r.dir}</span>
            {r.exists ? (
              <span className="text-gray-400">{r.count}</span>
            ) : (
              <span className="text-yellow-600">missing</span>
            )}
          </span>
        ))}
      </div>
    </div>
  );
}

// App config first, then profiles with the active one first, the rest alphabetical.
function orderedProfiles(profiles: ProfileEntry[]): ProfileEntry[] {
  return [...profiles].sort((a, b) => {
    if (a.active !== b.active) return a.active ? -1 : 1;
    return a.name.localeCompare(b.name);
  });
}

export default function ConfigPage() {
  // The active tab is "app" or a profile name.
  const [tab, setTab] = useState<string>("app");
  const [profiles, setProfiles] = useState<ProfileEntry[]>([]);
  const [schema, setSchema] = useState<ConfigSchema | null>(null);
  const [edits, setEdits] = useState<Record<string, string>>({});
  // Profiles open in view mode; one whole-profile toggle unlocks the fields.
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  // Load the profile list once to build the tab set (App + each profile).
  useEffect(() => {
    api
      .get<ProfilesInfo>("/profiles")
      .then((info) => {
        setProfiles(
          info.entries ??
            info.profiles.map((n) => ({
              name: n,
              active: n === info.active,
              read_only: false,
              external: false,
            }))
        );
      })
      .catch(() => setProfiles([]));
  }, []);

  const isProfile = tab !== "app";
  const current = profiles.find((p) => p.name === tab) ?? null;
  const readOnly = isProfile && !!current?.read_only;
  const fieldsDisabled = isProfile && (readOnly || !editing);

  useEffect(() => {
    setSchema(null);
    setEdits({});
    setEditing(false);
    setSaved(false);
    setError(null);
    const query =
      tab === "app" ? "scope=app" : `scope=profile&name=${encodeURIComponent(tab)}`;
    api
      .get<ConfigSchema>(`/config?${query}`)
      .then(setSchema)
      .catch((e) => setError(String(e)));
  }, [tab]);

  const groups = schema
    ? Array.from(new Set(Object.values(schema).map((f) => f.group)))
    : [];
  const outline: OutlineItem[] = groups.map((g) => ({
    id: `config-${slug(g)}`,
    label: g,
  }));
  const activeId = useScrollSpy(
    outline.map((o) => o.id),
    [schema]
  );

  // Indented scroll-spy anchors for the active tab's subsections (config-schema groups).
  const subAnchors = (
    <ul className="mt-0.5 mb-1 space-y-0.5">
      {outline.map((it) => (
        <li key={it.id}>
          <button
            onClick={() => scrollToSection(it.id)}
            title={it.label}
            className={`block w-full text-left pl-5 pr-2 py-1 text-sm rounded border-l-2
              transition-colors truncate ${
                activeId === it.id
                  ? "border-blue-600 text-blue-600 font-medium bg-blue-50"
                  : "border-transparent text-gray-500 hover:text-gray-800 hover:bg-gray-50"
              }`}
          >
            {it.label}
          </button>
        </li>
      ))}
    </ul>
  );

  const tabClass = (active: boolean) =>
    `block w-full text-left px-3 py-1.5 text-sm rounded font-medium transition-colors ${
      active ? "bg-blue-600 text-white" : "text-gray-700 hover:bg-gray-100"
    }`;

  // Left sidebar: the config tabs (App, then profiles active-first); the active tab
  // expands to its subsections as scroll-spy anchors.
  const sidebar = (
    <nav className="w-52 shrink-0" aria-label="Configuration sections">
      <ul className="sticky top-16 space-y-0.5 max-h-[85vh] overflow-y-auto pr-1">
        <li>
          <button onClick={() => setTab("app")} className={tabClass(tab === "app")}>
            App
          </button>
          {tab === "app" && subAnchors}
        </li>
        {orderedProfiles(profiles).map((p) => (
          <li key={p.name}>
            <button
              onClick={() => setTab(p.name)}
              className={`capitalize ${tabClass(tab === p.name)}`}
            >
              {p.active ? `${p.name} (active)` : p.name}
            </button>
            {tab === p.name && subAnchors}
          </li>
        ))}
      </ul>
    </nav>
  );

  const hint = !isProfile
    ? APP_HINT
    : readOnly
      ? `${PROFILE_HINT} ${READ_ONLY_HINT}`
      : PROFILE_HINT;

  if (!schema) {
    return (
      <div className="max-w-6xl mx-auto p-6">
        <div className="flex gap-6">
          {sidebar}
          <div className="flex-1 min-w-0 text-gray-500">
            {error ? <span className="text-red-600">{error}</span> : "Loading…"}
          </div>
        </div>
      </div>
    );
  }

  const handleChange = (key: string, value: string) => {
    setEdits((prev) => ({ ...prev, [key]: value }));
    setSaved(false);
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const query =
        tab === "app" ? "scope=app" : `scope=profile&name=${encodeURIComponent(tab)}`;
      const updated = await api.put<ConfigSchema>(`/config?${query}`, {
        updates: edits,
      });
      setSchema(updated);
      setEdits({});
      setSaved(true);
      if (isProfile) setEditing(false);
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  const cancelEdit = () => {
    setEdits({});
    setEditing(false);
    setSaved(false);
    setError(null);
  };

  const hasEdits = Object.keys(edits).length > 0;

  const saveButton = (
    <button
      onClick={handleSave}
      disabled={!hasEdits || saving}
      className="px-4 py-1.5 rounded bg-blue-600 text-white text-sm font-medium
        hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed"
    >
      {saving ? "Saving…" : "Save changes"}
    </button>
  );

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Configuration</h1>
        </div>
        <div className="flex items-center gap-3">
          {saved && <span className="text-sm text-green-600">Saved</span>}
          {error && <span className="text-sm text-red-600">{error}</span>}
          {!isProfile && saveButton}
          {isProfile && !editing && (
            <button
              onClick={() => setEditing(true)}
              disabled={readOnly}
              title={readOnly ? READ_ONLY_HINT : undefined}
              className="px-4 py-1.5 rounded border border-gray-300 text-sm font-medium
                text-gray-700 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Edit
            </button>
          )}
          {isProfile && editing && (
            <>
              {saveButton}
              <button
                onClick={cancelEdit}
                disabled={saving}
                className="px-3 py-1.5 rounded text-sm text-gray-600 hover:bg-gray-100
                  disabled:opacity-40"
              >
                Cancel
              </button>
            </>
          )}
        </div>
      </div>

      <UpdatePanel />
      <ProfilesPanel />

      <div className="flex gap-6">
        {sidebar}
        <div className="flex-1 min-w-0">
          <p className="text-xs text-gray-500 mb-6">{hint}</p>
          {isProfile && <ProfileResourcesPanel name={tab} />}
          <div className="space-y-10">
            {groups.map((group) => (
              <section
                key={group}
                id={`config-${slug(group)}`}
                className="scroll-mt-16"
              >
                <SectionHeader>{group}</SectionHeader>
                <div className="space-y-4">
                  {Object.entries(schema)
                    .filter(([, f]) => f.group === group)
                    .map(([key, field]) => (
                      <div key={key}>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          {field.label}
                          {field.required && (
                            <span className="ml-1 text-red-500">*</span>
                          )}
                        </label>
                        {field.description && (
                          <p className="text-xs text-gray-500 mb-1">
                            {field.description}
                          </p>
                        )}
                        {field.is_secret ? (
                          <div className="flex items-center gap-2">
                            <span
                              className={`inline-flex items-center px-2.5 py-1 rounded text-xs font-medium ${
                                field.is_set
                                  ? "bg-green-100 text-green-800"
                                  : "bg-yellow-100 text-yellow-800"
                              }`}
                            >
                              {field.is_set ? "Set" : "Not set"}
                            </span>
                            <span className="text-xs text-gray-400 italic">
                              Secrets can only be set by editing config/.env directly.
                            </span>
                          </div>
                        ) : field.options ? (
                          <select
                            value={edits[key] ?? field.value ?? ""}
                            onChange={(e) => handleChange(key, e.target.value)}
                            disabled={fieldsDisabled}
                            className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded
                            focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono bg-white
                            disabled:bg-gray-100 disabled:text-gray-500 disabled:cursor-not-allowed"
                          >
                            {!field.required && <option value="">Default</option>}
                            {field.options.map((opt) => (
                              <option key={opt} value={opt}>
                                {opt}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <input
                            type="text"
                            value={edits[key] ?? field.value ?? ""}
                            onChange={(e) => handleChange(key, e.target.value)}
                            disabled={fieldsDisabled}
                            className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded
                            focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono
                            disabled:bg-gray-100 disabled:text-gray-500 disabled:cursor-not-allowed"
                            placeholder={field.required ? "Required" : ""}
                          />
                        )}
                      </div>
                    ))}
                </div>
              </section>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
