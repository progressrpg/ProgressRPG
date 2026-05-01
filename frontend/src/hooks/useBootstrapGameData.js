import { useEffect, useState } from 'react';
import { apiFetch } from "../utils/api";
import { useAuth } from '../context/useAuth';

export function useBootstrapGameData() {
  const { isAuthenticated, loading: authLoading } = useAuth();

  const [player, setPlayer] = useState(null);
  const [character, setCharacter] = useState(null);
  const [activityTimerInfo, setActivityTimerInfo] = useState(null);
  const [populationCentreInfo, setPopulationCentreInfo] = useState(null);
  const [xpMods, setXpMods] = useState([]);
  const [loginState, setLoginState] = useState("none");
  const [loginStreak, setLoginStreak] = useState(0);
  const [loginEventAt, setLoginEventAt] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [buildNumber, setBuildNumber] = useState(true);
  const [freeTimerLimitSeconds, setFreeTimerLimitSeconds] = useState(1800);

  useEffect(() => {
    if (authLoading) return;

    if (!isAuthenticated) {
      setLoginState("none");
      setLoginStreak(0);
      setLoginEventAt(null);
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
        setPopulationCentreInfo(info.population_centre);
        setXpMods(info.xp_mods || []);
        setLoginState(typeof info.login_state === 'string' ? info.login_state : 'none');
        setLoginStreak(Number(info.login_streak) || 0);
        setLoginEventAt(info.login_event_at || null);
        setBuildNumber(info.build_number);
        setFreeTimerLimitSeconds(info.free_timer_limit_seconds ?? 1800);
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
    populationCentreInfo,
    xpMods,
    loginState,
    loginStreak,
    loginEventAt,
    buildNumber,
    freeTimerLimitSeconds,
    loading,
    error
  };
}
