import React from 'react';
import { Accordion as AccordionPrimitive } from 'tamagui';

/**
 * Tamagui's Accordion (built on its Collapsible primitive) already mirrors
 * Radix's Root/Item/Header/Trigger/Content shape and its `type`/`value`/
 * `defaultValue`/`onValueChange` API almost exactly ("adapted from
 * radix-ui accordion" per its own source) - unlike Popover/DropdownMenu,
 * every part here renders as a genuine Tamagui host element rather than
 * `asChild`-wrapping one of our own plain components, so there's no
 * onPress/onClick gap to work around. This wrapper just applies `unstyled`
 * by default so call sites don't have to repeat it, and keeps the import
 * local rather than reaching into `tamagui` directly from feature code.
 */

interface AccordionRootProps {
  children: React.ReactNode;
  type: 'single' | 'multiple';
  className?: string;
  value?: string | string[];
  defaultValue?: string | string[];
  onValueChange?: (value: string | string[]) => void;
}

function Root(props: AccordionRootProps): React.ReactElement {
  // Tamagui's `Root` distinguishes single/multiple by the *shape* of
  // value/defaultValue (string vs string[]) rather than reading `type`
  // itself for that, but still requires `type` for its own validation -
  // passing everything straight through keeps both satisfied.
  return <AccordionPrimitive {...(props as React.ComponentProps<typeof AccordionPrimitive>)} />;
}

interface AccordionItemProps {
  children: React.ReactNode;
  value: string;
  className?: string;
}

function Item({ children, ...rest }: AccordionItemProps): React.ReactElement {
  return <AccordionPrimitive.Item {...rest}>{children}</AccordionPrimitive.Item>;
}

interface AccordionHeaderProps {
  children: React.ReactNode;
  className?: string;
}

function Header({ children, ...rest }: AccordionHeaderProps): React.ReactElement {
  return <AccordionPrimitive.Header {...rest}>{children}</AccordionPrimitive.Header>;
}

interface AccordionTriggerProps {
  children: React.ReactNode;
  className?: string;
}

function Trigger({ children, ...rest }: AccordionTriggerProps): React.ReactElement {
  return (
    <AccordionPrimitive.Trigger unstyled {...rest}>
      {children}
    </AccordionPrimitive.Trigger>
  );
}

interface AccordionContentProps {
  children: React.ReactNode;
  className?: string;
}

function Content({ children, ...rest }: AccordionContentProps): React.ReactElement {
  return (
    <AccordionPrimitive.Content unstyled {...rest}>
      {children}
    </AccordionPrimitive.Content>
  );
}

const Accordion = { Root, Item, Header, Trigger, Content };

export default Accordion;
