import { useEffect, type RefObject } from "react";
import type { WalkerState } from "../sourceData";
import type { GeoJSONFeature } from "../mapTypes";

interface UseWalkerAnimationArgs {
  walkingFeatures: GeoJSONFeature[];
  mapReady: boolean;
  refreshVillageSource: () => void;
  // Owned by the caller (shared with useVillageSource, which reads it to
  // build the character features it feeds the map source) rather than by
  // this hook - both hooks need it, and having whichever one creates it
  // hand it to the other would make them depend on call order.
  walkersRef: RefObject<Map<string, WalkerState>>;
}

/**
 * The two effects that drive per-character walker state (current
 * interpolated position, remaining path, speed): resetting each walking
 * character's checkpoint whenever a new poll arrives, and the per-frame
 * animation loop that interpolates between checkpoints.
 *
 * This is the state the audit called out as split across "one effect and
 * two others 100+ lines apart" - collected here so the full read/write
 * cycle is in one place instead of requiring a jump around the file.
 */
export function useWalkerAnimation({
  walkingFeatures,
  mapReady,
  refreshVillageSource,
  walkersRef,
}: UseWalkerAnimationArgs) {
  // Resets each walking character's checkpoint to the latest poll whenever
  // the underlying geojson changes: the authoritative position, its
  // remaining path, its speed, and the moment this checkpoint was taken.
  // Unconditional - there's no drift to weigh here, since the animation loop
  // below never accumulates state across polls; it only ever measures time
  // elapsed since this checkpoint.
  useEffect(() => {
    const activeIds = new Set<string>();
    const receivedAt = Date.now();

    for (const feature of walkingFeatures) {
      const id = String(feature.properties?.id);
      activeIds.add(id);
      const [x, y] = feature.geometry.coordinates as [number, number];
      const path = feature.properties?.path ?? [];
      const speed = Number(feature.properties?.effective_speed) || 0;

      walkersRef.current.set(id, { checkpointPos: [x, y], path, speed, receivedAt });
    }

    // Characters no longer walking (arrived, or gone from the map) fall back
    // to idle placement next render - drop their stale walker state so a
    // later journey starts clean instead of resuming from wherever this one
    // left off.
    for (const id of walkersRef.current.keys()) {
      if (!activeIds.has(id)) walkersRef.current.delete(id);
    }
    // walkersRef is a stable ref object passed in by the caller - its
    // identity never changes, so omitting it doesn't affect when this runs.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [walkingFeatures]);

  // Drives smooth per-frame movement for walking characters between polls.
  // Each frame recomputes position from scratch - the checkpoint plus how
  // much time has passed since it was taken - rather than stepping forward
  // from wherever the previous frame left off, so nothing compounds across
  // frames or across polls (see the WalkerState comment above). Only runs
  // while at least one character actually has an active journey - an idle
  // village (the common case) has nothing to animate, so there's no reason
  // to keep a 60fps timer alive rebuilding the source every 16ms.
  useEffect(() => {
    if (!mapReady || walkingFeatures.length === 0) return;

    const tick = () => refreshVillageSource();

    tick();
    const intervalId = window.setInterval(tick, 16);
    return () => window.clearInterval(intervalId);
  }, [mapReady, walkingFeatures.length, refreshVillageSource]);

  return { walkersRef };
}
