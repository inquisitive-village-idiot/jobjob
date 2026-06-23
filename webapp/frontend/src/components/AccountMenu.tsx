import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { ProfilesInfo } from "../types";

/**
 * Top-right account/profile menu: shows the active profile, switches between
 * registered profiles, and links to Settings (app + profile config).
 */
export default function AccountMenu({
  onSettings,
  onSetup,
}: {
  onSettings: () => void;
  onSetup?: () => void;
}) {
  const [info, setInfo] = useState<ProfilesInfo | null>(null);
  const [open, setOpen] = useState(false);
  const [switching, setSwitching] = useState<string | null>(null);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api
      .get<ProfilesInfo>("/profiles")
      .then(setInfo)
      .catch(() => setInfo(null));
  }, []);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const switchTo = async (name: string) => {
    if (name === info?.active) return setOpen(false);
    setSwitching(name);
    try {
      await api.put<ProfilesInfo>("/profiles/active", { name });
      // A switch changes content, applicant identity, and template across the
      // app — reload so every page reflects the new profile.
      window.location.reload();
    } catch {
      setSwitching(null);
    }
  };

  const active = info?.active ?? "—";

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded text-sm font-medium
          text-gray-600 hover:bg-gray-100"
        title="Profile and settings"
      >
        <span
          className="inline-flex items-center justify-center w-5 h-5 rounded-full
          bg-blue-600 text-white text-xs font-semibold"
        >
          {active.charAt(0).toUpperCase()}
        </span>
        <span className="capitalize">{active}</span>
        <svg className="w-3 h-3 text-gray-400" viewBox="0 0 20 20" fill="currentColor">
          <path d="M5.5 7.5L10 12l4.5-4.5z" />
        </svg>
      </button>

      {open && (
        <div
          className="absolute right-0 mt-1 w-56 bg-white border border-gray-200 rounded-lg
          shadow-lg py-1 z-20 text-sm"
        >
          <div className="px-3 py-1.5 text-xs font-semibold text-gray-400 uppercase tracking-wide">
            Profiles
          </div>
          {(info?.profiles ?? []).map((name) => (
            <button
              key={name}
              onClick={() => switchTo(name)}
              disabled={switching !== null}
              className="w-full flex items-center justify-between px-3 py-1.5 text-left
                hover:bg-gray-50 capitalize disabled:opacity-50"
            >
              <span>{name}</span>
              {name === info?.active && <span className="text-blue-600">✓</span>}
              {switching === name && <span className="text-gray-400">…</span>}
            </button>
          ))}
          <div className="my-1 border-t border-gray-100" />
          <button
            onClick={() => {
              setOpen(false);
              onSettings();
            }}
            className="w-full px-3 py-1.5 text-left hover:bg-gray-50"
          >
            Settings
          </button>
          {onSetup && (
            <button
              onClick={() => {
                setOpen(false);
                onSetup();
              }}
              className="w-full px-3 py-1.5 text-left hover:bg-gray-50"
            >
              Run setup
            </button>
          )}
        </div>
      )}
    </div>
  );
}
