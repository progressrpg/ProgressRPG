import { useContext } from 'react';
import { WebSocketContext } from '../context/webSocketContext';

export function useWebSocket() {
  return useContext(WebSocketContext);
}
