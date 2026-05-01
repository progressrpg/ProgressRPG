// hooks/useWebSocketEvent.js
import { useEffect } from 'react';
import { useWebSocket } from './useWebSocket';

export function useWebSocketEvent(callback) {
  const { addEventHandler } = useWebSocket();

  useEffect(() => {
    if (!callback) return;
    const remove = addEventHandler(callback);
    return () => remove();
  }, [callback, addEventHandler]);
}
