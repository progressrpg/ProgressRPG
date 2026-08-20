import type React from "react";
import { createPortal } from "react-dom";
import { Dialog } from "tamagui";
import styles from "./DetailSurface.module.scss";
import { useReturnFocusOnClose } from "../Overlay/useReturnFocusOnClose";

// The one file in the map entity detail card (DetailSurface -> DetailCard
// -> CharacterDetail/BuildingDetail, see MapTooltips.tsx/Map.tsx) allowed
// to import a UI library primitive directly - everything above it works
// against this component's plain open/onOpenChange/title/children props,
// so swapping the overlay/sheet/dialog primitive underneath only touches
// this file.
interface DetailSurfaceProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Accessible name for the surface - not rendered visually here (DetailCard
   * renders its own visible title inside `children`); every Dialog needs
   * one for screen reader users. */
  title: string;
  children: React.ReactNode;
  /** Modal (default): dimming overlay, focus trap, closes on outside click -
   * the right choice for a card floating over content it obscures. Non-modal
   * drops all three, so the surface stays open and the page underneath (e.g.
   * Map) stays fully interactive - for a docked side panel, which is meant
   * to keep browsing alongside rather than block it. */
  modal?: boolean;
  /** DOM node to portal into instead of document.body (Tamagui's
   * `Dialog.Portal` default, unconditionally - unlike Radix, it has no
   * per-instance container override) - e.g. Map's own wrapper element, so a
   * non-modal docked panel (see MapDetailCard) positions relative to the map
   * rather than the viewport. Bypasses `Dialog.Portal` entirely when set
   * (see the manual `createPortal` below) since there's no way to redirect
   * it otherwise; falsy falls back to `Dialog.Portal`'s own default. */
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
  const onCloseAutoFocus = useReturnFocusOnClose(open);

  const content = (
    <>
      {modal && <Dialog.Overlay unstyled className={styles.overlay} />}
      <Dialog.Content
        unstyled
        className={styles.content}
        onCloseAutoFocus={onCloseAutoFocus}
        onInteractOutside={(e: Event) => {
          if (!modal) e.preventDefault();
        }}
      >
        <Dialog.Title className="sr-only">{title}</Dialog.Title>
        {children}
      </Dialog.Content>
    </>
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange} modal={modal}>
      {container ? (
        // Dialog.Content itself doesn't gate its own mounting on `open` -
        // that's Dialog.Portal's job internally (it renders null while
        // fully closed) - so bypassing Portal here means gating manually,
        // otherwise the docked panel would sit in the DOM at all times,
        // non-interactive (Content sets pointer-events: none while closed)
        // but still visible.
        open && createPortal(content, container)
      ) : (
        // role="presentation" strips the implicit ARIA `dialog` role the
        // browser assigns to Portal's underlying <dialog> HTML tag -
        // without it, this wrapper and Content above (which sets the real
        // `role="dialog"`, wired to the actual title) both expose as
        // "dialog" landmarks, so `getByRole('dialog')`/assistive tech see
        // two nested dialogs for what's semantically one. aria-modal is
        // stripped alongside it - Tamagui sets it by default on this frame,
        // but aria-modal is only valid on role="dialog"/"alertdialog", and
        // this element's role is now "presentation".
        <Dialog.Portal role="presentation" aria-modal={undefined}>
          {content}
        </Dialog.Portal>
      )}
    </Dialog>
  );
}
