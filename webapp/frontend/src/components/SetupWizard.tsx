import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { ProfilesInfo, SetupStatus } from "../types";

type Details = {
  APPLICANT_NAME: string;
  APPLICANT_EMAIL: string;
  APPLICANT_PHONE: string;
  APPLICANT_LINKEDIN: string;
};

const EMPTY_DETAILS: Details = {
  APPLICANT_NAME: "",
  APPLICANT_EMAIL: "",
  APPLICANT_PHONE: "",
  APPLICANT_LINKEDIN: "",
};

/**
 * First-run setup wizard. Walks the user through the Anthropic key, optional
 * Google connection, profile setup (register an existing profile or bootstrap from a
 * résumé), and applicant identity. Auto-opened by the app shell when setup is
 * incomplete and not dismissed; also re-openable from the account menu.
 */
export default function SetupWizard({
  onClose,
  onDone,
}: {
  onClose: () => void;
  onDone: () => void;
}) {
  const [step, setStep] = useState(0);
  const [status, setStatus] = useState<SetupStatus | null>(null);
  // Lifted so the résumé-import step can prefill the details step.
  const [details, setDetails] = useState<Details>(EMPTY_DETAILS);

  const refresh = () =>
    api
      .get<SetupStatus>("/setup/status")
      .then(setStatus)
      .catch(() => {});

  useEffect(() => {
    refresh();
  }, []);

  const steps = ["Anthropic key", "Google (optional)", "Profile", "Your details"];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-lg bg-white rounded-xl shadow-xl flex flex-col max-h-[90vh]">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Welcome to jobjob</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            A few one-time steps to get you running.
          </p>
          <div className="flex gap-1.5 mt-3">
            {steps.map((label, i) => (
              <div key={label} className="flex-1">
                <div
                  className={`h-1 rounded-full ${
                    i <= step ? "bg-blue-600" : "bg-gray-200"
                  }`}
                />
                <span
                  className={`text-[11px] ${
                    i === step ? "text-blue-600 font-medium" : "text-gray-400"
                  }`}
                >
                  {label}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="px-6 py-5 overflow-y-auto">
          {step === 0 && <KeyStep status={status} onSaved={refresh} />}
          {step === 1 && <GoogleStep status={status} onChange={refresh} />}
          {step === 2 && (
            <ProfileStep
              onImportedIdentity={(patch) => setDetails((d) => ({ ...d, ...patch }))}
            />
          )}
          {step === 3 && (
            <DetailsStep form={details} setForm={setDetails} onSaved={refresh} />
          )}
        </div>

        <div className="px-6 py-3 border-t border-gray-200 flex items-center justify-between">
          <button
            onClick={async () => {
              await api.post("/setup/dismiss", { dismissed: true }).catch(() => {});
              onClose();
            }}
            className="text-xs text-gray-400 hover:text-gray-600"
          >
            Don't show again
          </button>
          <div className="flex gap-2">
            {step > 0 && (
              <button
                onClick={() => setStep((s) => s - 1)}
                className="px-3 py-1.5 text-sm font-medium text-gray-700 border
                  border-gray-200 rounded hover:bg-gray-50"
              >
                Back
              </button>
            )}
            {step < steps.length - 1 ? (
              <button
                onClick={() => setStep((s) => s + 1)}
                className="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded
                  hover:bg-blue-700"
              >
                Next
              </button>
            ) : (
              <button
                onClick={onDone}
                className="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded
                  hover:bg-blue-700"
              >
                Finish
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function Saved() {
  return <span className="ml-2 text-xs text-green-600">✓ saved</span>;
}

function KeyStep({
  status,
  onSaved,
}: {
  status: SetupStatus | null;
  onSaved: () => void;
}) {
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const save = async () => {
    setBusy(true);
    try {
      await api.put("/setup/anthropic-key", { value });
      setValue("");
      onSaved();
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="space-y-3">
      <p className="text-sm text-gray-600">
        Paste your Anthropic API key. It powers the AI and is stored locally on this
        machine only.{" "}
        <a
          href="https://console.anthropic.com/settings/keys"
          target="_blank"
          rel="noreferrer"
          className="text-blue-600 hover:underline"
        >
          Get a key
        </a>
        .
      </p>
      <div className="flex gap-2">
        <input
          type="password"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="sk-ant-…"
          className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded
            focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          onClick={save}
          disabled={busy || !value.trim()}
          className="px-3 py-2 text-sm font-medium text-white bg-blue-600 rounded
            hover:bg-blue-700 disabled:opacity-50"
        >
          Save
        </button>
      </div>
      {status?.anthropic_key && (
        <p className="text-sm text-green-600">✓ A key is configured.</p>
      )}
    </div>
  );
}

function GoogleStep({
  status,
  onChange,
}: {
  status: SetupStatus | null;
  onChange: () => void;
}) {
  const [busy, setBusy] = useState(false);

  // Poll while an OAuth flow is running so the UI reflects completion.
  useEffect(() => {
    if (!status?.auth_running) return;
    const t = setInterval(onChange, 1500);
    return () => clearInterval(t);
  }, [status?.auth_running, onChange]);

  const upload = async (file: File) => {
    setBusy(true);
    try {
      const form = new FormData();
      form.append("file", file);
      await api.postForm("/setup/credentials", form);
      onChange();
    } finally {
      setBusy(false);
    }
  };

  const connect = async () => {
    await api.post("/setup/google-auth", {}).catch(() => {});
    onChange();
  };

  return (
    <div className="space-y-3">
      <p className="text-sm text-gray-600">
        Connect Google to save resumes and cover letters to Drive/Docs. Optional — skip
        for local-only output.{" "}
        <a
          href="https://github.com/inquisitive-village-idiot/jobjob/blob/main/docs/install-google-project.md"
          target="_blank"
          rel="noreferrer"
          className="text-blue-600 hover:underline"
        >
          How to get credentials.json
        </a>
        .
      </p>

      <label className="block text-sm">
        <span className="text-gray-700">1. Upload your credentials.json</span>
        <input
          type="file"
          accept="application/json,.json"
          disabled={busy}
          onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])}
          className="mt-1 block w-full text-sm text-gray-600 file:mr-3 file:py-1.5
            file:px-3 file:rounded file:border-0 file:text-sm file:font-medium
            file:bg-gray-100 file:text-gray-700 hover:file:bg-gray-200"
        />
        {status?.credentials_file && <Saved />}
      </label>

      <div>
        <button
          onClick={connect}
          disabled={!status?.credentials_file || status?.auth_running}
          className="px-3 py-2 text-sm font-medium text-white bg-blue-600 rounded
            hover:bg-blue-700 disabled:opacity-50"
        >
          2. {status?.auth_running ? "Waiting for consent…" : "Connect Google"}
        </button>
        {status?.google_token && (
          <p className="text-sm text-green-600 mt-2">✓ Google is connected.</p>
        )}
        {status?.auth_error && (
          <p className="text-sm text-red-600 mt-2">{status.auth_error}</p>
        )}
      </div>
    </div>
  );
}

const ACCEPT_RESUME = ".pdf,.docx,.txt,.md";

interface ExtractIdentity {
  name?: string;
  email?: string;
  phone?: string;
  linkedin?: string;
}
interface ExtractResult {
  identity: ExtractIdentity;
  highlights: unknown[];
  skills: unknown[];
}

// Profile step: register an existing profile folder, OR bootstrap from a résumé
// (prefills the applicant identity and can import highlights/skills). Both optional.
function ProfileStep({
  onImportedIdentity,
}: {
  onImportedIdentity: (patch: Partial<Details>) => void;
}) {
  // Register-existing-profile state.
  const [regName, setRegName] = useState("");
  const [regPath, setRegPath] = useState("");
  const [regBusy, setRegBusy] = useState(false);
  const [regMsg, setRegMsg] = useState<string | null>(null);
  const [regError, setRegError] = useState<string | null>(null);

  // Résumé-import state.
  const [file, setFile] = useState<File | null>(null);
  const [extracting, setExtracting] = useState(false);
  const [impError, setImpError] = useState<string | null>(null);
  const [impMsg, setImpMsg] = useState<string | null>(null);
  const [draft, setDraft] = useState<ExtractResult | null>(null);
  const [savingContent, setSavingContent] = useState(false);

  const register = async () => {
    setRegBusy(true);
    setRegError(null);
    setRegMsg(null);
    try {
      await api.post<ProfilesInfo>("/profiles/register", {
        name: regName,
        location: regPath,
      });
      await api.put<ProfilesInfo>("/profiles/active", { name: regName });
      setRegMsg(`Registered and activated "${regName.trim().toLowerCase()}".`);
      setRegPath("");
    } catch (e) {
      setRegError(String(e));
    } finally {
      setRegBusy(false);
    }
  };

  const extract = async () => {
    if (!file) return;
    setExtracting(true);
    setImpError(null);
    setImpMsg(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await api.postForm<ExtractResult>("/resume-import/extract", form);
      setDraft(res);
      const id = res.identity ?? {};
      const patch: Partial<Details> = {};
      if (id.name) patch.APPLICANT_NAME = id.name;
      if (id.email) patch.APPLICANT_EMAIL = id.email;
      if (id.phone) patch.APPLICANT_PHONE = id.phone;
      if (id.linkedin) patch.APPLICANT_LINKEDIN = id.linkedin;
      onImportedIdentity(patch);
      const got = Object.keys(patch).length;
      setImpMsg(
        got
          ? `Extracted ${res.highlights.length} highlights and ${res.skills.length} skills; prefilled ${got} of your details (review on the next step).`
          : `Extracted ${res.highlights.length} highlights and ${res.skills.length} skills. No contact details were found in the résumé.`
      );
    } catch (e) {
      setImpError(String(e));
    } finally {
      setExtracting(false);
    }
  };

  const importContent = async () => {
    if (!draft) return;
    setSavingContent(true);
    setImpError(null);
    try {
      await api.post("/resume-import/save", {
        highlights: draft.highlights,
        skills: draft.skills,
        targets: { highlights: "append", skills: "append" },
      });
      setImpMsg("Imported highlights and skills into your active profile.");
      setDraft((d) => (d ? { ...d, highlights: [], skills: [] } : d));
    } catch (e) {
      setImpError(String(e));
    } finally {
      setSavingContent(false);
    }
  };

  const hasContent =
    !!draft && (draft.highlights.length > 0 || draft.skills.length > 0);

  return (
    <div className="space-y-5">
      <p className="text-sm text-gray-600">
        Optional. Point jobjob at an existing profile folder, or bootstrap a new one
        from a résumé. You can also skip this and edit everything later in Settings.
      </p>

      {/* ── Register an existing profile ── */}
      <div className="border border-gray-200 rounded-lg p-4 space-y-2">
        <h3 className="text-sm font-semibold text-gray-900">
          Use an existing profile folder
        </h3>
        <p className="text-xs text-gray-500">
          If you already have a jobjob profile repo on this machine, register it and
          make it active.
        </p>
        <input
          value={regName}
          onChange={(e) => setRegName(e.target.value)}
          placeholder="profile name (e.g. my_profile)"
          className="w-full px-3 py-2 text-sm border border-gray-300 rounded font-mono
            focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <input
          value={regPath}
          onChange={(e) => setRegPath(e.target.value)}
          placeholder="/path/to/your/profile"
          className="w-full px-3 py-2 text-sm border border-gray-300 rounded font-mono
            focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          onClick={register}
          disabled={regBusy || !regName.trim() || !regPath.trim()}
          className="px-3 py-2 text-sm font-medium text-white bg-blue-600 rounded
            hover:bg-blue-700 disabled:opacity-50"
        >
          {regBusy ? "Registering…" : "Register & activate"}
        </button>
        {regMsg && <p className="text-sm text-green-600">{regMsg}</p>}
        {regError && <p className="text-sm text-red-600">{regError}</p>}
      </div>

      {/* ── Bootstrap from a résumé ── */}
      <div className="border border-gray-200 rounded-lg p-4 space-y-2">
        <h3 className="text-sm font-semibold text-gray-900">Bootstrap from a résumé</h3>
        <p className="text-xs text-gray-500">
          Upload a résumé to prefill your contact details and extract reusable
          highlights and skills. Needs an Anthropic key (step 1). Supports{" "}
          {ACCEPT_RESUME}.
        </p>
        <div className="flex flex-wrap items-center gap-3">
          <input
            type="file"
            accept={ACCEPT_RESUME}
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="text-sm"
          />
          <button
            onClick={extract}
            disabled={!file || extracting}
            className="px-3 py-2 text-sm font-medium text-white bg-blue-600 rounded
              hover:bg-blue-700 disabled:opacity-50"
          >
            {extracting ? "Extracting…" : "Extract"}
          </button>
          {hasContent && (
            <button
              onClick={importContent}
              disabled={savingContent}
              className="px-3 py-2 text-sm font-medium text-gray-700 border
                border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50"
            >
              {savingContent ? "Importing…" : "Import highlights & skills"}
            </button>
          )}
        </div>
        {impMsg && <p className="text-sm text-green-600">{impMsg}</p>}
        {impError && <p className="text-sm text-red-600">{impError}</p>}
      </div>
    </div>
  );
}

function DetailsStep({
  form,
  setForm,
  onSaved,
}: {
  form: Details;
  setForm: React.Dispatch<React.SetStateAction<Details>>;
  onSaved: () => void;
}) {
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  const field = (key: keyof Details, label: string, type = "text") => (
    <label className="block text-sm">
      <span className="text-gray-700">{label}</span>
      <input
        type={type}
        value={form[key]}
        onChange={(e) => {
          setForm({ ...form, [key]: e.target.value });
          setSaved(false);
        }}
        className="mt-1 w-full px-3 py-2 text-sm border border-gray-300 rounded
          focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
    </label>
  );

  const save = async () => {
    setBusy(true);
    try {
      const updates = Object.fromEntries(
        Object.entries(form).filter(([, v]) => v.trim())
      );
      await api.put("/config?scope=profile", { updates });
      setSaved(true);
      onSaved();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-3">
      <p className="text-sm text-gray-600">
        These appear on your cover-letter header. You can change them later in Settings.
      </p>
      {field("APPLICANT_NAME", "Name")}
      {field("APPLICANT_EMAIL", "Email", "email")}
      {field("APPLICANT_PHONE", "Phone")}
      {field("APPLICANT_LINKEDIN", "LinkedIn URL")}
      <button
        onClick={save}
        disabled={busy || !form.APPLICANT_NAME.trim()}
        className="px-3 py-2 text-sm font-medium text-white bg-blue-600 rounded
          hover:bg-blue-700 disabled:opacity-50"
      >
        Save details
      </button>
      {saved && <Saved />}
    </div>
  );
}
