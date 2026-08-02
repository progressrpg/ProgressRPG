import type { GeoJSONFeature } from "../Map";

// Placeholder palette until real character sprites/art exist. Colour is
// picked deterministically from the character id so the same character
// always renders the same way, without persisting anything new.
export const CHARACTER_COLOURS = [
  "#e07a5f",
  "#3d5a80",
  "#81b29a",
  "#f2cc8f",
  "#9d8189",
  "#588157",
];

export function colourForCharacter(id: number | undefined): string {
  if (!Number.isFinite(id)) return CHARACTER_COLOURS[0];
  return CHARACTER_COLOURS[(id as number) % CHARACTER_COLOURS.length];
}

export type Ring = number[][];

// Several residents can be idle at the exact same point (e.g. everyone
// "home" shares their building's entrance/central node), which would
// otherwise render as one marker stacked on another - or, with a small ring
// around that point, as everyone standing in a tight formation. Instead,
// place each one at a random spot inside their building's actual footprint,
// so they read as scattered around the house rather than clustered at its
// door.
export const BUILDING_INSET_RATIO = 0.18; // keep a little clear of the walls
export const MAX_RANDOM_POINT_ATTEMPTS = 20;
// Markers are ~3.6 GIS units wide (see the person glyph in Map.tsx); keep
// housemates at least that far apart centre-to-centre so they don't overlap.
export const MIN_CHARACTER_DISTANCE = 3.5;

// Fallback for characters whose point doesn't fall inside any building
// footprint (e.g. mid-journey, standing on a path) - a small ring-with-
// jitter around their shared point, same idea as before building-aware
// placement existed.
export const CHARACTER_SCATTER_RADIUS = 2.4;
export const CHARACTER_SCATTER_JITTER = 0.9;

// Small deterministic PRNG (mulberry32-ish) so the same character id always
// lands on the same-looking spot, instead of jumping around every poll.
export function seededRandom(seed: number): number {
  let t = seed + 0x6d2b79f5;
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}

export function pointInPolygon(point: [number, number], ring: Ring): boolean {
  const [px, py] = point;
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];
    const intersects =
      yi > py !== yj > py && px < ((xj - xi) * (py - yi)) / (yj - yi) + xi;
    if (intersects) inside = !inside;
  }
  return inside;
}

export function polygonBounds(ring: Ring) {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const [x, y] of ring) {
    if (x < minX) minX = x;
    if (x > maxX) maxX = x;
    if (y < minY) minY = y;
    if (y > maxY) maxY = y;
  }
  return { minX, minY, maxX, maxY };
}

export function distanceBetween(a: [number, number], b: [number, number]): number {
  const dx = a[0] - b[0];
  const dy = a[1] - b[1];
  return Math.sqrt(dx * dx + dy * dy);
}

// Characters idling at a building's entrance node sit exactly on its
// footprint's boundary (the entrance is the midpoint of the building's
// longest wall) - not safely inside it. Ray-casting point-in-polygon tests
// like pointInPolygon are unreliable exactly on an edge (float precision can
// flip the parity either way), which was leaving some households matched to
// no footprint at all and falling back to the door-side scatter. Building
// footprints are currently always axis-aligned rectangles (see
// create_building_footprint in spawn_villages.py), so their bounding box
// *is* their shape - matching against the box with a small epsilon sidesteps
// the boundary-precision problem entirely.
export function pointNearFootprint(
  point: [number, number],
  ring: Ring,
  epsilon = 0.05
): boolean {
  const { minX, minY, maxX, maxY } = polygonBounds(ring);
  const [x, y] = point;
  return (
    x >= minX - epsilon &&
    x <= maxX + epsilon &&
    y >= minY - epsilon &&
    y <= maxY + epsilon
  );
}

