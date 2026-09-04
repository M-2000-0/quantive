import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';

export interface DemoUser {
  id: string;
  email: string;
  name: string;
  role: string;
  org_id: string;
}

interface DemoModeValue {
  isDemoMode: boolean;
  demoUser: DemoUser;
  enterDemoMode: () => void;
  exitDemoMode: () => void;
}

const DEMO_KEY = 'demo_mode';

const DEFAULT_DEMO_USER: DemoUser = {
  id: 'demo-user-001',
  email: 'demo@quantive.gov',
  name: 'Demo User',
  role: 'admin',
  org_id: 'demo-org',
};

const DemoModeContext = createContext<DemoModeValue | null>(null);

function readDemoMode(): boolean {
  try {
    return localStorage.getItem(DEMO_KEY) === 'true';
  } catch {
    return false;
  }
}

export function DemoModeProvider({ children }: { children: ReactNode }) {
  const [isDemoMode, setIsDemoMode] = useState<boolean>(() => readDemoMode());

  useEffect(() => {
    try {
      localStorage.setItem(DEMO_KEY, isDemoMode ? 'true' : 'false');
      if (isDemoMode && !localStorage.getItem('user')) {
        localStorage.setItem('user', JSON.stringify(DEFAULT_DEMO_USER));
      }
    } catch {
      /* storage unavailable — demo mode stays in memory only */
    }
  }, [isDemoMode]);

  const enterDemoMode = useCallback(() => setIsDemoMode(true), []);
  const exitDemoMode = useCallback(() => {
    setIsDemoMode(false);
    try {
      localStorage.removeItem(DEMO_KEY);
    } catch {
      /* noop */
    }
  }, []);

  return (
    <DemoModeContext.Provider
      value={{ isDemoMode, demoUser: DEFAULT_DEMO_USER, enterDemoMode, exitDemoMode }}
    >
      {children}
    </DemoModeContext.Provider>
  );
}

export function useDemoMode(): DemoModeValue {
  const ctx = useContext(DemoModeContext);
  if (!ctx) throw new Error('useDemoMode must be used within DemoModeProvider');
  return ctx;
}
