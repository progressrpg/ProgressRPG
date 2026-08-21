import React from 'react';
import classNames from 'classnames';
import styles from './Button.module.scss';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children?: React.ReactNode;
  variant?: string;
  size?: 'default' | 'small';
  icon?: React.ReactNode;
  as?: 'button' | 'a';
  href?: string;
  onClick?: React.MouseEventHandler<HTMLButtonElement | HTMLAnchorElement>;
  className?: string;
  disabled?: boolean;
  type?: 'button' | 'submit' | 'reset';
  ariaLabel?: string;
  ariaDescribedBy?: string;
  /** Never used - discarded to prevent Tamagui asChild leakage. See destructuring below. */
  onPress?: unknown;
  /** Extra HTML attributes forwarded to the underlying element. */
  [key: string]: unknown;
}

export default function Button({
  children,
  variant = 'primary',
  size = 'default',
  icon = null,
  as = 'button',
  href,
  onClick,
  className,
  disabled = false,
  type = 'button',
  ariaLabel,
  ariaDescribedBy,
  // Tamagui's `asChild` cloning (e.g. Popover.Trigger) always injects an
  // `onPress` prop onto its child, even when the toggle behaviour it drives
  // is disabled - see Popover.tsx's Trigger comment. `Button` is a plain
  // DOM component, not RN-style, so it must be dropped here rather than
  // spread onto the underlying element, which React logs as an unknown
  // DOM event handler.
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  onPress: _onPress,
  ...props
}: ButtonProps) {
  const Component = as === 'a' ? 'a' : 'button';

  return (
    <Component
      className={classNames(
        styles.button,
        styles[variant],
        { [styles.small]: size === 'small' },
        { [styles.disabled]: disabled },
        className
      )}
      href={as === 'a' ? href : undefined}
      onClick={onClick as React.MouseEventHandler<HTMLButtonElement & HTMLAnchorElement>}
      type={as === 'button' ? type : undefined}
      disabled={as === 'button' ? disabled : undefined}
      aria-disabled={disabled}
      aria-label={ariaLabel}
      aria-describedby={ariaDescribedBy}
      role={as === 'a' && onClick ? 'button' : undefined}
      {...(props as Record<string, unknown>)}
    >
      {icon && <span className={styles.icon} aria-hidden="true">{icon}</span>}
      {children}
    </Component>
  );
}
