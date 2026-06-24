import { useEffect, useState } from "react";
import { api } from "../api/client";
import type {
  ConfigField,
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

const slug = (group: string) => group.toLowerCase().replace(/\s+/g, "-");

// Optional fields often document a conventional default ("… Default: content.").
// Surface it as the input placeholder so an unset field reads as its default value
// rather than looking empty/unpopulated.
function placeholderFor(field: ConfigField): string {
  if (field.required) return "Required";
  const m = field.description?.match(/Default:\s*([^.]+)\./i);
  return m ? m[1].trim() : "";
}

const ISSUES_URL = "https://github.com/inquisitive-village-idiot/jobjob/issues";

const APP_HINT = "This jobjob instance — machine-local (config/.env), never committed.";
const PROFILE_HINT =
  "This profile — committed to its resources repo (config/.profile).";
const READ_ONLY_HINT =
  "This is the bundled example profile and is read-only — duplicate it to make an editable copy.";

// Left-nav sections. Profiles are body tabs (not nav items); the "＋" tab adds one.
type Section = "app" | "profiles" | "about";
const ADD_TAB = "__add__";

function entriesOf(info: ProfilesInfo): ProfileEntry[] {
  return (
    info.entries ??
    info.profiles.map((n) => ({
      name: n,
      active: n === info.active,
      read_only: false,
      external: false,
    }))
  );
}

// Tab order: the active profile first, the read-only bundled example last, and every
// other profile alphabetical in between. (Active wins if the example itself is active.)
function orderedProfiles(profiles: ProfileEntry[]): ProfileEntry[] {
  return [...profiles].sort((a, b) => {
    if (a.active !== b.active) return a.active ? -1 : 1;
    if (a.read_only !== b.read_only) return a.read_only ? 1 : -1;
    return a.name.localeCompare(b.name);
  });
}

// Read-only display of a profile's on-disk location and the file counts of its
// resource directories (content/reference/prompt). It surfaces whether jobjob
// actually sees content for a profile (e.g. "content 0" when a registered folder
// is empty), independent of whether the profile is active.
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

export default function ConfigPage() {
  const [section, setSection] = useState<Section>("app");
  const [profiles, setProfiles] = useState<ProfileEntry[]>([]);
  // Selected profile tab within the Profiles section (a name, or the "＋" add tab).
  const [profileTab, setProfileTab] = useState<string>(ADD_TAB);

  const [schema, setSchema] = useState<ConfigSchema | null>(null);
  const [edits, setEdits] = useState<Record<string, string>>({});
  // Profiles open in view mode; one whole-profile toggle unlocks the fields.
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const loadProfiles = () =>
    api.get<ProfilesInfo>("/profiles").then((info) => {
      const entries = entriesOf(info);
      setProfiles(entries);
      return entries;
    });

  // Load the profile list once; default the Profiles tab to the active profile so a
  // selection is ready before the user opens the section.
  useEffect(() => {
    loadProfiles()
      .then((entries) => {
        const first = entries.find((e) => e.active) ?? entries[0];
        if (first) setProfileTab(first.name);
      })
      .catch(() => setProfiles([]));
  }, []);

  const isProfileConfig = section === "profiles" && profileTab !== ADD_TAB;
  const configActive = section === "app" || isProfileConfig;
  const configQuery =
    section === "app"
      ? "scope=app"
      : `scope=profile&name=${encodeURIComponent(profileTab)}`;

  // Fetch the config schema for whichever target is selected (app, or a profile).
  useEffect(() => {
    if (!configActive) {
      setSchema(null);
      return;
    }
    setSchema(null);
    setEdits({});
    setEditing(false);
    setSaved(false);
    setError(null);
    api
      .get<ConfigSchema>(`/config?${configQuery}`)
      .then(setSchema)
      .catch((e) => setError(String(e)));
    // configActive/configQuery derive from section + profileTab.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [section, profileTab]);

  const current = profiles.find((p) => p.name === profileTab) ?? null;
  const readOnly = isProfileConfig && !!current?.read_only;
  const fieldsDisabled = isProfileConfig && (readOnly || !editing);

  const groups = schema
    ? Array.from(new Set(Object.values(schema).map((f) => f.group)))
    : [];
  // The editable "Directories" overrides duplicate the read-only Location panel, so
  // show them only while editing a profile (the Location panel is hidden then).
  const visibleGroups =
    isProfileConfig && !editing ? groups.filter((g) => g !== "Directories") : groups;
  const outline: OutlineItem[] = groups.map((g) => ({
    id: `config-${slug(g)}`,
    label: g,
  }));
  const activeId = useScrollSpy(
    outline.map((o) => o.id),
    [schema]
  );

  const handleChange = (key: string, value: string) => {
    setEdits((prev) => ({ ...prev, [key]: value }));
    setSaved(false);
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const updated = await api.put<ConfigSchema>(`/config?${configQuery}`, {
        updates: edits,
      });
      setSchema(updated);
      setEdits({});
      setSaved(true);
      if (isProfileConfig) setEditing(false);
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

  const switchTo = async (name: string) => {
    try {
      await api.put<ProfilesInfo>("/profiles/active", { name });
      // Content, applicant identity, and template change across the app — reload.
      window.location.reload();
    } catch (e) {
      setError(String(e));
    }
  };

  const remove = async (name: string) => {
    if (!window.confirm(`Delete profile "${name}"? This cannot be undone.`)) return;
    try {
      const entries = entriesOf(await api.del<ProfilesInfo>(`/profiles/${name}`));
      setProfiles(entries);
      const first = entries.find((e) => e.active) ?? entries[0];
      setProfileTab(first ? first.name : ADD_TAB);
    } catch (e) {
      setError(String(e));
    }
  };

  // A newly created/duplicated/registered profile: refresh the tab list and select
  // it so its config + content load immediately (no activation required).
  const handleAdded = (info: ProfilesInfo, name: string) => {
    setProfiles(entriesOf(info));
    setProfileTab(name);
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

  const statusBadges = (
    <>
      {saved && <span className="text-sm text-green-600">Saved</span>}
      {error && <span className="text-sm text-red-600">{error}</span>}
    </>
  );

  // Indented scroll-spy anchors for the App config's subsections (schema groups).
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

  const navClass = (active: boolean) =>
    `block w-full text-left px-3 py-1.5 text-sm rounded font-medium transition-colors ${
      active ? "bg-blue-600 text-white" : "text-gray-700 hover:bg-gray-100"
    }`;

  const sidebar = (
    <nav className="w-52 shrink-0" aria-label="Configuration sections">
      <ul className="sticky top-16 space-y-0.5 max-h-[85vh] overflow-y-auto pr-1">
        <li>
          <button
            onClick={() => setSection("app")}
            className={navClass(section === "app")}
          >
            App
          </button>
          {section === "app" && subAnchors}
        </li>
        <li>
          <button
            onClick={() => setSection("profiles")}
            className={navClass(section === "profiles")}
          >
            Profiles
          </button>
        </li>
        <li>
          <button
            onClick={() => setSection("about")}
            className={navClass(section === "about")}
          >
            About
          </button>
        </li>
      </ul>
    </nav>
  );

  // Profiles open read-only (a clean summary); the editable inputs appear on Edit.
  const profileViewMode = isProfileConfig && !editing;

  // The config form (schema-driven groups + fields), shared by App and Profile. In a
  // profile's read-only view it renders values as plain text instead of inputs.
  const configForm = schema ? (
    <div className="space-y-10">
      {visibleGroups.map((group) => (
        <section key={group} id={`config-${slug(group)}`} className="scroll-mt-16">
          <SectionHeader>{group}</SectionHeader>
          <div className="space-y-4">
            {Object.entries(schema)
              .filter(([, f]) => f.group === group)
              .map(([key, field]) => (
                <div key={key}>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {field.label}
                    {field.required && <span className="ml-1 text-red-500">*</span>}
                  </label>
                  {field.description && !profileViewMode && (
                    <p className="text-xs text-gray-500 mb-1">{field.description}</p>
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
                  ) : profileViewMode ? (
                    <ReadOnlyValue field={field} />
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
                      placeholder={placeholderFor(field)}
                    />
                  )}
                </div>
              ))}
          </div>
        </section>
      ))}
    </div>
  ) : (
    <div className="text-gray-500">
      {error ? <span className="text-red-600">{error}</span> : "Loading…"}
    </div>
  );

  const appSection = (
    <>
      <div className="flex items-center justify-between mb-6">
        <p className="text-xs text-gray-500">{APP_HINT}</p>
        <div className="flex items-center gap-3">
          {statusBadges}
          {saveButton}
        </div>
      </div>
      {configForm}
    </>
  );

  const profileHint = readOnly ? `${PROFILE_HINT} ${READ_ONLY_HINT}` : PROFILE_HINT;

  const profileTabClass = (active: boolean) =>
    `whitespace-nowrap px-3 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
      active
        ? "border-blue-600 text-blue-600"
        : "border-transparent text-gray-600 hover:text-gray-800"
    }`;

  const profilesSection = (
    <>
      <div
        className="flex items-center gap-1 border-b border-gray-200 mb-5 overflow-x-auto"
        role="tablist"
        aria-label="Profiles"
      >
        {orderedProfiles(profiles).map((p) => (
          <button
            key={p.name}
            role="tab"
            aria-selected={profileTab === p.name}
            onClick={() => setProfileTab(p.name)}
            className={`capitalize ${profileTabClass(profileTab === p.name)}`}
          >
            {p.active ? `${p.name} (active)` : p.name}
          </button>
        ))}
        <button
          role="tab"
          aria-selected={profileTab === ADD_TAB}
          aria-label="Add a profile"
          title="Add a profile"
          onClick={() => setProfileTab(ADD_TAB)}
          className={profileTabClass(profileTab === ADD_TAB)}
        >
          ＋
        </button>
      </div>

      {profileTab === ADD_TAB ? (
        <AddProfileForm
          entries={profiles}
          onAdded={handleAdded}
          onCancel={() => {
            const first = profiles.find((e) => e.active) ?? profiles[0];
            if (first) setProfileTab(first.name);
          }}
        />
      ) : (
        <>
          <div className="flex items-center justify-between mb-4 gap-3">
            <p className="text-xs text-gray-500 min-w-0">{profileHint}</p>
            <div className="flex items-center gap-2 shrink-0">
              {statusBadges}
              {!current?.active && (
                <button
                  onClick={() => switchTo(profileTab)}
                  className="px-3 py-1.5 rounded text-sm font-medium text-blue-700
                    border border-blue-200 hover:bg-blue-50"
                >
                  Switch to active
                </button>
              )}
              {!editing ? (
                <button
                  onClick={() => setEditing(true)}
                  disabled={readOnly}
                  title={readOnly ? READ_ONLY_HINT : undefined}
                  className="px-4 py-1.5 rounded border border-gray-300 text-sm font-medium
                    text-gray-700 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Edit
                </button>
              ) : (
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
              {!current?.active && !readOnly && (
                <button
                  onClick={() => remove(profileTab)}
                  className="px-3 py-1.5 rounded text-sm text-red-600 hover:bg-red-50"
                >
                  Delete
                </button>
              )}
            </div>
          </div>
          {!editing && <ProfileResourcesPanel name={profileTab} />}
          {configForm}
        </>
      )}
    </>
  );

  const aboutSection = (
    <>
      <UpdatePanel />
      <section className="border border-gray-200 rounded-lg p-4">
        <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wide mb-2">
          About
        </h2>
        <p className="text-sm text-gray-600">
          jobjob runs entirely on your machine. Found a bug or have an idea?{" "}
          <a
            href={ISSUES_URL}
            target="_blank"
            rel="noreferrer"
            className="text-blue-600 hover:underline"
          >
            Report an issue
          </a>
          .
        </p>
      </section>
    </>
  );

  return (
    <div className="max-w-6xl mx-auto p-6">
      <h1 className="text-xl font-semibold text-gray-900 mb-4">Configuration</h1>
      <div className="flex gap-6">
        {sidebar}
        <div className="flex-1 min-w-0">
          {section === "app" && appSection}
          {section === "profiles" && profilesSection}
          {section === "about" && aboutSection}
        </div>
      </div>
    </div>
  );
}

// Inline add-profile form (create / duplicate / register an existing folder).
function AddProfileForm({
  entries,
  onAdded,
  onCancel,
}: {
  entries: ProfileEntry[];
  onAdded: (info: ProfilesInfo, name: string) => void;
  onCancel: () => void;
}) {
  type Action = "create" | "duplicate" | "register";
  const [action, setAction] = useState<Action>("create");
  const [name, setName] = useState("");
  const [source, setSource] = useState(entries[0]?.name ?? "example");
  const [location, setLocation] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      const info =
        action === "create"
          ? await api.post<ProfilesInfo>("/profiles", { name })
          : action === "duplicate"
            ? await api.post<ProfilesInfo>("/profiles/duplicate", { source, name })
            : await api.post<ProfilesInfo>("/profiles/register", { name, location });
      onAdded(info, name);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const tab = (a: Action, label: string) => (
    <button
      onClick={() => setAction(a)}
      className={`text-xs px-2.5 py-1 rounded font-medium ${
        action === a ? "bg-blue-600 text-white" : "text-gray-600 hover:bg-gray-100"
      }`}
    >
      {label}
    </button>
  );

  return (
    <div className="max-w-lg border border-gray-200 rounded-lg p-4">
      <div className="flex items-center gap-1.5 mb-3">
        {tab("create", "New (blank)")}
        {tab("duplicate", "Duplicate")}
        {tab("register", "Register folder")}
      </div>

      <p className="text-xs text-gray-500 mb-3">
        {action === "create"
          ? "Create an empty profile from the skeleton."
          : action === "duplicate"
            ? "Copy an existing profile's content into a new editable profile."
            : "Point jobjob at an existing profile folder on disk (e.g. a cloned resources repo). Its content loads immediately — you don't have to make it active."}
      </p>

      <div className="space-y-2">
        {action === "duplicate" && (
          <Field label="Copy from">
            <select
              value={source}
              onChange={(e) => setSource(e.target.value)}
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
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. my_profile (lowercase, letters/digits/underscores)"
            className="w-full px-2 py-1 text-sm border border-gray-300 rounded font-mono"
          />
        </Field>
        {action === "register" && (
          <Field label="Existing folder path">
            <input
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="/path/to/your/profile"
              className="w-full px-2 py-1 text-sm border border-gray-300 rounded font-mono"
            />
          </Field>
        )}
        <div className="flex items-center gap-2 pt-1">
          <button
            onClick={submit}
            disabled={busy || !name || (action === "register" && !location)}
            className="px-3 py-1.5 rounded bg-blue-600 text-white text-sm font-medium
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
            onClick={onCancel}
            disabled={busy}
            className="px-3 py-1.5 rounded text-sm text-gray-600 hover:bg-gray-100"
          >
            Cancel
          </button>
        </div>
      </div>

      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
    </div>
  );
}

// Read-only display of a config field's value: the set value, else the documented
// default shown muted as "<default> (default)", else "Not set".
function ReadOnlyValue({ field }: { field: ConfigField }) {
  if (field.value) {
    return <span className="text-sm font-mono text-gray-900">{field.value}</span>;
  }
  const fallback = placeholderFor(field);
  if (fallback && fallback !== "Required") {
    return (
      <span className="text-sm font-mono text-gray-400">{fallback} (default)</span>
    );
  }
  return <span className="text-sm text-gray-400 italic">Not set</span>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      {children}
    </div>
  );
}
