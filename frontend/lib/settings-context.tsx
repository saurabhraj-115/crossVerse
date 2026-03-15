'use client';

import { createContext, useContext, useState, type ReactNode } from 'react';
import { ALL_RELIGIONS, type Religion } from './types';

interface Settings {
  globalReligions: Religion[];
  setGlobalReligions: (r: Religion[]) => void;
}

const SettingsContext = createContext<Settings>({
  globalReligions: ALL_RELIGIONS,
  setGlobalReligions: () => {},
});

function readFromStorage(): Religion[] {
  if (typeof window === 'undefined') return ALL_RELIGIONS;
  try {
    const raw = localStorage.getItem('cv_religions');
    if (raw) {
      const parsed: unknown = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length > 0) return parsed as Religion[];
    }
  } catch {
    // ignore
  }
  return ALL_RELIGIONS;
}

export function SettingsProvider({ children }: { children: ReactNode }) {
  // Lazy initializer: reads localStorage synchronously — safe because this is a 'use client' component
  const [globalReligions, setGlobalReligionsState] = useState<Religion[]>(readFromStorage);

  const setGlobalReligions = (r: Religion[]) => {
    const next = r.length === 0 ? ALL_RELIGIONS : r;
    setGlobalReligionsState(next);
    try {
      localStorage.setItem('cv_religions', JSON.stringify(next));
    } catch {
      // ignore
    }
  };

  return (
    <SettingsContext.Provider value={{ globalReligions, setGlobalReligions }}>
      {children}
    </SettingsContext.Provider>
  );
}

export const useSettings = () => useContext(SettingsContext);
