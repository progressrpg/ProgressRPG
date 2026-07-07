import classNames from "classnames";

import {
  useEntitySearchInput,
  type SearchEntity,
} from "./useEntitySearchInput";
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
  /** Keep the results panel visible even without focus, e.g. for a persistent always-open list. */
  alwaysOpen?: boolean;
  /** Results to show when the query is empty (only used when alwaysOpen is set). */
  defaultResults?: SearchEntity[];
  /** Message shown in the panel when there are no results to display (only used when alwaysOpen is set). */
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
  alwaysOpen = false,
  defaultResults,
  emptyMessage = "Nothing here yet — keep typing to search or start something new.",
}: EntitySearchInputProps) {
  const {
    rootRef,
    canSearch,
    results,
    taskItems,
    activityItems,
    showGroupLabels,
    isDropdownOpen,
    activeHighlightedIndex,
    handleInputFocus,
    handleInputChange,
    handleKeyDown,
    commitSelection,
  } = useEntitySearchInput({
    type,
    value,
    onChange,
    onSelect,
    onCreate,
    disabled,
    searchEnabled,
    alwaysOpen,
    defaultResults,
  });

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

      {(isDropdownOpen || (alwaysOpen && canSearch)) && (
        <ul
          id={`${type}-entity-search-results`}
          className={classNames(styles.dropdown, { [styles.dropdownPersistent]: alwaysOpen })}
          role="listbox"
          aria-label={`${type} suggestions`}
        >
          {results.length === 0 ? (
            <li role="presentation" className={styles.emptyState}>
              {emptyMessage}
            </li>
          ) : (
            (() => {
              const renderItem = (entity: SearchEntity, index: number) => {
                const isHighlighted = index === activeHighlightedIndex;
                return (
                  <li key={`${entity.id}-${entity.name}`} className={styles.optionItem}>
                    <button
                      type="button"
                      role="option"
                      aria-selected={isHighlighted}
                      className={classNames(styles.optionButton, {
                        [styles.optionButtonActive]: isHighlighted,
                      })}
                      onMouseDown={(event) => event.preventDefault()}
                      onClick={() => commitSelection(entity)}
                    >
                      {entity.name}
                    </button>
                  </li>
                );
              };

              return (
                <>
                  {taskItems.length > 0 && (
                    <>
                      {showGroupLabels && (
                        <li role="presentation" className={styles.groupLabel}>Tasks</li>
                      )}
                      {taskItems.map((entity) => renderItem(entity, results.indexOf(entity)))}
                    </>
                  )}
                  {activityItems.length > 0 && (
                    <>
                      {showGroupLabels && (
                        <li role="presentation" className={styles.groupLabel}>Activities</li>
                      )}
                      {activityItems.map((entity) => renderItem(entity, results.indexOf(entity)))}
                    </>
                  )}
                </>
              );
            })()
          )}
        </ul>
      )}
    </div>
  );
}