// Rejection-samples a deterministic point inside the polygon's bounding box
// (inset slightly so nobody renders flush against a wall) that's also at
// least MIN_CHARACTER_DISTANCE from every already-placed housemate. If
// nothing clears both within a few tries (small house, many residents),
// falls back to the best-spaced interior point it found rather than giving
// up - still inside the footprint, just as far from its housemates as
// possible. Returns null only if no point inside the polygon was found at
// all (odd/thin footprint shapes).
export function randomPointInPolygon(
  ring: Ring,
  seed: number,
  existingPoints: [number, number][]
): [number, number] | null {
  const { minX, minY, maxX, maxY } = polygonBounds(ring);
  const insetX = (maxX - minX) * BUILDING_INSET_RATIO;
  const insetY = (maxY - minY) * BUILDING_INSET_RATIO;
  const loX = minX + insetX;
  const loY = minY + insetY;
  const hiX = maxX - insetX;
  const hiY = maxY - insetY;

  let bestCandidate: [number, number] | null = null;
  let bestCandidateDistance = -Infinity;

  for (let attempt = 0; attempt < MAX_RANDOM_POINT_ATTEMPTS; attempt++) {
    const point: [number, number] = [
      loX + seededRandom(seed + attempt * 2) * (hiX - loX),
      loY + seededRandom(seed + attempt * 2 + 1) * (hiY - loY),
    ];
    if (!pointInPolygon(point, ring)) continue;

    const nearestDistance = existingPoints.length
      ? Math.min(...existingPoints.map((p) => distanceBetween(point, p)))
      : Infinity;

    if (nearestDistance >= MIN_CHARACTER_DISTANCE) {
      return point;
    }
    if (nearestDistance > bestCandidateDistance) {
      bestCandidateDistance = nearestDistance;
      bestCandidate = point;
    }
  }
  return bestCandidate;
}

export function scatterOffset(
  id: number | undefined,
  index: number,
  groupSize: number
): [number, number] {
  if (groupSize <= 1) return [0, 0];

  const seed = Number.isFinite(id) ? (id as number) : index;
  const baseAngle = (2 * Math.PI * index) / groupSize;
  const angleJitter = (seededRandom(seed * 2) - 0.5) * (Math.PI / groupSize);
  const radius =
    CHARACTER_SCATTER_RADIUS +
    (seededRandom(seed * 2 + 1) - 0.5) * CHARACTER_SCATTER_JITTER;
  const angle = baseAngle + angleJitter;

  return [radius * Math.cos(angle), radius * Math.sin(angle)];
}

export interface PositionedCharacter {
  feature: GeoJSONFeature;
  cx: number;
  cy: number;
  isWalking?: boolean;
}

// Groups characters by (rounded) coordinate - several residents idle in the
// same house share one point - then places each one at a random spot inside
// that house's footprint. Falls back to a small scatter around the shared
// point for characters not inside any building (e.g. mid-journey). Sorting
// each group by id keeps every character's spot stable from one poll to the
// next instead of jumping around.
export function scatterCharacters(
  characterFeatures: GeoJSONFeature[],
  buildingFootprints: Ring[]
): PositionedCharacter[] {
  const groups = new Map<string, GeoJSONFeature[]>();
  for (const feature of characterFeatures) {
    const [x, y] = feature.geometry.coordinates as number[];
    if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
    const key = `${x.toFixed(2)},${y.toFixed(2)}`;
    const group = groups.get(key);
    if (group) {
      group.push(feature);
    } else {
      groups.set(key, [feature]);
    }
  }

  const positioned: PositionedCharacter[] = [];
  for (const group of groups.values()) {
    group.sort(
      (a, b) => (Number(a.properties?.id) || 0) - (Number(b.properties?.id) || 0)
    );
    const [baseX, baseY] = group[0].geometry.coordinates as number[];
    const footprint = buildingFootprints.find((ring) =>
      pointNearFootprint([baseX, baseY], ring)
    );
    const placedInGroup: [number, number][] = [];

    group.forEach((feature, index) => {
      const id = Number(feature.properties?.id);
      const seed = Number.isFinite(id) ? id : index;
      const randomPoint = footprint
        ? randomPointInPolygon(footprint, seed, placedInGroup)
        : null;

      if (randomPoint) {
        placedInGroup.push(randomPoint);
        positioned.push({ feature, cx: randomPoint[0], cy: randomPoint[1] });
      } else {
        const [dx, dy] = scatterOffset(id, index, group.length);
        positioned.push({ feature, cx: baseX + dx, cy: baseY + dy });
      }
    });
  }

  return positioned;
}
