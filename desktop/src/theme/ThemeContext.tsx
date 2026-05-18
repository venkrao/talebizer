import {
  createContext,
  useCallback,
  useContext,
  useLayoutEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type ThemePreference = "dark" | "light";

const STORAGE_KEY = "talebizer-theme";

function systemPrefersDark(): boolean {
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

/** Reads stored theme; migrates legacy `"system"` to explicit dark/light. */
function readStoredPreference(): ThemePreference {
  try {
    const s = localStorage.getItem(STORAGE_KEY);
    if (s === "dark" || s === "light") return s;
    if (s === "system") {
      const next = systemPrefersDark() ? "dark" : "light";
      localStorage.setItem(STORAGE_KEY, next);
      return next;
    }
  } catch {
    /* ignore */
  }
  return "dark";
}

/** Keep in sync with `index.html` inline script. */
export function applyThemeClass(isDark: boolean) {
  const root = document.documentElement;
  if (isDark) root.classList.add("dark");
  else root.classList.remove("dark");
}

const ThemeContext = createContext<{
  preference: ThemePreference;
  /** Alias for chart palettes — always matches `preference`. */
  resolved: ThemePreference;
  toggleTheme: () => void;
} | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [preference, setPreferenceState] = useState<ThemePreference>(() =>
    readStoredPreference(),
  );

  const resolved = preference;

  useLayoutEffect(() => {
    applyThemeClass(resolved === "dark");
  }, [resolved]);

  const toggleTheme = useCallback(() => {
    setPreferenceState((prev) => {
      const next = prev === "dark" ? "light" : "dark";
      try {
        localStorage.setItem(STORAGE_KEY, next);
      } catch {
        /* ignore */
      }
      applyThemeClass(next === "dark");
      return next;
    });
  }, []);

  const value = useMemo(
    () => ({ preference, resolved, toggleTheme }),
    [preference, resolved, toggleTheme],
  );

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error("useTheme must be used within ThemeProvider");
  }
  return ctx;
}
