import ActivityTimeline from "../../components/ActivityTimeline/ActivityTimeline";
import CharacterCurrentActivity from "../../components/CharacterCurrentActivity/CharacterCurrentActivity";
import ActivityInput from "../../components/ActivityInput/ActivityInput";
import styles from "./ActivityTimelinePage.module.scss";

export default function ActivityTimelinePage() {

  return (
    <div className={styles.page}>
      <h1 className={styles.header}>Activity Timer</h1>

      <div className={styles.main}>
        <ActivityTimeline />
        <CharacterCurrentActivity />
        <ActivityInput />
      </div>
    </div>
  );
}
