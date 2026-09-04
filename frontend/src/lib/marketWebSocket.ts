// ── Market WebSocket Service ──────────────────────────────────────────
// Connects to Yahoo Finance streaming for real-time stock prices.
// Features: auto-reconnect, exponential backoff, subscription management.

import { validatePriceUpdate } from './marketValidation';
import { setCache } from './marketCache';

export interface WebSocketMarketUpdate {
  ticker: string;
  price: number;
  previousPrice: number;
  change: number;
  changePercent: number;
  volume: number;
  timestamp: number;
}

type UpdateCallback = (update: WebSocketMarketUpdate) => void;
type StatusCallback = (status: 'connecting' | 'connected' | 'disconnected' | 'error') => void;

class MarketWebSocket {
  private ws: WebSocket | null = null;
  private subscriptions = new Map<string, Set<UpdateCallback>>();
  private statusListeners = new Set<StatusCallback>();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private pingTimer: ReturnType<typeof setInterval> | null = null;
  private lastPrices = new Map<string, number>();
  private url: string;
  private isIntentionalClose = false;

  constructor(url: string = 'wss://streamer.finance.yahoo.com/v1/quote') {
    this.url = url;
  }

  /**
   * Connect to the WebSocket server.
   */
  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    this.isIntentionalClose = false;
    this.notifyStatus('connecting');

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.info('[MarketWS] Connected');
        this.reconnectAttempts = 0;
        this.notifyStatus('connected');
        this.startPing();

        // Re-subscribe to all active tickers
        const tickers = Array.from(this.subscriptions.keys());
        if (tickers.length > 0) {
          this.sendSubscribe(tickers);
        }
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleMessage(data);
        } catch {
          // Skip malformed messages
        }
      };

      this.ws.onclose = (event) => {
        console.info(`[MarketWS] Disconnected (code: ${event.code})`);
        this.stopPing();
        this.notifyStatus('disconnected');

        if (!this.isIntentionalClose) {
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = (error) => {
        console.error('[MarketWS] Error:', error);
        this.notifyStatus('error');
      };
    } catch (err) {
      console.error('[MarketWS] Connection failed:', err);
      this.notifyStatus('error');
      this.scheduleReconnect();
    }
  }

  /**
   * Subscribe to price updates for a specific ticker.
   * Returns an unsubscribe function.
   */
  subscribe(ticker: string, callback: UpdateCallback): () => void {
    if (!this.subscriptions.has(ticker)) {
      this.subscriptions.set(ticker, new Set());
      // Send subscribe message if connected
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.sendSubscribe([ticker]);
      }
    }
    this.subscriptions.get(ticker)!.add(callback);

    return () => {
      const callbacks = this.subscriptions.get(ticker);
      callbacks?.delete(callback);
      if (callbacks?.size === 0) {
        this.subscriptions.delete(ticker);
        // Send unsubscribe message
        if (this.ws?.readyState === WebSocket.OPEN) {
          this.sendUnsubscribe([ticker]);
        }
      }
    };
  }

  /**
   * Subscribe to status changes.
   */
  onStatusChange(callback: StatusCallback): () => void {
    this.statusListeners.add(callback);
    return () => this.statusListeners.delete(callback);
  }

  /**
   * Subscribe to multiple tickers at once.
   */
  subscribeMultiple(
    tickers: string[],
    callback: UpdateCallback
  ): () => void {
    const unsubscribers = tickers.map((t) => this.subscribe(t, callback));
    return () => unsubscribers.forEach((unsub) => unsub());
  }

  /**
   * Disconnect from the WebSocket server.
   */
  disconnect(): void {
    this.isIntentionalClose = true;
    this.stopPing();
    clearTimeout(this.reconnectTimer);
    this.reconnectAttempts = 0;

    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }
    this.notifyStatus('disconnected');
  }

  /**
   * Get connection status.
   */
  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * Get the number of active subscriptions.
   */
  get subscriptionCount(): number {
    return this.subscriptions.size;
  }

  // ── Private Methods ──────────────────────────────────────────────

  private handleMessage(data: Record<string, unknown>): void {
    // Yahoo Finance streaming format
    const quote = data.quote || data;
    const ticker = (quote.symbol || quote.ticker) as string;
    const price = (quote.price || quote.regularMarketPrice || quote.p) as number;

    if (!ticker || !price || !isFinite(price)) return;

    const previousPrice = this.lastPrices.get(ticker) || price;
    this.lastPrices.set(ticker, price);

    // Anomaly detection: reject crazy price jumps
    const validation = validatePriceUpdate(previousPrice, price, 10);
    if (!validation.valid) {
      console.warn(`[MarketWS] Rejected update for ${ticker}: ${validation.reason}`);
      return;
    }

    const update: WebSocketMarketUpdate = {
      ticker,
      price,
      previousPrice,
      change: price - previousPrice,
      changePercent: previousPrice > 0 ? ((price - previousPrice) / previousPrice) * 100 : 0,
      volume: (quote.volume || quote.regularMarketVolume || 0) as number,
      timestamp: Date.now(),
    };

    // Notify subscribers
    const callbacks = this.subscriptions.get(ticker);
    callbacks?.forEach((cb) => cb(update));

    // Also notify wildcard subscribers
    const wildcardCallbacks = this.subscriptions.get('*');
    wildcardCallbacks?.forEach((cb) => cb(update));

    // Cache the update
    setCache(`ws_quote_${ticker}`, update, 30000);
  }

  private sendSubscribe(tickers: string[]): void {
    if (this.ws?.readyState !== WebSocket.OPEN) return;

    const message = JSON.stringify({
      subscribe: tickers,
    });
    this.ws.send(message);
    console.info(`[MarketWS] Subscribed to: ${tickers.join(', ')}`);
  }

  private sendUnsubscribe(tickers: string[]): void {
    if (this.ws?.readyState !== WebSocket.OPEN) return;

    const message = JSON.stringify({
      unsubscribe: tickers,
    });
    this.ws.send(message);
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[MarketWS] Max reconnect attempts reached');
      this.notifyStatus('error');
      return;
    }

    // Exponential backoff: 1s, 2s, 4s, 8s, ... capped at 30s
    const delay = Math.min(30000, 1000 * Math.pow(2, this.reconnectAttempts));
    this.reconnectAttempts++;

    console.info(`[MarketWS] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
    this.reconnectTimer = setTimeout(() => this.connect(), delay);
  }

  private startPing(): void {
    this.pingTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ ping: true }));
      }
    }, 25000);
  }

  private stopPing(): void {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }

  private notifyStatus(status: 'connecting' | 'connected' | 'disconnected' | 'error'): void {
    this.statusListeners.forEach((cb) => cb(status));
  }
}

// ── Singleton Instance ────────────────────────────────────────────────

let instance: MarketWebSocket | null = null;

export function getMarketWebSocket(): MarketWebSocket {
  if (!instance) {
    instance = new MarketWebSocket();
  }
  return instance;
}

/**
 * Convenience hook-style function for React components.
 * Returns subscribe/unsubscribe functions and connection status.
 */
export function createMarketStream() {
  const ws = getMarketWebSocket();

  return {
    connect: () => ws.connect(),
    disconnect: () => ws.disconnect(),
    subscribe: (ticker: string, callback: UpdateCallback) => ws.subscribe(ticker, callback),
    subscribeMultiple: (tickers: string[], callback: UpdateCallback) => ws.subscribeMultiple(tickers, callback),
    onStatusChange: (callback: StatusCallback) => ws.onStatusChange(callback),
    get isConnected() { return ws.isConnected; },
    get subscriptionCount() { return ws.subscriptionCount; },
  };
}
