import { useEffect, useRef, useState } from "react";

export interface RowAction {
  label: string;
  onClick?: () => void;
  href?: string; // renders as an external link instead of a button
  disabled?: boolean;
  title?: string;
}

// Per-row action dropdown: replaces a strip of buttons that no longer fits
// (Build / Re-build / Apply / ATS / Notes / …). Closes on outside click.
export default function RowActions({ actions }: { actions: RowAction[] }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  return (
    <div className="relative inline-block text-left" ref={ref}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="px-2 py-0.5 text-xs font-medium text-gray-700 border
          border-gray-200 rounded hover:bg-gray-50"
        title="Actions"
      >
        Actions ▾
      </button>
      {open && (
        <div
          className="absolute right-0 mt-1 w-40 bg-white border border-gray-200
            rounded-lg shadow-lg py-1 z-20 text-sm"
        >
          {actions.map((action) =>
            action.href ? (
              <a
                key={action.label}
                href={action.href}
                target="_blank"
                rel="noreferrer"
                onClick={() => setOpen(false)}
                className="block px-3 py-1.5 text-left text-gray-700 hover:bg-gray-50"
                title={action.title}
              >
                {action.label}
              </a>
            ) : (
              <button
                key={action.label}
                onClick={() => {
                  setOpen(false);
                  action.onClick?.();
                }}
                disabled={action.disabled}
                className="w-full px-3 py-1.5 text-left text-gray-700 hover:bg-gray-50
                  disabled:text-gray-300 disabled:cursor-not-allowed disabled:hover:bg-white"
                title={action.title}
              >
                {action.label}
              </button>
            )
          )}
        </div>
      )}
    </div>
  );
}
