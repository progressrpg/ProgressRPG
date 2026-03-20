import { useEffect, useRef, useCallback, useState } from 'react';
import { API_BASE_URL } from '../config';
import { apiFetch } from '../../utils/api';

// WebSocket connection constants
const RECONNECT_DELAY_MS = 3000;
const RETRY_DELAY_MS = 5000;
const NORMAL_CLOSURE = 1000;
const GOING_AWAY = 1001;

export function useWebSocketConnection(playerId, onMessage, onError, onClose, onOpen, shouldConnect = true) {
  const socketRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const [isConnected, setIsConnected] = useState(false);
  const intentionalCloseRef = useRef(false);

  const connect = useCallback(async () => {
    if (!shouldConnect) {
      return;
    }

    if (!playerId) {
      console.warn('[WS] No player ID, skipping connection');
      return;
    }

    try {
      // Get UUID for connection using shared auth/refresh logic.
      const { uuid } = await apiFetch('/ws_auth/', { method: 'GET' });

      // Build WebSocket URL
      const url = new URL(API_BASE_URL);
      const protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${url.host}/ws/profile_${playerId}/?uuid=${uuid}`;

      // Close existing socket if any
      if (socketRef.current?.readyState === WebSocket.OPEN) {
        intentionalCloseRef.current = true;
        socketRef.current.close();
      }

      const socket = new WebSocket(wsUrl);
      socketRef.current = socket;

      socket.onopen = () => {
        console.log('[WS] Connected');
        setIsConnected(true);
        intentionalCloseRef.current = false;
        onOpen?.();
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessage?.(data);
        } catch (err) {
          console.error('[WS] Parse error:', err);
        }
      };

      socket.onerror = (err) => {
        console.error('[WS] Error:', err);
        setIsConnected(false);
        onError?.(err);
      };

      socket.onclose = (event) => {
        console.log('[WS] Closed. Code:', event.code);
        setIsConnected(false);
        onClose?.(event);

        // Auto-reconnect after delay (except for intentional closes)
        if (!intentionalCloseRef.current && event.code !== NORMAL_CLOSURE && event.code !== GOING_AWAY) {
          console.log(`[WS] Scheduling reconnection in ${RECONNECT_DELAY_MS}ms...`);
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log('[WS] Attempting reconnection...');
            connect();
          }, RECONNECT_DELAY_MS);
        }
      };

    } catch (err) {
      console.error('[WS] Connection failed:', err);
      setIsConnected(false);

      // Avoid repeated 401 spam loops. Auth flow will re-enable connection when ready.
      if (!shouldConnect) {
        return;
      }
      if ((err?.message || '').toLowerCase().includes('unauthorized')) {
        return;
      }

      // Retry connection after delay on connection failure
      reconnectTimeoutRef.current = setTimeout(() => {
        console.log('[WS] Retrying after connection failure...');
        connect();
      }, RETRY_DELAY_MS);
    }
  }, [playerId, onMessage, onError, onClose, onOpen, shouldConnect]);

  useEffect(() => {
    if (shouldConnect) {
      connect();
    }

    return () => {
      // Cleanup on unmount
      intentionalCloseRef.current = true;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (socketRef.current) {
        socketRef.current.close(NORMAL_CLOSURE);
      }
      setIsConnected(false);
    };
  }, [connect, shouldConnect]);

  const send = useCallback((data) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(data));
    } else {
      console.warn('[WS] Cannot send, socket not open');
    }
  }, []);

  const disconnect = useCallback((code = NORMAL_CLOSURE, reason = 'logout') => {
    intentionalCloseRef.current = true;

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (socketRef.current) {
      try {
        socketRef.current.close(code, reason);
      } catch (e) {
        // some browsers are fussy about close(reason)
        socketRef.current.close(code);
      }
      socketRef.current = null;
    }

    setIsConnected(false);
  }, []);


  return { send, isConnected, disconnect };
}
