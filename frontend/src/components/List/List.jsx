import React from 'react';
import classNames from 'classnames';
import styles from './List.module.scss';

export default function List({
  items = [],
  renderItem,
  getKey,
  onSelect,
  selectedItem,
  selectable = false,
  className,
  sectionClass,
  getItemClassName,
  ariaLabel,
}) {
  if (!Array.isArray(items)) {
    items = Array.isArray(items.results) ? items.results : [];
  }

  const handleKeyPress = (e, item) => {
    if (selectable && (e.key === 'Enter' || e.key === ' ')) {
      e.preventDefault();
      onSelect?.(item);
    }
  };

  return (
    <section className={classNames(styles.listSection, sectionClass)}>
      <ul
        className={classNames(styles.list, {
          [styles.selectable]: selectable,
        }, className)}
        role={selectable ? 'listbox' : 'list'}
        aria-label={ariaLabel}
      >
        {items.map((item, index) => {
          const isSelected = item === selectedItem;
          const isHidden = item.isHidden;
          const itemClass = getItemClassName?.(item, index);

          return (
            <li
              key={getKey ? getKey(item, index) : (item.id || index)}
              className={classNames(itemClass, {
                [styles.selected]: isSelected,
                [styles.hidden]: isHidden,
              })}
              onClick={() => selectable && onSelect?.(item)}
              onKeyPress={(e) => handleKeyPress(e, item)}
              role={selectable ? 'option' : 'listitem'}
              aria-selected={selectable ? isSelected : undefined}
              tabIndex={selectable ? 0 : undefined}
            >
              {renderItem ? renderItem(item, index) : item}
            </li>
          );
        })}
      </ul>
    </section>
  );
}


// EXAMPLE USAGE
/*
const items = ['Apples', 'Bananas', 'Cherries'];

export default function FruitList() {
  const [selected, setSelected] = React.useState(null);

  return (
    <List
      items={items}
      selectable
      selectedItem={selected}
      onSelect={setSelected}
      renderItem={(item) => <span>{item}</span>}
    />
  );
}

 */
