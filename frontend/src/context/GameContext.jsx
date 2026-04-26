// GameContext.jsx
import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';

import { useBootstrapGameData } from '../hooks/useBootstrapGameData';
import { apiFetch } from "../utils/api";
import useActivityTimer from '../hooks/useActivityTimer';
import { useAuth } from './AuthContext';


const GameContext = createContext();

export const useGame = () => {
  return useContext(GameContext);
}

const getActivityWindow = () => {
  const now = new Date();
  const since = new Date(now.getTime() - 24 * 60 * 60 * 1000);
  return {
    start: since.toISOString(),
    end: now.toISOString(),
  };
};

export const GameProvider = ({ children }) => {
  const {
    player: playerOnload,
    character: characterOnload,
    activityTimerInfo,
    populationCentreInfo,
    xpMods: xpModsOnload,
    loginState,
    loginStreak,
    loginEventAt,
    loading,
    error,
    buildNumber,
    freeTimerLimitSeconds,
  } = useBootstrapGameData();


  const [player, setPlayer] = useState(playerOnload);
  const [character, setCharacter] = useState(characterOnload);
  const [xpMods, setXpMods] = useState(xpModsOnload);
  const [playerActivities, setPlayerActivities] = useState([]);
  const [characterActivities, setCharacterActivities] = useState([]);
  const [characterCurrentActivity, setCharacterCurrentActivity] = useState({});
  const [populationCentre, setPopulationCentre] = useState(populationCentreInfo);

  const activityTimer = useActivityTimer();


  // ----------------------------------------
  //  STABLE CALLBACKS
  // ----------------------------------------


  const fetchPlayerAndCharacter = useCallback(async () => {
    const freshPlayer = await apiFetch(`/me/player/`);
    setPlayer(freshPlayer);

    try {
      const freshCharacter = await apiFetch(`/me/character/`);
      setCharacter(freshCharacter);
    } catch (err) {
      // A 404 is expected when the player has no linked character.
      console.debug('[GameContext] No character linked for player:', err?.message);
      setCharacter(null);
    }
  }, []);

  const fetchActivities = useCallback(async () => {
    const activityWindow = getActivityWindow();
    const [playerData, charData] = await Promise.all([
      apiFetch(
        `/player-activities/?is_complete=true&completed_at_after=${activityWindow.start}&completed_at_before=${activityWindow.end}`
      ),
      apiFetch(
        `/character-activities/?is_complete=true&completed_at_after=${activityWindow.start}&completed_at_before=${activityWindow.end}`
      ),
    ]);
    setPlayerActivities(await playerData?.results ?? []);
    setCharacterActivities(await charData?.results ?? []);
  }, []);

  const fetchCharacterCurrent = useCallback(async () => {
    const data = await apiFetch(`/character-activities/current/`);
    //console.log("/current, data:", data);
    setCharacterCurrentActivity(data.current);
    return data.current;
  }, []);

  const fetchPopulationCentre = useCallback(async (pcId) => {
    const data = await apiFetch(`/population-centres/${pcId}/`);
    setPopulationCentre(data);
    return data;
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
      activityTimer.loadFromServer(activityTimerInfo, {
        limitSeconds: player?.is_premium ? null : freeTimerLimitSeconds,
      });
    }
  }, [
    activityTimer.loadFromServer,
    activityTimerInfo,
    freeTimerLimitSeconds,
    player?.is_premium,
  ]);

  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      fetchActivities();
    }
  }, [fetchActivities, isAuthenticated, authLoading]);

  useEffect(() => {
    if (xpModsOnload) {
      setXpMods(xpModsOnload);
    }
  }, [xpModsOnload]);


  // ----------------------------------------
  //  STABLE PROVIDER VALUE
  // ----------------------------------------


  const value = useMemo(
    () => ({
      player,
      setPlayer,
      character,
      setCharacter,
      xpMods,
      setXpMods,
      fetchPlayerAndCharacter,
      activityTimer,
      playerActivities,
      characterActivities,
      fetchActivities,
      fetchCharacterCurrent,
      characterCurrentActivity,
      setCharacterCurrentActivity,
      populationCentre,
      fetchPopulationCentre,
      loginState,
      loginStreak,
      loginEventAt,
      loading,
      buildNumber,
      freeTimerLimitSeconds,
    }),
    [
      player,
      character,
      xpMods,
      playerActivities,
      characterActivities,
      characterCurrentActivity,
      activityTimer,
      fetchPlayerAndCharacter,
      fetchActivities,
      fetchCharacterCurrent,
      loading,
      buildNumber,
      freeTimerLimitSeconds,
      populationCentre,
      fetchPopulationCentre,
      loginState,
      loginStreak,
      loginEventAt,
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
