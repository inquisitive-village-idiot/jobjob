import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { ApplicationSource, CompletedItem } from "../types";

interface Props {
  item: CompletedItem;
  onClose: () => void;
}

// Minimal source-tier editor (application-identity, phase 1): correct a parse
// error (company/role) or attach a posting URL/external ref to a PDF drop.
// description and entity_id are not editable here — the backend rejects them.
export default function SourceEditModal({ item, onClose }: Props) {
  const [source, setSource] = useState<ApplicationSource | null>(null);
  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");
  const [webUri, setWebUri] = useState("");
  const [externalRef, setExternalRef] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const folder = encodeURIComponent(item.folder_name);

  useEffect(() => {
    api
      .get<{ source: ApplicationSource }>(`/tracking/applications/${folder}/source`)
      .then((r) => {
        setSource(r.source);
        setCompany(r.source.company ?? "");
        setRole(r.source.role ?? "");
        setWebUri(r.source.web_uri ?? "");
        setExternalRef(r.source.external_ref ?? "");
      })
      .catch((e) => setError(String(e instanceof Error ? e.message : e)));
  }, [folder]);

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      const r = await api.patch<{ source: ApplicationSource }>(
        `/tracking/applications/${folder}/source`,
        { company, role, web_uri: webUri, external_ref: externalRef }
      );
      setSource(r.source);
      onClose();
    } catch (e) {
      setError(String(e instanceof Error ? e.message : e));
    } finally {
      setSaving(false);
    }
  };

  const label = item.company
    ? `${item.company} — ${item.title || ""}`.trim()
    : item.folder_name;

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4 flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-gray-900 truncate">
              Edit source
            </h2>
            <p className="text-xs text-gray-500 truncate">{label}</p>
            {item.entity_id && (
              <p className="text-xs text-gray-300 font-mono truncate">
                {item.entity_id.slice(0, 8)}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        <div className="p-5 space-y-3">
          {source === null && !error ? (
            <p className="text-sm text-gray-400">Loading…</p>
          ) : (
            <>
              <label className="block text-xs font-medium text-gray-600">
                Company
                <input
                  value={company}
                  onChange={(e) => setCompany(e.target.value)}
                  className="mt-1 w-full px-2 py-1.5 text-sm border border-gray-300 rounded
                    focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </label>
              <label className="block text-xs font-medium text-gray-600">
                Role
                <input
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="mt-1 w-full px-2 py-1.5 text-sm border border-gray-300 rounded
                    focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </label>
              <label className="block text-xs font-medium text-gray-600">
                Posting URL
                <input
                  value={webUri}
                  onChange={(e) => setWebUri(e.target.value)}
                  placeholder="https://…"
                  className="mt-1 w-full px-2 py-1.5 text-sm border border-gray-300 rounded
                    focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </label>
              <label className="block text-xs font-medium text-gray-600">
                External ref (requisition id)
                <input
                  value={externalRef}
                  onChange={(e) => setExternalRef(e.target.value)}
                  className="mt-1 w-full px-2 py-1.5 text-sm border border-gray-300 rounded
                    focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </label>
            </>
          )}
          {error && <p className="text-sm text-red-600">{error}</p>}
        </div>

        <div className="px-5 py-4 border-t border-gray-200 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-1.5 text-sm text-gray-700 bg-gray-100 rounded hover:bg-gray-200"
          >
            Cancel
          </button>
          <button
            onClick={save}
            disabled={saving || source === null}
            className="px-4 py-1.5 text-sm font-medium text-white bg-blue-600 rounded
              hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
