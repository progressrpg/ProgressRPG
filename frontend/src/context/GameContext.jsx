// GameContext.jsx
import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';

import { useBootstrapGameData } from '../hooks/useBootstrapGameData';
import { apiFetch } from '../../utils/api';
import useTimers from '../hooks/useTimers';

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
    questTimerInfo,
    buildNumber,
    loading,
  } = useBootstrapGameData();


  const [player, setPlayer] = useState(playerOnload);
  const [character, setCharacter] = useState(characterOnload);
  const [playerActivities, setPlayerActivities] = useState({ results: [], count: 0 });
  const [characterActivities, setCharacterActivities] = useState({ results: [], count: 0 });
  const [quests, setQuests] = useState([]);

  const [onboardingStage, setOnboardingStage] = useState(4);

  const activityTimer = useTimers({ mode: "activity" });
  const questTimer = useTimers({ mode: "quest" });


  // ----------------------------------------
  //  STABLE CALLBACKS
  // ----------------------------------------


  const fetchPlayerAndCharacter = useCallback(async () => {
    if (!characterOnload?.id) return;

    const [freshPlayer, freshCharacter] = await Promise.all([
      apiFetch(`/profile/me/`),
      apiFetch(`/character/${characterOnload.id}/`),
    ]);

    setPlayer(freshPlayer);
    setCharacter(freshCharacter);
  }, [characterOnload?.id]);

  const formattedDate = getFormattedDate();

  const fetchActivities = useCallback(async () => {
    const [playerData, charData] = await Promise.all([
      apiFetch(
        `/player-activities/?date_after=${formattedDate}&date_before=${formattedDate}`
      ),
      apiFetch(
        `/character-activities/?date_after=${formattedDate}&date_before=${formattedDate}`
      ),
    ]);

    setPlayerActivities(await playerData);
    setCharacterActivities(await charData);
  }, [formattedDate]);

  const fetchQuests = useCallback(async () => {
    const data = await apiFetch(`/quests/eligible`);
    setQuests(data.eligible_quests);
  }, []);


  // ----------------------------------------
  //  EFFECTS
  // ----------------------------------------


  useEffect(() => {
    fetchPlayerAndCharacter();
  }, [fetchPlayerAndCharacter]);

  useEffect(() => {
    if (activityTimerInfo) activityTimer.loadFromServer(activityTimerInfo);
    if (questTimerInfo) questTimer.loadFromServer(questTimerInfo);
  }, [activityTimerInfo, questTimerInfo]);

  useEffect(() => {
    fetchActivities();
  }, [fetchActivities]);

  useEffect(() => {
    fetchQuests();
  }, [fetchQuests]);


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
      questTimer,
      activities,
      fetchActivities,
      quests,
      fetchQuests,
      loading,
      buildNumber,
      onboardingStage,
      setOnboardingStage,
    }),
    [
      player,
      character,
      activities,
      quests,
      activityTimer,
      questTimer,
      fetchPlayerAndCharacter,
      fetchActivities,
      fetchQuests,
      loading,
      buildNumber,
      onboardingStage,
    ]
  );


  return (
    <GameContext.Provider value={value}>
      {children}
    </GameContext.Provider>
  );
};
