import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { SetupStatus } from "../types";

/**
 * First-run setup wizard. Walks the user through the Anthropic key, optional
 * Google connection, and applicant identity. Auto-opened by the app shell when
 * setup is incomplete and not dismissed; also re-openable from the account menu.
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

  const refresh = () =>
    api
      .get<SetupStatus>("/setup/status")
      .then(setStatus)
      .catch(() => {});

  useEffect(() => {
    refresh();
  }, []);

  const steps = ["Anthropic key", "Google (optional)", "Your details"];

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
          {step === 2 && <DetailsStep onSaved={refresh} />}
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
          href="https://github.com/inquisitive-village-idiot/jobjob/blob/main/docs/credentials-setup.md"
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

function DetailsStep({ onSaved }: { onSaved: () => void }) {
  const [form, setForm] = useState({
    APPLICANT_NAME: "",
    APPLICANT_EMAIL: "",
    APPLICANT_PHONE: "",
    APPLICANT_LINKEDIN: "",
  });
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  const field = (key: keyof typeof form, label: string, type = "text") => (
    <label className="block text-sm">
      <span className="text-gray-700">{label}</span>
      <input
        type={type}
        value={form[key]}
        onChange={(e) => setForm({ ...form, [key]: e.target.value })}
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
