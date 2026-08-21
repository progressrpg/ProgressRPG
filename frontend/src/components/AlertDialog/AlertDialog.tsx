import React from 'react';
import { AlertDialog as AlertDialogPrimitive } from 'tamagui';
import styles from './AlertDialog.module.scss';
import Button from '../Button/Button';
import { useReturnFocusOnClose } from '../Overlay/useReturnFocusOnClose';

// Tamagui's AlertDialog.Cancel default-focuses itself on open via an
// internal `cancelRef`, which `Cancel asChild` composes onto its child - but
// that only works if the child forwards refs. Our app-wide `Button` is a
// plain function component (no forwardRef), so that ref chain silently
// stays null. Focusing by id below sidesteps it entirely.
const CANCEL_BUTTON_ID = 'alert-dialog-cancel-button';

interface AlertDialogProps {
  open: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
  variant?: 'default' | 'destructive';
}

/**
 * Use AlertDialog for confirm/destructive prompts that interrupt the user and
 * require a decision before continuing. For informational overlays, use Modal.
 */
export default function AlertDialog({
  open,
  title,
  description,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  onConfirm,
  onCancel,
  variant = 'default',
}: AlertDialogProps) {
  const onCloseAutoFocus = useReturnFocusOnClose(open);

  return (
    <AlertDialogPrimitive open={open} onOpenChange={(o: boolean) => { if (!o) onCancel(); }}>
      {/*
        role="presentation" strips the implicit ARIA `dialog` role the
        browser assigns to Portal's underlying <dialog> HTML tag - without
        it, this wrapper and Content below (which sets the real
        `role="alertdialog"`, wired to the actual title/description) both
        expose as dialog-family landmarks, so `getByRole('alertdialog')`/
        assistive tech see two nested dialogs for what's semantically one.
        render="div" goes with it - role="presentation" isn't a permitted
        ARIA role on a native <dialog> element (only "alertdialog" is), so
        the frame is switched to a plain <div> where "presentation" is
        valid. aria-modal is stripped for the same reason: it's only valid
        on role="dialog"/"alertdialog", not "presentation".
      */}
      <AlertDialogPrimitive.Portal role="presentation" render="div" aria-modal={undefined}>
        <AlertDialogPrimitive.Overlay unstyled className={styles.overlay} />
        <AlertDialogPrimitive.Content
          unstyled
          className={styles.content}
          onCloseAutoFocus={onCloseAutoFocus}
          onOpenAutoFocus={(event: Event) => {
            event.preventDefault();
            document.getElementById(CANCEL_BUTTON_ID)?.focus();
          }}
        >
          <AlertDialogPrimitive.Title className={styles.title}>
            {title}
          </AlertDialogPrimitive.Title>
          <AlertDialogPrimitive.Description className={styles.description}>
            {description}
          </AlertDialogPrimitive.Description>
          <div className={styles.actions}>
            {/*
              Plain Buttons with explicit onClick handlers, not
              `AlertDialog.Cancel`/`.Action` asChild - both compose their
              click behaviour onto Tamagui's `onPress` prop, which our
              app-wide `Button` (a plain function component, not RN-style)
              never receives as a real DOM `onClick`, so it silently
              wouldn't fire through asChild. `onOpenChange`/Escape/outside
              -click still route through the Root's own onOpenChange above.
            */}
            <Button id={CANCEL_BUTTON_ID} variant="secondary" onClick={onCancel}>
              {cancelLabel}
            </Button>
            <Button
              variant={variant === 'destructive' ? 'danger' : 'primary'}
              onClick={onConfirm}
            >
              {confirmLabel}
            </Button>
          </div>
        </AlertDialogPrimitive.Content>
      </AlertDialogPrimitive.Portal>
    </AlertDialogPrimitive>
  );
}
