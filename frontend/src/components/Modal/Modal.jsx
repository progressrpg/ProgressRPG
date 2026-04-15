import React, { useEffect, useRef } from "react";
import styles from "./Modal.module.scss";
import Button from "../Button/Button"

export default function Modal({
  title,
  children,
  onClose,
  onBack,
  backLabel = "Back",
  id = 'modal',
}) {
  const modalRef = useRef(null);
  const previousFocusRef = useRef(null);

  const handleHeaderControlPointerDown = (e) => {
    // Keep focused text inputs from swallowing the first tap/click on modal controls.
    e.preventDefault();
  };

  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
    onClose?.();
    }
  };

  useEffect(() => {
    // Store previous focus
    previousFocusRef.current = document.activeElement;

    // Focus modal
    modalRef.current?.focus();

    // Prevent body scroll
    document.body.style.overflow = 'hidden';

    const handleKeyDown = (e) => {
      if (e.key === "Escape") {
        onClose?.();
      }

      // Tab key focus trap
      if (e.key === "Tab") {
        const focusableElements = modalRef.current?.querySelectorAll(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );

        if (!focusableElements || focusableElements.length === 0) return;

        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        if (e.shiftKey && document.activeElement === firstElement) {
          e.preventDefault();
          lastElement.focus();
        } else if (!e.shiftKey && document.activeElement === lastElement) {
          e.preventDefault();
          firstElement.focus();
        }
      }
    };

    // Listen for keydown when modal is mounted
    document.addEventListener("keydown", handleKeyDown);

    // Cleanup listener on unmount
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = '';
      previousFocusRef.current?.focus();
    };
  }, [onClose]);

  const titleId = `${id}-title`;

  return (
    <div className={styles.modalBackdrop} onClick={handleBackdropClick} role="presentation">
      <div
        ref={modalRef}
        className={styles.modal}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
      >
        <header className={styles.modalHeader}>
          {onBack ? (
            <Button
              onClick={onBack}
              onMouseDown={handleHeaderControlPointerDown}
              onPointerDown={handleHeaderControlPointerDown}
              ariaLabel={backLabel}
              className={styles.backButton}
            >
              {backLabel}
            </Button>
          ) : null}
          <h2 id={titleId}>{title}</h2>
          <Button
            onClick={onClose}
            onMouseDown={handleHeaderControlPointerDown}
            onPointerDown={handleHeaderControlPointerDown}
            ariaLabel="Close modal"
            className={styles.closeButton}
          >
            &times;
          </Button>
        </header>
        <div className={styles.modalContent}>
          {children}
        </div>
      </div>
    </div>
  );
}
