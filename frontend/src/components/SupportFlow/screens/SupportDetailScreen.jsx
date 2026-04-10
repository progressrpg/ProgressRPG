// SupportFlow/screens/SupportDetailScreen.jsx
import Button from "../../Button/Button";
import ButtonFrame from "../../Button/ButtonFrame";
import { SUPPORT_ACTIONS } from "../supportFlowReducer";
import styles from "../SupportFlowModal.module.scss";

export default function SupportDetailScreen({
  supportActionId,
  onBackToSupportMenu,
}) {
  const action = SUPPORT_ACTIONS[supportActionId];

  if (!action) return null;

  return (
    <div>
      <p className={styles.detailIntro}>Take your time with these steps:</p>
      <ol className={styles.stepsList}>
        {action.steps.map((step, i) => (
          <li key={i}>{step}</li>
        ))}
      </ol>
      <ButtonFrame>
        <Button onClick={onBackToSupportMenu}>Back to support menu</Button>
      </ButtonFrame>
    </div>
  );
}
