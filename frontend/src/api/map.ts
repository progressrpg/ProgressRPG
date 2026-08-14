// src/api/map.ts
import { apiFetch } from "../utils/api";

export interface InitialMapCentre {
  id: number | null;
  name: string | null;
  // [minX, minY, maxX, maxY] in raw EPSG:3857 metres - just enough to frame
  // the camera on this village; not the full per-village feature payload
  // fetchPopulationCentreMap returns (see InitialMapCentreView's docstring).
  bbox: [number, number, number, number] | null;
}

// Which village the map's camera should open on - the requesting player's
// linked character's village if they have one, otherwise an arbitrary but
// deterministic fallback (see InitialMapCentreView, locations/views.py).
// Deliberately a separate, lightweight endpoint rather than reusing
// fetchPopulationCentreMap: this only needs to get the camera pointed at the
// right place before useMapViewport (bbox-scoped, polled) takes over as the
// source of truth moments later, once the camera's first move settles.
export function fetchInitialMapCentre(): Promise<InitialMapCentre> {
  return apiFetch("/map/initial-centre/");
}

export interface PopulationCentreSummary {
  id: number;
  name: string;
  location: [number, number];
}

type PopulationCentreSummaryResponse =
  | { results?: PopulationCentreSummary[] }
  | PopulationCentreSummary[];

// id/name/location for every seeded PopulationCentre - used to let the map
// jump the camera to any village on demand (see MapPage's "find village"
// button), not the heavier per-village payload PopulationCentreSerializer
// also nests (residents/buildings), which this endpoint returns too but
// callers here don't need.
export async function fetchPopulationCentres(): Promise<PopulationCentreSummary[]> {
  const data = await apiFetch<PopulationCentreSummaryResponse>("/population-centres/");
  const list = Array.isArray(data) ? data : (data?.results ?? []);
  // Guards against a stale/mismatched API response (e.g. an old serializer
  // still running, or a centre with no location for some other reason)
  // rather than handing MapPage a village it can't fly the camera to.
  return list.filter(
    (centre) =>
      Array.isArray(centre.location) &&
      centre.location.length === 2 &&
      centre.location.every((n) => typeof n === "number" && Number.isFinite(n))
  );
}

// GeoJSON shape varies by feature type; typed loosely until Map is typed.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function fetchPopulationCentreMap(pcId: number): Promise<any> {
  return apiFetch(`/population-centres/${pcId}/map/`);
}

// Cross-village, bbox-bounded map data (MapViewportView, locations/views.py).
// `bbox` is "minx,miny,maxx,maxy" in raw EPSG:3857 metres.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function fetchMapViewport(bbox: string): Promise<any> {
  return apiFetch(`/map/viewport/?bbox=${encodeURIComponent(bbox)}`);
}

export interface MapCharacterRelationship {
  character_id: number;
  name: string;
  // Human-readable ("husband", "daughter", ...) - see
  // character.services.relationship_services.household_relationship_label.
  label: string;
}

export interface MapCharacterDetail {
  id: number;
  name: string;
  age: number;
  sex: string;
  home_type: string | null;
  home_id: number | null;
  work_type: string | null;
  work_id: number | null;
  current_activity: string | null;
  is_moving: boolean;
  relationships: MapCharacterRelationship[];
}

// On-demand detail for one character's map detail card (MapCharacterDetailView,
// locations/views.py) - deliberately separate from the bulk per-poll map
// viewport features, which only carry cheap tooltip-level data (see that
// view's own docstring).
export function fetchMapCharacterDetail(characterId: number): Promise<MapCharacterDetail> {
  return apiFetch(`/map/characters/${characterId}/`);
}

interface MapWorldBoundsResponse {
  bbox: [number, number, number, number] | null;
}

// Padded bbox covering every seeded PopulationCentre (MapWorldBoundsView),
// used to derive the map's maxBounds so panning is limited to a generous
// area around the world instead of being unbounded.
export function fetchMapWorldBounds(): Promise<MapWorldBoundsResponse> {
  return apiFetch("/map/world-bounds/");
}
