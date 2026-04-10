// SupportFlow/screens/DailyRewardScreen.jsx
import Button from "../../Button/Button";
import ButtonFrame from "../../Button/ButtonFrame";

export default function DailyRewardScreen({ onStart, onSupport }) {
  return (
    <div>
      <p>Welcome back! 🌟 You showed up today.</p>
      <ButtonFrame>
        <Button onClick={onStart}>Start</Button>
        <Button onClick={onSupport}>Get support</Button>
      </ButtonFrame>
    </div>
  );
}
