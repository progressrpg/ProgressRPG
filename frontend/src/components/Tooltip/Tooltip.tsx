import React from 'react';
import classNames from 'classnames';
import * as TooltipPrimitive from '@radix-ui/react-tooltip';
import styles from './Tooltip.module.scss';

type TooltipPlacement = 'top' | 'bottom' | 'left' | 'right';
type TooltipAlign = 'start' | 'center' | 'end';

interface TooltipProviderProps {
  children: React.ReactNode;
  delayDuration?: number;
  skipDelayDuration?: number;
  disableHoverableContent?: boolean;
}

interface TooltipProps {
  children: React.ReactElement;
  content: React.ReactNode;
  placement?: TooltipPlacement;
  align?: TooltipAlign;
  sideOffset?: number;
  className?: string;
  disabled?: boolean;
}

export function TooltipProvider({
  children,
  delayDuration = 250,
  skipDelayDuration = 100,
  disableHoverableContent = true,
}: TooltipProviderProps): React.ReactElement {
  return (
    <TooltipPrimitive.Provider
      delayDuration={delayDuration}
      skipDelayDuration={skipDelayDuration}
      disableHoverableContent={disableHoverableContent}
    >
      {children}
    </TooltipPrimitive.Provider>
  );
}

/**
 * Use tooltips only for supplementary context. The trigger must remain a
 * focusable interactive element, and any essential information should stay
 * available without requiring hover or focus.
 */
export default function Tooltip({
  children,
  content,
  placement = 'top',
  align = 'center',
  sideOffset = 8,
  className,
  disabled = false,
}: TooltipProps): React.ReactElement {
  const [open, setOpen] = React.useState(false);

  if (disabled || content === null || content === undefined || content === false) {
    return <>{children}</>;
  }

  // Radix's hover logic explicitly ignores touch pointers, and a tap's own
  // pointerdown/click still reach the trigger's built-in "close" handlers -
  // so on mobile the tooltip flashes open and is immediately closed by the
  // same tap that opened it. Toggling our own controlled state on touch
  // pointerdown (and preventDefault-ing, which per the Pointer Events spec
  // suppresses the compatibility click that would otherwise re-close it)
  // makes a tap behave like a real toggle instead.
  const handlePointerDown = (event: React.PointerEvent) => {
    if (event.pointerType !== 'touch') return;
    event.preventDefault();
    setOpen((prev) => !prev);
  };

  return (
    <TooltipPrimitive.Root open={open} onOpenChange={setOpen}>
      <TooltipPrimitive.Trigger asChild onPointerDown={handlePointerDown}>
        {children}
      </TooltipPrimitive.Trigger>
      <TooltipPrimitive.Portal>
        <TooltipPrimitive.Content
          className={classNames(styles.content, className)}
          side={placement}
          align={align}
          sideOffset={sideOffset}
          collisionPadding={8}
        >
          {content}
          <TooltipPrimitive.Arrow className={styles.arrow} width={10} height={6} />
        </TooltipPrimitive.Content>
      </TooltipPrimitive.Portal>
    </TooltipPrimitive.Root>
  );
}
