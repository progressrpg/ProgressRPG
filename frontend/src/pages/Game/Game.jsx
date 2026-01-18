// pages/Game/Game.jsx
import React, { useState, useEffect } from 'react';

import { useGame } from '../../context/GameContext';
import { useWebSocket } from '../../context/WebSocketContext';

import styles from './Game.module.scss';
import GameContainer from '../../layout/GameContainer/GameContainer';


export default function Game() {
  const { loading, error } = useGame();
  const { addEventHandler } = useWebSocket();

  if (loading) return <p>Loading game data...</p>;
  if (error) return <p>Error: {error}. Please refresh the page!</p>;

  return (
    <div className={styles.page}>
      <div className={styles.content}>
        <GameContainer />
      </div>
    </div>
  );
}
