// src/pages/MapPage.tsx
import React, { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import Button from "../../components/Button/Button";
import PopulationCentreMap, {
  type PopulationCentreMapHandle,
} from "../../components/Map/Map";
import TodayPointsBadge from "../../components/TodayPointsBadge/TodayPointsBadge";
import FeatureToggle from "../../components/FeatureToggle";
import {
  useInitialMapCentre,
  useMapViewport,
  useMapWorldBounds,
  usePopulationCentreId,
  usePopulationCentres,
  useTargetCentreMap,
} from "../../hooks/useMap";

import styles from "./MapPage.module.scss";

// Inline rather than pulling in an icon library for one glyph. Purely
// decorative - the button's accessible name comes from Button's ariaLabel.
function HomeIcon(): React.ReactElement {
  return (
    <svg
      viewBox="0 0 24 24"
      width="18"
      height="18"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M3 9.5 12 3l9 6.5" />
      <path d="M5 9.5V21h14V9.5" />
      <path d="M9 21v-6h6v6" />
    </svg>
  );
}

export default function MapPage(): React.ReactElement {
  const queryClient = useQueryClient();
  const { data: pcId } = usePopulationCentreId();
  // One-time fetch of the single seeded village's map, used only to give the
  // camera somewhere to start (see useInitialMapCentre) and to have
  // something on screen before the camera has settled on its first
  // viewport below.
  const { data: initialCentre } = useInitialMapCentre(pcId);

  const [bbox, setBbox] = useState<string | null>(null);
  const { data: viewportGeojson } = useMapViewport(bbox);
  const { data: worldBounds } = useMapWorldBounds();

  // Set by handleFindVillage when the camera starts flying to a new
  // village, and cleared once the real viewport data for it arrives (see
  // handleViewportChange below). onViewportChange only fires on "moveend"
  // plus a debounce (Map.tsx), so without this the map would keep showing
  // the departure village - stale and possibly off-screen - for the whole
  // flight; useTargetCentreMap reads the cache MapPage's prefetch effect
  // already primed for this village, so it resolves instantly.
  const [targetCentreId, setTargetCentreId] = useState<number | null>(null);
  const { data: targetCentreGeojson } = useTargetCentreMap(targetCentreId);

  // Once the map's camera has fitted itself to the initial village and
  // reported its first viewport (Map.tsx's onViewportChange), the
  // bbox-scoped viewport poll becomes the source of truth for what's on
  // screen; until then, fall back to the mid-flight target (if any) or the
  // one-time initial fetch.
  const geojson = viewportGeojson ?? targetCentreGeojson ?? initialCentre;

  const handleViewportChange = (nextBbox: string) => {
    setBbox(nextBbox);
    setTargetCentreId(null);
  };

  const mapRef = useRef<PopulationCentreMapHandle>(null);
  const { data: populationCentres } = usePopulationCentres();
  // Index of the village the "find village" button will jump to *next* -
  // advances (and wraps) on each click, cycling through every seeded
  // PopulationCentre one at a time rather than needing the user to know
  // where any of them are.
  const [cycleIndex, setCycleIndex] = useState(0);
  const nextVillage = populationCentres?.length
    ? populationCentres[cycleIndex % populationCentres.length]
    : null;

  useEffect(() => {
    if (!populationCentres?.length || !initialCentre) return;

    const currentVillage = populationCentres[cycleIndex % populationCentres.length];
    const nextVillageToPrefetch = populationCentres[(cycleIndex + 1) % populationCentres.length];

    const villagesToPrefetch = [currentVillage, nextVillageToPrefetch].filter(Boolean);
    for (const village of villagesToPrefetch) {
      void queryClient.prefetchQuery({
        queryKey: ["map", "population-centre", "initial-centre", village.id],
        queryFn: () => import("../../api/map").then(({ fetchPopulationCentreMap }) => fetchPopulationCentreMap(village.id)),
        staleTime: 15 * 60 * 1000,
        gcTime: 30 * 60 * 1000,
      });
    }
  }, [cycleIndex, initialCentre, populationCentres, queryClient]);

  const handleFindVillage = () => {
    if (!nextVillage) return;
    mapRef.current?.flyToPoint(nextVillage.location);
    setTargetCentreId(nextVillage.id);
    setCycleIndex((index) => index + 1);
  };

  return (
    <div className={styles.page}>
      {/* Visually hidden but still present - the page needs a heading for
          screen reader/landmark navigation even though this page has no
          visible title (the map itself is the content). */}
      <h1 className="sr-only">{geojson?.meta?.population_centre_name || "Village map"}</h1>
      <div className={styles.content}>
        {initialCentre ? (
          <PopulationCentreMap
            ref={mapRef}
            geojson={geojson}
            onViewportChange={handleViewportChange}
            worldBounds={worldBounds?.bbox}
          >
            <FeatureToggle flag="todayPointsBadge" fallback={null}>
              <TodayPointsBadge />
            </FeatureToggle>
            {nextVillage && (
              <Button
                type="button"
                variant="secondary"
                className={styles.findVillageButton}
                ariaLabel={`Find ${nextVillage.name}`}
                onClick={handleFindVillage}
              >
                <HomeIcon />
              </Button>
            )}
          </PopulationCentreMap>
        ) : (
          "Loading..."
        )}
      </div>
    </div>
  );
}
