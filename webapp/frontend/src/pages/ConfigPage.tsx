import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { ConfigSchema, ConfigScope } from "../types";
import { FloatingOutline, SectionHeader, useScrollSpy } from "../components/PageOutline";
import type { OutlineItem } from "../components/PageOutline";
import UpdatePanel from "./UpdatePanel";
import ProfilesPanel from "./ProfilesPanel";

const slug = (group: string) => group.toLowerCase().replace(/\s+/g, "-");

const SCOPES: { id: ConfigScope; label: string; hint: string }[] = [
  { id: "app", label: "App", hint: "This jobjob instance — machine-local (config/.env), never committed." },
  { id: "profile", label: "Profile", hint: "The active profile — committed to its resources repo (config/.profile)." },
];

export default function ConfigPage() {
  const [scope, setScope] = useState<ConfigScope>("app");
  const [schema, setSchema] = useState<ConfigSchema | null>(null);
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setSchema(null);
    setEdits({});
    setSaved(false);
    setError(null);
    api
      .get<ConfigSchema>(`/config?scope=${scope}`)
      .then(setSchema)
      .catch((e) => setError(String(e)));
  }, [scope]);

  const groups = schema
    ? Array.from(new Set(Object.values(schema).map((f) => f.group)))
    : [];
  const outline: OutlineItem[] = groups.map((g) => ({
    id: `config-${slug(g)}`,
    label: g,
  }));
  const activeId = useScrollSpy(outline.map((o) => o.id), [schema]);

  const scopeTabs = (
    <div className="flex gap-1 mb-1">
      {SCOPES.map((s) => (
        <button
          key={s.id}
          onClick={() => setScope(s.id)}
          className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
            scope === s.id ? "bg-blue-600 text-white" : "text-gray-600 hover:bg-gray-100"
          }`}
        >
          {s.label}
        </button>
      ))}
    </div>
  );

  if (!schema) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        {scopeTabs}
        <div className="text-gray-500 mt-4">
          {error ? <span className="text-red-600">{error}</span> : "Loading…"}
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
      const updated = await api.put<ConfigSchema>(`/config?scope=${scope}`, {
        updates: edits,
      });
      setSchema(updated);
      setEdits({});
      setSaved(true);
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  const hasEdits = Object.keys(edits).length > 0;

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Configuration</h1>
        </div>
        <div className="flex items-center gap-3">
          {saved && <span className="text-sm text-green-600">Saved</span>}
          {error && <span className="text-sm text-red-600">{error}</span>}
          <button
            onClick={handleSave}
            disabled={!hasEdits || saving}
            className="px-4 py-1.5 rounded bg-blue-600 text-white text-sm font-medium
              hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {saving ? "Saving…" : "Save changes"}
          </button>
        </div>
      </div>

      <UpdatePanel />
      <ProfilesPanel />

      {scopeTabs}
      <p className="text-xs text-gray-500 mb-6">
        {SCOPES.find((s) => s.id === scope)?.hint}
      </p>

      <div className="relative">
        <FloatingOutline items={outline} activeId={activeId} />
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
                        {field.required && <span className="ml-1 text-red-500">*</span>}
                      </label>
                      {field.description && (
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
                      ) : field.options ? (
                        <select
                          value={edits[key] ?? field.value ?? ""}
                          onChange={(e) => handleChange(key, e.target.value)}
                          className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded
                            focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono bg-white"
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
                          className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded
                            focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
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
  );
}
