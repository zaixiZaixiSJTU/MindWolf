import { useRef, useCallback, useEffect, useState } from 'react';
import type { WSMessage } from './types';

export function useWebSocket(url: string) {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WSMessage | null>(null);
  const listeners = useRef<Map<string, Set<(msg: WSMessage) => void>>>(new Map());

  useEffect(() => {
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);

    ws.onmessage = (event) => {
      const msg: WSMessage = JSON.parse(event.data);
      setLastMessage(msg);
      const handlers = listeners.current.get(msg.type);
      if (handlers) {
        handlers.forEach((fn) => fn(msg));
      }
    };

    return () => { ws.close(); };
  }, [url]);

  const on = useCallback((type: string, handler: (msg: WSMessage) => void) => {
    if (!listeners.current.has(type)) {
      listeners.current.set(type, new Set());
    }
    listeners.current.get(type)!.add(handler);
    return () => {
      listeners.current.get(type)?.delete(handler);
    };
  }, []);

  return { connected, lastMessage, on };
}
