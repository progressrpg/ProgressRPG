import { useEffect, useState } from 'react';
import { apiFetch } from "../utils/api";
import { useAuth } from '../context/AuthContext';
import type {
  Player,
  Character,
  ActivityTimerApiData,
  PopulationCentre,
  XpModifier,
  LoginState,
  FetchInfoResponse,
  GameSettings,
} from '../types';

export function useBootstrapGameData() {
  const { isAuthenticated, loading: authLoading } = useAuth();

  const [player, setPlayer] = useState<Player | null>(null);
  const [character, setCharacter] = useState<Character | null>(null);
  const [activityTimerInfo, setActivityTimerInfo] = useState<ActivityTimerApiData | null>(null);
  const [populationCentreInfo, setPopulationCentreInfo] = useState<PopulationCentre | null>(null);
  const [xpMods, setXpMods] = useState<XpModifier[]>([]);
  const [loginState, setLoginState] = useState<LoginState>("none");
  const [loginStreak, setLoginStreak] = useState<number>(0);
  const [loginEventAt, setLoginEventAt] = useState<string | null>(null);
  const [loginRewardXp, setLoginRewardXp] = useState<number>(0);
  const [announcementUnreadCount, setAnnouncementUnreadCount] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [buildNumber, setBuildNumber] = useState<string | boolean>(true);
  const [freeTimerLimitSeconds, setFreeTimerLimitSeconds] = useState<number>(1800);
  const [gameSettings, setGameSettings] = useState<GameSettings | null>(null);
  const [onlineCount, setOnlineCount] = useState<number>(0);

  useEffect(() => {
    if (authLoading) return;

    if (!isAuthenticated) {
      const resetToLoggedOutDefaults = () => {
        setLoginState("none");
        setLoginStreak(0);
        setLoginEventAt(null);
        setLoginRewardXp(0);
        setLoading(false);
      };
      resetToLoggedOutDefaults();
      return;
    }

    const fetchGameData = async () => {
      try {
        setLoading(true);

        const info = await apiFetch<FetchInfoResponse>('/fetch_info/');
        // console.log("bootstrap info:", info);
        setPlayer(info.player);
        setCharacter(info.character);
        setActivityTimerInfo(info.activity_timer);
        setPopulationCentreInfo(info.population_centre);
        setXpMods(info.xp_mods || []);
        setLoginState(typeof info.login_state === 'string' ? info.login_state : 'none');
        setLoginStreak(Number(info.login_streak) || 0);
        setLoginEventAt(info.login_event_at || null);
        setLoginRewardXp(Number(info.login_reward_xp) || 0);
        setAnnouncementUnreadCount(Number(info.announcement_unread_count) || 0);
        setBuildNumber(info.build_number);
        setGameSettings(info.game_settings ?? null);
        setOnlineCount(Number(info.online_count) || 0);
        setFreeTimerLimitSeconds(info.game_settings?.free_timer_limit_seconds ?? info.free_timer_limit_seconds ?? 1800);
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
    loginRewardXp,
    announcementUnreadCount,
    buildNumber,
    freeTimerLimitSeconds,
    gameSettings,
    onlineCount,
    loading,
    error
  };
}
