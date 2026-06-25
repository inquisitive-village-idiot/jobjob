import { useState } from "react";
import { api } from "../api/client";

const TOPICS = [
  "",
  "Collaboration",
  "Communication",
  "Creativity",
  "Leadership",
  "Teamwork",
  "Technical",
];

const ACCEPT = ".pdf,.docx,.txt,.md";

type Mode = "replace" | "append";

interface DraftHighlight {
  context: string;
  topic: string;
  text: string;
  keywords: string[];
  enabled: boolean;
}
interface DraftSkill {
  label: string;
  text: string;
  keywords: string[];
}
interface DraftRole {
  company: string;
  title: string;
  location: string;
  start: string;
  end: string;
  current: boolean;
  description: string;
}
interface ExtractResult {
  objective: string;
  sections: string[];
  background: string;
  highlights: DraftHighlight[];
  skills: DraftSkill[];
  experience: DraftRole[];
  background_mode: string;
}
interface SaveResult {
  saved: Record<string, { mode: string; count?: number; path?: string }>;
}

function SaveModeSelect({
  value,
  onChange,
}: {
  value: Mode;
  onChange: (m: Mode) => void;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value as Mode)}
      className="text-xs border border-gray-300 rounded px-1.5 py-1
        focus:outline-none focus:ring-2 focus:ring-blue-500"
    >
      <option value="append">Append to existing</option>
      <option value="replace">Replace existing</option>
    </select>
  );
}

