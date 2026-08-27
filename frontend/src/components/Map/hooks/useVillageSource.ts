import { useCallback, useEffect, type RefObject } from "react";
import type { GeoJSONSource } from "maplibre-gl";
import {
  buildCharacterPointFeatures,
  buildVillageSourceData,
  type WalkerState,
} from "../sourceData";
import type { GeoJSONFeature } from "../mapTypes";

interface UseVillageSourceArgs {
  sourceRef: RefObject<GeoJSONSource | null>;
  mapReady: boolean;
  features: GeoJSONFeature[];
  staticVillageFeatures: GeoJSONFeature[];
  characterFeatures: GeoJSONFeature[];
  idleCharacterPositions: Map<string, [number, number]>;
  walkersRef: RefObject<Map<string, WalkerState>>;
}

/**
 * Owns pushing this village's data into the map's GeoJSON source: the
 * on-demand refresh callback (also used by the walker animation loop for
 * per-frame updates), and the two effects that call it in response to a new
 * poll or a walking-state change.
 */
export function useVillageSource({
  sourceRef,
  mapReady,
  features,
  staticVillageFeatures,
  characterFeatures,
  idleCharacterPositions,
  walkersRef,
}: UseVillageSourceArgs) {
  const refreshVillageSource = useCallback(() => {
    sourceRef.current?.setData({
      type: "FeatureCollection",
      features: [
        ...staticVillageFeatures,
        ...buildCharacterPointFeatures({
          characterFeatures,
          idleCharacterPositions,
          walkers: walkersRef.current,
          now: Date.now(),
        }),
      ],
    });
  }, [sourceRef, staticVillageFeatures, characterFeatures, idleCharacterPositions, walkersRef]);

  // Feeds the current geojson into the map's GeoJSON source whenever it
  // changes.
  useEffect(() => {
    if (!mapReady) return;
    refreshVillageSource();
  }, [mapReady, refreshVillageSource]);

  // Rebuilds the symbol-layer source whenever walking state changes.
  useEffect(() => {
    if (!mapReady) return;
    sourceRef.current?.setData(
      buildVillageSourceData({
        features,
        characterFeatures,
        idleCharacterPositions,
        walkers: walkersRef.current,
        now: Date.now(),
      })
    );
  }, [characterFeatures, features, idleCharacterPositions, mapReady, sourceRef, walkersRef]);

  return { refreshVillageSource };
}
