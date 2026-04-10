// SupportFlow/screens/NotReadyMenuScreen.jsx
import Button from "../../Button/Button";
import { SUPPORT_ACTIONS } from "../supportFlowReducer";
import styles from "../SupportFlowModal.module.scss";

const SUPPORT_ACTION_DESCRIPTIONS = {
  breathing: "Slow your breathing to calm your body and reduce stress quickly.",
  eat_drink: "Refuel with water or a snack so your brain has enough energy.",
  toilet: "Stand up, swing your arms around, and walk up and down a bit.",
};

export default function NotReadyMenuScreen({ onPick }) {
  return (
    <div className={styles.supportOptionList}>
      <p>Let&apos;s take care of you first.</p>

      {Object.values(SUPPORT_ACTIONS).map((action) => (
        <div className={styles.supportOptionRow} key={action.id}>
          <Button onClick={() => onPick(action.id)}>
            {action.label}
          </Button>
          <p className={styles.supportOptionText}>
            {SUPPORT_ACTION_DESCRIPTIONS[action.id] ?? action.label}
          </p>
        </div>
      ))}
    </div>
  );
}
