// SupportFlow/screens/ActivityMenuScreen.jsx
import Button from "../../Button/Button";
import ButtonFrame from "../../Button/ButtonFrame";
import { ACTIVITY_PRESETS } from "../supportFlowReducer";

export default function ActivityMenuScreen({ onPickPreset }) {
  return (
    <div>
      <p>What would you like to do?</p>
      <ButtonFrame>
        {Object.values(ACTIVITY_PRESETS).map((preset) => (
          <Button key={preset.id} onClick={() => onPickPreset(preset.id)}>
            {preset.label}
          </Button>
        ))}
      </ButtonFrame>
    </div>
  );
}
