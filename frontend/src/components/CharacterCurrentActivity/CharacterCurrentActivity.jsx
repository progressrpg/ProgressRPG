// components/CharacterActivityCurrent/CharacterActivityCurrent.jsx
import { useEffect, useState } from "react";
import classNames from "classnames";
import { useGame } from "../../context/GameContext";
import { useWebSocket } from "../../context/WebSocketContext";
import styles from "./CharacterCurrentActivity.module.scss";

const fmtTime = (iso) =>
  iso
    ? new Date(iso).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      })
    : "";

export default function CharacterCurrentActivity() {
  const {
    character,
    characterCurrentActivity,
    fetchCharacterCurrent,
  } = useGame();
  
  const { addEventHandler } = useWebSocket();
  const [boostLevel, setBoostLevel] = useState('none');
  const [multiplier, setMultiplier] = useState(1.0);

  useEffect(() => {
    fetchCharacterCurrent();
  }, [fetchCharacterCurrent]);
  
  // Listen for boost events via WebSocket
  useEffect(() => {
    const handleBoostEvent = (data) => {
      if (data.type === 'character.boost' || data.action === 'character.boost') {
        const eventData = data.data || data;
        setBoostLevel(eventData.boost_level || 'none');
        setMultiplier(eventData.multiplier || 1.0);
      }
    };
    
    return addEventHandler(handleBoostEvent);
  }, [addEventHandler]);

  if (!character || !characterCurrentActivity) return null;

  const activityName =
    characterCurrentActivity.name?.trim().toLowerCase() ||
    characterCurrentActivity.kind;

  const startTime = fmtTime(characterCurrentActivity.started_at || characterCurrentActivity.scheduled_start);
  
  const getBoostIndicator = () => {
    switch(boostLevel) {
      case 'active':
        return ' 🔥🔥';
      case 'online': 
        return ' ✨';
      default:
        return '';
    }
  };
  
  const getBoostClass = () => {
    switch(boostLevel) {
      case 'active':
        return styles.boosted;
      case 'online':
        return styles.energized;
      default:
        return '';
    }
  };

  return (
    <div className={classNames(styles.line, getBoostClass())}>
      <strong>{character.first_name}</strong> began{" "}
      <span className={styles.activity}>
        {activityName}{getBoostIndicator()}
      </span>{" "}
      at <span className={styles.time}>{startTime}</span>
      {boostLevel !== 'none' && multiplier > 1.0 && (
        <span className={styles.multiplier}>
          {multiplier}x XP
        </span>
      )}
    </div>
  );
}
