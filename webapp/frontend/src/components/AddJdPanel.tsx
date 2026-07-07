import { useState } from "react";
import type { ReactNode } from "react";

type Mode = "url" | "text";

/**
 * Add a JD to the Apply queue from a posting URL or pasted text. The server fetches
 * (URL) or accepts (paste) the posting, writes a durable snapshot into data/jobs/,
 * and launches apply — mirroring the file-drop flow without leaving the browser.
 */
export default function AddJdPanel({
  onSubmit,
}: {
  onSubmit: (
    source: { url: string } | { text: string },
    opts: { skipDrive: boolean }
  ) => Promise<string>;
}) {
  const [mode, setMode] = useState<Mode>("url");
  const [url, setUrl] = useState("");
  const [text, setText] = useState("");
  const [skipDrive, setSkipDrive] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit = mode === "url" ? url.trim().length > 0 : text.trim().length > 0;

  const submit = async () => {
    if (!canSubmit || busy) return;
    setBusy(true);
    setError(null);
    try {
      const source = mode === "url" ? { url: url.trim() } : { text };
      await onSubmit(source, { skipDrive });
      // Clear the inputs once the job is launched.
      setUrl("");
      setText("");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="border border-gray-200 rounded-lg p-4 bg-white space-y-3">
      <div className="flex items-center gap-2">
        <TabButton active={mode === "url"} onClick={() => setMode("url")}>
          From URL
        </TabButton>
        <TabButton active={mode === "text"} onClick={() => setMode("text")}>
          Paste text
        </TabButton>
      </div>

      {mode === "url" ? (
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          placeholder="https://company.example.com/careers/role"
          className="w-full px-3 py-2 text-sm border border-gray-300 rounded
            focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      ) : (
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={6}
          placeholder="Paste the full job-posting text here…"
          className="w-full px-3 py-2 text-sm border border-gray-300 rounded font-mono
            focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      )}

      <p className="text-xs text-gray-400">
        {mode === "url"
          ? "A snapshot of the posting is saved so it survives the listing being taken down. JavaScript-rendered or sign-in-walled boards may not extract — paste the text instead."
          : "The reliable fallback for boards that won't fetch (LinkedIn, Workday, Greenhouse, …)."}
      </p>

      {error && <p className="text-xs text-red-600">{error}</p>}

      <div className="flex items-center justify-between">
        <label className="flex items-center gap-2 text-xs text-gray-600">
          <input
            type="checkbox"
            checked={skipDrive}
            onChange={(e) => setSkipDrive(e.target.checked)}
          />
          Skip Google Drive (local only)
        </label>
        <button
          onClick={submit}
          disabled={!canSubmit || busy}
          className="px-3 py-1 text-xs font-medium text-white bg-blue-600 rounded
            hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {/* NOTE: UI-only rename — the pipeline is "Build" in copy; API/CLI names unchanged (full rename is a future change). */}
          {busy ? "Capturing…" : "Capture & Build"}
        </button>
      </div>
    </section>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1 text-xs font-medium rounded ${
        active
          ? "bg-blue-600 text-white"
          : "text-gray-600 border border-gray-200 hover:bg-gray-50"
      }`}
    >
      {children}
    </button>
  );
}
