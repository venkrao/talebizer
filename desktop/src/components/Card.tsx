import type { ReactNode } from "react";

export function Card({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900/60">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
        {title}
      </h2>
      <div className="space-y-2 text-sm text-zinc-800 dark:text-zinc-200">{children}</div>
    </section>
  );
}

export function Row({
  label,
  value,
}: {
  label: string;
  value: ReactNode;
}) {
  return (
    <div className="flex flex-wrap gap-x-2 gap-y-1 border-b border-zinc-200 py-1.5 last:border-0 dark:border-zinc-800/80">
      <span className="min-w-[8rem] text-zinc-500 dark:text-zinc-500">{label}</span>
      <span className="break-all font-mono text-xs text-zinc-900 dark:text-zinc-100">
        {value}
      </span>
    </div>
  );
}