export default function ResumeImportPanel() {
  const [file, setFile] = useState<File | null>(null);
  const [backgroundMode, setBackgroundMode] = useState<"fuller" | "conservative">(
    "fuller"
  );
  const [extracting, setExtracting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState<ExtractResult | null>(null);

  const [saveHighlights, setSaveHighlights] = useState(true);
  const [hlMode, setHlMode] = useState<Mode>("append");
  const [saveSkills, setSaveSkills] = useState(true);
  const [skMode, setSkMode] = useState<Mode>("append");
  const [saveExperience, setSaveExperience] = useState(true);
  const [exMode, setExMode] = useState<Mode>("append");
  const [saveBackground, setSaveBackground] = useState(false);
  const [bgMode, setBgMode] = useState<Mode>("replace");
  const [saving, setSaving] = useState(false);
  const [savedSummary, setSavedSummary] = useState<string | null>(null);

  const extract = async () => {
    if (!file) return;
    setExtracting(true);
    setError(null);
    setSavedSummary(null);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("background_mode", backgroundMode);
      const res = await api.postForm<ExtractResult>("/resume-import/extract", form);
      setDraft(res);
      setSaveBackground(Boolean(res.background));
    } catch (e) {
      setError(String(e));
    } finally {
      setExtracting(false);
    }
  };

  const patchHighlight = (i: number, patch: Partial<DraftHighlight>) =>
    setDraft((d) =>
      d
        ? {
            ...d,
            highlights: d.highlights.map((h, idx) =>
              idx === i ? { ...h, ...patch } : h
            ),
          }
        : d
    );
  const removeHighlight = (i: number) =>
    setDraft((d) =>
      d ? { ...d, highlights: d.highlights.filter((_, idx) => idx !== i) } : d
    );
  const patchSkill = (i: number, patch: Partial<DraftSkill>) =>
    setDraft((d) =>
      d
        ? {
            ...d,
            skills: d.skills.map((s, idx) => (idx === i ? { ...s, ...patch } : s)),
          }
        : d
    );
  const removeSkill = (i: number) =>
    setDraft((d) => (d ? { ...d, skills: d.skills.filter((_, idx) => idx !== i) } : d));
  const patchRole = (i: number, patch: Partial<DraftRole>) =>
    setDraft((d) =>
      d
        ? {
            ...d,
            experience: d.experience.map((r, idx) =>
              idx === i ? { ...r, ...patch } : r
            ),
          }
        : d
    );
  const removeRole = (i: number) =>
    setDraft((d) =>
      d ? { ...d, experience: d.experience.filter((_, idx) => idx !== i) } : d
    );

  const save = async () => {
    if (!draft) return;
    setSaving(true);
    setError(null);
    setSavedSummary(null);
    try {
      const targets: Record<string, Mode> = {};
      if (saveHighlights) targets.highlights = hlMode;
      if (saveSkills) targets.skills = skMode;
      if (saveExperience) targets.experience = exMode;
      if (saveBackground) targets.background = bgMode;
      const res = await api.post<SaveResult>("/resume-import/save", {
        highlights: draft.highlights,
        skills: draft.skills,
        experience: draft.experience,
        background: draft.background,
        targets,
      });
      const parts = Object.entries(res.saved).map(([k, v]) => {
        const detail = v.count != null ? `${v.mode}, ${v.count}` : v.mode;
        return `${k} (${detail})`;
      });
      setSavedSummary(
        `Saved ${parts.join(", ")}. Switch to the relevant tab (or reload) to see it.`
      );
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-5">
      <p className="text-sm text-gray-600">
        Upload an existing résumé to bootstrap your reusable content. jobjob extracts
        highlights, skills, your work history, an objective, and a background narrative
        for you to review and edit before saving into your active profile.
      </p>

      {/* ── Upload ── */}
      <div className="border border-gray-200 rounded-lg p-4 space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          <input
            type="file"
            accept={ACCEPT}
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="text-sm"
          />
          <label className="text-sm text-gray-600 flex items-center gap-1">
            Background:
            <select
              value={backgroundMode}
              onChange={(e) =>
                setBackgroundMode(e.target.value as "fuller" | "conservative")
              }
              className="text-sm border border-gray-300 rounded px-1.5 py-1
                focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="fuller">Fuller (uses your writing samples)</option>
              <option value="conservative">Conservative (facts only)</option>
            </select>
          </label>
          <button
            onClick={extract}
            disabled={!file || extracting}
            className="px-3 py-1.5 rounded bg-blue-600 text-white text-sm font-medium
              hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {extracting ? "Extracting…" : "Extract"}
          </button>
        </div>
        <p className="text-xs text-gray-400">
          Supports {ACCEPT}. Scanned/image-only PDFs can&apos;t be read — export a
          text-based PDF or DOCX. Fuller mode mirrors the voice in your reference
          writing samples; nothing is invented beyond the résumé.
        </p>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}
      {savedSummary && (
        <p className="text-sm text-green-700 bg-green-50 border border-green-200 rounded p-2">
          {savedSummary}
        </p>
      )}

      {draft && (
        <div className="space-y-6">
          {/* ── Objective (suggested; not directly saved) ── */}
          {draft.objective && (
            <section>
              <h3 className="text-sm font-semibold text-gray-900 mb-1">
                Suggested objective
              </h3>
              <p className="text-sm text-gray-700 italic">{draft.objective}</p>
              {draft.sections.length > 0 && (
                <p className="text-xs text-gray-400 mt-1">
                  Détected résumé sections: {draft.sections.join(", ")}
                </p>
              )}
            </section>
          )}

          {/* ── Highlights ── */}
          <section>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold text-gray-900">
                Highlights ({draft.highlights.length})
              </h3>
              <label className="flex items-center gap-2 text-xs text-gray-600">
                <input
                  type="checkbox"
                  checked={saveHighlights}
                  onChange={(e) => setSaveHighlights(e.target.checked)}
                />
                Save
                {saveHighlights && (
                  <SaveModeSelect value={hlMode} onChange={setHlMode} />
                )}
              </label>
            </div>
            <div className="space-y-3">
              {draft.highlights.map((h, i) => (
                <div
                  key={i}
                  className="border border-gray-200 rounded-lg p-3 space-y-2"
                >
                  <div className="flex items-center gap-2">
                    <select
                      value={h.topic}
                      onChange={(e) => patchHighlight(i, { topic: e.target.value })}
                      className="text-xs border border-gray-300 rounded px-1.5 py-1
                        focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      {TOPICS.map((t) => (
                        <option key={t} value={t}>
                          {t || "— topic —"}
                        </option>
                      ))}
                    </select>
                    <span className="text-xs text-gray-400 truncate flex-1">
                      {h.context}
                    </span>
                    <button
                      onClick={() => removeHighlight(i)}
                      className="text-xs text-gray-400 hover:text-red-600"
                    >
                      Remove
                    </button>
                  </div>
                  <textarea
                    value={h.text}
                    onChange={(e) => patchHighlight(i, { text: e.target.value })}
                    rows={2}
                    className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded
                      focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
                  />
                  <input
                    value={h.keywords.join(", ")}
                    onChange={(e) =>
                      patchHighlight(i, {
                        keywords: e.target.value
                          .split(",")
                          .map((k) => k.trim())
                          .filter(Boolean),
                      })
                    }
                    placeholder="keywords, comma separated"
                    className="w-full px-2 py-1 text-xs border border-gray-300 rounded
                      focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              ))}
              {draft.highlights.length === 0 && (
                <p className="text-xs text-gray-400">No highlights extracted.</p>
              )}
            </div>
          </section>

          {/* ── Skills ── */}
          <section>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold text-gray-900">
                Skills ({draft.skills.length})
              </h3>
              <label className="flex items-center gap-2 text-xs text-gray-600">
                <input
                  type="checkbox"
                  checked={saveSkills}
                  onChange={(e) => setSaveSkills(e.target.checked)}
                />
                Save
                {saveSkills && <SaveModeSelect value={skMode} onChange={setSkMode} />}
              </label>
            </div>
            <div className="space-y-2">
              {draft.skills.map((s, i) => (
                <div
                  key={i}
                  className="border border-gray-200 rounded-lg p-2 flex items-center gap-2"
                >
                  <input
                    value={s.text}
                    onChange={(e) => patchSkill(i, { text: e.target.value })}
                    className="px-2 py-1 text-sm border border-gray-300 rounded w-48
                      focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <input
                    value={s.keywords.join(", ")}
                    onChange={(e) =>
                      patchSkill(i, {
                        keywords: e.target.value
                          .split(",")
                          .map((k) => k.trim())
                          .filter(Boolean),
                      })
                    }
                    placeholder="keywords"
                    className="flex-1 px-2 py-1 text-xs border border-gray-300 rounded
                      focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <button
                    onClick={() => removeSkill(i)}
                    className="text-xs text-gray-400 hover:text-red-600 shrink-0"
                  >
                    Remove
                  </button>
                </div>
              ))}
              {draft.skills.length === 0 && (
                <p className="text-xs text-gray-400">No skills extracted.</p>
              )}
            </div>
          </section>

          {/* ── Experience ── */}
          <section>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold text-gray-900">
                Work experience ({draft.experience.length})
              </h3>
              <label className="flex items-center gap-2 text-xs text-gray-600">
                <input
                  type="checkbox"
                  checked={saveExperience}
                  onChange={(e) => setSaveExperience(e.target.checked)}
                />
                Save
                {saveExperience && (
                  <SaveModeSelect value={exMode} onChange={setExMode} />
                )}
              </label>
            </div>
            <p className="text-xs text-gray-400 mb-2">
              One entry per role. Several roles at the same employer (e.g. a promotion)
              are kept separate — each with its own dates and bullets — which is how an
              application form wants them.
            </p>
            <div className="space-y-3">
              {draft.experience.map((r, i) => (
                <div
                  key={i}
                  className="border border-gray-200 rounded-lg p-3 space-y-2"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <input
                      value={r.title}
                      onChange={(e) => patchRole(i, { title: e.target.value })}
                      placeholder="Title"
                      className="px-2 py-1 text-sm border border-gray-300 rounded w-44
                        focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <input
                      value={r.company}
                      onChange={(e) => patchRole(i, { company: e.target.value })}
                      placeholder="Company"
                      className="px-2 py-1 text-sm border border-gray-300 rounded w-44
                        focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <input
                      value={r.location}
                      onChange={(e) => patchRole(i, { location: e.target.value })}
                      placeholder="Location"
                      className="px-2 py-1 text-xs border border-gray-300 rounded w-28
                        focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <button
                      onClick={() => removeRole(i)}
                      className="text-xs text-gray-400 hover:text-red-600 ml-auto"
                    >
                      Remove
                    </button>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <input
                      value={r.start}
                      onChange={(e) => patchRole(i, { start: e.target.value })}
                      placeholder="Start (e.g. 2021-04)"
                      className="px-2 py-1 text-xs border border-gray-300 rounded w-36
                        focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <input
                      value={r.end}
                      onChange={(e) => patchRole(i, { end: e.target.value })}
                      placeholder="End"
                      disabled={r.current}
                      className="px-2 py-1 text-xs border border-gray-300 rounded w-36
                        focus:outline-none focus:ring-2 focus:ring-blue-500
                        disabled:bg-gray-50 disabled:text-gray-400"
                    />
                    <label className="flex items-center gap-1 text-xs text-gray-600">
                      <input
                        type="checkbox"
                        checked={r.current}
                        onChange={(e) =>
                          patchRole(i, {
                            current: e.target.checked,
                            ...(e.target.checked ? { end: "" } : {}),
                          })
                        }
                      />
                      Current role
                    </label>
                  </div>
                  <textarea
                    value={r.description}
                    onChange={(e) => patchRole(i, { description: e.target.value })}
                    rows={3}
                    placeholder="One accomplishment per line"
                    className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded
                      focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
                  />
                </div>
              ))}
              {draft.experience.length === 0 && (
                <p className="text-xs text-gray-400">No work experience extracted.</p>
              )}
            </div>
          </section>

          {/* ── Background ── */}
          <section>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold text-gray-900">Background</h3>
              <label className="flex items-center gap-2 text-xs text-gray-600">
                <input
                  type="checkbox"
                  checked={saveBackground}
                  onChange={(e) => setSaveBackground(e.target.checked)}
                />
                Save
                {saveBackground && (
                  <SaveModeSelect value={bgMode} onChange={setBgMode} />
                )}
              </label>
            </div>
            <textarea
              value={draft.background}
              onChange={(e) =>
                setDraft((d) => (d ? { ...d, background: e.target.value } : d))
              }
              rows={5}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded
                focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
            />
          </section>

          {/* ── Save ── */}
          <div className="flex items-center justify-end gap-3 border-t border-gray-100 pt-3">
            <button
              onClick={save}
              disabled={
                saving ||
                (!saveHighlights && !saveSkills && !saveExperience && !saveBackground)
              }
              className="px-4 py-2 rounded bg-blue-600 text-white text-sm font-medium
                hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {saving ? "Saving…" : "Save selected"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
