import List from "../List/List";
import styles from "./PopulationCentreResidents.module.scss";

const formatActivity = (activity) => {
  if (!activity) return "idle";
  return String(activity).toLowerCase();
};

const formatName = (firstName, lastName) => {
  const name = `${firstName || ""} ${lastName || ""}`.trim();
  return name || "Unknown";
};

export default function PopulationCentreResidents({
  residents = [],
  linkedCharacterId,
}) {
  const sortedResidents = [...residents].sort((left, right) => {
    const leftLinked = left?.id === linkedCharacterId;
    const rightLinked = right?.id === linkedCharacterId;

    if (leftLinked && !rightLinked) return -1;
    if (!leftLinked && rightLinked) return 1;

    const leftLast = String(left?.last_name || "").toLowerCase();
    const rightLast = String(right?.last_name || "").toLowerCase();

    if (leftLast < rightLast) return -1;
    if (leftLast > rightLast) return 1;

    const leftAge = Number.isFinite(left?.age) ? left.age : -1;
    const rightAge = Number.isFinite(right?.age) ? right.age : -1;

    return rightAge - leftAge;
  });

  if (!Array.isArray(residents) || residents.length === 0) {
    return (
      <section className={styles.section}>
        <h2 className={styles.heading}>Residents</h2>
        <p className={styles.empty}>No residents found.</p>
      </section>
    );
  }

  return (
    <section className={styles.section}>
      <h2 className={styles.heading}>Residents</h2>
      <List
        items={sortedResidents}
        className={styles.list}
        getKey={(resident) =>
          resident?.id || `${resident?.first_name}-${resident?.last_name}`
        }
        getItemClassName={(resident) =>
          `${styles.item} ${
            resident?.id === linkedCharacterId ? styles.linked : ""
          }`
        }
        renderItem={(resident) => {
          const name = formatName(resident?.first_name, resident?.last_name);
          const age = resident?.age ?? "Unknown";
          const activity = formatActivity(resident?.current_activity);
          const linkedText = !resident?.is_npc
            ? resident?.id === linkedCharacterId
              ? "Linked to you"
              : "Linked"
            : "";

          return (
            <span className={styles.line}>
              <span className={styles.lineText}>
                {name} ({age}) is {activity}
              </span>
              {linkedText && (
                <span className={styles.linkedText}>{linkedText}</span>
              )}
            </span>
          );
        }}
      />
    </section>
  );
}
