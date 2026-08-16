import React from "react";
import { Dialog } from "tamagui";
import styles from "./Modal.module.scss";
import Button from "../Button/Button";
import { useReturnFocusOnClose } from "../Overlay/useReturnFocusOnClose";

interface ModalProps {
  title?: string;
  children?: React.ReactNode;
  footer?: React.ReactNode;
  onClose?: () => void;
  onBack?: (() => void) | null;
  backLabel?: string;
  id?: string;
  size?: string;
  className?: string;
  style?: React.CSSProperties;
}

export default function Modal({
  title,
  children,
  footer,
  onClose,
  onBack,
  backLabel = "Back",
  id = 'modal',
  size,
  className,
  style,
}: ModalProps) {
  // Modal is always-open by design (the consumer mounts/unmounts it) rather
  // than exposing an `open` prop, so `open` is always true here - the return
  // point for this hook is simply "whatever had focus when Modal mounted".
  const onCloseAutoFocus = useReturnFocusOnClose(true);

  return (
    <Dialog open onOpenChange={(open: boolean) => { if (!open) onClose?.(); }}>
      {/*
        role="presentation" strips the implicit ARIA `dialog` role the
        browser assigns to Portal's underlying <dialog> HTML tag - without
        it, this wrapper and Content below (which sets the real
        `role="dialog"`, wired to the actual title/description) both expose
        as "dialog" landmarks, so `getByRole('dialog')`/assistive tech see
        two nested dialogs for what's semantically one.
      */}
      <Dialog.Portal role="presentation">
        <Dialog.Overlay unstyled className={styles.modalBackdrop} data-testid="modal-overlay" />
        <Dialog.Content
          unstyled
          id={id}
          className={[styles.modal, size ? styles[size] : '', className || ''].join(' ').trim()}
          style={style}
          onCloseAutoFocus={onCloseAutoFocus}
        >
          <div className={styles.modalHeader}>
            {onBack ? (
              <Button
                onClick={onBack}
                ariaLabel={backLabel}
                className={styles.backButton}
              >
                ← {backLabel}
              </Button>
            ) : null}
            {/* asChild wraps our own literal <h2> (needed for the
                `.modalHeader h2` selector) rather than letting Title render
                its own tag - `unstyled` is dropped here since it has no
                variant to cancel on DialogTitleFrame and, under asChild,
                leaks through as a literal (invalid) DOM attribute instead
                of being consumed. */}
            <Dialog.Title asChild>
              <h2>{title}</h2>
            </Dialog.Title>
            {/*
              Plain Button with an explicit onClick, not `Dialog.Close
              asChild` - Close composes its auto-close via Tamagui's `onPress`
              prop, which our app-wide `Button` (a plain function component,
              not RN-style) never receives as a real DOM `onClick`, so the
              close-on-click behaviour silently wouldn't fire through asChild.
            */}
            <Button
              onClick={onClose}
              ariaLabel="Close modal"
              className={styles.closeButton}
            >
              &times;
            </Button>
          </div>
          <div className={styles.modalContent}>
            {children}
          </div>
          {footer && (
            <div className={styles.modalFooter}>
              {footer}
            </div>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog>
  );
}
