// GameContext.jsx
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useBootstrapGameData } from '../hooks/useBootstrapGameData';
import { apiFetch } from '../../utils/api';
import useTimers from '../hooks/useTimers';

const GameContext = createContext();

const getFormattedDate = () => {
  const today = new Date();
  const yyyy = today.getFullYear();
  const mm = String(today.getMonth() + 1).padStart(2, '0'); // Months are zero-based
  const dd = String(today.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

export const useGame = () => {
  const context = useContext(GameContext);
  return context;
}

export const GameProvider = ({ children }) => {
  const { player: playerOnload, character: characterOnload, activityTimerInfo, questTimerInfo, buildNumber, loading, error } = useBootstrapGameData();
  const [activities, setActivities] = useState({ results: [], count: 0 });
  const [quests, setQuests] = useState([]);
  const [player, setPlayer] = useState(playerOnload);
  const [character, setCharacter] = useState(characterOnload);
  const activityTimer = useTimers({ mode: "activity" });
  const questTimer = useTimers({ mode: "quest" });

  async function fetchPlayerAndCharacter() {
    const [freshPlayer, freshCharacter] = await Promise.all([
      apiFetch(`/profile/${playerOnload.id}/`),
      apiFetch(`/character/${characterOnload.id}/`),
    ]);
    setPlayer(freshPlayer);
    setCharacter(freshCharacter);
  }

  useEffect(() => {
    if (!playerOnload?.id || !characterOnload?.id) return;

    fetchPlayerAndCharacter();
  }, [playerOnload, characterOnload]);

  useEffect(() => {
    if (activityTimerInfo || questTimerInfo) {
      activityTimer.loadFromServer(activityTimerInfo);
      questTimer.loadFromServer(questTimerInfo);
    }
  }, [activityTimerInfo, questTimerInfo]);

  const formattedDate = getFormattedDate();

  async function fetchActivities() {
    const data = await apiFetch(`/activities/?date_after=${formattedDate}&date_before=${formattedDate}`);
    setActivities(data);
  }

  useEffect(() => {
    fetchActivities();
  }, [formattedDate]);

  async function fetchQuests() {
    const data = await apiFetch(`/quests/eligible`);
    setQuests(data.eligible_quests);
  }

  useEffect(() => {
    fetchQuests();
  }, [player, character]);

  const value = React.useMemo(() => ({
    player,
    setPlayer,
    character,
    setCharacter,
    activityTimer,
    questTimer,
    activities,
    fetchActivities,
    quests,
    fetchQuests,
    loading,
    buildNumber
  }), [player, character, activityTimer, questTimer, activities, fetchActivities, quests, fetchQuests, loading, buildNumber]);


  return (
    <GameContext.Provider value={value}>
      {children}
    </GameContext.Provider>
  );
};
