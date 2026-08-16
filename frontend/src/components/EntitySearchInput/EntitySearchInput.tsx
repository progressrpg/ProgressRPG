import { useEffect, useRef } from "react";
import type { CSSProperties, KeyboardEvent } from "react";
import classNames from "classnames";

import { useEntitySearchInput, type SearchEntity } from "./useEntitySearchInput";
import styles from "./EntitySearchInput.module.scss";

interface EntitySearchInputProps {
  type: "activity" | "task";
  value: string;
  onChange?: (value: string) => void;
  onSelect?: (entity: SearchEntity) => void;
  onCreate?: (name: string) => void | Promise<void>;
  placeholder?: string;
  ariaLabel?: string;
  className?: string;
  inputClassName?: string;
  disabled?: boolean;
  searchEnabled?: boolean;
  /** Shown in place of Fuse results when the query is blank. */
  defaultResults?: SearchEntity[];
  /** Keep the dropdown open regardless of focus (persistent list mode). */
  alwaysOpen?: boolean;
  /** Cap the combined (task + activity) rows rendered, regardless of source. */
  maxVisibleRows?: number;
  /** Shown instead of the list when alwaysOpen is set and there are no rows. */
  emptyMessage?: string;
}

export default function EntitySearchInput({
  type,
  value,
  onChange,
  onSelect,
  onCreate,
  placeholder = "",
  ariaLabel,
  className,
  inputClassName,
  disabled = false,
  searchEnabled = true,
  defaultResults,
  alwaysOpen = false,
  maxVisibleRows,
  emptyMessage,
}: EntitySearchInputProps) {
  const {
    canSearch,
    taskItems,
    activityItems,
    showGroupLabels,
    isDropdownOpen,
    activeHighlightedIndex,
    handleInputFocus,
    handleInputChange,
    commitSelection,
    onSelectNext,
    onSelectPrevious,
    onDismiss,
    onCommit,
  } = useEntitySearchInput({
    type,
    value,
    onChange,
    onSelect,
    onCreate,
    disabled,
    searchEnabled,
    defaultResults,
    alwaysOpen,
    maxVisibleRows,
  });

  const rootRef = useRef<HTMLDivElement>(null);

  // Dismiss on outside click — the hook exposes the semantic action, this
  // component owns the DOM listener that detects the gesture.
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        onDismiss();
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [onDismiss]);

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (disabled) return;

    switch (event.key) {
      case "ArrowDown":
        if (isDropdownOpen) event.preventDefault();
        onSelectNext();
        return;
      case "ArrowUp":
        if (isDropdownOpen) event.preventDefault();
        onSelectPrevious();
        return;
      case "Escape":
        if (isDropdownOpen) event.preventDefault();
        onDismiss();
        return;
      case "Enter":
        if (onCommit()) event.preventDefault();
        return;
      default:
        return;
    }
  };

  const renderOption = (entity: SearchEntity, index: number) => {
    const isHighlighted = index === activeHighlightedIndex;
    return (
      // role="option" lives on the <li> itself, not a nested button: a
      // listbox's immediate children must carry the option role directly
      // (axe's aria-required-children), so an <option> role one level
      // deeper (on a button inside the <li>) doesn't satisfy it.
      <li
        key={`${entity.id}-${entity.name}`}
        role="option"
        aria-selected={isHighlighted}
        className={styles.optionItem}
      >
        <div
          className={classNames(styles.optionButton, {
            [styles.optionButtonActive]: isHighlighted,
          })}
          onMouseDown={(event) => event.preventDefault()}
          onClick={() => commitSelection(entity)}
        >
          {entity.name}
        </div>
      </li>
    );
  };

  // Persistent mode reserves room for maxVisibleRows (worst case: both group
  // labels shown) so the list settling to fewer rows, or falling back to
  // emptyMessage, doesn't reflow whatever sits below it.
  const persistentMinHeightStyle =
    alwaysOpen && typeof maxVisibleRows === "number"
      ? ({
          "--entity-search-persistent-min-height": `calc(${maxVisibleRows} * 2.75rem + 2 * 1.75rem)`,
        } as CSSProperties)
      : undefined;

  return (
    <div ref={rootRef} className={classNames(styles.root, className)}>
      <input
        type="text"
        role="combobox"
        value={value}
        onChange={(event) => handleInputChange(event.target.value)}
        onFocus={handleInputFocus}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        aria-label={ariaLabel}
        aria-autocomplete={canSearch ? "list" : "none"}
        aria-expanded={isDropdownOpen}
        aria-controls={isDropdownOpen ? `${type}-entity-search-results` : undefined}
        className={classNames(styles.input, inputClassName)}
        disabled={disabled}
      />

      {isDropdownOpen && (
        <ul
          id={`${type}-entity-search-results`}
          className={classNames(styles.dropdown, { [styles.dropdownPersistent]: alwaysOpen })}
          role="listbox"
          aria-label={`${type} suggestions`}
          style={persistentMinHeightStyle}
        >
          {taskItems.length > 0 && (
            <>
              {showGroupLabels && (
                <li role="presentation" className={styles.groupLabel}>Tasks</li>
              )}
              {taskItems.map(({ entity, index }) => renderOption(entity, index))}
            </>
          )}
          {activityItems.length > 0 && (
            <>
              {showGroupLabels && (
                <li role="presentation" className={styles.groupLabel}>Activities</li>
              )}
              {activityItems.map(({ entity, index }) => renderOption(entity, index))}
            </>
          )}
        </ul>
      )}

      {alwaysOpen && !isDropdownOpen && emptyMessage && (
        <p className={styles.emptyMessage} style={persistentMinHeightStyle}>
          {emptyMessage}
        </p>
      )}
    </div>
  );
}
