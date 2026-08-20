import { Toast, ToastViewport } from 'tamagui';
import styles from './Toast.module.scss';
import type { Toast as ToastMessage } from '../../context/toastContextDef';

interface ToastManagerProps {
  messages: ToastMessage[];
  onDismiss: (id: string) => void;
}

export default function ToastManager({ messages, onDismiss }: ToastManagerProps) {
  return (
    <>
      {messages.map(({ id, message }) => (
        // `unstyled` skips Tamagui's default background/padding/elevation so
        // .toast (SCSS) stays the sole source of visual truth, same as the
        // Radix Toast.Root this replaces never applied its own visuals either
        // (see ProgressBar, #580, for the same pattern).
        //
        // Accepted a11y gap (#581): Radix's Toast.Root/Viewport render as a
        // real <li>/<ol> (Primitive.li / Primitive.ol in its source), giving
        // screen readers native list navigation ("item 2 of 3") across
        // stacked toasts. Tamagui's Toast/ToastViewport are View-based
        // (styled(YStack, ...)) with no tag-override escape hatch - there is
        // no way to make them render as li/ol from this call site. The
        // announcement itself (role="status", aria-live politeness below)
        // is preserved; only the native list *structure* is lost. Recorded
        // here rather than silently dropped, per #587's baseline.
        <Toast
          key={id}
          unstyled
          open
          onOpenChange={(open) => { if (!open) onDismiss(id); }}
          className={styles.toast}
          type="background"
        >
          <div className={styles.inner}>
            <div className={styles.icon} aria-hidden="true" />
            <div className={styles.content}>
              <Toast.Description unstyled className={styles.message}>{message}</Toast.Description>
            </div>
          </div>
        </Toast>
      ))}
      <ToastViewport unstyled className={styles.toastViewport} />
    </>
  );
}
