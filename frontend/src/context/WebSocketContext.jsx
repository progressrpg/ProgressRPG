// context/WebSocketContext.jsx
import React, { useRef, useCallback } from 'react';
import { useGame } from './GameContext';
import { useToast } from './ToastContext';
import { useAuth } from './AuthContext';
import { useWebSocketConnection } from '../hooks/useWebSocketConnection';
import { handleGlobalWebSocketEvent } from '../websockets/handleGlobalWebSocketEvent';
import { useMaintenanceStatus } from '../hooks/useMaintenanceStatus';
import { WebSocketContext } from './webSocketContext';

export const WebSocketProvider = ({ children }) => {
  const { player } = useGame();
  const { isAuthenticated, loading: authLoading } = useAuth();
  const { showToast } = useToast();
  const { refetch: maintenanceRefetch } = useMaintenanceStatus();
  const eventHandlersRef = useRef(new Set());
  const wsEnabled = Boolean(!authLoading && isAuthenticated && player?.id);

  const onMessage = useCallback((data) => {
    //console.log("[WS Provider] showToast:", showToast);
    handleGlobalWebSocketEvent(data, { showToast, maintenanceRefetch });
    eventHandlersRef.current.forEach((handler) => handler(data));
  }, [showToast, maintenanceRefetch ]);

  const onError = useCallback(() => {
    console.error('WebSocket connection error');
  }, []);

  const onClose = useCallback(() => {
    console.warn('WebSocket disconnected');
  }, []);

  const onOpen = useCallback(() => {
    //console.log('WebSocket connected!');
  }, []);

  const { send, isConnected, disconnect } = useWebSocketConnection(
    player?.id,
    onMessage,
    onError,
    onClose,
    onOpen,
    wsEnabled
  );

  const addEventHandler = useCallback((handler) => {
    eventHandlersRef.current.add(handler);
    return () => eventHandlersRef.current.delete(handler);
  }, []);


  return (
    <WebSocketContext.Provider value={{ send, isConnected, addEventHandler, disconnect }}>
      {children}
    </WebSocketContext.Provider>
  );
}
