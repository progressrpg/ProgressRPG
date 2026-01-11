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
  ...props
}) {
  const Component = as === 'a' ? 'a' : 'button';

  return (
    <Component
      className={classNames(
        styles.button,
        styles[variant],
        className
      )}
      href={as === 'a' ? href : undefined}
      onClick={onClick}
      {...props}
    >
      {icon && <span className={styles.icon}>{icon}</span>}
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
