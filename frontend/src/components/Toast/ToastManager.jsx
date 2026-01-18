// components/Toast/ToastManager.jsx
import styles from './Toast.module.scss';
import classNames from 'classnames';

export default function ToastManager({ messages }) {
  return (
    <div className={styles.toastContainer} aria-live="assertive" aria-atomic="true">
      {messages.map(({ id, message, type = 'info', title }) => (
        <div
          key={id}
          className={classNames(styles.toast, styles[type])}
          role="status"
        >
          <div className={styles.inner}>
            <div className={styles.icon} aria-hidden="true" />
            <div className={styles.content}>
              {title && <div className={styles.title}>{title}</div>}
              <div className={styles.message}>{message}</div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
