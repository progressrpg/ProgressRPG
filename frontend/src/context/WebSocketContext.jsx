// context/WebSocketContext.jsx
import React, { createContext, useContext, useRef, useCallback, useState } from 'react';
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
  const [onlinePlayers, setOnlinePlayers] = useState([]);
  const { refetch: maintenanceRefetch } = useMaintenanceStatus();
  const eventHandlersRef = useRef(new Set());

  const onMessage = useCallback((data) => {
    handleGlobalWebSocketEvent(data, { showToast, maintenanceRefetch });

    // Presence handling
    if (data.type === 'action' && data.action === 'online_players_update') {
      console.log('[WS] Received online players update:', data.players);
      setOnlinePlayers(data.players || []);
    }

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
    <WebSocketContext.Provider
      value={{
        send,
        isConnected,
        addEventHandler,
        disconnect,
        onlinePlayers,
      }}>
      {children}
    </WebSocketContext.Provider>
  );
}
