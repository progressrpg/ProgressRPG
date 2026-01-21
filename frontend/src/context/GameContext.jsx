// GameContext.jsx
import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';

import { useBootstrapGameData } from '../hooks/useBootstrapGameData';
import { apiFetch } from '../../utils/api';
import useActivityTimer from '../hooks/useActivityTimer';
import { useAuth } from './AuthContext';

const GameContext = createContext();

export const useGame = () => {
  return useContext(GameContext);
}

const getFormattedDate = () => {
  const today = new Date();
  const yyyy = today.getFullYear();
  const mm = String(today.getMonth() + 1).padStart(2, '0'); // Months are zero-based
  const dd = String(today.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

export const GameProvider = ({ children }) => {
  const {
    player: playerOnload,
    character: characterOnload,
    activityTimerInfo,
    loading,
    error,
  } = useBootstrapGameData();


  const [player, setPlayer] = useState(playerOnload);
  const [character, setCharacter] = useState(characterOnload);
  const [playerActivities, setPlayerActivities] = useState({ results: [], count: 0 });
  const [characterActivities, setCharacterActivities] = useState({ results: [], count: 0 });
  const [characterCurrentActivity, setCharacterCurrentActivity] = useState({});
  const [quests, setQuests] = useState([]);

  const activityTimer = useActivityTimer();


  // ----------------------------------------
  //  STABLE CALLBACKS
  // ----------------------------------------


  const fetchPlayerAndCharacter = useCallback(async () => {
    const freshPlayer = await apiFetch(`/me/player/`);
    setPlayer(freshPlayer);

    if (characterOnload?.id) {
      const freshCharacter = await apiFetch(`/character/${characterOnload.id}/`);
      setCharacter(freshCharacter);
    }
  }, [characterOnload?.id]);

  const formattedDate = getFormattedDate();

  const fetchActivities = useCallback(async () => {
    const [playerData, charData] = await Promise.all([
      apiFetch(
        `/player-activities/?is_complete=true&completed_at_after=${formattedDate}&completed_at_before=${formattedDate}`
      ),
      apiFetch(
        `/character-activities/?is_complete=true&completed_at_after=${formattedDate}&completed_at_before=${formattedDate}`
      ),
    ]);
    setPlayerActivities(await playerData?.results ?? []);
    setCharacterActivities(await charData?.results ?? []);
  }, [formattedDate]);

  const fetchCharacterCurrent = useCallback(async () => {
    const data = await apiFetch(`/character-activities/current/`);
    //console.log("/current, data:", data);
    setCharacterCurrentActivity(data.current); // depending on your response shape
    return data.current;
  }, []);


  const fetchQuests = useCallback(async () => {
    const data = await apiFetch(`/quests/eligible`);
    setQuests(data.eligible_quests);
  }, []);


  // ----------------------------------------
  //  EFFECTS
  // ----------------------------------------

  const { isAuthenticated, loading: authLoading } = useAuth();

  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      fetchPlayerAndCharacter();
    }
  }, [fetchPlayerAndCharacter, isAuthenticated, authLoading]);

  useEffect(() => {
    if (activityTimerInfo) {
      activityTimer.loadFromServer(activityTimerInfo);
    }
  }, [activityTimerInfo]);

  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      fetchActivities();
    }
  }, [fetchActivities, isAuthenticated, authLoading]);

  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      fetchQuests();
    }
  }, [fetchQuests, isAuthenticated, authLoading]);


  // ----------------------------------------
  //  STABLE PROVIDER VALUE
  // ----------------------------------------


  const value = useMemo(
    () => ({
      player,
      setPlayer,
      character,
      setCharacter,
      fetchPlayerAndCharacter,
      activityTimer,
      playerActivities,
      characterActivities,
      fetchActivities,
      fetchCharacterCurrent,
      characterCurrentActivity,
      setCharacterCurrentActivity,
      quests,
      fetchQuests,
      loading,
      buildNumber,
    }),
    [
      player,
      character,
      playerActivities,
      characterActivities,
      characterCurrentActivity,
      quests,
      activityTimer,
      fetchPlayerAndCharacter,
      fetchActivities,
      fetchCharacterCurrent,
      fetchQuests,
      loading,
      buildNumber,
    ]
  );


  // Don't render children until data is loaded
  if (loading) {
    return <div style={{ textAlign: 'center', padding: '2rem' }}>Loading game data...</div>;
  }

  if (error) {
    return <div style={{ textAlign: 'center', padding: '2rem' }}>Error loading game: {error}</div>;
  }

  return (
    <GameContext.Provider value={value}>
      {children}
    </GameContext.Provider>
  );
};
