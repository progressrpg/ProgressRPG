import React, { useEffect } from "react";
import styles from "./Modal.module.scss";
import Button from "../Button/Button"

export default function Modal({ title, children, onClose }) {
  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
    onClose?.();
    }
  };

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape") {
        onClose?.();
      }
    };

    // Listen for keydown when modal is mounted
    document.addEventListener("keydown", handleKeyDown);

    // Cleanup listener on unmount
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [onClose]);

  return (
    <div className={styles.modalBackdrop} onClick={handleBackdropClick}>
      <div className={styles.modal}>
        <header className={styles.modalHeader}>
          <h2>{title}</h2>
          <Button
            onClick={onClose}
            aria-label="Close modal"
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
