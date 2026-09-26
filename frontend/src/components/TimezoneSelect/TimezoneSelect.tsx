import { useEffect, useRef } from "react";
import type { KeyboardEvent } from "react";
import classNames from "classnames";

import { useTimezoneSelect } from "./useTimezoneSelect";
import type { TimezoneChoice } from "../../types/api";
import styles from "./TimezoneSelect.module.scss";

const optionId = (index: number) => `timezone-select-option-${index}`;

interface TimezoneSelectProps {
  options: TimezoneChoice[];
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  ariaLabel?: string;
  id?: string;
  className?: string;
}

export default function TimezoneSelect({
  options,
  value,
  onChange,
  disabled = false,
  ariaLabel = "Timezone",
  id,
  className,
}: TimezoneSelectProps) {
  const {
    query,
    isOpen,
    highlightedIndex,
    filteredOptions,
    openDropdown,
    closeDropdown,
    handleQueryChange,
    commitSelection,
    selectHighlighted,
    moveHighlight,
  } = useTimezoneSelect({ options, value, onChange, disabled });

  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        closeDropdown();
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [closeDropdown]);

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (disabled) return;

    switch (event.key) {
      case "ArrowDown":
        event.preventDefault();
        moveHighlight(1);
        return;
      case "ArrowUp":
        event.preventDefault();
        moveHighlight(-1);
        return;
      case "Escape":
        if (isOpen) event.preventDefault();
        closeDropdown();
        return;
      case "Enter":
        if (selectHighlighted()) event.preventDefault();
        return;
      default:
        return;
    }
  };

  return (
    <div ref={rootRef} className={classNames(styles.root, className)}>
      <input
        id={id}
        type="text"
        role="combobox"
        value={query}
        onChange={(event) => handleQueryChange(event.target.value)}
        onFocus={openDropdown}
        onKeyDown={handleKeyDown}
        aria-label={ariaLabel}
        aria-autocomplete="list"
        aria-expanded={isOpen}
        aria-controls={isOpen ? "timezone-select-results" : undefined}
        aria-activedescendant={
          isOpen && highlightedIndex >= 0 ? optionId(highlightedIndex) : undefined
        }
        className={styles.input}
        disabled={disabled}
        autoComplete="off"
      />

      {isOpen && (
        <ul
          id="timezone-select-results"
          className={styles.dropdown}
          role="listbox"
          aria-label="Timezone suggestions"
        >
          {filteredOptions.length === 0 && (
            <li role="presentation" className={styles.emptyMessage}>
              No matching timezones
            </li>
          )}
          {filteredOptions.map((option, index) => (
            <li
              key={option.value}
              id={optionId(index)}
              role="option"
              aria-selected={index === highlightedIndex}
              className={styles.optionItem}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => commitSelection(option)}
            >
              <div
                className={classNames(styles.optionButton, {
                  [styles.optionButtonActive]: index === highlightedIndex,
                  [styles.optionButtonSelected]: option.value === value,
                })}
              >
                {option.label}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
