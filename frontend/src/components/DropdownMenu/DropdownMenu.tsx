import React from 'react';
import { Menu as MenuPrimitive } from 'tamagui';

interface DropdownMenuContextValue {
  open: boolean;
  setOpen: (open: boolean) => void;
}

const DropdownMenuContext = React.createContext<DropdownMenuContextValue | null>(null);

function useDropdownMenuContext(componentName: string): DropdownMenuContextValue {
  const context = React.useContext(DropdownMenuContext);
  if (!context) {
    throw new Error(`DropdownMenu.${componentName} must be used within DropdownMenu.Root`);
  }
  return context;
}

type DropdownMenuSide = 'top' | 'bottom' | 'left' | 'right';
type DropdownMenuAlign = 'start' | 'center' | 'end';

// Radix positions via side/align/sideOffset on Content; Tamagui's Menu (like
// Popover) resolves placement/offset up at the Root, so those props live on
// Root here too.
function toTamaguiPlacement(side: DropdownMenuSide, align: DropdownMenuAlign) {
  return align === 'center' ? side : (`${side}-${align}` as const);
}

interface DropdownMenuRootProps {
  children: React.ReactNode;
  open?: boolean;
  defaultOpen?: boolean;
  onOpenChange?: (open: boolean) => void;
  side?: DropdownMenuSide;
  align?: DropdownMenuAlign;
  sideOffset?: number;
}

// Unlike Popover, Tamagui's `Menu` root has no built-in uncontrolled mode of
// its own (no `useControllableState` internally - it just takes `open` as a
// plain boolean and proxies `onOpenChange` straight to the caller), so this
// wrapper's own open-state management isn't optional here the way it was
// optional-but-convenient for Popover.
function Root({
  children,
  open: openProp,
  defaultOpen = false,
  onOpenChange,
  side = 'bottom',
  align = 'start',
  sideOffset = 0,
}: DropdownMenuRootProps): React.ReactElement {
  const [uncontrolledOpen, setUncontrolledOpen] = React.useState(defaultOpen);
  const isControlled = openProp !== undefined;
  const open = isControlled ? openProp : uncontrolledOpen;

  const setOpen = React.useCallback(
    (value: boolean) => {
      if (!isControlled) setUncontrolledOpen(value);
      onOpenChange?.(value);
    },
    [isControlled, onOpenChange]
  );

  const contextValue = React.useMemo<DropdownMenuContextValue>(
    () => ({ open, setOpen }),
    [open, setOpen]
  );

  return (
    <DropdownMenuContext.Provider value={contextValue}>
      <MenuPrimitive
        open={open}
        onOpenChange={setOpen}
        placement={toTamaguiPlacement(side, align)}
        offset={sideOffset}
      >
        {children}
      </MenuPrimitive>
    </DropdownMenuContext.Provider>
  );
}

type ClickableElement = React.ReactElement<
  { onClick?: React.MouseEventHandler } & Record<string, unknown>
>;

interface DropdownMenuTriggerProps {
  children: React.ReactNode;
  className?: string;
  'aria-label'?: string;
}

/**
 * Deliberately not `asChild`. Tamagui's Menu trigger fires through a real
 * `onPointerDown`/`onClick` once mounted (RN's `onPress` only applies on
 * native - see createNonNativeMenu's `pressEvent`), but merging that via
 * `asChild` onto one of our own plain DOM elements (a raw `<button>`)
 * silently breaks under a coarse-pointer/touch viewport - confirmed with a
 * dedicated repro against real Playwright touch emulation, not just this
 * one sandbox quirk, since real phones also report a coarse pointer: the
 * merged `onClick` never attaches at all, so tapping the account menu
 * button would do nothing on an actual phone. Rendering Tamagui's own
 * trigger directly (no asChild) sidesteps it, since it then owns its own
 * host element and wires onClick/onPress correctly regardless of pointer
 * type. That host renders as a `<div role="button">`, not a real
 * `<button>`, so `tabIndex={0}` is needed for keyboard reachability -
 * Enter/Space activation, ArrowDown-opens-and-focuses-first-item, and
 * aria-expanded/haspopup/controls are all already wired in correctly once
 * the trigger owns its own element.
 */
function Trigger({ children, className, ...rest }: DropdownMenuTriggerProps): React.ReactElement {
  return (
    <MenuPrimitive.Trigger tabIndex={0} className={className} {...rest}>
      {children}
    </MenuPrimitive.Trigger>
  );
}

interface DropdownMenuPortalProps {
  children: React.ReactNode;
}

function Portal({ children }: DropdownMenuPortalProps): React.ReactElement {
  return <MenuPrimitive.Portal>{children}</MenuPrimitive.Portal>;
}

interface DropdownMenuContentProps {
  children: React.ReactNode;
  className?: string;
}

function Content({ children, className }: DropdownMenuContentProps): React.ReactElement {
  return (
    <MenuPrimitive.Content unstyled className={className}>
      {children}
    </MenuPrimitive.Content>
  );
}

interface AsChildItemProps {
  children: ClickableElement;
  asChild: true;
  className?: string;
  onSelect?: () => void;
}

interface PlainItemProps {
  children: React.ReactNode;
  asChild?: false;
  className?: string;
  onSelect?: (event: { preventDefault: () => void }) => void;
}

type DropdownMenuItemProps = AsChildItemProps | PlainItemProps;

/**
 * Tamagui's own `Menu.Item` closes the menu (and fires `onSelect`) through
 * `onPress` - fine for the plain-content case below, where `Menu.Item`
 * renders its own real Tamagui host element and `onPress` works natively,
 * but not for `asChild` wrapping one of our own links: the click/Enter/Space
 * handling that gets composed onto the child (via `.click()`, so navigation
 * itself always works) never reaches `onPress`, so the menu would silently
 * never close and `onSelect` would never fire. `asChild` items bypass
 * Tamagui's built-in select handling entirely and close through our own
 * `onClick` instead - the same shape of fix Popover's Trigger/Close needed.
 */
function Item(props: DropdownMenuItemProps): React.ReactElement {
  const { setOpen } = useDropdownMenuContext('Item');

  if (props.asChild) {
    const { children, className, onSelect } = props;
    const handleClick = (event: React.MouseEvent) => {
      children.props.onClick?.(event);
      onSelect?.();
      setOpen(false);
    };

    return (
      <MenuPrimitive.Item asChild className={className}>
        {React.cloneElement(children, { onClick: handleClick })}
      </MenuPrimitive.Item>
    );
  }

  const { children, className, onSelect } = props;

  return (
    <MenuPrimitive.Item unstyled className={className} onSelect={onSelect}>
      {children}
    </MenuPrimitive.Item>
  );
}

const DropdownMenu = { Root, Trigger, Portal, Content, Item };

export default DropdownMenu;
