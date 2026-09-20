import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';

interface DemoModeContextType {
  isDemoMode: boolean;
  enableDemoMode: () => void;
  disableDemoMode: () => void;
}

const DemoModeContext = createContext<DemoModeContextType>({
  isDemoMode: false,
  enableDemoMode: () => {},
  disableDemoMode: () => {},
});

export function useDemoMode() {
  return useContext(DemoModeContext);
}

export function DemoModeProvider({ children }: { children: ReactNode }) {
  const [isDemoMode, setIsDemoMode] = useState(() => {
    return localStorage.getItem('quantive_demo_mode') === 'true';
  });

  useEffect(() => {
    localStorage.setItem('quantive_demo_mode', String(isDemoMode));
  }, [isDemoMode]);

  return (
    <DemoModeContext.Provider
      value={{
        isDemoMode,
        enableDemoMode: () => setIsDemoMode(true),
        disableDemoMode: () => setIsDemoMode(false),
      }}
    >
      {children}
    </DemoModeContext.Provider>
  );
}
