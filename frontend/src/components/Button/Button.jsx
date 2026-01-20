import React from 'react';
import classNames from 'classnames';
import styles from './Button.module.scss';

export default function Button({
  children,
  variant = 'primary', // or 'secondary', 'ghost', etc.
  icon = null,
  as = 'button', // can be 'a' or 'button'
  href,
  onClick,
  className,
  disabled = false,
  type = 'button',
  ariaLabel,
  ariaDescribedBy,
  ...props
}) {
  const Component = as === 'a' ? 'a' : 'button';

  return (
    <Component
      className={classNames(
        styles.button,
        styles[variant],
        { [styles.disabled]: disabled },
        className
      )}
      href={as === 'a' ? href : undefined}
      onClick={onClick}
      type={as === 'button' ? type : undefined}
      disabled={as === 'button' ? disabled : undefined}
      aria-disabled={disabled}
      aria-label={ariaLabel}
      aria-describedby={ariaDescribedBy}
      role={as === 'a' && onClick ? 'button' : undefined}
      {...props}
    >
      {icon && <span className={styles.icon} aria-hidden="true">{icon}</span>}
      {children}
    </Component>
  );
}

{/* USAGE EXAMPLES
     <Button>Default Button</Button>

<Button variant="secondary" fullWidth>
  Full Width Secondary
</Button>

<Button as="a" href="/register" icon={<UserIcon />}>
  Sign Up
</Button>
 */}
