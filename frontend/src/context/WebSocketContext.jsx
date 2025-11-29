// context/WebSocketContext.jsx
import React, { createContext, useState, useContext, useRef, useCallback } from 'react';
import { useGame } from './GameContext';
import { useToast } from './ToastContext';
import { useWebSocketConnection } from '../hooks/useWebSocketConnection';
import { handleGlobalWebSocketEvent } from '../websockets/handleGlobalWebSocketEvent';
import { useMaintenanceStatus } from '../hooks/useMaintenanceStatus';

const WebSocketContext = createContext();

export const WebSocketProvider = ({ children }) => {
  const [onlinePlayers, setOnlinePlayers] = useState([]);
  const { player } = useGame();
  const { showToast } = useToast();
  const { refetch: maintenanceRefetch } = useMaintenanceStatus();
  const eventHandlersRef = useRef(new Set());

  const onMessage = useCallback((data) => {
    handleGlobalWebSocketEvent(data, { showToast, maintenanceRefetch, setOnlinePlayers });

    eventHandlersRef.current.forEach((handler) => handler(data));
  }, [showToast, maintenanceRefetch, setOnlinePlayers ]);

  const onError = useCallback(() => {
    console.error('WebSocket connection error');
  }, []);

  const onClose = useCallback(() => {
    console.warn('WebSocket disconnected');
  }, []);

  const onOpen = useCallback(() => {
    //console.log('WebSocket connected!');
  }, []);

  const { send, isConnected } = useWebSocketConnection(
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
    <WebSocketContext.Provider value={{ send, isConnected, addEventHandler }}>
      {children}
    </WebSocketContext.Provider>
  );
}

export const useWebSocket = () => {
  return useContext(WebSocketContext);
}
