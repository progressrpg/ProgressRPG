// context/WebSocketContext.tsx
import { useRef, useCallback } from 'react';
import type { ReactNode, ReactElement } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useGame } from '../hooks/useGame';
import { useOnlineCount } from './OnlineCountContext';
import { useToast } from '../hooks/useToast';
import { useAuth } from './AuthContext';
import { useWebSocketConnection } from '../hooks/useWebSocketConnection';
import { handleGlobalWebSocketEvent } from '../websockets/handleGlobalWebSocketEvent';
import { useMaintenanceStatus } from '../hooks/useMaintenanceStatus';
import { useMaintenanceContext } from './MaintenanceContext';
import { WebSocketContext } from './webSocketContext';
import {
  ANNOUNCEMENTS_QUERY_KEY,
  ANNOUNCEMENT_UNREAD_QUERY_KEY,
} from '../hooks/useAnnouncements';
import type { ActivityTimerApiData, IncomingWebSocketMessage, OutgoingWebSocketMessage } from '../types';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ProviderProps {
  children: ReactNode;
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export const WebSocketProvider = ({ children }: ProviderProps): ReactElement => {
  const { player, activityTimer, freeTimerLimitSeconds } = useGame();
  const { setOnlinePlayerCount } = useOnlineCount();
  const { isAuthenticated, loading: authLoading } = useAuth();
  const { showToast } = useToast();
  const { refetch: maintenanceRefetch } = useMaintenanceStatus();
  const { setMaintenance } = useMaintenanceContext();
  const queryClient = useQueryClient();
  // Set stores message handler callbacks registered by child components
  const eventHandlersRef = useRef<Set<(data: IncomingWebSocketMessage) => void>>(new Set());
  const wsEnabled = Boolean(!authLoading && isAuthenticated && player?.id);

  const { loadFromServer } = activityTimer;
  const onActivityTimerUpdate = useCallback((activityTimerData: ActivityTimerApiData) => {
    // Reconciles this session's timer to the authoritative state pushed
    // whenever another of the player's open sessions (tabs/devices) starts,
    // labels, or submits the activity timer. loadFromServer just overwrites
    // local state, so applying it to the session that originated the change
    // (an echo of its own update) is harmless.
    loadFromServer(activityTimerData, {
      limitSeconds: player?.is_premium ? null : freeTimerLimitSeconds,
    });
  }, [loadFromServer, player?.is_premium, freeTimerLimitSeconds]);

  const onAnnouncementPublished = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ANNOUNCEMENTS_QUERY_KEY });
    queryClient.invalidateQueries({ queryKey: ANNOUNCEMENT_UNREAD_QUERY_KEY });
  }, [queryClient]);

  const onMessage = useCallback((data: IncomingWebSocketMessage) => {
    if (data.type === 'online_count') {
      setOnlinePlayerCount(data.count);
    }
    //console.log("[WS Provider] showToast:", showToast);
    handleGlobalWebSocketEvent(data, {
      showToast,
      maintenanceRefetch,
      setMaintenance,
      onActivityTimerUpdate,
      onAnnouncementPublished,
    });
    eventHandlersRef.current.forEach((handler) => handler(data));
  }, [showToast, maintenanceRefetch, setMaintenance, setOnlinePlayerCount, onActivityTimerUpdate, onAnnouncementPublished]);

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

  const addEventHandler = useCallback((handler: (data: IncomingWebSocketMessage) => void): (() => void) => {
    eventHandlersRef.current.add(handler);
    return () => eventHandlersRef.current.delete(handler);
  }, []);

  const typedSend = (data: OutgoingWebSocketMessage): void => send(data);

  return (
    <WebSocketContext.Provider value={{ send: typedSend, isConnected, addEventHandler, disconnect }}>
      {children}
    </WebSocketContext.Provider>
  );
};
