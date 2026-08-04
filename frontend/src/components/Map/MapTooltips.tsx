// Structured tooltip content for building/character map markers, kept out
// of Map.tsx since the trigger elements (polygons/glyphs) already carry a
// lot of pan/zoom/rendering logic.
import ProgressBar from "../ProgressBar/ProgressBar";
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
}

export function BuildingTooltipContent({
  label,
  buildingType,
  workers,
  residents,
  goods,
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
    </div>
  );
}

interface CharacterTooltipProps {
  name?: string;
  home?: string | null;
  work?: string | null;
  hungerLabel?: string | null;
}

export function CharacterTooltipContent({ name, home, work, hungerLabel }: CharacterTooltipProps) {
  return (
    <div>
      <div>{name}</div>
      {home && <div>Lives at: {home}</div>}
      {work && <div>Works at: {work}</div>}
      {hungerLabel && <div>{hungerLabel}</div>}
    </div>
  );
}

interface PopulationCentreTooltipProps {
  name?: string;
  state?: string | null;
  progress?: number | null;
}

// Expanded content shown when a village marker is tapped/selected - the
// marker itself only shows a state-coded dot at rest (see VILLAGE_MARKER_LAYER
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
