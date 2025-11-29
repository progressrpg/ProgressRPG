import React from 'react';
import { useWebSocket } from '../context/WebSocketContext'; // adjust path

export default function OnlinePlayersOverlay() {
  const { onlinePlayers } = useWebSocket();

  if (!onlinePlayers || onlinePlayers.length === 0) return null;

  return (
    <div
      style={{
        position: 'fixed',
        top: '4rem', // below navbar
        left: '1rem',
        backgroundColor: 'rgba(255,255,255,0.9)',
        padding: '0.5rem 1rem',
        borderRadius: '0.25rem',
        boxShadow: '0 2px 6px rgba(0,0,0,0.2)',
        zIndex: 1000,
        fontSize: '0.875rem',
      }}
    >
      <strong>Online:</strong> {onlinePlayers.map(p => p.name).join(', ')}
    </div>
  );
}
