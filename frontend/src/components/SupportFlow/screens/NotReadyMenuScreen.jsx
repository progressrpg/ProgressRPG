// SupportFlow/screens/NotReadyMenuScreen.jsx
import Button from "../../Button/Button";
import ButtonFrame from "../../Button/ButtonFrame";
import { SUPPORT_ACTIONS } from "../supportFlowReducer";

export default function NotReadyMenuScreen({ onPick }) {
  return (
    <div>
      <p>That&apos;s okay. Let&apos;s take care of you first.</p>
      <ButtonFrame>
        {Object.values(SUPPORT_ACTIONS).map((action) => (
          <Button key={action.id} onClick={() => onPick(action.id)}>
            {action.label}
          </Button>
        ))}
      </ButtonFrame>
    </div>
  );
}
