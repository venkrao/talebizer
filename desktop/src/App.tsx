import { useState } from "react";
import { PortfolioView } from "./components/PortfolioView";
import { SystemSettingsView } from "./components/SystemSettingsView";

type Screen = "portfolio" | "system";

export function App() {
  const [screen, setScreen] = useState<Screen>("portfolio");

  const tabBtn = (id: Screen, label: string) => (
    <button
      type="button"
      onClick={() => setScreen(id)}
      className={`rounded-md px-3 py-2 text-sm font-medium transition-colors ${
        screen === id
          ? "bg-emerald-900/50 text-emerald-100 ring-1 ring-emerald-700/60"
          : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
      }`}
    >
      {label}
    </button>
  );

  return (
    <div className="min-h-screen bg-zinc-950">
      <div className="border-b border-zinc-800 bg-zinc-950/95 backdrop-blur-sm">
        <div className="flex w-full flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6 lg:px-8">
          <span className="text-sm font-semibold text-zinc-300">Talebizer</span>
          <nav className="flex gap-1" aria-label="Primary">
            {tabBtn("portfolio", "Portfolio")}
            {tabBtn("system", "System")}
          </nav>
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
