import React from 'react';
import classNames from 'classnames';
import styles from './List.module.scss';
import Li from './Li';

export default function List({
  items = [],
  renderItem,
  getKey,
  onSelect,
  selectedItem,
  canSelect = false,
  canHover = false,
  itemTone = 'neutral',
  className,
  sectionClass,
  getItemClassName,
  getItemTone,
  ariaLabel,
}) {
  if (!Array.isArray(items)) {
    items = Array.isArray(items.results) ? items.results : [];
  }

  const handleKeyPress = (e, item) => {
    if (canSelect && (e.key === 'Enter' || e.key === ' ')) {
      e.preventDefault();
      onSelect?.(item);
    }
  };

  return (
    <section className={classNames(styles.listSection, sectionClass)}>
      <ul
        className={classNames(styles.list, {
          [styles.canSelect]: canSelect,
          [styles.canHover]: canHover,
        }, className)}
        role={canSelect ? 'listbox' : 'list'}
        aria-label={ariaLabel}
      >
        {items.map((item, index) => {
          {/* const isSelected = item === selectedItem;
          const isHidden = item.isHidden; */}
          const itemClass = getItemClassName?.(item, index);
          const itemToneValue = getItemTone?.(item, index) ?? itemTone;

          const tone = item.player ? 'player' : item.character ? 'character' : 'neutral';
          return (
            <Li
              key={getKey ? getKey(item, index) : (item.id || index)}
              className={itemClass}
              isSelected={item === selectedItem}
              isHidden={item.isHidden}
              tone={tone}
              onClick={() => canSelect && onSelect?.(item)}
              onKeyDown={(e) => handleKeyPress(e, item)}
              role={canSelect ? 'option' : 'listitem'}
              aria-selected={canSelect ? isSelected : undefined}
              tabIndex={canSelect ? 0 : undefined}
            >
              {renderItem ? renderItem(item, index) : item}
            </Li>
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
      canSelect
      selectedItem={selected}
      onSelect={setSelected}
      renderItem={(item) => <span>{item}</span>}
    />
  );
}

 */
