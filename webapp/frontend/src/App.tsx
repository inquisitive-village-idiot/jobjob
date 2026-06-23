import { useEffect, useState } from "react";
import DashboardPage from "./pages/DashboardPage";
import QueuePage from "./pages/QueuePage";
import ConfigPage from "./pages/ConfigPage";
import StaticContentPage from "./pages/StaticContentPage";
import PromptsPage from "./pages/PromptsPage";
import AccountMenu from "./components/AccountMenu";
import SetupWizard from "./components/SetupWizard";
import { api } from "./api/client";
import type { SetupStatus } from "./types";

type Page = "dashboard" | "queue" | "config" | "static" | "prompts";

// Config is reached via the account menu (Settings), not the main nav.
const NAV: { id: Page; label: string }[] = [
  { id: "dashboard", label: "Dashboard" },
  { id: "queue", label: "Queue" },
  { id: "static", label: "Static Content" },
  { id: "prompts", label: "Prompts" },
];
const PAGES: Page[] = ["dashboard", "queue", "static", "prompts", "config"];

function pageFromHash(hash: string): Page {
  const id = hash.replace("#", "") as Page;
  return PAGES.includes(id) ? id : "dashboard";
}

export default function App() {
  const [page, setPage] = useState<Page>(() => pageFromHash(window.location.hash));
  const [showWizard, setShowWizard] = useState(false);

  useEffect(() => {
    const handler = () => setPage(pageFromHash(window.location.hash));
    window.addEventListener("hashchange", handler);
    return () => window.removeEventListener("hashchange", handler);
  }, []);

  // Auto-open the setup wizard on first run (incomplete + not dismissed).
  useEffect(() => {
    api
      .get<SetupStatus>("/setup/status")
      .then((s) => {
        if (!s.complete && !s.dismissed) setShowWizard(true);
      })
      .catch(() => {});
  }, []);

  const navigate = (id: Page, e: React.MouseEvent<HTMLAnchorElement>) => {
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
    e.preventDefault();
    window.location.hash = id;
    setPage(id);
  };

  const goToConfig = () => {
    window.location.hash = "config";
    setPage("config");
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-6 flex items-center gap-6 h-12">
          <a
            href="#dashboard"
            onClick={(e) => navigate("dashboard", e)}
            className="font-semibold text-gray-900 text-sm tracking-tight hover:text-blue-600"
          >
            jobjob
          </a>
          <nav className="flex gap-1">
            {NAV.map(({ id, label }) => (
              <a
                key={id}
                href={`#${id}`}
                onClick={(e) => navigate(id, e)}
                className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                  page === id
                    ? "bg-blue-600 text-white"
                    : "text-gray-600 hover:bg-gray-100"
                }`}
              >
                {label}
              </a>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-1">
            <button
              type="button"
              onClick={goToConfig}
              aria-label="Settings"
              title="Settings"
              className={`p-1.5 rounded transition-colors ${
                page === "config"
                  ? "bg-blue-600 text-white"
                  : "text-gray-600 hover:bg-gray-100"
              }`}
            >
              <svg
                className="w-4 h-4"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="12" cy="12" r="3" />
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
              </svg>
            </button>
            <AccountMenu onSettings={goToConfig} onSetup={() => setShowWizard(true)} />
          </div>
        </div>
      </header>

      <main className="py-6">
        {page === "dashboard" && <DashboardPage />}
        {page === "queue" && <QueuePage />}
        {page === "config" && <ConfigPage />}
        {page === "static" && <StaticContentPage />}
        {page === "prompts" && <PromptsPage />}
      </main>

      {showWizard && (
        <SetupWizard
          onClose={() => setShowWizard(false)}
          onDone={() => setShowWizard(false)}
        />
      )}
    </div>
  );
}
