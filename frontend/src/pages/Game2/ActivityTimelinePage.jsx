import ActivityTimeline from "../../components/ActivityTimeline/ActivityTimeline";
import ActivityInput from "../../components/ActivityInput/ActivityInput";
import styles from "./ActivityTimelinePage.module.scss";

export default function ActivityTimelinePage() {

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>Activity Timeline</h1>
      </header>

      <main className={styles.main}>
        <ActivityTimeline />
        <ActivityInput />
      </main>
    </div>
  );
}
