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
    <section className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900/60">
      <details className="group">
        <summary className="cursor-pointer list-none text-sm font-semibold text-zinc-800 [&::-webkit-details-marker]:hidden dark:text-zinc-200">
          <span className="mr-2 inline-block text-zinc-400 transition-transform group-open:rotate-90 dark:text-zinc-500">
            ▸
          </span>
          {title}
        </summary>
        <div className="mt-4 border-t border-zinc-200/90 pt-4 dark:border-zinc-800/80">
          {children}
        </div>
      </details>
    </section>
  );
}
