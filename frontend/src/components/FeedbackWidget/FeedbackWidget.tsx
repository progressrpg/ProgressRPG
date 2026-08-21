import React from "react";
import Popover from "../Popover/Popover";
import styles from "./FeedbackWidget.module.scss";
import Button from "../Button/Button";

const FeedbackWidget = () => {
  return (
    <div className={styles.feedbackWidget}>
      <Popover.Root side="top" align="end" sideOffset={8}>
        <Popover.Trigger asChild>
          <Button className={styles.feedbackButton}>💬 Feedback</Button>
        </Popover.Trigger>

        <Popover.Content className={styles.feedbackPanel}>
          <Popover.Close asChild>
            <Button className={styles.closeButton} ariaLabel="Close feedback panel">
              ×
            </Button>
          </Popover.Close>
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
        </Popover.Content>
      </Popover.Root>
    </div>
  );
};

export default FeedbackWidget;
