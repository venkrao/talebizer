import { useState } from "react";
import { PortfolioView } from "./components/PortfolioView";
import { SystemSettingsView } from "./components/SystemSettingsView";
import { ThemeToggle } from "./components/ThemeToggle";

type Screen = "portfolio" | "system";

export function App() {
  const [screen, setScreen] = useState<Screen>("portfolio");

  const tabBtn = (id: Screen, label: string) => (
    <button
      type="button"
      onClick={() => setScreen(id)}
      className={`rounded-md px-3 py-2 text-sm font-medium transition-colors ${
        screen === id
          ? "bg-emerald-600 text-white ring-1 ring-emerald-700/50 dark:bg-emerald-900/50 dark:text-emerald-100 dark:ring-emerald-700/60"
          : "text-zinc-600 hover:bg-zinc-200 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
      }`}
    >
      {label}
    </button>
  );

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950">
      <div className="border-b border-zinc-200 bg-white/90 backdrop-blur-sm dark:border-zinc-800 dark:bg-zinc-950/95">
        <div className="flex w-full flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6 lg:px-8">
          <span className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">
            Talebizer
          </span>
          <div className="flex flex-wrap items-center gap-3">
            <ThemeToggle />
            <nav className="flex gap-1" aria-label="Primary">
              {tabBtn("portfolio", "Portfolio")}
              {tabBtn("system", "System")}
            </nav>
          </div>
        </div>
      </div>

      <div className={screen !== "portfolio" ? "hidden" : undefined}>
        <PortfolioView />
      </div>
      <div className={screen !== "system" ? "hidden" : undefined}>
        <SystemSettingsView active={screen === "system"} />
      </div>
    </div>
  );
}
