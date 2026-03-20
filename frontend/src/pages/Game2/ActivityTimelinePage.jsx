import ActivityTimeline from "../../components/ActivityTimeline/ActivityTimeline";
import CurrentActivity from "../../components/CurrentActivity/CurrentActivity";
import styles from "./ActivityTimelinePage.module.scss";

export default function ActivityTimelinePage() {

  return (
    <div className={styles.page}>
      <div className={styles.content}>
        <CurrentActivity />
        <ActivityTimeline />
      </div>
    </div>
  );
}
