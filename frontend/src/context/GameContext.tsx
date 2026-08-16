// GameContext.tsx
import { useState, useEffect, useCallback, useMemo } from 'react';
import type { ReactElement, ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';

import { useBootstrapGameData } from '../hooks/useBootstrapGameData';
import { useEventCallback } from '../hooks/useEventCallback';
import { apiFetch } from "../utils/api";
import useActivityTimer from '../hooks/useActivityTimer';
import useUnloadWarning from '../hooks/useUnloadWarning';
import { initialMapCentreQueryOptions, mapWorldBoundsQueryOptions } from '../hooks/useMap';
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
// Helpers
// ---------------------------------------------------------------------------

const getActivityWindow = (): { start: string } => {
  const now = new Date();
  const since = new Date(now.getTime() - 24 * 60 * 60 * 1000);
  return {
    start: since.toISOString(),
  };
};

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
    announcementUnreadCount: announcementUnreadCountOnload,
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
  const [announcementUnreadCount, setAnnouncementUnreadCount] = useState<number>(announcementUnreadCountOnload);

  const activityTimer = useActivityTimer();
  const { loadFromServer } = activityTimer;

  useUnloadWarning(activityTimer.status === 'active');

  const queryClient = useQueryClient();


  // ----------------------------------------
  //  STABLE CALLBACKS
  // ----------------------------------------


  const fetchPlayerAndCharacter = useCallback(async (): Promise<void> => {
    const freshPlayer = await apiFetch<Player>(`/me/player/`);
    setPlayer(freshPlayer);
    setCharacter(null);
  }, []);

  const fetchActivities = useCallback(async (): Promise<void> => {
    const activityWindow = getActivityWindow();
    const [playerData, charData] = await Promise.all([
      apiFetch<{ results: PlayerActivity[] }>(
        `/player-activities/?is_complete=true&completed_at_after=${activityWindow.start}`
      ),
      apiFetch<{ results: CharacterActivity[] }>(
        `/character-activities/?is_complete=true&completed_at_after=${activityWindow.start}`
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

  const onAuthReadyFetchPlayerAndCharacter = useEventCallback(fetchPlayerAndCharacter);
  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      onAuthReadyFetchPlayerAndCharacter();
    }
  }, [onAuthReadyFetchPlayerAndCharacter, isAuthenticated, authLoading]);

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

  // Primes the map's two cheap, one-shot "where/how big is the world"
  // queries as soon as fetch_info has resolved, rather than waiting for the
  // player to navigate to the map page and pay for them there. Both use the
  // same {queryKey, queryFn, staleTime} as useInitialMapCentre/
  // useMapWorldBounds (see useMap.ts) so this primes exactly the cache entry
  // those hooks read - if the player never opens the map, the prefetched
  // data just sits unused until its gcTime expires. Deliberately doesn't
  // prefetch /map/viewport/: that needs a bbox only the mounted map
  // component can produce, and (unlike these two) starts a 2s poll once
  // enabled, which would run in the background for every session whether or
  // not the player ever opens the map.
  useEffect(() => {
    if (loading || !isAuthenticated) return;
    void queryClient.prefetchQuery(initialMapCentreQueryOptions);
    void queryClient.prefetchQuery(mapWorldBoundsQueryOptions);
  }, [loading, isAuthenticated, queryClient]);

  const onAuthReadyFetchActivities = useEventCallback(fetchActivities);
  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      onAuthReadyFetchActivities();
    }
  }, [onAuthReadyFetchActivities, isAuthenticated, authLoading]);

  // Adjust local state when the bootstrap-loaded values arrive, per
  // https://react.dev/learn/you-might-not-need-an-effect#adjusting-some-state-when-a-prop-changes
  const [prevXpModsOnload, setPrevXpModsOnload] = useState(xpModsOnload);
  if (xpModsOnload !== prevXpModsOnload) {
    setPrevXpModsOnload(xpModsOnload);
    if (xpModsOnload) {
      setXpMods(xpModsOnload);
    }
  }

  const [prevAnnouncementUnreadCountOnload, setPrevAnnouncementUnreadCountOnload] = useState(
    announcementUnreadCountOnload
  );
  if (announcementUnreadCountOnload !== prevAnnouncementUnreadCountOnload) {
    setPrevAnnouncementUnreadCountOnload(announcementUnreadCountOnload);
    setAnnouncementUnreadCount(announcementUnreadCountOnload);
  }


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
      announcementUnreadCount,
      setAnnouncementUnreadCount,
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
      announcementUnreadCount,
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
