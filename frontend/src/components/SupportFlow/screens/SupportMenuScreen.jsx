// SupportFlow/screens/SupportMenuScreen.jsx
import Button from "../../Button/Button";
import styles from "../SupportFlowModal.module.scss";

export default function SupportMenuScreen({ onReady, onNotReady }) {
  return (
    <div className={styles.supportOptionList}>
      <div className={styles.supportOptionRow}>
        <Button onClick={onReady}>I&apos;m ready to start</Button>
        <p className={styles.supportOptionText}>
          I have enough energy to begin. Help me pick and start the next task.
        </p>
      </div>

      <div className={styles.supportOptionRow}>
        <Button onClick={onNotReady}>I&apos;m not ready yet</Button>
        <p className={styles.supportOptionText}>
          I&apos;m stuck or overwhelmed. Help me reset before I start working.
        </p>
      </div>
    </div>
  );
}
