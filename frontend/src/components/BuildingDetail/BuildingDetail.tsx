import List from "../List/List";
import styles from "./BuildingDetail.module.scss";

interface BuildingDetailGood {
  good_type?: string;
  display?: string;
}

// Also reused for workers - both are just "a character tied to this
// building", differing only in which List section they render under.
export interface BuildingDetailResident {
  id: number;
  name: string;
  currentActivity?: string | null;
  isMoving?: boolean | null;
}

interface BuildingDetailProps {
  buildingType?: string;
  residents: BuildingDetailResident[];
  workers?: BuildingDetailResident[];
  workerCount?: number | null;
  residentialCapacity?: number | null;
  goods?: BuildingDetailGood[] | null;
  /** Omit to render residents as a plain, non-interactive list. */
  onSelectResident?: (characterId: number) => void;
  /** Omit to render workers as a plain, non-interactive list. */
  onSelectWorker?: (characterId: number) => void;
}

function capitalize(word: string): string {
  return word.charAt(0).toUpperCase() + word.slice(1);
}

function residentLine(resident: BuildingDetailResident): string {
  // "walking" overrides the scheduled activity while moving, same rule as
  // a character's own map tooltip (CharacterTooltipContent).
  return resident.name;
}

export default function BuildingDetail({
  buildingType,
  residents,
  workers = [],
  workerCount,
  residentialCapacity,
  goods,
  onSelectResident,
  onSelectWorker,
}: BuildingDetailProps) {
  const isResidential = buildingType === "residential";
  const stockedGoods = (goods ?? []).filter((good) => good.display);

  return (
    <div className={styles.root}>
      {stockedGoods.length > 0 && (
        <section className={styles.section}>
          <h3 className={styles.sectionHeading}>Inventory</h3>
          <ul className={styles.goodsList}>
            {stockedGoods.map((good, index) => (
              <li key={good.good_type ?? index}>
                {good.good_type ? capitalize(good.good_type) : ""}: {good.display}
              </li>
            ))}
          </ul>
        </section>
      )}

      {isResidential ? (
        <section className={styles.section}>
          <div className={styles.sectionHeadingRow}>
            <h3 className={styles.sectionHeading}>Residents</h3>
            <span className={styles.sectionCount}>
              {residents.length}
              {residentialCapacity != null && residentialCapacity > 0
                ? ` / ${residentialCapacity}`
                : ""}
            </span>
          </div>
          {residents.length > 0 && (
            <List<BuildingDetailResident>
              items={residents}
              className={styles.residentsList}
              compact
              canSelect={Boolean(onSelectResident)}
              canHover={Boolean(onSelectResident)}
              onSelect={(resident) => onSelectResident?.(resident.id)}
              renderItem={(resident) => <span>{residentLine(resident)}</span>}
            />
          )}
        </section>
      ) : (
        workerCount != null && (
          <section className={styles.section}>
            <div className={styles.sectionHeadingRow}>
              <h3 className={styles.sectionHeading}>Workers</h3>
              <span className={styles.sectionCount}>{workerCount}</span>
            </div>
            {workers.length > 0 && (
              <List<BuildingDetailResident>
                items={workers}
                className={styles.residentsList}
                compact
                canSelect={Boolean(onSelectWorker)}
                canHover={Boolean(onSelectWorker)}
                onSelect={(worker) => onSelectWorker?.(worker.id)}
                renderItem={(worker) => <span>{residentLine(worker)}</span>}
              />
            )}
          </section>
        )
      )}
    </div>
  );
}
