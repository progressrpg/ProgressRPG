import type React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import styles from "./DetailSurface.module.scss";

// The one file in the map entity detail card (DetailSurface -> DetailCard
// -> CharacterDetail/BuildingDetail, see MapTooltips.tsx/Map.tsx) allowed
// to import a UI library primitive directly - everything above it works
// against this component's plain open/onOpenChange/title/children props,
// so swapping the overlay/sheet/dialog primitive underneath (e.g. once the
// project's in-progress Radix -> Tamagui migration reaches this component)
// only touches this file.
interface DetailSurfaceProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Accessible name for the surface - not rendered visually here (DetailCard
   * renders its own visible title inside `children`); Radix requires every
   * Dialog to have one for screen reader users. */
  title: string;
  children: React.ReactNode;
  /** Modal (default): dimming overlay, focus trap, closes on outside click -
   * the right choice for a card floating over content it obscures. Non-modal
   * drops all three, so the surface stays open and the page underneath (e.g.
   * Map) stays fully interactive - for a docked side panel, which is meant
   * to keep browsing alongside rather than block it. */
  modal?: boolean;
  /** DOM node to portal into instead of document.body (Radix's default) -
   * e.g. Map's own wrapper element, so a non-modal docked panel (see
   * MapDetailCard) positions relative to the map rather than the
   * viewport. */
  container?: HTMLElement | null;
}

export default function DetailSurface({
  open,
  onOpenChange,
  title,
  children,
  modal = true,
  container,
}: DetailSurfaceProps) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange} modal={modal}>
      <DialogPrimitive.Portal container={container ?? undefined}>
        {modal && <DialogPrimitive.Overlay className={styles.overlay} />}
        <DialogPrimitive.Content
          className={styles.content}
          onInteractOutside={(e) => {
            if (!modal) e.preventDefault();
          }}
        >
          <DialogPrimitive.Title className="sr-only">{title}</DialogPrimitive.Title>
          {children}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
