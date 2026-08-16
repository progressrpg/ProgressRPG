import React from 'react';
import classNames from 'classnames';
import styles from './List.module.scss';
import Li from './Li';
import type { PaginatedResponse } from '../../types';

// List is generic over item shape — it doesn't need to know the item type
// as long as it has optional id/player/character/isHidden properties.
interface ListItem {
  id?: string | number;
  /** Present if this is a player activity */
  player?: unknown;
  /** Present if this is a character activity */
  character?: unknown;
  /** When true, item is visually hidden */
  isHidden?: boolean;
}

interface ListProps<T extends ListItem> {
  items?: T[] | PaginatedResponse<T>;
  renderItem?: (item: T, index: number) => React.ReactNode;
  getKey?: (item: T, index: number) => string | number;
  onSelect?: (item: T) => void;
  selectedItem?: T | null;
  canSelect?: boolean;
  /** Also exposed as selectable for legacy callers */
  selectable?: boolean;
  canHover?: boolean;
  /** Tighter item padding/gap - for lists nested inside an already-dense panel (e.g. BuildingDetail's residents/workers). */
  compact?: boolean;
  itemTone?: 'neutral' | 'player' | 'character';
  className?: string;
  sectionClass?: string;
  getItemClassName?: (item: T, index: number) => string | undefined;
  getItemTone?: (item: T, index: number) => 'neutral' | 'player' | 'character' | undefined;
  ariaLabel?: string;
}

export default function List<T extends ListItem>({
  items = [],
  renderItem,
  getKey,
  onSelect,
  selectedItem,
  canSelect = false,
  selectable = false,
  canHover = false,
  compact = false,
  itemTone = 'neutral',
  className,
  sectionClass,
  getItemClassName,
  getItemTone,
  ariaLabel,
}: ListProps<T>) {
  // Support both canSelect and the legacy selectable prop
  const isSelectable = canSelect || selectable;

  let normalizedItems: T[];
  if (!Array.isArray(items)) {
    normalizedItems = Array.isArray((items as PaginatedResponse<T>).results)
      ? (items as PaginatedResponse<T>).results
      : [];
  } else {
    normalizedItems = items;
  }

  const handleKeyPress = (e: React.KeyboardEvent<HTMLLIElement>, item: T) => {
    if (isSelectable && (e.key === 'Enter' || e.key === ' ')) {
      e.preventDefault();
      onSelect?.(item);
    }
  };

  return (
    <section className={classNames(styles.listSection, sectionClass)}>
      <ul
        className={classNames(styles.list, {
          [styles.canSelect]: isSelectable,
          [styles.canHover]: canHover,
          [styles.compact]: compact,
        }, className)}
        role={isSelectable ? 'listbox' : 'list'}
        aria-label={ariaLabel}
      >
        {normalizedItems.map((item, index) => {
          const isSelected = item === selectedItem;
          const itemClass = getItemClassName?.(item, index);
          const tone = getItemTone?.(item, index)
            ?? (item.player ? 'player' : item.character ? 'character' : itemTone);
          return (
            <Li
              key={getKey ? getKey(item, index) : (item.id as string | number | undefined) ?? index}
              className={itemClass}
              isSelected={isSelected}
              isHidden={Boolean(item.isHidden)}
              tone={tone}
              onClick={() => isSelectable && onSelect?.(item)}
              onKeyDown={(e) => handleKeyPress(e, item)}
              role={isSelectable ? 'option' : 'listitem'}
              aria-selected={isSelectable ? isSelected : undefined}
              tabIndex={isSelectable ? 0 : undefined}
            >
              {renderItem ? renderItem(item, index) : String(item)}
            </Li>
          );
        })}
      </ul>
    </section>
  );
}
