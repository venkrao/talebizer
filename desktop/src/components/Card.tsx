import type { ReactNode } from "react";

export function Card({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-lg border border-zinc-800 bg-zinc-900/60 p-4 shadow-sm">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-400">
        {title}
      </h2>
      <div className="space-y-2 text-sm text-zinc-200">{children}</div>
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
    <div className="flex flex-wrap gap-x-2 gap-y-1 border-b border-zinc-800/80 py-1.5 last:border-0">
      <span className="min-w-[8rem] text-zinc-500">{label}</span>
      <span className="break-all font-mono text-xs text-zinc-100">{value}</span>
    </div>
  );
}
