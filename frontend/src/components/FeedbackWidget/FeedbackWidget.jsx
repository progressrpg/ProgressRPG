import React, { useState } from "react";
import styles from "./FeedbackWidget.module.scss";
import Button from "../Button/Button";

const FeedbackWidget = () => {
  const [isOpen, setIsOpen] = useState(false);

  const toggleModal = () => setIsOpen(!isOpen);

  return (
    <div className={styles.feedbackWidget}>
      <Button className={styles.feedbackButton} onClick={toggleModal}>
        💬 Feedback
      </Button>

      {isOpen && (
        <div className={styles.feedbackModal}>
          <div className={styles.modalContent}>
            <Button className={styles.closeButton} onClick={toggleModal}>
              ×
            </Button>
            <h3>Help us improve Progress RPG</h3>
            <p>Spotted a bug? Got an idea? Send us your feedback:</p>
            <div className={styles.buttonGroup}>
              <a
                href="https://forms.gle/uCCg2grwzgVwwB617"
                target="_blank"
                rel="noopener noreferrer"
                className={`${styles.modalButton} ${styles.form}`}
              >
                ⌚ Quick feedback (30 seconds)
              </a>
              <a
                href="https://forms.gle/bHPqtd7ukbwF4WGu8"
                target="_blank"
                rel="noopener noreferrer"
                className={`${styles.modalButton} ${styles.form}`}
              >
                💡 First impressions (5 minutes)
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FeedbackWidget;
