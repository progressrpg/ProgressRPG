import { useCallback, useEffect, useMemo, useState } from "react";
import Fuse from "fuse.js";

import { useEntitySearchCache } from "../../hooks/useEntitySearchCache";

const MIN_QUERY_LENGTH = 2;
const DEBOUNCE_MS = 90;
const MAX_RESULTS = 8;

export interface SearchEntity {
  id: number | string;
  name: string;
  nameKey?: string;
  taskId?: number | null;
  source?: string;
}

interface UseEntitySearchInputProps {
  type: "activity" | "task";
  value: string;
  onChange?: (value: string) => void;
  onSelect?: (entity: SearchEntity) => void;
  onCreate?: (name: string) => void | Promise<void>;
  disabled?: boolean;
  searchEnabled?: boolean;
  /** Shown in place of Fuse results when the query is blank. */
  defaultResults?: SearchEntity[];
  /** Keep the dropdown open regardless of focus (persistent list mode). */
  alwaysOpen?: boolean;
  /** Cap the combined (task + activity) rows rendered, regardless of source. */
  maxVisibleRows?: number;
}

function normalizeQuery(value: string | undefined): string {
  return typeof value === "string" ? value.trim().replace(/\s+/g, " ") : "";
}

function getEntityNameKey(name: string): string {
  return normalizeQuery(name).toLowerCase();
}

function useEntitySearchResults({
  entities,
  value,
  canSearch,
  defaultResults,
  maxVisibleRows,
}: {
  entities: SearchEntity[];
  value: string;
  canSearch: boolean;
  defaultResults?: SearchEntity[];
  maxVisibleRows?: number;
}) {
  const [debouncedQuery, setDebouncedQuery] = useState(value);

  const normalizedValue = useMemo(() => normalizeQuery(value), [value]);

  const searchableEntities = useMemo(
    () => entities.map((entity) => ({ ...entity, nameKey: getEntityNameKey(entity.name) })),
    [entities]
  );

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      setDebouncedQuery(value);
    }, DEBOUNCE_MS);

    return () => clearTimeout(timeoutId);
  }, [value]);

  const fuse = useMemo(
    () =>
      new Fuse(searchableEntities, {
        keys: ["name"],
        threshold: 0.35,
        ignoreLocation: true,
        minMatchCharLength: MIN_QUERY_LENGTH,
      }),
    [searchableEntities]
  );

  const rawResults = useMemo(() => {
    if (!canSearch) return [];

    const query = normalizeQuery(debouncedQuery);
    if (!query) return defaultResults ?? [];
    if (query.length < MIN_QUERY_LENGTH) return [];

    const queryKey = getEntityNameKey(query);
    const currentValueKey = getEntityNameKey(normalizedValue);

    const directPrefixMatches: typeof searchableEntities = [];
    const directIncludesMatches: typeof searchableEntities = [];

    for (const entity of searchableEntities) {
      if (entity.source !== "task" && entity.nameKey === currentValueKey) continue;

      if (entity.nameKey.startsWith(queryKey)) {
        directPrefixMatches.push(entity);
      } else if (entity.nameKey.includes(queryKey)) {
        directIncludesMatches.push(entity);
      }

      if (directPrefixMatches.length + directIncludesMatches.length >= MAX_RESULTS) {
        break;
      }
    }

    const directMatches = [...directPrefixMatches, ...directIncludesMatches].slice(0, MAX_RESULTS);
    if (directMatches.length >= MAX_RESULTS) {
      return directMatches;
    }

    const uniqueResults: typeof searchableEntities = [];
    const seenNames = new Set(directMatches.map((entity) => entity.nameKey));

    uniqueResults.push(...directMatches);

    fuse
      .search(query, { limit: MAX_RESULTS })
      .map((result) => result.item)
      .filter((entity) => entity.source === "task" || entity.nameKey !== currentValueKey)
      .forEach((entity) => {
        const key = entity.nameKey;
        if (!seenNames.has(key)) {
          seenNames.add(key);
          uniqueResults.push(entity);
        }
      });

    return uniqueResults.slice(0, MAX_RESULTS);
  }, [canSearch, debouncedQuery, defaultResults, fuse, normalizedValue, searchableEntities]);

  const results = useMemo(() => {
    const taskResults = rawResults.filter((result) => result.source === "task");
    const taskNames = new Set(taskResults.map((result) => result.nameKey));
    const activityResults = rawResults.filter(
      (result) => result.source !== "task" && !taskNames.has(result.nameKey ?? "")
    );

    const combined = [...taskResults, ...activityResults];
    return typeof maxVisibleRows === "number" ? combined.slice(0, maxVisibleRows) : combined;
  }, [rawResults, maxVisibleRows]);

  const { taskItems, activityItems } = useMemo(() => {
    const taskItems: Array<{ entity: SearchEntity; index: number }> = [];
    const activityItems: Array<{ entity: SearchEntity; index: number }> = [];

    results.forEach((entity, index) => {
      (entity.source === "task" ? taskItems : activityItems).push({ entity, index });
    });

    return { taskItems, activityItems };
  }, [results]);

  return {
    results,
    taskItems,
    activityItems,
  };
}

