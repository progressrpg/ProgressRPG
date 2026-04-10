// SupportFlow/screens/SupportMenuScreen.jsx
import Button from "../../Button/Button";
import ButtonFrame from "../../Button/ButtonFrame";

export default function SupportMenuScreen({ onReady, onNotReady }) {
  return (
    <div>
      <p>How are you feeling right now?</p>
      <ButtonFrame>
        <Button onClick={onReady}>I&apos;m ready to start</Button>
        <Button variant="secondary" onClick={onNotReady}>
          I&apos;m not ready yet
        </Button>
      </ButtonFrame>
    </div>
  );
}
