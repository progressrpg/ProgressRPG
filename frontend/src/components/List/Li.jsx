import React from 'react';
import classNames from 'classnames';
import styles from './List.module.scss';

export default function Li({
  children,
  className,
  isSelected = false,
  isHidden = false,
  tone = 'neutral',
  ...rest
}) {
  const toneClass =
    tone === 'player'
      ? styles.tonePlayer
      : tone === 'character'
      ? styles.toneCharacter
      : undefined;

  return (
    <li
      className={classNames(
        styles.listItem,
        className,
        toneClass,
        {
          [styles.selected]: isSelected,
          [styles.hidden]: isHidden,
        },
      )}
      {...rest}
    >
      {children}
    </li>
  );
}