function useEntitySearchDropdown() {
  const [isFocused, setIsFocused] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);

  const dismiss = useCallback(() => {
    setIsFocused(false);
    setHighlightedIndex(-1);
  }, []);

  return {
    isFocused,
    setIsFocused,
    highlightedIndex,
    setHighlightedIndex,
    dismiss,
  };
}

export function useEntitySearchInput({
  type,
  value,
  onChange,
  onSelect,
  onCreate,
  disabled = false,
  searchEnabled = true,
  defaultResults,
  alwaysOpen = false,
  maxVisibleRows,
}: UseEntitySearchInputProps) {
  const { entities, addEntityToCache } = useEntitySearchCache(type);

  const canSearch = searchEnabled && !disabled;

  const { isFocused, setIsFocused, highlightedIndex, setHighlightedIndex, dismiss } =
    useEntitySearchDropdown();

  const { results, taskItems, activityItems } = useEntitySearchResults({
    entities,
    value,
    canSearch,
    defaultResults,
    maxVisibleRows,
  });

  const isDropdownOpen = alwaysOpen ? results.length > 0 : isFocused && results.length > 0;

  const activeHighlightedIndex =
    highlightedIndex >= 0 && highlightedIndex < results.length ? highlightedIndex : -1;

  const showGroupLabels = taskItems.length > 0 && activityItems.length > 0;

  const commitSelection = useCallback(
    (entity: SearchEntity) => {
      onChange?.(entity.name);
      onSelect?.(entity);
      dismiss();
    },
    [onChange, onSelect, dismiss]
  );

  const commitCreate = useCallback(async () => {
    const nextName = normalizeQuery(value);
    if (!nextName) return;

    addEntityToCache(nextName);
    onChange?.(nextName);
    await onCreate?.(nextName);
    dismiss();
  }, [addEntityToCache, onChange, onCreate, dismiss, value]);

  const handleInputFocus = useCallback(() => {
    setIsFocused(true);
  }, [setIsFocused]);

  const handleInputChange = useCallback(
    (nextValue: string) => {
      onChange?.(nextValue);
    },
    [onChange]
  );

  /** Move the highlight to the next result, wrapping to the top. No-op while closed. */
  const onSelectNext = useCallback(() => {
    if (!isDropdownOpen) return;
    setHighlightedIndex(activeHighlightedIndex < results.length - 1 ? activeHighlightedIndex + 1 : 0);
  }, [activeHighlightedIndex, isDropdownOpen, results.length, setHighlightedIndex]);

  /** Move the highlight to the previous result, wrapping to the bottom. No-op while closed. */
  const onSelectPrevious = useCallback(() => {
    if (!isDropdownOpen) return;
    setHighlightedIndex(activeHighlightedIndex > 0 ? activeHighlightedIndex - 1 : results.length - 1);
  }, [activeHighlightedIndex, isDropdownOpen, results.length, setHighlightedIndex]);

  /** Close the dropdown and clear the highlight, e.g. on Escape or an outside click/tap. */
  const onDismiss = useCallback(() => {
    dismiss();
  }, [dismiss]);

  /**
   * Commit the highlighted result, or create a new entity from the typed
   * value when nothing is highlighted. Returns whether it took action, so
   * callers translating a "commit" gesture (e.g. Enter) know whether to
   * suppress its default behaviour.
   */
  const onCommit = useCallback(() => {
    if (!canSearch) return false;

    const hasHighlightedResult =
      isDropdownOpen && activeHighlightedIndex >= 0 && activeHighlightedIndex < results.length;

    if (hasHighlightedResult) {
      commitSelection(results[activeHighlightedIndex]);
      return true;
    }

    if (normalizeQuery(value)) {
      void commitCreate();
      return true;
    }

    return false;
  }, [activeHighlightedIndex, canSearch, commitCreate, commitSelection, isDropdownOpen, results, value]);

  return {
    canSearch,
    results,
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
  };
}
