import { useMapCharacterDetail } from "../../hooks/useMap";
import { buildingTypeLabel } from "../Map/geojson";
import List from "../List/List";
import styles from "./CharacterDetail.module.scss";

interface CharacterDetailProps {
  characterId: number;
  /** Omit to render home/work as plain, non-interactive text. */
  onSelectBuilding?: (buildingId: number) => void;
  /** Omit to render relationships as a plain, non-interactive list. */
  onSelectRelationship?: (characterId: number) => void;
}

export default function CharacterDetail({
  characterId,
  onSelectBuilding,
  onSelectRelationship,
}: CharacterDetailProps) {
  const { data, isLoading, isError } = useMapCharacterDetail(characterId);

  if (isLoading) {
    return <p className={styles.status}>Loading...</p>;
  }

  if (isError || !data) {
    return <p className={styles.status}>Couldn&apos;t load this character.</p>;
  }

  // "walking" overrides the scheduled activity while moving, same rule as
  // the character's own map tooltip (CharacterTooltipContent).
  const activityLabel = data.is_moving ? "walking" : data.current_activity;
  const home = data.home_type ? buildingTypeLabel(data.home_type) : null;
  const work = data.work_type ? buildingTypeLabel(data.work_type) : null;

  // List's generic constraint needs an `id` field - reuse character_id
  // rather than widen the item type with an index signature.
  type RelationshipListItem = (typeof data.relationships)[number] & {
    id: number;
  };
  const relationshipItems: RelationshipListItem[] = data.relationships.map(
    (relationship) => ({ ...relationship, id: relationship.character_id })
  );

  return (
    <div className={styles.root}>
      <dl className={styles.facts}>
        {activityLabel && (
          <div className={styles.fact}>
            <dt>Currently</dt>
            <dd>{activityLabel}</dd>
          </div>
        )}
        <div className={styles.fact}>
          <dt>Age</dt>
          <dd>
            {data.age}, {data.sex}
          </dd>
        </div>

        {home && (
          <div className={styles.fact}>
            <dt>Home</dt>
            <dd>
              {onSelectBuilding && data.home_id != null ? (
                <button
                  type="button"
                  className={styles.linkButton}
                  onClick={() => onSelectBuilding(data.home_id as number)}
                >
                  {home}
                </button>
              ) : (
                home
              )}
            </dd>
          </div>
        )}
        {work && (
          <div className={styles.fact}>
            <dt>Work</dt>
            <dd>
              {onSelectBuilding && data.work_id != null ? (
                <button
                  type="button"
                  className={styles.linkButton}
                  onClick={() => onSelectBuilding(data.work_id as number)}
                >
                  {work}
                </button>
              ) : (
                work
              )}
            </dd>
          </div>
        )}
      </dl>

      {data.relationships.length > 0 && (
        <section className={styles.section}>
          <h3 className={styles.sectionHeading}>Relationships</h3>
          <List<RelationshipListItem>
            items={relationshipItems}
            className={styles.relationshipsList}
            canSelect={Boolean(onSelectRelationship)}
            canHover={Boolean(onSelectRelationship)}
            onSelect={(relationship) => onSelectRelationship?.(relationship.character_id)}
            renderItem={(relationship) => (
              <span>
                {relationship.name} — {relationship.label}
              </span>
            )}
          />
        </section>
      )}
    </div>
  );
}
