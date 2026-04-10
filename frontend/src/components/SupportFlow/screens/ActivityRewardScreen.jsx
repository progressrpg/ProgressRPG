// SupportFlow/screens/ActivityRewardScreen.jsx
import Button from "../../Button/Button";
import ButtonFrame from "../../Button/ButtonFrame";

export default function ActivityRewardScreen({ onContinue, onSupport }) {
  return (
    <div>
      <p>Great work! 🎉 You completed an activity.</p>
      <ButtonFrame>
        <Button onClick={onContinue}>Continue</Button>
        <Button variant="secondary" onClick={onSupport}>
          Get support
        </Button>
      </ButtonFrame>
    </div>
  );
}
