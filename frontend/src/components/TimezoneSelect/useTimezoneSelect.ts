import { useCallback, useMemo, useState } from "react";
import type { TimezoneChoice } from "../../types/api";

interface UseTimezoneSelectArgs {
  options: TimezoneChoice[];
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

// Caps the rendered list so typing a broad query (or focusing with an empty
// query, which matches everything) doesn't mount ~400 <li> nodes at once -
// narrowing the query trims the list back down, same as any typeahead.
const MAX_VISIBLE_OPTIONS = 50;

export function useTimezoneSelect({
  options,
  value,
  onChange,
  disabled,
}: UseTimezoneSelectArgs) {
  const selectedLabel = useMemo(
    () => options.find((option) => option.value === value)?.label ?? value,
    [options, value]
  );

  const [query, setQuery] = useState(selectedLabel);
  const [isOpen, setIsOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);

  // Keep the input's displayed text in sync when the selected value changes
  // from outside (e.g. another tab's save, or the "use detected" hint).
  // Adjusted during render rather than in an effect - React's documented
  // pattern for syncing state to a changed prop without an extra render
  // pass (react.dev/learn/you-might-not-need-an-effect).
  const [prevSelectedLabel, setPrevSelectedLabel] = useState(selectedLabel);
  if (selectedLabel !== prevSelectedLabel) {
    setPrevSelectedLabel(selectedLabel);
    setQuery(selectedLabel);
  }

  const filteredOptions = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    const matches =
      normalizedQuery === "" || normalizedQuery === selectedLabel.toLowerCase()
        ? options
        : options.filter((option) =>
            option.label.toLowerCase().includes(normalizedQuery)
          );
    return matches.slice(0, MAX_VISIBLE_OPTIONS);
  }, [options, query, selectedLabel]);

  // Stable-identity handlers (useCallback, correct deps) rather than plain
  // closures: TimezoneSelect subscribes closeDropdown to a document
  // mousedown listener, and a bare closure recreated every render would
  // otherwise get captured once by an empty-deps effect - permanently
  // pinned to whatever `selectedLabel` was at mount (see EntitySearchInput's
  // useEntitySearchInput for the same pattern with onDismiss).
  const openDropdown = useCallback(() => {
    if (disabled) return;
    setIsOpen(true);
    setHighlightedIndex(-1);
  }, [disabled]);

  const closeDropdown = useCallback(() => {
    setIsOpen(false);
    setHighlightedIndex(-1);
    // Revert to the last committed selection - an abandoned query shouldn't
    // linger in the box looking like it was applied.
    setQuery(selectedLabel);
  }, [selectedLabel]);

  const handleQueryChange = useCallback(
    (nextQuery: string) => {
      if (disabled) return;
      setQuery(nextQuery);
      setIsOpen(true);
      setHighlightedIndex(-1);
    },
    [disabled]
  );

  const commitSelection = useCallback(
    (option: TimezoneChoice) => {
      onChange(option.value);
      setQuery(option.label);
      setIsOpen(false);
      setHighlightedIndex(-1);
    },
    [onChange]
  );

  const selectHighlighted = useCallback((): boolean => {
    if (!isOpen || highlightedIndex < 0) return false;
    const option = filteredOptions[highlightedIndex];
    if (!option) return false;
    commitSelection(option);
    return true;
  }, [isOpen, highlightedIndex, filteredOptions, commitSelection]);

  const moveHighlight = useCallback(
    (delta: number) => {
      if (!isOpen) {
        openDropdown();
        return;
      }
      setHighlightedIndex((current) => {
        const count = filteredOptions.length;
        if (count === 0) return -1;
        const next = current + delta;
        if (next < 0) return count - 1;
        if (next >= count) return 0;
        return next;
      });
    },
    [isOpen, filteredOptions.length, openDropdown]
  );

  return {
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
  };
}
