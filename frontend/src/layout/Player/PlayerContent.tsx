import React from "react";
import styles from "./PlayerContent.module.scss";
import FeatureToggle from "../../components/FeatureToggle";
import ActivityList from "../ActivityList/ActivityList";
import { Link } from "react-router";

// PlayerContent accepts arbitrary props and forwards them to ActivityList.
// The props are not formally typed here because ActivityList itself accepts none —
// this component exists as a container and the spread is intentional.
interface PlayerContentProps {
  [key: string]: unknown;
}

export default function PlayerContent(props: PlayerContentProps) {
  return (
    <div className={styles.profileContent}>
      <div className={styles.profileSection}>
        <h1>Player</h1>
        <div>
          Check out the map for your village:{" "}
          <Link to="/map">View map</Link>
        </div>
        <FeatureToggle flag="activityList">
          <ActivityList {...(props as Record<string, unknown>)} />
        </FeatureToggle>
      </div>
      <div className={styles.profileSection}>
        <h1>Character</h1>
      </div>
    </div>
  );
}
