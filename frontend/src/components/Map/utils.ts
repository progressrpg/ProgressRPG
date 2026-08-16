
/**
 * MapLibre's rendering pipeline is Mercator-projection-based: it expects
 * source coordinates as [lng, lat] and internally clamps/wraps latitude to
 * roughly +-85 degrees (the standard Web Mercator-valid range - much
 * tighter than longitude's +-180). Feeding it raw EPSG:3857 metres directly
 * (which range into the millions) is far outside that domain.
 *
 * Since this map has no basemap/tile layer, nothing visually depends on
 * these being real-world coordinates - MAP_COORD_SCALE is a synthetic,
 * reversible unit conversion that keeps the game world's expected extent
 * comfortably inside MapLibre's valid lat range, not a real projection.
 *
 * Villages are seeded 1-2km apart (see spawn_villages.py); a scale of
 * 10,000 keeps the world addressable out to roughly +-850km (lat = +-85)
 * before hitting MapLibre's clamp, several orders of magnitude beyond any
 * currently seeded world size.
 */
export const MAP_COORD_SCALE = 10_000;

export function toLngLat([x, y]: [number, number]): [number, number] {
  return [x / MAP_COORD_SCALE, y / MAP_COORD_SCALE];
}

export function fromLngLat([lng, lat]: [number, number]): [number, number] {
  return [lng * MAP_COORD_SCALE, lat * MAP_COORD_SCALE];
}

// A GeoJSON `coordinates` array is arbitrarily nested depending on geometry
// type (Point: [x, y]; LineString: [[x, y], ...]; Polygon: [[[x, y], ...]]).
// This recurses down to the leaf [x, y] pairs regardless of nesting depth.
type CoordTree = [number, number] | CoordTree[];

function mapCoordTree(
  coords: CoordTree,
  fn: (pt: [number, number]) => [number, number]
): CoordTree {
  if (typeof coords[0] === "number") {
    return fn(coords as [number, number]);
  }
  return (coords as CoordTree[]).map((c) => mapCoordTree(c, fn));
}

/** Converts a whole GeoJSON `coordinates` tree from 3857 metres to synthetic lng/lat. */
export function coordsToLngLat(coords: CoordTree): CoordTree {
  return mapCoordTree(coords, toLngLat);
}

/** Converts a whole GeoJSON `coordinates` tree from synthetic lng/lat back to 3857 metres. */
export function coordsFromLngLat(coords: CoordTree): CoordTree {
  return mapCoordTree(coords, fromLngLat);
}

// Backend hard-caps the queryable bbox at MAX_BBOX_AREA_SQ_M = 100 km²
// (locations/utils.py) and 400s past it - keeping each padded side under
// this leaves headroom under that cap even after padding
// (9500m * 9500m ~= 90.25 km² < 100 km²).
const MAX_PADDED_BBOX_SIDE_M = 9500;

// Widens a camera-derived bbox by `ratio` on every side before it's sent to
// the backend, so the fetched (and therefore rendered) area is bigger than
// what's immediately on screen - panning a little reveals already-loaded
// content at the edges instead of a blank gap while the next poll catches
// up. Clamped so padding never pushes a side past the backend's area cap;
// if the unpadded bbox is already at/over that limit (very zoomed out), no
// padding is added and the bbox passes through unchanged - same as before.
export function padBbox(
  [minx, miny, maxx, maxy]: [number, number, number, number],
  ratio = 0.5
): [number, number, number, number] {
  const width = maxx - minx;
  const height = maxy - miny;
  const padX = Math.max(0, Math.min(width * ratio, (MAX_PADDED_BBOX_SIDE_M - width) / 2));
  const padY = Math.max(0, Math.min(height * ratio, (MAX_PADDED_BBOX_SIDE_M - height) / 2));
  return [minx - padX, miny - padY, maxx + padX, maxy + padY];
}

// Rounds a camera-derived bbox (raw 3857 metres) to the nearest `step` so
// that sub-pixel camera jitter during a drag/zoom doesn't mint a new
// TanStack Query key - and therefore a new network request - on every
// frame. 50m is small next to a village's extent (a building footprint is
// tens of metres wide) but coarse enough that a settled camera reuses the
// same key.
export function quantizeBbox(
  [minx, miny, maxx, maxy]: [number, number, number, number],
  step = 50
): string {
  const q = (v: number) => Math.round(v / step) * step;
  return `${q(minx)},${q(miny)},${q(maxx)},${q(maxy)}`;
}

// Bare soil - a crop subzone with no field planted yet, or fallow.
const FIELD_FILL_FALLOW = "#c2a878";
// Wheat gold - a mature, ready-to-harvest field. Same value the map used
// unconditionally for every crop subzone before stage-aware colouring.
const FIELD_FILL_READY = "#E4C158";
// Growing fields interpolate between these two HSL lightness values as
// growth_progress goes 0 -> 1: pale/sparse green just after sowing, deepening
// to a lush green as the crop nears maturity.
const GROWING_HUE = 100;
const GROWING_SATURATION = 45;
const GROWING_LIGHTNESS_START = 75;
const GROWING_LIGHTNESS_END = 35;

/**
 * Field fill colour for a crop subzone, derived from its FieldCrop stage
 * and (while growing) its growth_progress fraction - presentation only,
 * doesn't affect simulation.
 */
export function fieldFillFor(
  stage: string | null | undefined,
  progress: number | null | undefined
): string {
  if (stage === "ready") return FIELD_FILL_READY;
  if (stage === "growing") {
    const t = Math.min(1, Math.max(0, progress ?? 0));
    const lightness =
      GROWING_LIGHTNESS_START + (GROWING_LIGHTNESS_END - GROWING_LIGHTNESS_START) * t;
    return `hsl(${GROWING_HUE}, ${GROWING_SATURATION}%, ${lightness}%)`;
  }
  return FIELD_FILL_FALLOW;
}
