import React, { useRef } from "react";
import classNames from "classnames";
import styles from "./ModeSwitcher.module.scss";

export interface ModeOption {
  key: string;
  label: string;
}

interface ModeSwitcherProps {
  modes: ModeOption[];
  activeKey: string;
  onSelect: (key: string) => void;
  ariaLabel?: string;
  className?: string;
}

export default function ModeSwitcher({
  modes,
  activeKey,
  onSelect,
  ariaLabel = "Mode",
  className,
}: ModeSwitcherProps): React.ReactElement {
  const chipRefs = useRef<Array<HTMLButtonElement | null>>([]);

  const focusAndSelect = (index: number) => {
    const wrapped = (index + modes.length) % modes.length;
    const target = modes[wrapped];
    chipRefs.current[wrapped]?.focus();
    onSelect(target.key);
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLButtonElement>, index: number) => {
    switch (event.key) {
      case "ArrowRight":
      case "ArrowDown":
        event.preventDefault();
        focusAndSelect(index + 1);
        break;
      case "ArrowLeft":
      case "ArrowUp":
        event.preventDefault();
        focusAndSelect(index - 1);
        break;
      case "Home":
        event.preventDefault();
        focusAndSelect(0);
        break;
      case "End":
        event.preventDefault();
        focusAndSelect(modes.length - 1);
        break;
      default:
        break;
    }
  };

  return (
    <div className={classNames(styles.radiogroup, className)} role="radiogroup" aria-label={ariaLabel}>
      {modes.map((mode, index) => {
        const isActive = mode.key === activeKey;
        return (
          <button
            key={mode.key}
            ref={(el) => {
              chipRefs.current[index] = el;
            }}
            type="button"
            role="radio"
            aria-checked={isActive}
            tabIndex={isActive ? 0 : -1}
            className={classNames(styles.chip, { [styles.active]: isActive })}
            onClick={() => onSelect(mode.key)}
            onKeyDown={(event) => handleKeyDown(event, index)}
          >
            {mode.label}
          </button>
        );
      })}
    </div>
  );
}
