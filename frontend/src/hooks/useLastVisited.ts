import { useState, useEffect, useCallback } from 'react';

const STORAGE_KEY = 'quantive_last_visited';
const MAX_ITEMS = 5;

export function useLastVisited() {
  const [lastVisited, setLastVisited] = useState<string[]>(() => {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    } catch {
      return [];
    }
  });

  const addVisit = useCallback((path: string) => {
    setLastVisited(prev => {
      const updated = [path, ...prev.filter(p => p !== path)].slice(0, MAX_ITEMS);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
      return updated;
    });
  }, []);

  const isRecentlyVisited = useCallback((path: string) => {
    return lastVisited.includes(path);
  }, [lastVisited]);

  return { lastVisited, addVisit, isRecentlyVisited };
}
