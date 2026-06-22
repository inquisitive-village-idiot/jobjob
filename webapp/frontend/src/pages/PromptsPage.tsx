import { useEffect, useState } from "react";
import { api } from "../api/client";

// One editable prompt template, as returned by GET /api/prompts.
interface PromptView {
  stem: string;
  title: string;
  kind: "generation" | "extraction";
  description: string;
  placeholders: string[];
  content: string;
  default: string;
  overridden: boolean;
  editable: boolean;
}

const KIND_LABEL: Record<PromptView["kind"], string> = {
  generation: "Generation",
  extraction: "Extraction",
};

// Placeholder chips — the ${name} variables the template can reference.
function Placeholders({ names }: { names: string[] }) {
  if (names.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1">
      {names.map((n) => (
        <code
          key={n}
          className="inline-flex items-center px-1.5 py-0.5 rounded text-xs
            bg-indigo-50 text-indigo-700 border border-indigo-200 font-mono"
          title={`Insert with \${${n}}`}
        >
          {`\${${n}}`}
        </code>
      ))}
    </div>
  );
}

export default function PromptsPage() {
  const [prompts, setPrompts] = useState<PromptView[] | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api
      .get<PromptView[]>("/prompts")
      .then(setPrompts)
      .catch((e) => setError(String(e)));
  }, []);

  const current = prompts?.find((p) => p.stem === selected) ?? null;

  const select = (p: PromptView) => {
    setSelected(p.stem);
    setDraft(p.content);
    setDirty(false);
    setSaved(false);
    setError(null);
  };

  // Auto-select the first prompt once the list loads.
  useEffect(() => {
    if (prompts && prompts.length > 0 && selected === null) select(prompts[0]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prompts]);

  const replace = (updated: PromptView) => {
    setPrompts((ps) => ps?.map((p) => (p.stem === updated.stem ? updated : p)) ?? ps);
    setDraft(updated.content);
    setDirty(false);
  };

  const save = async () => {
    if (!current) return;
    setSaving(true);
    setError(null);
    try {
      replace(
        await api.put<PromptView>(`/prompts/${current.stem}`, { content: draft })
      );
      setSaved(true);
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  const reset = async () => {
    if (!current) return;
    if (
      !window.confirm(
        "Reset this prompt to the bundled default? Your override will be deleted."
      )
    )
      return;
    setSaving(true);
    setError(null);
    try {
      replace(await api.del<PromptView>(`/prompts/${current.stem}`));
      setSaved(false);
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  const groups: PromptView["kind"][] = ["generation", "extraction"];

  return (
    <div className="max-w-5xl mx-auto p-6">
      <h1 className="text-xl font-semibold text-gray-900 mb-1">Prompts</h1>
      <p className="text-sm text-gray-500 mb-6">
        Customize the AI prompts for the active profile. A saved prompt overrides the
        bundled default; reset to revert. Reference the listed{" "}
        <code className="text-xs">${"{variables}"}</code> in your text.
      </p>

      <div className="flex gap-4">
        {/* Prompt list */}
        <aside className="w-56 shrink-0 space-y-4">
          {prompts === null ? (
            <p className="text-xs text-gray-400">Loading…</p>
          ) : (
            groups.map((kind) => {
              const items = prompts.filter((p) => p.kind === kind);
              if (items.length === 0) return null;
              return (
                <div key={kind}>
                  <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">
                    {KIND_LABEL[kind]}
                  </h2>
                  <ul className="space-y-0.5">
                    {items.map((p) => (
                      <li key={p.stem}>
                        <button
                          onClick={() => select(p)}
                          className={`w-full text-left px-2 py-1.5 rounded text-sm flex items-center
                            justify-between gap-2 ${
                              selected === p.stem
                                ? "bg-blue-100 text-blue-800 font-medium"
                                : "text-gray-700 hover:bg-gray-100"
                            }`}
                        >
                          <span className="truncate">{p.title}</span>
                          {p.overridden && (
                            <span
                              title="Customized for this profile"
                              className="shrink-0 w-1.5 h-1.5 rounded-full bg-amber-500"
                            />
                          )}
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })
          )}
        </aside>

        {/* Editor */}
        <div className="flex-1 min-w-0">
          {current ? (
            <div className="space-y-3">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <h2 className="text-base font-semibold text-gray-900">
                      {current.title}
                    </h2>
                    <span className="text-xs px-1.5 py-0.5 rounded bg-gray-100 text-gray-500">
                      {KIND_LABEL[current.kind]}
                    </span>
                    {current.overridden ? (
                      <span className="text-xs px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200">
                        Customized
                      </span>
                    ) : (
                      <span className="text-xs px-1.5 py-0.5 rounded bg-gray-50 text-gray-400 border border-gray-200">
                        Default
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-500 mt-1">{current.description}</p>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  {saved && <span className="text-sm text-green-600">Saved</span>}
                  {error && <span className="text-sm text-red-600">{error}</span>}
                  {current.overridden && (
                    <button
                      onClick={reset}
                      disabled={saving || !current.editable}
                      className="px-3 py-1.5 rounded text-sm text-gray-700 bg-gray-100
                        hover:bg-gray-200 disabled:opacity-40"
                    >
                      Reset to default
                    </button>
                  )}
                  <button
                    onClick={save}
                    disabled={!dirty || saving || !current.editable}
                    className="px-3 py-1.5 rounded bg-blue-600 text-white text-sm font-medium
                      hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {saving ? "Saving…" : "Save"}
                  </button>
                </div>
              </div>

              {!current.editable && (
                <div className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2">
                  This profile is read-only. Duplicate it (Settings → Profiles) to edit
                  prompts.
                </div>
              )}

              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">
                  Available variables
                </label>
                <Placeholders names={current.placeholders} />
              </div>

              <textarea
                value={draft}
                onChange={(e) => {
                  setDraft(e.target.value);
                  setDirty(true);
                  setSaved(false);
                }}
                disabled={!current.editable}
                spellCheck={false}
                className="w-full h-[55vh] p-3 text-sm font-mono border border-gray-300 rounded
                  focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y
                  disabled:bg-gray-50 disabled:text-gray-500"
              />
            </div>
          ) : (
            <div className="flex items-center justify-center h-64 text-gray-400 text-sm">
              {error ? (
                <span className="text-red-600">{error}</span>
              ) : (
                "Select a prompt to edit"
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
