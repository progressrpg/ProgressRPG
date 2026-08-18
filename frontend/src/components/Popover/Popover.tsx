import React from 'react';
import { Popover as PopoverPrimitive } from 'tamagui';

type PopoverSide = 'top' | 'bottom' | 'left' | 'right';
type PopoverAlign = 'start' | 'center' | 'end';

interface PopoverContextValue {
  open: boolean;
  setOpen: (open: boolean) => void;
  contentId: string;
}

const PopoverContext = React.createContext<PopoverContextValue | null>(null);

function usePopoverContext(componentName: string): PopoverContextValue {
  const context = React.useContext(PopoverContext);
  if (!context) {
    throw new Error(`Popover.${componentName} must be used within Popover.Root`);
  }
  return context;
}

// Radix positions via side/align/sideOffset on Content; Tamagui's underlying
// Popper resolves placement/offset up at the Root instead, so those props
// live on Root here rather than Content.
function toTamaguiPlacement(side: PopoverSide, align: PopoverAlign) {
  return align === 'center' ? side : (`${side}-${align}` as const);
}

interface PopoverRootProps {
  children: React.ReactNode;
  open?: boolean;
  defaultOpen?: boolean;
  onOpenChange?: (open: boolean) => void;
  side?: PopoverSide;
  align?: PopoverAlign;
  sideOffset?: number;
}

function Root({
  children,
  open: openProp,
  defaultOpen = false,
  onOpenChange,
  side = 'top',
  align = 'center',
  sideOffset = 8,
}: PopoverRootProps): React.ReactElement {
  const [uncontrolledOpen, setUncontrolledOpen] = React.useState(defaultOpen);
  const isControlled = openProp !== undefined;
  const open = isControlled ? openProp : uncontrolledOpen;
  const contentId = React.useId();

  const setOpen = React.useCallback(
    (value: boolean) => {
      if (!isControlled) setUncontrolledOpen(value);
      onOpenChange?.(value);
    },
    [isControlled, onOpenChange]
  );

  const contextValue = React.useMemo<PopoverContextValue>(
    () => ({ open, setOpen, contentId }),
    [open, setOpen, contentId]
  );

  return (
    <PopoverContext.Provider value={contextValue}>
      <PopoverPrimitive
        open={open}
        onOpenChange={setOpen}
        placement={toTamaguiPlacement(side, align)}
        offset={sideOffset}
        allowFlip
        stayInFrame={{ padding: 8 }}
      >
        {children}
      </PopoverPrimitive>
    </PopoverContext.Provider>
  );
}

type ClickableElement = React.ReactElement<
  { onClick?: React.MouseEventHandler } & Record<string, unknown>
>;

interface PopoverTriggerProps {
  children: ClickableElement;
  asChild?: boolean;
  className?: string;
}

/**
 * Tamagui's built-in click-to-toggle fires through `onPress`, which our
 * plain (non-RN) `Button` never receives as a real DOM event - the same
 * class of gap #582's AlertDialog hit with Cancel/Action. `disablePressTrigger`
 * turns that off; toggling instead happens through a normal `onClick` we
 * compose onto the child ourselves, matching Radix's own trigger (which used
 * a real `onClick` too).
 */
function Trigger({ children, className }: PopoverTriggerProps): React.ReactElement {
  const { open, setOpen, contentId } = usePopoverContext('Trigger');

  const handleClick = (event: React.MouseEvent) => {
    children.props.onClick?.(event);
    setOpen(!open);
  };

  return (
    <PopoverPrimitive.Trigger asChild disablePressTrigger className={className}>
      {React.cloneElement(children, {
        onClick: handleClick,
        'aria-haspopup': 'dialog',
        'aria-controls': open ? contentId : undefined,
      })}
    </PopoverPrimitive.Trigger>
  );
}

interface PopoverContentProps {
  children: React.ReactNode;
  className?: string;
}

// Tamagui already assigns `role="dialog"` to the floating wrapper itself
// (@tamagui/popover's useFloatingContext wires floating-ui's `useRole`) -
// setting it again here would just duplicate the landmark. `id` still needs
// setting explicitly so Trigger's `aria-controls` below has something
// stable to point at.
function Content({ children, className }: PopoverContentProps): React.ReactElement {
  const { contentId } = usePopoverContext('Content');

  return (
    <PopoverPrimitive.Content id={contentId} unstyled className={className}>
      {children}
    </PopoverPrimitive.Content>
  );
}

interface PopoverCloseProps {
  children: ClickableElement;
  asChild?: boolean;
}

/**
 * Bypasses Tamagui's own `Popover.Close` for the same reason `Trigger` does:
 * it composes onto `onPress`, which our `Button` never turns into a real
 * click. Closing directly through our own `setOpen` sidesteps it.
 */
function Close({ children }: PopoverCloseProps): React.ReactElement {
  const { setOpen } = usePopoverContext('Close');

  const handleClick = (event: React.MouseEvent) => {
    children.props.onClick?.(event);
    setOpen(false);
  };

  return React.cloneElement(children, { onClick: handleClick });
}

const Popover = { Root, Trigger, Content, Close };

export default Popover;
