import React from "react";
import FeatureToggle from "../components/FeatureToggle";
import { useGame } from "../hooks/useGame";
import MapPage from "../pages/MapPage/MapPage";

// Testers/premium keep access via the "map" flag regardless of level (see
// FeatureToggle's alsoEnabledWhen); new signups additionally unlock it at
// level 4 (see users.services.progressive_unlocks).
export default function MapRoute(): React.ReactElement {
  const { player } = useGame() ?? {};
  return (
    <FeatureToggle
      flag="map"
      alsoEnabledWhen={Boolean(player?.progressive_unlocks.map)}
    >
      <MapPage />
    </FeatureToggle>
  );
}
