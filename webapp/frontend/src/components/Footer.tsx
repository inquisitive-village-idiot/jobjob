const ISSUES_URL = "https://github.com/inquisitive-village-idiot/jobjob/issues";

/**
 * Site footer: copyright line and a link to report an issue on GitHub. Rendered
 * once at the bottom of the app shell, below the routed page content.
 */
export default function Footer() {
  return (
    <footer className="border-t border-gray-200 mt-8">
      <div
        className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between
          text-xs text-gray-500"
      >
        <span>© inquisitive-village-idiot</span>
        <a
          href={ISSUES_URL}
          target="_blank"
          rel="noreferrer"
          className="hover:text-blue-600"
        >
          Report an issue
        </a>
      </div>
    </footer>
  );
}
