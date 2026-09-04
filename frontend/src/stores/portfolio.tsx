import { useState, useEffect, useCallback, createContext, useContext } from 'react';
import type { Portfolio } from '../types';
import { api } from '../api';

interface PortfolioState {
  portfolios: Portfolio[];
  selectedPortfolio: Portfolio | null;
  recentPortfolios: Portfolio[];
  loading: boolean;
  error: string | null;
  selectPortfolio: (id: string) => void;
  clearSelection: () => void;
  refresh: () => Promise<void>;
}

const PortfolioContext = createContext<PortfolioState | null>(null);

const RECENT_KEY = 'quantive_recent_portfolios';
const SELECTED_KEY = 'quantive_selected_portfolio';

function loadRecent(): string[] {
  try {
    return JSON.parse(localStorage.getItem(RECENT_KEY) || '[]');
  } catch { return []; }
}

function saveRecent(ids: string[]) {
  localStorage.setItem(RECENT_KEY, JSON.stringify(ids.slice(0, 10)));
}

export function PortfolioProvider({ children }: { children: React.ReactNode }) {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [selectedPortfolio, setSelectedPortfolio] = useState<Portfolio | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [recentIds, setRecentIds] = useState<string[]>(loadRecent);

  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.portfolios.list();
      setPortfolios(data as Portfolio[]);

      // Restore selected portfolio from localStorage
      const savedId = localStorage.getItem(SELECTED_KEY);
      if (savedId) {
        const found = (data as Portfolio[]).find(p => p.id === savedId);
        if (found) setSelectedPortfolio(found);
      }

      // Restore recent portfolios
      const recent = loadRecent();
      setRecentIds(recent);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load portfolios');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const selectPortfolio = useCallback((id: string) => {
    const found = portfolios.find(p => p.id === id);
    if (found) {
      setSelectedPortfolio(found);
      localStorage.setItem(SELECTED_KEY, id);

      // Update recents
      const newRecent = [id, ...recentIds.filter(r => r !== id)].slice(0, 10);
      setRecentIds(newRecent);
      saveRecent(newRecent);
    }
  }, [portfolios, recentIds]);

  const clearSelection = useCallback(() => {
    setSelectedPortfolio(null);
    localStorage.removeItem(SELECTED_KEY);
  }, []);

  const recentPortfolios = recentIds
    .map(id => portfolios.find(p => p.id === id))
    .filter(Boolean) as Portfolio[];

  return (
    <PortfolioContext.Provider value={{
      portfolios,
      selectedPortfolio,
      recentPortfolios,
      loading,
      error,
      selectPortfolio,
      clearSelection,
      refresh,
    }}>
      {children}
    </PortfolioContext.Provider>
  );
}

export function usePortfolios() {
  const ctx = useContext(PortfolioContext);
  if (!ctx) throw new Error('usePortfolios must be used within PortfolioProvider');
  return ctx;
}
