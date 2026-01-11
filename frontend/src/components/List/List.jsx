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
}) {
  if (!Array.isArray(items)) {
    items = Array.isArray(items.results) ? items.results : [];
  }

  return (
    <section className={classNames(styles.listSection, sectionClass)}>
      <ul
        className={classNames(styles.list, {
          [styles.selectable]: selectable,
        }, className)}
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
