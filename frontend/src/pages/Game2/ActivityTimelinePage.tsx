import React from "react";
import CurrentActivity from "../../components/CurrentActivity/CurrentActivity";
import Infobar from "../../layout/Infobar/Infobar";
import styles from "./ActivityTimelinePage.module.scss";

export default function ActivityTimelinePage(): React.ReactElement {

  return (
    <div className={styles.page}>
      <div className={styles.content}>
        <h1 className="sr-only">Timer</h1>
        <Infobar />
        <CurrentActivity />
      </div>
    </div>
  );
}
