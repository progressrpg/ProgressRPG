// src/hooks/useMap.ts
import { useQuery } from "@tanstack/react-query";
import {
  fetchInitialMapCentre,
  fetchMapCharacterDetail,
  fetchMapViewport,
  fetchMapWorldBounds,
  fetchPopulationCentreMap,
  fetchPopulationCentres,
} from "../api/map";

// Close to move_characters_tick's 1s cadence (locations/tasks.py) so the map
// tracks actual journeys closely, without polling every single tick.
export const MAP_POLL_INTERVAL_MS = 2000;

// Shared {queryKey, queryFn, staleTime, gcTime} for the map's two cheap,
// one-shot "where/how big is the world" queries - exported (rather than
// inlined in useInitialMapCentre/useMapWorldBounds below) so GameContext's
// login-time prefetch (see useBootstrapGameData) primes the exact same cache
// entries these hooks read, instead of duplicating the queryKey literals and
// risking the two drifting apart.
//
// One-shot (not polled) fetch of just enough (id/name/bbox) to know where
// the camera should start - the requesting player's linked character's
// village if they have one, otherwise an arbitrary but deterministic
// fallback (see InitialMapCentreView's docstring, locations/views.py).
// Deliberately not the full per-village map payload fetchPopulationCentreMap
// returns: once the camera exists, all ongoing content comes from
// useMapViewport below instead, so there's nothing here worth paying for
// beyond the bbox to fit to. A short staleTime (rather than
// effectively-forever) means a player who links to a different character
// mid-session and revisits the map later still gets pointed at the right
// village instead of a stale cached one.
export const initialMapCentreQueryOptions = {
  queryKey: ["map", "initial-centre"] as const,
  queryFn: fetchInitialMapCentre,
  staleTime: 5 * 60 * 1000,
  gcTime: 15 * 60 * 1000,
};

export function useInitialMapCentre() {
  return useQuery(initialMapCentreQueryOptions);
}

// Reads the same cache entry MapPage's prefetch effect primes for the
// upcoming "find village" target (see the prefetchQuery call there) - while
// the camera is mid-flight to that village, onViewportChange hasn't fired
// yet (only fires on "moveend" + a debounce, see Map.tsx), so this fills the
// gap with the prefetched village's data instead of showing stale content
// from wherever the camera used to be. Resolves instantly from cache when
// the prefetch already completed; only hits the network if it hasn't.
export function useTargetCentreMap(centreId: number | null) {
  return useQuery({
    queryKey: ["map", "population-centre", "full-map", centreId],
    queryFn: () => fetchPopulationCentreMap(centreId as number),
    enabled: centreId != null,
    staleTime: 15 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
  });
}

// Cross-village map data bounded by the camera's current viewport. `bbox` is
// a quantized "minx,miny,maxx,maxy" string (see quantizeBbox in
// components/Map/utils.ts) so sub-pixel camera jitter doesn't churn the
// query key, and is null while the map hasn't settled on an initial camera
// yet (query is disabled until then).
export function useMapViewport(bbox: string | null) {
  return useQuery({
    queryKey: ["map", "viewport", bbox],
    queryFn: () => fetchMapViewport(bbox as string),
    enabled: bbox != null,
    refetchInterval: MAP_POLL_INTERVAL_MS,
    staleTime: 5 * 1000,
    gcTime: 15 * 60 * 1000,
    placeholderData: (previousData: unknown) => previousData,
  });
}

// Padded bbox covering every seeded PopulationCentre, used to derive
// MapLibre's maxBounds (see design decision #6 in the map-viewport plan).
// One-shot per session rather than polled - the world's overall extent
// changes far more slowly than any individual viewport's contents.
export const mapWorldBoundsQueryOptions = {
  queryKey: ["map", "world-bounds"] as const,
  queryFn: fetchMapWorldBounds,
  staleTime: 30 * 60 * 1000,
  gcTime: 60 * 60 * 1000,
};

export function useMapWorldBounds() {
  return useQuery(mapWorldBoundsQueryOptions);
}

// On-demand fetch for one character's map detail card (see DetailCard/
// CharacterDetail) - only enabled while that character's card is actually
// open, not polled like useMapViewport, since age/sex/relationships don't
// need to track second-to-second the way position/activity do.
export function useMapCharacterDetail(characterId: number | null) {
  return useQuery({
    queryKey: ["map", "character-detail", characterId],
    queryFn: () => fetchMapCharacterDetail(characterId as number),
    enabled: characterId != null,
    staleTime: 15 * 1000,
    gcTime: 5 * 60 * 1000,
  });
}

// id/name/location for every seeded PopulationCentre - lets MapPage's "find
// village" button cycle the camera through all of them. One-shot like
// useMapWorldBounds: which villages exist changes far more slowly than
// anything the map polls for.
export function usePopulationCentres() {
  return useQuery({
    queryKey: ["population-centres", "all"],
    queryFn: fetchPopulationCentres,
    staleTime: 30 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
  });
}
