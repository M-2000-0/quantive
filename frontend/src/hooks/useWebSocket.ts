/**
 * WebSocket hook for real-time optimization progress and portfolio updates.
 *
 * Usage:
 *   const { connected, send, subscribe } = useWebSocket(userId);
 *   subscribe(`optimization:${optId}`, (msg) => setProgress(msg.progress));
 */
import { useCallback, useEffect, useRef, useState } from 'react';

interface WebSocketMessage {
  type: string;
  [key: string]: unknown;
}

type MessageHandler = (message: WebSocketMessage) => void;

interface UseWebSocketReturn {
  connected: boolean;
  send: (data: Record<string, unknown>) => void;
  subscribe: (roomId: string, handler: MessageHandler) => () => void;
  lastMessage: WebSocketMessage | null;
}

export function useWebSocket(userId: string | undefined): UseWebSocketReturn {
  const [connected, setConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const handlersRef = useRef<Map<string, Set<MessageHandler>>>(new Map());
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>();
  const reconnectAttempts = useRef(0);

  const connect = useCallback(() => {
    if (!userId || wsRef.current?.readyState === WebSocket.OPEN) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const url = `${protocol}//${host}/ws/${userId}`;

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        reconnectAttempts.current = 0;
        console.log('[WS] Connected');
      };

      ws.onmessage = (event) => {
        try {
          const msg: WebSocketMessage = JSON.parse(event.data);
          setLastMessage(msg);

          // Dispatch to room subscribers
          const roomHandlers = handlersRef.current.get(msg.type);
          if (roomHandlers) {
            roomHandlers.forEach((handler) => handler(msg));
          }

          // Also dispatch to wildcard subscribers
          const wildcardHandlers = handlersRef.current.get('*');
          if (wildcardHandlers) {
            wildcardHandlers.forEach((handler) => handler(msg));
          }
        } catch {
          // Ignore parse errors
        }
      };

      ws.onclose = () => {
        setConnected(false);
        wsRef.current = null;

        // Reconnect with exponential backoff
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
        reconnectAttempts.current++;
        reconnectTimeoutRef.current = setTimeout(connect, delay);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      // Connection failed, retry
      reconnectTimeoutRef.current = setTimeout(connect, 2000);
    }
  }, [userId]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimeoutRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  // Heartbeat
  useEffect(() => {
    if (!connected) return;
    const interval = setInterval(() => {
      send({ type: 'ping' });
    }, 30000);
    return () => clearInterval(interval);
  }, [connected]);

  const send = useCallback((data: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  const subscribe = useCallback((roomId: string, handler: MessageHandler) => {
    if (!handlersRef.current.has(roomId)) {
      handlersRef.current.set(roomId, new Set());
    }
    handlersRef.current.get(roomId)!.add(handler);

    // Tell server to join the room
    send({ type: 'join_room', room_id: roomId });

    return () => {
      handlersRef.current.get(roomId)?.delete(handler);
      send({ type: 'leave_room', room_id: roomId });
    };
  }, [send]);

  return { connected, send, subscribe, lastMessage };
}
