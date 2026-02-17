import { useEffect, useState } from 'react';
import { apiFetch } from '../../utils/api';
import { useAuth } from '../context/AuthContext.jsx';

export function useBootstrapGameData() {
  const { isAuthenticated, loading: authLoading } = useAuth();

  const [player, setPlayer] = useState(null);
  const [character, setCharacter] = useState(null);
  const [activityTimerInfo, setActivityTimerInfo] = useState(null);
  //const [populationCentreInfo, setPopulationCentreInfo] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [buildNumber, setBuildNumber] = useState(true);

  useEffect(() => {
    if (authLoading) return;

    if (!isAuthenticated) {
      setLoading(false);
      return;
    }

    const fetchGameData = async () => {
      try {
        setLoading(true);

        const info = await apiFetch('/fetch_info/');
        // console.log("bootstrap info:", info);
        setPlayer(info.player);
        setCharacter(info.character);
        setActivityTimerInfo(info.activity_timer);
        //setPopulationCentreInfo(info.population_centre);
        setBuildNumber(info.build_number);
      } catch (err) {
        console.error('[Bootstrap] Error loading game data:', err);
        setError('Something went wrong while loading game data.');
      } finally {
        setLoading(false);
      }
    };

    fetchGameData();
  }, [authLoading, isAuthenticated]);

  return {
    player,
    character,
    activityTimerInfo,
    //populationCentreInfo,
    buildNumber,
    loading,
    error
  };
}
