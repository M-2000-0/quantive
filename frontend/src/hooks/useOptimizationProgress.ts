/**
 * Hook for tracking real-time optimization progress via WebSocket.
 *
 * Usage:
 *   const { progress, status, message, strategies } = useOptimizationProgress(optimizationId, userId);
 */
import { useEffect, useState } from 'react';
import { useWebSocket } from './useWebSocket';

interface OptimizationProgress {
  progress: number;
  status: string;
  message: string;
  result: {
    strategies?: number;
    feasible?: boolean;
    best_cost?: number;
  } | null;
}

export function useOptimizationProgress(
  optimizationId: string | undefined,
  userId: string | undefined,
): OptimizationProgress & { connected: boolean } {
  const { connected, subscribe } = useWebSocket(userId);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('idle');
  const [message, setMessage] = useState('');
  const [result, setResult] = useState<OptimizationProgress['result']>(null);

  useEffect(() => {
    if (!optimizationId) return;

    const unsubscribe = subscribe(`optimization:${optimizationId}`, (msg) => {
      if (msg.type === 'optimization_progress' && msg.optimization_id === optimizationId) {
        setProgress(msg.progress as number);
        setStatus(msg.status as string);
        setMessage((msg.message as string) || '');
        if (msg.result) {
          setResult(msg.result as OptimizationProgress['result']);
        }
      }
    });

    return unsubscribe;
  }, [optimizationId, subscribe]);

  return { progress, status, message, result, connected };
}
