"use client";

import { useEffect, useRef, useState, useCallback } from "react";

interface UseWebSocketOptions {
  url: string;
  onMessage?: (data: any) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

type ConnectionStatus = "connecting" | "connected" | "disconnected" | "error";

export function useWebSocket({
  url,
  onMessage,
  onOpen,
  onClose,
  onError,
  reconnectInterval = 5000,
  maxReconnectAttempts = 5,
}: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");

  const connect = useCallback(() => {
    if (typeof window === "undefined") return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      setStatus("connecting");
      const ws = new WebSocket(url);

      ws.onopen = () => {
        setStatus("connected");
        reconnectAttempts.current = 0;
        onOpen?.();
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessage?.(data);
        } catch {
          onMessage?.(event.data);
        }
      };

      ws.onclose = () => {
        setStatus("disconnected");
        onClose?.();
        // Auto reconnect
        if (reconnectAttempts.current < maxReconnectAttempts) {
          reconnectTimer.current = setTimeout(() => {
            reconnectAttempts.current++;
            connect();
          }, reconnectInterval);
        }
      };

      ws.onerror = (error) => {
        setStatus("error");
        onError?.(error);
      };

      wsRef.current = ws;
    } catch {
      setStatus("error");
    }
  }, [url, onMessage, onOpen, onClose, onError, reconnectInterval, maxReconnectAttempts]);

  const disconnect = useCallback(() => {
    if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    reconnectAttempts.current = maxReconnectAttempts; // prevent reconnect
    wsRef.current?.close();
    wsRef.current = null;
    setStatus("disconnected");
  }, [maxReconnectAttempts]);

  const send = useCallback((data: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(typeof data === "string" ? data : JSON.stringify(data));
    }
  }, []);

  useEffect(() => {
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, []);

  return { status, connect, disconnect, send };
}

export default useWebSocket;
