import React from "react";
import { useGame } from "../hooks/useGame";
import styles from "./FeatureToggle.module.scss";

interface ProgressiveUnlockGateProps {
  unlock: "infobar" | "library" | "map";
  title: string;
  message: string;
  children: React.ReactNode;
}

/**
 * Gates a page behind a progressive-unlock milestone (see
 * users.services.progressive_unlocks), reusing FeatureToggle's locked-page
 * fallback card pattern but keyed on player.progressive_unlocks rather than
 * a cohort-based FeatureFlag - there's no flag to check against here, this
 * unlock state is per-player.
 */
export default function ProgressiveUnlockGate({
  unlock,
  title,
  message,
  children,
}: ProgressiveUnlockGateProps) {
  const { player } = useGame() ?? {};

  if (!player?.progressive_unlocks[unlock]) {
    return (
      <div className={styles.fallbackPage}>
        <div className={styles.fallbackCard}>
          <p className={styles.fallbackTitle}>{title}</p>
          <p>{message}</p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
