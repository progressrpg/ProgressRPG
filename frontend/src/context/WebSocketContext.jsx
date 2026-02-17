// context/WebSocketContext.jsx
import React, { createContext, useContext, useRef, useCallback } from 'react';
import { useGame } from './GameContext';
import { useToast } from './ToastContext';
import { useWebSocketConnection } from '../hooks/useWebSocketConnection';
import { handleGlobalWebSocketEvent } from '../websockets/handleGlobalWebSocketEvent';
import { useMaintenanceStatus } from '../hooks/useMaintenanceStatus';

const WebSocketContext = createContext();

export const useWebSocket = () => {
  return useContext(WebSocketContext);
}

export const WebSocketProvider = ({ children }) => {
  const { player } = useGame();
  const { showToast } = useToast();
  const { refetch: maintenanceRefetch } = useMaintenanceStatus();
  const eventHandlersRef = useRef(new Set());

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
    onOpen
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
