// Structured tooltip content for building/character map markers, kept out
// of Map.tsx since the trigger elements (polygons/glyphs) already carry a
// lot of pan/zoom/rendering logic.
import ProgressBar from "../ProgressBar/ProgressBar";
import Button from "../Button/Button";
import { VILLAGE_STATE_PROGRESS_COLORS } from "./layers";

interface GoodEntry {
  good_type?: string;
  display?: string;
}

function capitalize(word: string): string {
  return word.charAt(0).toUpperCase() + word.slice(1);
}

interface BuildingTooltipProps {
  label: string;
  buildingType?: string;
  workers?: number | null;
  residents?: number | null;
  goods?: GoodEntry[] | null;
  /** Second level of progressive disclosure (issue: map entity detail card) -
   * omit to render the tooltip with no "View details" affordance. */
  onViewDetails?: () => void;
}

export function BuildingTooltipContent({
  label,
  buildingType,
  workers,
  residents,
  goods,
  onViewDetails,
}: BuildingTooltipProps) {
  const stockedGoods = (goods ?? []).filter((g) => g.display);
  const isResidential = buildingType === "residential";
  const occupancyCount = isResidential ? residents : workers;
  const occupancyLabel = isResidential ? "Residents" : "Workers";
  return (
    <div>
      <div>{label}</div>
      {occupancyCount !== null && occupancyCount !== undefined && (
        <div>
          {occupancyLabel}: {occupancyCount}
        </div>
      )}
      {stockedGoods.length > 0 && (
        <>
          <div>Inventory:</div>
          <ul>
            {stockedGoods.map((g, i) => (
              <li key={g.good_type ?? i}>
                {g.good_type ? capitalize(g.good_type) : ""}: {g.display}
              </li>
            ))}
          </ul>
        </>
      )}
      {onViewDetails && (
        <Button variant="secondary" size="small" onClick={onViewDetails}>
          View details
        </Button>
      )}
    </div>
  );
}

interface CharacterTooltipProps {
  name?: string;
  currentActivity?: string | null;
  isMoving?: boolean | null;
  /** Plain label ("House", "Bakery") for the building the character is
   * currently in, or null/undefined if they're not inside a building. */
  currentLocationLabel?: string | null;
  /** Plain label for the building the character is walking to, or
   * null/undefined if their destination isn't inside a building. Only
   * relevant while isMoving. */
  destinationLabel?: string | null;
  /** Second level of progressive disclosure (issue: map entity detail card) -
   * omit to render the tooltip with no "View details" affordance. */
  onViewDetails?: () => void;
}

// Tooltip location words read lower-case ("at bakery", "to the mill"), and
// "house" reads as "home" here - a character's own residence, not a
// building type label.
function tooltipLocationWord(label: string): string {
  const lower = label.toLowerCase();
  return lower === "house" ? "home" : lower;
}

export function CharacterTooltipContent({
  name,
  currentActivity,
  isMoving,
  currentLocationLabel,
  destinationLabel,
  onViewDetails,
}: CharacterTooltipProps) {
  const activityLabel =
    currentActivity && currentActivity.charAt(0).toUpperCase() + currentActivity.slice(1);
  const statusLine = isMoving
    ? destinationLabel
      ? `Walking to ${tooltipLocationWord(destinationLabel)}`
      : "Walking outside"
    : activityLabel &&
      (currentLocationLabel
        ? `${activityLabel} at ${tooltipLocationWord(currentLocationLabel)}`
        : `${activityLabel} outside`);

  return (
    <div>
      <div>{name}</div>
      {statusLine && <div>{statusLine}</div>}
      {onViewDetails && (
        <Button variant="secondary" size="small" onClick={onViewDetails}>
          View details
        </Button>
      )}
    </div>
  );
}

interface PopulationCentreTooltipProps {
  name?: string;
  state?: string | null;
  progress?: number | null;
}

// Expanded content shown when a village's name label is tapped/selected - the
// label itself is only coloured by state at rest (see VILLAGE_LABEL_LAYER
// in layers.ts); this is where the full progress bar + state label live.
export function PopulationCentreTooltipContent({
  name,
  state,
  progress,
}: PopulationCentreTooltipProps) {
  return (
    <div>
      <div>{name}</div>
      {state && (
        <ProgressBar
          value={progress ?? 0}
          max={100}
          label={state}
          color={VILLAGE_STATE_PROGRESS_COLORS[state] ?? "default"}
        />
      )}
    </div>
  );
}
