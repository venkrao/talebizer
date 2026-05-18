import type { ReactNode } from "react";

/** Expand/collapse panel — same pattern as `ConcentrationHeatmap` (`<details>`). */
export function CollapsibleSection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-lg border border-zinc-800 bg-zinc-900/60 p-4 shadow-sm">
      <details className="group">
        <summary className="cursor-pointer list-none text-sm font-semibold text-zinc-200 [&::-webkit-details-marker]:hidden">
          <span className="mr-2 inline-block text-zinc-500 transition-transform group-open:rotate-90">
            ▸
          </span>
          {title}
        </summary>
        <div className="mt-4 border-t border-zinc-800/80 pt-4">{children}</div>
      </details>
    </section>
  );
}
