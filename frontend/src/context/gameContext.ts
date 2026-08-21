import { createContext } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import type {
  Player,
  Character,
  XpModifier,
  PlayerActivity,
  CharacterActivity,
  PopulationCentre,
  GameSettings,
  LoginState,
  ActivityTimerReturn,
} from '../types';

export interface GameContextValue {
  player: Player | null;
  setPlayer: Dispatch<SetStateAction<Player | null>>;
  character: Character | null;
  setCharacter: Dispatch<SetStateAction<Character | null>>;
  xpMods: XpModifier[];
  setXpMods: Dispatch<SetStateAction<XpModifier[]>>;
  fetchPlayerAndCharacter: () => Promise<void>;
  activityTimer: ActivityTimerReturn;
  playerActivities: PlayerActivity[];
  characterActivities: CharacterActivity[];
  fetchActivities: () => Promise<void>;
  fetchCharacterCurrent: () => Promise<CharacterActivity | null>;
  characterCurrentActivity: CharacterActivity | null;
  setCharacterCurrentActivity: Dispatch<SetStateAction<CharacterActivity | null>>;
  populationCentre: PopulationCentre | null;
  fetchPopulationCentre: (pcId: number) => Promise<PopulationCentre>;
  loginState: LoginState;
  loginStreak: number;
  loginEventAt: string | null;
  loginRewardXp: number;
  announcementUnreadCount: number;
  setAnnouncementUnreadCount: Dispatch<SetStateAction<number>>;
  loading: boolean;
  buildNumber: string;
  freeTimerLimitSeconds: number;
  gameSettings: GameSettings | null;
  /** Online player count as of the initial bootstrap fetch; frozen after load.
   *  Live updates flow through OnlineCountContext instead, to avoid
   *  re-rendering every useGame() consumer on each websocket broadcast. */
  initialOnlineCount: number;
}

export const GameContext = createContext<GameContextValue | null>(null);
