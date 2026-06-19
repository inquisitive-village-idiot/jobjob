import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { ReferenceFile, TomlFile } from "../types";
import { FloatingOutline, SectionHeader, useScrollSpy } from "../components/PageOutline";
import type { OutlineItem } from "../components/PageOutline";

type Tab = "highlights" | "skills" | "templates" | "reference";

// ── Helpers ──────────────────────────────────────────────────────────────────

function formatTitle(raw: string): string {
  return raw
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

type TomlName = "highlights" | "skills" | "templates";
const ARRAY_KEY: Record<TomlName, string> = {
  highlights: "highlight",
  skills: "skill",
  templates: "template",
};

type ConfigScalar = string | number | boolean;

function _tool(name: TomlName, parsed: Record<string, unknown> | null): Record<string, unknown> {
  return (
    ((parsed?.tool as Record<string, unknown>)?.[name] as
      | Record<string, unknown>
      | undefined) ?? {}
  );
}

// Item titles for a category — the floating outline's jump targets.
function categoryTitles(
  name: TomlName,
  parsed: Record<string, unknown> | null
): string[] {
  const items = (_tool(name, parsed)[ARRAY_KEY[name]] as Record<string, unknown>[] | undefined) ?? [];
  return items.map((it, i) => {
    if (name === "skills") return String(it.text ?? i);
    return formatTitle(String((name === "templates" ? it.name : it.context) ?? i));
  });
}

// Tool-level scalar parameters (everything that isn't the item array).
function categoryParams(
  name: TomlName,
  parsed: Record<string, unknown> | null
): Record<string, ConfigScalar> {
  const params: Record<string, ConfigScalar> = {};
  for (const [k, v] of Object.entries(_tool(name, parsed))) {
    if (k !== ARRAY_KEY[name] && (typeof v !== "object" || v === null)) {
      params[k] = v as ConfigScalar;
    }
  }
  return params;
}

function EditIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4" aria-hidden>
      <path d="M13.586 3.586a2 2 0 112.828 2.828l-8.5 8.5a1 1 0 01-.45.263l-3 .857a.5.5 0 01-.618-.618l.857-3a1 1 0 01.263-.45l8.5-8.5zM12.172 5L4 13.172V15h1.828L14 6.828 12.172 5z" />
    </svg>
  );
}

function ClipboardIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4" aria-hidden>
      <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
      <path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clipRule="evenodd" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4" aria-hidden>
      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
    </svg>
  );
}

function KeywordPills({ keywords }: { keywords: string[] }) {
  const sorted = [...keywords].sort((a, b) => a.localeCompare(b));
  return (
    <div className="flex flex-wrap gap-1 mt-2">
      {sorted.map((kw) => (
        <span
          key={kw}
          className="inline-flex items-center px-2 py-0.5 rounded-full text-xs
            bg-indigo-50 text-indigo-700 border border-indigo-200"
        >
          {kw}
        </span>
      ))}
    </div>
  );
}

// ── Item property table ───────────────────────────────────────────────────────

function renderValue(key: string, value: unknown) {
  if (Array.isArray(value)) return <KeywordPills keywords={value as string[]} />;
  if (typeof value === "boolean") return value ? "Yes" : "No";
  const mono = key === "doc_id" || key === "archetype";
  return (
    <span className={mono ? "font-mono text-xs" : "whitespace-pre-wrap leading-relaxed"}>
      {String(value)}
    </span>
  );
}

