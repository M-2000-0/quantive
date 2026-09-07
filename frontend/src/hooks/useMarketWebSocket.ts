// ── useMarketWebSocket Hook ───────────────────────────────────────────
// React hook for managing WebSocket market data subscriptions.
// Handles connection lifecycle, auto-reconnect, and cleanup.

import { useState, useEffect, useCallback, useRef } from 'react';
import { getMarketWebSocket, type WebSocketMarketUpdate } from '../lib/marketWebSocket';

interface UseMarketWebSocketOptions {
  /** Tickers to subscribe to */
  tickers: string[];
  /** Whether to auto-connect on mount (default: true) */
  autoConnect?: boolean;
}

interface UseMarketWebSocketResult {
  /** Current prices by ticker */
  prices: Map<string, WebSocketMarketUpdate>;
  /** Connection status */
  status: 'connecting' | 'connected' | 'disconnected' | 'error';
  /** Whether the WebSocket is connected */
  isConnected: boolean;
  /** Connect to the WebSocket */
  connect: () => void;
  /** Disconnect from the WebSocket */
  disconnect: () => void;
  /** Get price for a specific ticker */
  getPrice: (ticker: string) => WebSocketMarketUpdate | null;
}

export function useMarketWebSocket(
  options: UseMarketWebSocketOptions
): UseMarketWebSocketResult {
  const { tickers, autoConnect = true } = options;
  const [prices, setPrices] = useState<Map<string, WebSocketMarketUpdate>>(new Map());
  const [status, setStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
  const unsubscribersRef = useRef<Array<() => void>>([]);

  const ws = getMarketWebSocket();

  const connect = useCallback(() => {
    ws.connect();
  }, [ws]);

  const disconnect = useCallback(() => {
    ws.disconnect();
  }, [ws]);

  const getPrice = useCallback(
    (ticker: string) => prices.get(ticker) || null,
    [prices]
  );

  // Subscribe to tickers and status changes (single effect to avoid double-subscription)
  useEffect(() => {
    if (!autoConnect) return;

    // Connect
    ws.connect();

    // Subscribe to status changes
    const unsubStatus = ws.onStatusChange(setStatus);

    // Subscribe to tickers
    const unsubTickers = ws.subscribeMultiple(tickers, (update) => {
      setPrices((prev) => {
        const next = new Map(prev);
        next.set(update.ticker, update);
        return next;
      });
    });

    unsubscribersRef.current = [unsubStatus, unsubTickers];

    return () => {
      unsubscribersRef.current.forEach((unsub) => unsub());
      unsubscribersRef.current = [];
    };
  }, [autoConnect, tickers, ws]);

  return {
    prices,
    status,
    isConnected: status === 'connected',
    connect,
    disconnect,
    getPrice,
  };
}

/**
 * Hook for getting a single ticker's price from the WebSocket.
 */
export function useTickerPrice(ticker: string): {
  price: WebSocketMarketUpdate | null;
  isConnected: boolean;
} {
  const { prices, isConnected } = useMarketWebSocket({
    tickers: [ticker],
  });

  return {
    price: prices.get(ticker) || null,
    isConnected,
  };
}
