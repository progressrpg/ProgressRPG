import { useEffect, useRef } from 'react';
import { useGame } from '../context/GameContext';
import { API_BASE_URL } from '../config';

export default function PlayerSocketListener({ onEvent }) {
  const { player } = useGame();
  const socketRef = useRef(null);

  useEffect(() => {
    if (!player?.id) return;

    const connectSocket = async () => {
      try {
        // Step 1: Get JWT from storage
        const token = localStorage.getItem('accessToken');
        if (!token) {
            console.warn('[WS] Token missing — not attempting connection');
            return;
        }


        // Step 2: Request UUID from Django
        const url_raw = API_BASE_URL;
        const response = await fetch(`${url_raw}/api/v1/ws_auth/`, {
            method: 'GET',
            headers: {
                Authorization: `Bearer ${token}`,
                'Content-Type': 'application/json',
            },
        });

        if (!response.ok) throw new Error('Failed to fetch WS auth UUID');
        const { uuid } = await response.json();



        // Step 3: Build secure WebSocket URL
        const url = new URL(url_raw);
        const protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${url.host}/ws/profile_${player.id}/?uuid=${uuid}`;

        // Step 4: Connect!
        const socket = new WebSocket(wsUrl);
        socketRef.current = socket;

        socket.onopen = () => {
          console.log('[WS] Connected');
          socket.send(JSON.stringify({ type: 'ping' }));
        };

        socket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            onEvent?.(data);
          } catch (err) {
            console.error('[WS] JSON parse error:', err);
          }
        };

        socket.onerror = (err) => console.error('[WS] Error:', err);
        socket.onclose = () => console.warn('[WS] Closed');
      } catch (err) {
        console.error('[WS] Connection failed:', err.message);
      }
    };

    connectSocket();
    return () => socketRef.current?.close();
  }, [player?.id]);

  return null;
}
