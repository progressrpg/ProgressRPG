import React from 'react';
import { Tabs as TabsPrimitive } from 'tamagui';

interface TabsRootProps {
  children: React.ReactNode;
  value?: string;
  defaultValue?: string;
  onValueChange?: (value: string) => void;
  className?: string;
}

interface TabsListProps {
  children: React.ReactNode;
  className?: string;
  'aria-label'?: string;
}

interface TabsTriggerProps {
  children: React.ReactNode;
  value: string;
  className?: string;
  disabled?: boolean;
}

interface TabsContentProps {
  children: React.ReactNode;
  value: string;
  className?: string;
}

// Tracks which value is active so Trigger (below) can compute its own
// roving-tabindex - see the comment there for why that can't just be left
// to Tamagui. Resolved here (rather than left to Tamagui's own internal
// useControllableState) so both Root and Trigger read the same source of
// truth regardless of whether the caller uses controlled (`value`) or
// uncontrolled (`defaultValue`) mode.
const TabsActiveValueContext = React.createContext('');

function useResolvedValue(
  value: string | undefined,
  defaultValue: string | undefined,
  onValueChange: ((value: string) => void) | undefined
) {
  const [uncontrolledValue, setUncontrolledValue] = React.useState(defaultValue ?? '');
  const isControlled = value !== undefined;
  const resolvedValue = isControlled ? value : uncontrolledValue;
  const setValue = React.useCallback(
    (next: string) => {
      if (!isControlled) setUncontrolledValue(next);
      onValueChange?.(next);
    },
    [isControlled, onValueChange]
  );
  return [resolvedValue, setValue] as const;
}

/**
 * Thin wrapper over Tamagui's `Tabs`, mirroring the four-part
 * Root/List/Trigger/Content shape `@radix-ui/react-tabs` exposed so call
 * sites only need to swap the import - props are unchanged. `unstyled`
 * everywhere it's recognised (Root, List, Trigger - Content has no
 * `unstyled` variant of its own to consume it, see below), like
 * `Modal`/`Tooltip`, so consumer CSS modules stay the only source of
 * visuals; Tamagui sets `data-state="active"/"inactive"` on triggers just
 * like Radix did, so existing `[data-state='active']` selectors carry over
 * unchanged.
 *
 * `activationMode="automatic"` overrides Tamagui's own default ("manual")
 * to match Radix's default behaviour: arrow-key focus movement between
 * tabs (via Tamagui's roving-focus-group-backed `List`) activates the
 * focused tab immediately, rather than requiring a separate Enter/Space.
 */
export function Root({
  children,
  value,
  defaultValue,
  onValueChange,
  className,
}: TabsRootProps): React.ReactElement {
  const [resolvedValue, setValue] = useResolvedValue(value, defaultValue, onValueChange);
  return (
    <TabsActiveValueContext.Provider value={resolvedValue}>
      <TabsPrimitive
        unstyled
        value={resolvedValue}
        onValueChange={setValue}
        activationMode="automatic"
        className={className}
      >
        {children}
      </TabsPrimitive>
    </TabsActiveValueContext.Provider>
  );
}

export function List({ children, className, ...rest }: TabsListProps): React.ReactElement {
  return (
    <TabsPrimitive.List unstyled className={className} {...rest}>
      {children}
    </TabsPrimitive.List>
  );
}

export function Trigger({ children, value, className, disabled }: TabsTriggerProps): React.ReactElement {
  const activeValue = React.useContext(TabsActiveValueContext);
  return (
    <TabsPrimitive.Trigger
      unstyled
      value={value}
      disabled={disabled}
      className={className}
      // @tamagui/roving-focus@2.7.6's RovingFocusGroupItem computes
      // `isCurrentTabStop` but never actually uses it to set `tabIndex` -
      // every focusable trigger ends up with `tabIndex=0` (confirmed by
      // reading node_modules/@tamagui/roving-focus's source and verifying
      // in a real browser: without this, all three LibraryPage tabs land
      // in the sequential Tab order simultaneously). Radix's real roving
      // tabindex only ever puts the *active* tab in the tab order. This
      // explicit `tabIndex` wins the asChild prop merge (child value beats
      // the Slot's default, verified manually), restoring that behaviour
      // without patching the library.
      tabIndex={activeValue === value ? 0 : -1}
    >
      {children}
    </TabsPrimitive.Trigger>
  );
}

export function Content({ children, value, className }: TabsContentProps): React.ReactElement {
  return (
    // No `unstyled` here (unlike the other three) - DefaultTabsContentFrame
    // (@tamagui/tabs's Tabs.mjs) is a bare `styled(ThemeableStack, {name:
    // CONTENT_NAME})` with no variants block at all, so it never declares
    // an `unstyled` variant to consume one - passed anyway, it leaks
    // through as a literal (invalid) boolean DOM attribute, the same class
    // of issue #582/#583 hit with asChild prop merges. Harmless to omit:
    // with no variants, the frame has no default visual styles to cancel
    // in the first place.
    <TabsPrimitive.Content value={value} className={className}>
      {children}
    </TabsPrimitive.Content>
  );
}
