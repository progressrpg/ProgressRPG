/* eslint-disable react-hooks/set-state-in-effect */
// GameContext.tsx
import { useState, useEffect, useCallback, useMemo } from 'react';
import type { ReactElement, ReactNode } from 'react';

import { useBootstrapGameData } from '../hooks/useBootstrapGameData';
import { apiFetch } from "../utils/api";
import useActivityTimer from '../hooks/useActivityTimer';
import { useAuth } from './AuthContext';
import { GameContext, type GameContextValue } from './gameContext';
import type {
  Player,
  Character,
  XpModifier,
  PlayerActivity,
  CharacterActivity,
  PopulationCentre,
} from '../types';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/**
 * Shape of the /character-activities/current/ response.
 * The `current` field is a CharacterActivity or null.
 */
interface CharacterCurrentResponse {
  current: CharacterActivity | null;
}

interface ProviderProps {
  children: ReactNode;
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export const GameProvider = ({ children }: ProviderProps): ReactElement => {
  const {
    player: playerOnload,
    character: characterOnload,
    activityTimerInfo,
    populationCentreInfo,
    xpMods: xpModsOnload,
    loginState,
    loginStreak,
    loginEventAt,
    loginRewardXp,
    loading,
    error,
    buildNumber,
    freeTimerLimitSeconds,
    gameSettings,
    onlineCount: initialOnlineCount,
  } = useBootstrapGameData();


  const [player, setPlayer] = useState<Player | null>(playerOnload);
  const [character, setCharacter] = useState<Character | null>(characterOnload);
  const [xpMods, setXpMods] = useState<XpModifier[]>(xpModsOnload);
  const [playerActivities, setPlayerActivities] = useState<PlayerActivity[]>([]);
  const [characterActivities, setCharacterActivities] = useState<CharacterActivity[]>([]);
  const [characterCurrentActivity, setCharacterCurrentActivity] = useState<CharacterActivity | null>(null);
  const [populationCentre, setPopulationCentre] = useState<PopulationCentre | null>(populationCentreInfo);

  const activityTimer = useActivityTimer();
  const { loadFromServer } = activityTimer;


  // ----------------------------------------
  //  STABLE CALLBACKS
  // ----------------------------------------


  const fetchPlayerAndCharacter = useCallback(async (): Promise<void> => {
    const freshPlayer = await apiFetch<Player>(`/me/player/`);
    setPlayer(freshPlayer);
    setCharacter(null);
  }, []);

  const fetchActivities = useCallback(async (): Promise<void> => {
    const [playerData, charData] = await Promise.all([
      apiFetch<{ results: PlayerActivity[] }>(
        `/player-activities/?is_complete=true&ordering=-completed_at`
      ),
      apiFetch<{ results: CharacterActivity[] }>(
        `/character-activities/?is_complete=true&ordering=-completed_at`
      ),
    ]);
    setPlayerActivities(playerData?.results ?? []);
    setCharacterActivities(charData?.results ?? []);
  }, []);

  const fetchCharacterCurrent = useCallback(async (): Promise<CharacterActivity | null> => {
    const data = await apiFetch<CharacterCurrentResponse>(`/character-activities/current/`);
    //console.log("/current, data:", data);
    setCharacterCurrentActivity(data.current);
    return data.current;
  }, []);

  const fetchPopulationCentre = useCallback(async (pcId: number): Promise<PopulationCentre> => {
    const data = await apiFetch<PopulationCentre>(`/population-centres/${pcId}/`);
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
      loadFromServer(activityTimerInfo, {
        limitSeconds: player?.is_premium ? null : freeTimerLimitSeconds,
      });
    }
  }, [
    loadFromServer,
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


  const value = useMemo<GameContextValue>(
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
      loginRewardXp,
      loading,
      buildNumber,
      freeTimerLimitSeconds,
      gameSettings,
      initialOnlineCount,
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
      gameSettings,
      initialOnlineCount,
      populationCentre,
      fetchPopulationCentre,
      loginState,
      loginStreak,
      loginEventAt,
      loginRewardXp,
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
