// SupportFlow/screens/PostSupportMenuScreen.jsx
import Button from "../../Button/Button";
import ButtonFrame from "../../Button/ButtonFrame";

export default function PostSupportMenuScreen({ onTryTask, onMoreSupport }) {
  return (
    <div>
      <p>How are you feeling now?</p>
      <ButtonFrame>
        <Button onClick={onTryTask}>Try starting a task</Button>
        <Button onClick={onMoreSupport}>Do another support action</Button>
      </ButtonFrame>
    </div>
  );
}
