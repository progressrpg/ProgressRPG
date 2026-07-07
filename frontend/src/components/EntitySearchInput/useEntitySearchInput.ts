import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
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
  /** Keep the results panel visible even without focus, e.g. for a persistent always-open list. */
  alwaysOpen?: boolean;
  /** Results to show when the query is empty (only used when alwaysOpen is set). */
  defaultResults?: SearchEntity[];
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
  defaultResults = [],
}: {
  entities: SearchEntity[];
  value: string;
  canSearch: boolean;
  defaultResults?: SearchEntity[];
}) {
  const [debouncedQuery, setDebouncedQuery] = useState(value);

  const normalizedValue = useMemo(() => normalizeQuery(value), [value]);

  const searchableEntities = useMemo(
    () => entities.map((entity) => ({ ...entity, nameKey: getEntityNameKey(entity.name) })),
    [entities]
  );

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setDebouncedQuery(value);
    }, DEBOUNCE_MS);

    return () => window.clearTimeout(timeoutId);
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
    if (!query) return defaultResults;
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

    return [...taskResults, ...activityResults];
  }, [rawResults]);

  const taskItems = useMemo(() => results.filter((result) => result.source === "task"), [results]);
  const activityItems = useMemo(
    () => results.filter((result) => result.source !== "task"),
    [results]
  );

  return {
    results,
    taskItems,
    activityItems,
  };
}

function useEntitySearchDropdown(rootRef: React.RefObject<HTMLDivElement | null>) {
  const [isFocused, setIsFocused] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        setIsFocused(false);
        setHighlightedIndex(-1);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [rootRef]);

  return {
    isFocused,
    setIsFocused,
    highlightedIndex,
    setHighlightedIndex,
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
  alwaysOpen = false,
  defaultResults,
}: UseEntitySearchInputProps) {
  const rootRef = useRef<HTMLDivElement>(null);
  const { entities, addEntityToCache } = useEntitySearchCache(type);

  const canSearch = searchEnabled && !disabled;

  const { isFocused, setIsFocused, highlightedIndex, setHighlightedIndex } =
    useEntitySearchDropdown(rootRef);

  const { results, taskItems, activityItems } = useEntitySearchResults({
    entities,
    value,
    canSearch,
    defaultResults,
  });

  const isDropdownOpen = alwaysOpen ? canSearch : isFocused && results.length > 0;

  const activeHighlightedIndex =
    highlightedIndex >= 0 && highlightedIndex < results.length ? highlightedIndex : -1;

  const showGroupLabels = taskItems.length > 0 && activityItems.length > 0;

  const commitSelection = useCallback(
    (entity: SearchEntity) => {
      onChange?.(entity.name);
      onSelect?.(entity);
      setIsFocused(false);
      setHighlightedIndex(-1);
    },
    [onChange, onSelect, setHighlightedIndex, setIsFocused]
  );

  const commitCreate = useCallback(async () => {
    const nextName = normalizeQuery(value);
    if (!nextName) return;

    addEntityToCache(nextName);
    onChange?.(nextName);
    await onCreate?.(nextName);
    setIsFocused(false);
    setHighlightedIndex(-1);
  }, [addEntityToCache, onChange, onCreate, setHighlightedIndex, setIsFocused, value]);

  const handleInputFocus = useCallback(() => {
    setIsFocused(true);
  }, [setIsFocused]);

  const handleInputChange = useCallback(
    (nextValue: string) => {
      onChange?.(nextValue);
    },
    [onChange]
  );

  const handleKeyDown = useCallback(
    async (event: KeyboardEvent<HTMLInputElement>) => {
      if (disabled) return;

      if (event.key === "ArrowDown" && isDropdownOpen) {
        event.preventDefault();
        setHighlightedIndex(
          activeHighlightedIndex < results.length - 1 ? activeHighlightedIndex + 1 : 0
        );
        return;
      }

      if (event.key === "ArrowUp" && isDropdownOpen) {
        event.preventDefault();
        setHighlightedIndex(
          activeHighlightedIndex > 0 ? activeHighlightedIndex - 1 : results.length - 1
        );
        return;
      }

      if (event.key === "Escape") {
        if (isDropdownOpen) {
          event.preventDefault();
        }
        setIsFocused(false);
        setHighlightedIndex(-1);
        return;
      }

      if (event.key !== "Enter") return;

      if (!canSearch) {
        return;
      }

      const hasHighlightedResult =
        isDropdownOpen &&
        activeHighlightedIndex >= 0 &&
        activeHighlightedIndex < results.length;

      if (hasHighlightedResult) {
        event.preventDefault();
        commitSelection(results[activeHighlightedIndex]);
        return;
      }

      if (normalizeQuery(value)) {
        event.preventDefault();
        await commitCreate();
      }
    },
    [
      activeHighlightedIndex,
      canSearch,
      commitCreate,
      commitSelection,
      disabled,
      isDropdownOpen,
      results,
      setHighlightedIndex,
      setIsFocused,
      value,
    ]
  );

  return {
    rootRef,
    canSearch,
    results,
    taskItems,
    activityItems,
    showGroupLabels,
    isDropdownOpen,
    activeHighlightedIndex,
    highlightedIndex,
    handleInputFocus,
    handleInputChange,
    handleKeyDown,
    commitSelection,
  };
}