// Show an item's properties (Text, Enabled, Keywords, …) as a labeled table.
// Skips empty values and any field that just repeats the item's title.
function PropertyTable({
  fields,
  title,
}: {
  fields: Record<string, unknown>;
  title: string;
}) {
  const rows = Object.entries(fields).filter(([, v]) =>
    Array.isArray(v) ? v.length > 0 : v !== "" && v != null && String(v) !== title
  );
  if (rows.length === 0) return null;
  return (
    <table className="w-full text-sm">
      <tbody className="divide-y divide-gray-100">
        {rows.map(([key, value]) => (
          <tr key={key} className="align-top">
            <td className="py-1.5 pr-4 w-28 text-xs font-medium text-gray-500 uppercase tracking-wide">
              {formatTitle(key)}
            </td>
            <td className="py-1.5 text-gray-700">{renderValue(key, value)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// ── Keyword tag editor ────────────────────────────────────────────────────────

function KeywordEditor({
  value,
  onChange,
}: {
  value: string[];
  onChange: (v: string[]) => void;
}) {
  const [input, setInput] = useState(value.join(", "));

  const flush = (raw: string) => {
    const tags = raw
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    onChange(tags);
  };

  return (
    <input
      type="text"
      value={input}
      onChange={(e) => {
        setInput(e.target.value);
        flush(e.target.value);
      }}
      placeholder="comma-separated keywords"
      className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded
        focus:outline-none focus:ring-2 focus:ring-blue-500"
    />
  );
}

// ── Item card ─────────────────────────────────────────────────────────────────

interface ItemCardProps {
  index: number;
  title: string;
  subtitle?: string;
  enabled?: boolean;
  editableFields: Record<string, unknown>;
  tomlName: Tab;
  onSaved: (updated: TomlFile) => void;
  toggleAllSignal?: { n: number; value: boolean };
  domId?: string;
}

function ItemCard({
  index,
  title,
  subtitle,
  enabled,
  editableFields,
  tomlName,
  onSaved,
  toggleAllSignal,
  domId,
}: ItemCardProps) {
  const [open, setOpen] = useState(true); // items shown by default

  useEffect(() => {
    if (toggleAllSignal && toggleAllSignal.n > 0) setOpen(toggleAllSignal.value);
  }, [toggleAllSignal]);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<Record<string, unknown>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const copyText = (e: React.MouseEvent) => {
    e.stopPropagation();
    const text =
      (editableFields.text as string | undefined) ??
      (editableFields.description as string | undefined) ??
      "";
    if (!text) return;
    navigator.clipboard.writeText(text.trim()).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  const startEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    setDraft({ ...editableFields });
    setEditing(true);
    setOpen(true);
    setError(null);
  };

  const cancelEdit = () => {
    setEditing(false);
    setError(null);
  };

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      const updated = await api.patch<TomlFile>(
        `/static/toml/${tomlName}/items/${index}`,
        { fields: draft }
      );
      onSaved(updated);
      setEditing(false);
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div id={domId} className="scroll-mt-16">
      {/* Title row — a subtle underline separates it from the content */}
      <div
        className="group flex items-center justify-between py-1.5 border-b border-gray-100
          cursor-pointer select-none"
        onClick={() => !editing && setOpen((o) => !o)}
      >
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-sm font-medium text-gray-900 truncate">
            {title}
          </span>
          {subtitle && (
            <span className="text-xs text-gray-400 hidden sm:inline truncate">
              {subtitle}
            </span>
          )}
          {enabled === false && (
            <span className="shrink-0 text-xs px-1.5 py-0.5 rounded bg-gray-100 text-gray-500">
              disabled
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 ml-2 shrink-0">
          {"text" in editableFields || "description" in editableFields ? (
            <button
              onClick={copyText}
              title={copied ? "Copied!" : "Copy text"}
              aria-label={copied ? "Copied" : "Copy text"}
              className={`p-1 rounded transition-colors ${
                copied
                  ? "text-green-600 bg-green-50"
                  : "text-gray-400 hover:text-green-600 hover:bg-green-50"
              }`}
            >
              {copied ? <CheckIcon /> : <ClipboardIcon />}
            </button>
          ) : null}
          <button
            onClick={startEdit}
            title="Edit"
            aria-label="Edit"
            className="p-1 text-gray-400 hover:text-blue-600 rounded hover:bg-blue-50
              transition-colors"
          >
            <EditIcon />
          </button>
          <span className="text-gray-300 text-xs">{open ? "▲" : "▼"}</span>
        </div>
      </div>

      {/* Body */}
      {open && (
        <div className="pt-2 pb-1 space-y-3 text-gray-700">
          {editing ? (
            <>
              {/* Text / description textarea */}
              {"text" in editableFields && (
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">
                    Text
                  </label>
                  <textarea
                    value={(draft.text as string) ?? ""}
                    onChange={(e) =>
                      setDraft((d) => ({ ...d, text: e.target.value }))
                    }
                    rows={5}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded
                      focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y font-sans"
                  />
                </div>
              )}
              {"description" in editableFields && (
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">
                    Description
                  </label>
                  <textarea
                    value={(draft.description as string) ?? ""}
                    onChange={(e) =>
                      setDraft((d) => ({ ...d, description: e.target.value }))
                    }
                    rows={3}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded
                      focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
                  />
                </div>
              )}
              {/* Extra string fields (archetype, doc_id, label) */}
              {(["archetype", "doc_id", "label"] as const).map((field) =>
                field in editableFields ? (
                  <div key={field}>
                    <label className="block text-xs font-medium text-gray-500 mb-1 capitalize">
                      {field.replace("_", " ")}
                    </label>
                    <input
                      type="text"
                      value={(draft[field] as string) ?? ""}
                      onChange={(e) =>
                        setDraft((d) => ({ ...d, [field]: e.target.value }))
                      }
                      className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded
                        focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
                    />
                  </div>
                ) : null
              )}
              {"enabled" in editableFields && (
                <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={(draft.enabled as boolean) ?? true}
                    onChange={(e) =>
                      setDraft((d) => ({ ...d, enabled: e.target.checked }))
                    }
                    className="rounded"
                  />
                  Enabled
                </label>
              )}
              {"keywords" in editableFields && (
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">
                    Keywords (comma-separated)
                  </label>
                  <KeywordEditor
                    value={(draft.keywords as string[]) ?? []}
                    onChange={(v) => setDraft((d) => ({ ...d, keywords: v }))}
                  />
                  <KeywordPills
                    keywords={(draft.keywords as string[]) ?? []}
                  />
                </div>
              )}
              {error && (
                <p className="text-xs text-red-600">{error}</p>
              )}
              <div className="flex gap-2 pt-1">
                <button
                  onClick={save}
                  disabled={saving}
                  className="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded
                    hover:bg-blue-700 disabled:opacity-40"
                >
                  {saving ? "Saving…" : "Save"}
                </button>
                <button
                  onClick={cancelEdit}
                  className="px-3 py-1.5 text-sm text-gray-600 bg-gray-100 rounded hover:bg-gray-200"
                >
                  Cancel
                </button>
              </div>
            </>
          ) : (
            <PropertyTable fields={editableFields} title={title} />
          )}
        </div>
      )}
    </div>
  );
}

// ── Category view: styled items + floating item outline ───────────────────────

function CategoryView({
  name,
  file,
  onSaved,
}: {
  name: TomlName;
  file: TomlFile;
  onSaved: (f: TomlFile) => void;
}) {
  const parsed = file.parsed as Record<string, unknown> | null;
  const titles = categoryTitles(name, parsed);
  const params = categoryParams(name, parsed);
  const outline: OutlineItem[] = [
    { id: "sc-parameters", label: "Parameters" },
    { id: "sc-items", label: "Items" },
    ...titles.map((t, i) => ({ id: `sc-item-${i}`, label: t, indent: true })),
  ];
  const activeId = useScrollSpy(outline.map((o) => o.id), [name, titles.length]);

  if (!parsed) {
    return <p className="text-yellow-600 text-sm">TOML parse error — switch to raw editor.</p>;
  }

  return (
    <div className="relative">
      <FloatingOutline items={outline} activeId={activeId} />
      <div className="space-y-10">
        <section id="sc-parameters" className="scroll-mt-16">
          <SectionHeader>Parameters</SectionHeader>
          <ParametersTable name={name} params={params} onSaved={onSaved} />
        </section>
        <section id="sc-items" className="scroll-mt-16">
          <SectionHeader>Items</SectionHeader>
          <StyledTomlItems name={name} file={file} onSaved={onSaved} />
        </section>
      </div>
    </div>
  );
}

// ── Parameters table (tool-level scalars) ─────────────────────────────────────

function ParametersTable({
  name,
  params,
  onSaved,
}: {
  name: TomlName;
  params: Record<string, ConfigScalar>;
  onSaved: (f: TomlFile) => void;
}) {
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const keys = Object.keys(params);
  const dirty = keys.some((k) => k in draft && draft[k] !== String(params[k]));

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      const fields: Record<string, ConfigScalar> = {};
      for (const k of keys) {
        if (!(k in draft)) continue;
        const orig = params[k];
        fields[k] =
          typeof orig === "number"
            ? Number(draft[k])
            : typeof orig === "boolean"
            ? draft[k] === "true"
            : draft[k];
      }
      onSaved(await api.patch<TomlFile>(`/static/toml/${name}/config`, { fields }));
      setDraft({});
      setSaved(true);
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  if (keys.length === 0) {
    return <p className="text-sm text-gray-400">No parameters for this category.</p>;
  }

  return (
    <div className="space-y-3">
      <div className="inline-block border border-gray-200 rounded-lg overflow-hidden">
        <table className="text-sm">
          <tbody className="divide-y divide-gray-100">
            {keys.map((k) => (
              <tr key={k} className="bg-white">
                <td className="px-3 py-2 font-medium text-gray-700 bg-gray-50 align-middle">
                  {formatTitle(k)}
                </td>
                <td className="px-3 py-2">
                  <input
                    type={typeof params[k] === "number" ? "number" : "text"}
                    value={draft[k] ?? String(params[k])}
                    onChange={(e) => {
                      setDraft((d) => ({ ...d, [k]: e.target.value }));
                      setSaved(false);
                    }}
                    className="w-56 px-2 py-1 text-sm border border-gray-300 rounded
                      focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex items-center gap-3">
        <button
          onClick={save}
          disabled={!dirty || saving}
          className="px-3 py-1.5 rounded bg-blue-600 text-white text-sm font-medium
            hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {saving ? "Saving…" : "Save"}
        </button>
        {saved && <span className="text-sm text-green-600">Saved</span>}
        {error && <span className="text-sm text-red-600">{error}</span>}
      </div>
    </div>
  );
}

// ── TOML panel (styled) ───────────────────────────────────────────────────────

function TomlPanel({ name }: { name: "highlights" | "skills" | "templates" }) {
  const [file, setFile] = useState<TomlFile | null>(null);
  const [rawMode, setRawMode] = useState(false);
  const [draft, setDraft] = useState("");
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setFile(null);
    setRawMode(false);
    setDirty(false);
    setSaved(false);
    api
      .get<TomlFile>(`/static/toml/${name}`)
      .then((f) => {
        setFile(f);
        setDraft(f.content);
      })
      .catch((e) => setError(String(e)));
  }, [name]);

  const handleRawSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const updated = await api.put<TomlFile>(`/static/toml/${name}`, {
        content: draft,
      });
      setFile(updated);
      setDirty(false);
      setSaved(true);
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  if (!file && !error) return <p className="text-gray-400 text-sm">Loading…</p>;
  if (error) return <p className="text-red-600 text-sm">{error}</p>;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <code className="text-xs bg-gray-100 px-2 py-1 rounded">
          static/content/{name}.toml
        </code>
        <div className="flex items-center gap-3">
          {saved && <span className="text-sm text-green-600">Saved</span>}
          {error && <span className="text-sm text-red-600">{error}</span>}
          <button
            onClick={() => setRawMode((r) => !r)}
            className="text-xs text-gray-500 hover:text-gray-700 underline"
          >
            {rawMode ? "Styled view" : "Edit raw TOML"}
          </button>
          {rawMode && (
            <button
              onClick={handleRawSave}
              disabled={!dirty || saving}
              className="px-3 py-1.5 rounded bg-blue-600 text-white text-sm font-medium
                hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {saving ? "Saving…" : "Save"}
            </button>
          )}
        </div>
      </div>

      {rawMode ? (
        <textarea
          value={draft}
          onChange={(e) => {
            setDraft(e.target.value);
            setDirty(true);
            setSaved(false);
          }}
          className="w-full h-[60vh] p-3 text-sm font-mono border border-gray-300 rounded
            focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
          spellCheck={false}
        />
      ) : (
        <CategoryView
          name={name}
          file={file!}
          onSaved={(updated) => {
            setFile(updated);
            setDraft(updated.content);
          }}
        />
      )}
    </div>
  );
}

// ── Styled items renderer ─────────────────────────────────────────────────────

interface ParsedHighlight {
  context: string;
  enabled?: boolean;
  text?: string;
  keywords?: string[];
}
interface ParsedSkill {
  text: string;
  label?: string;
  keywords?: string[];
}
interface ParsedTemplate {
  name: string;
  archetype?: string;
  doc_id?: string;
  description?: string;
  keywords?: string[];
}

function StyledTomlItems({
  name,
  file,
  onSaved,
}: {
  name: "highlights" | "skills" | "templates";
  file: TomlFile;
  onSaved: (f: TomlFile) => void;
}) {
  const [allExpanded, setAllExpanded] = useState(true);
  const [toggleAllSignal, setToggleAllSignal] = useState({ n: 0, value: false });

  const toggleAll = () => {
    const next = !allExpanded;
    setAllExpanded(next);
    setToggleAllSignal((s) => ({ n: s.n + 1, value: next }));
  };

  const parsed = file.parsed as Record<string, unknown> | null;
  if (!parsed) {
    return <p className="text-yellow-600 text-sm">TOML parse error — switch to raw editor.</p>;
  }

  const tool = parsed.tool as Record<string, unknown>;

  const ToggleAllButton = () => (
    <div className="flex justify-end mb-2">
      <button
        onClick={toggleAll}
        className="text-xs text-gray-500 hover:text-gray-700 underline"
      >
        {allExpanded ? "Collapse all" : "Expand all"}
      </button>
    </div>
  );

  if (name === "highlights") {
    const items = ((tool?.highlights as Record<string, unknown>)?.highlight ??
      []) as ParsedHighlight[];
    return (
      <div>
        <ToggleAllButton />
        <div className="space-y-5">
          {items.map((item, i) => (
            <ItemCard
              key={item.context ?? i}
              index={i}
              title={formatTitle(item.context ?? String(i))}
              enabled={item.enabled}
              editableFields={{
                text: item.text ?? "",
                enabled: item.enabled ?? true,
                keywords: item.keywords ?? [],
              }}
              tomlName={name}
              onSaved={onSaved}
              toggleAllSignal={toggleAllSignal}
              domId={`sc-item-${i}`}
            />
          ))}
        </div>
      </div>
    );
  }

  if (name === "skills") {
    const items = ((tool?.skills as Record<string, unknown>)?.skill ??
      []) as ParsedSkill[];
    return (
      <div>
        <ToggleAllButton />
        <div className="space-y-5">
          {items.map((item, i) => (
            <ItemCard
              key={item.label ?? i}
              index={i}
              title={item.text}
              subtitle={item.label ? `(${item.label})` : undefined}
              editableFields={{
                text: item.text ?? "",
                label: item.label ?? "",
                keywords: item.keywords ?? [],
              }}
              tomlName={name}
              onSaved={onSaved}
              toggleAllSignal={toggleAllSignal}
              domId={`sc-item-${i}`}
            />
          ))}
        </div>
      </div>
    );
  }

  // templates
  const items = ((tool?.templates as Record<string, unknown>)?.template ??
    []) as ParsedTemplate[];
  return (
    <div>
      <ToggleAllButton />
      <div className="space-y-5">
        {items.map((item, i) => (
          <ItemCard
            key={item.name ?? i}
            index={i}
            title={formatTitle(item.name ?? String(i))}
            subtitle={item.archetype}
            editableFields={{
              name: item.name ?? "",
              archetype: item.archetype ?? "",
              doc_id: item.doc_id ?? "",
              description: item.description ?? "",
              keywords: item.keywords ?? [],
            }}
            tomlName={name}
            onSaved={onSaved}
            toggleAllSignal={toggleAllSignal}
            domId={`sc-item-${i}`}
          />
        ))}
      </div>
    </div>
  );
}

// ── Reference panel ───────────────────────────────────────────────────────────

function ReferencePanel() {
  const [files, setFiles] = useState<ReferenceFile[] | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [draft, setDraft] = useState<string>("");
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api
      .get<ReferenceFile[]>("/static/reference")
      .then(setFiles)
      .catch((e) => setError(String(e)));
  }, []);

  const openFile = async (path: string) => {
    setError(null);
    setSaved(false);
    try {
      const data = await api.get<{ path: string; content: string }>(
        `/static/reference/${path}`
      );
      setSelected(path);
      setDraft(data.content);
      setDirty(false);
    } catch (e) {
      setError(String(e));
    }
  };

  const handleSave = async () => {
    if (!selected) return;
    setSaving(true);
    setError(null);
    try {
      await api.put(`/static/reference/${selected}`, { content: draft });
      setDirty(false);
      setSaved(true);
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex gap-4 h-[65vh]">
      <aside className="w-52 shrink-0 overflow-y-auto border border-gray-200 rounded-lg p-2">
        {files === null ? (
          <p className="text-xs text-gray-400 p-2">Loading…</p>
        ) : (
          <ul className="space-y-0.5">
            {files.map((f) => (
              <li key={f.path}>
                <button
                  onClick={() => openFile(f.path)}
                  className={`w-full text-left px-2 py-1.5 rounded text-xs truncate ${
                    selected === f.path
                      ? "bg-blue-100 text-blue-800 font-medium"
                      : "text-gray-700 hover:bg-gray-100"
                  }`}
                  title={f.path}
                >
                  {f.path}
                </button>
              </li>
            ))}
          </ul>
        )}
      </aside>

      <div className="flex-1 flex flex-col gap-2">
        {selected ? (
          <>
            <div className="flex items-center justify-between">
              <code className="text-xs bg-gray-100 px-2 py-1 rounded">
                {selected}
              </code>
              <div className="flex items-center gap-3">
                {saved && <span className="text-sm text-green-600">Saved</span>}
                {error && <span className="text-sm text-red-600">{error}</span>}
                <button
                  onClick={handleSave}
                  disabled={!dirty || saving}
                  className="px-3 py-1.5 rounded bg-blue-600 text-white text-sm font-medium
                    hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {saving ? "Saving…" : "Save"}
                </button>
              </div>
            </div>
            <textarea
              value={draft}
              onChange={(e) => {
                setDraft(e.target.value);
                setDirty(true);
                setSaved(false);
              }}
              className="flex-1 p-3 text-sm font-mono border border-gray-300 rounded
                focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              spellCheck={false}
            />
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">
            {error ? (
              <span className="text-red-600">{error}</span>
            ) : (
              "Select a file to edit"
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function StaticContentPage() {
  const [activeTab, setActiveTab] = useState<Tab>("highlights");

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-xl font-semibold text-gray-900 mb-6">
        Static Content
      </h1>
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex gap-4">
          {(["highlights", "skills", "templates", "reference"] as Tab[]).map(
            (tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`pb-2 px-1 text-sm font-medium capitalize border-b-2 transition-colors ${
                  activeTab === tab
                    ? "border-blue-600 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
              >
                {tab}
              </button>
            )
          )}
        </nav>
      </div>
      {activeTab === "reference" ? (
        <ReferencePanel />
      ) : (
        <TomlPanel name={activeTab} />
      )}
    </div>
  );
}
