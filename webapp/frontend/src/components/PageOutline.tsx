import { useEffect, useState } from "react";
import type { ReactNode } from "react";

export interface OutlineItem {
  id: string;
  label: string;
  indent?: boolean;
}

const scrollTo = (id: string) =>
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });

// Scroll-spy: returns the id of the first observed section currently in view.
// `deps` re-registers the observer when the set of section ids changes.
export function useScrollSpy(ids: string[], deps: unknown[]): string {
  const [activeId, setActiveId] = useState(ids[0] ?? "");
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]) setActiveId(visible[0].target.id);
      },
      { rootMargin: "-64px 0px -55% 0px", threshold: 0 }
    );
    ids.forEach((id) => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return activeId;
}

// A section header with a subtle rule, so section boundaries (e.g. "Items",
// "Google") are easy to scan.
export function SectionHeader({ children }: { children: ReactNode }) {
  return (
    <h3
      className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3 pb-1.5
      border-b border-gray-200"
    >
      {children}
    </h3>
  );
}

// An outline that floats in the left margin. It must be the first child of a
// `relative` wrapper around the page's content area (below the title/tabs): it
// anchors to the top of that area — lined up with the start of the content — and
// sticks just under the header as the page scrolls. Hidden below `xl`, where the
// margin is too narrow to hold it without crowding the content. Nested entries
// (indent) render one level in.
export function FloatingOutline({
  items,
  activeId,
  onSelect = scrollTo,
}: {
  items: OutlineItem[];
  activeId: string;
  onSelect?: (id: string) => void;
}) {
  if (items.length === 0) return null;
  return (
    <nav
      className="hidden xl:block absolute right-full inset-y-0 mr-6 w-44"
      aria-label="Section outline"
    >
      <ul className="sticky top-16 space-y-0.5 max-h-[80vh] overflow-y-auto pr-1">
        {items.map((it) => (
          <li key={it.id}>
            <button
              onClick={() => onSelect(it.id)}
              title={it.label}
              className={`block w-full text-left ${
                it.indent ? "pl-5 pr-2" : "px-3"
              } py-1 text-sm rounded border-l-2 transition-colors truncate ${
                activeId === it.id
                  ? "border-blue-600 text-blue-600 font-medium bg-blue-50"
                  : "border-transparent text-gray-500 hover:text-gray-800 hover:bg-gray-50"
              }`}
            >
              {it.label}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}
