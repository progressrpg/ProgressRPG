import type React from "react";
import { coordsToLngLat, fieldFillFor } from "./utils";
import { BuildingTooltipContent } from "./MapTooltips";
import type { BuildingFootprint, Ring } from "./characters/placement";
import type { GeoJSONFeature, GeoJSONFeatureProperties } from "./Map";

export function buildingFootprintRings(features: GeoJSONFeature[]): BuildingFootprint[] {
  return features
    .filter(
      (f) => f.properties?.feature_type === "building" && f.geometry.type === "Polygon"
    )
    .map((f) => ({
      id: f.properties?.id as number,
      buildingType: f.properties?.building_type as string | undefined,
      ring: (f.geometry.coordinates as number[][][])[0],
    }))
    .filter((fp): fp is BuildingFootprint => Boolean(fp.ring?.length));
}

// Maps a field_shelter Building's id to the footprint ring(s) of every crops
// Subzone it services (see scatterCharacters in characters/placement.ts) - a
// shelter is shared by every crops Subzone in its population centre (see
// generate_fields.py), so this is a 1:many lookup.
export function cropSubzoneRingsByShelterBuilding(
  features: GeoJSONFeature[]
): Map<number, Ring[]> {
  const bySheltered = new Map<number, Ring[]>();
  for (const f of features) {
    if (f.properties?.feature_type !== "subzone") continue;
    if (f.properties?.usage !== "crops") continue;
    if (f.geometry.type !== "Polygon") continue;
    const shelterId = f.properties?.shelter_building_id as number | null | undefined;
    if (shelterId == null) continue;
    const ring = (f.geometry.coordinates as number[][][])[0];
    if (!ring?.length) continue;
    const rings = bySheltered.get(shelterId);
    if (rings) {
      rings.push(ring);
    } else {
      bySheltered.set(shelterId, [ring]);
    }
  }
  return bySheltered;
}

// Buildings carry full names like "House 2 of (Driftmoor village)" for
// backend bookkeeping; the tooltip only needs the plain building type.
export const BUILDING_TYPE_LABELS: Record<string, string> = {
  residential: "House",
  granary: "Granary",
  inn: "Inn",
  mill: "Mill",
  bakery: "Bakery",
  hall: "Hall",
  market: "Market",
  communal: "Communal",
  field_shelter: "Field Shelter",
};

// Buildings carry full bookkeeping names (see BuildingFeatureSerializer's
// docstring) that aren't meant for display - this is the single place that
// turns a building_type into the plain label shown in both a building's own
// tooltip below and a character's "Lives at:"/"Works at:" tooltip
// (CharacterTooltipContent, populated in Map.tsx).
export function buildingTypeLabel(buildingType: string | null | undefined): string {
  return (buildingType && BUILDING_TYPE_LABELS[buildingType]) || "Building";
}

// Anchors a polygon/multipolygon feature's tooltip to the top-center of its
// bounding box rather than wherever inside the shape it was clicked -
// otherwise a click near the middle of a large building/subzone footprint
// would leave the tooltip's own fixed offset (see .floatingTooltip in
// Map.module.scss) still overlapping the shape's own top edge.
export function polygonAnchorLngLat(geometry: {
  type: string;
  coordinates: unknown;
}): [number, number] {
  const rings: number[][][] =
    geometry.type === "MultiPolygon"
      ? (geometry.coordinates as number[][][][]).flat()
      : (geometry.coordinates as number[][][]);
  let minLng = Infinity;
  let maxLng = -Infinity;
  let maxLat = -Infinity;
  for (const ring of rings) {
    for (const [lng, lat] of ring) {
      if (lng < minLng) minLng = lng;
      if (lng > maxLng) maxLng = lng;
      if (lat > maxLat) maxLat = lat;
    }
  }
  return [(minLng + maxLng) / 2, maxLat];
}

export function polygonTooltipContent(
  properties: GeoJSONFeatureProperties | null | undefined,
  onViewDetails?: () => void
): React.ReactNode | undefined {
  if (properties?.feature_type === "building") {
    const buildingType = properties?.building_type as string | undefined;
    const label = (properties?.name as string | undefined) ?? buildingTypeLabel(buildingType);
    return (
      <BuildingTooltipContent
        label={label}
        buildingType={buildingType}
        workers={properties?.workers as number | null | undefined}
        residents={properties?.residents as number | null | undefined}
        goods={properties?.goods as { good_type?: string; display?: string }[] | null | undefined}
        onViewDetails={onViewDetails}
      />
    );
  }
  if (properties?.feature_type === "subzone") {
    if (properties?.usage === "square") return "Square";
    if (properties?.usage !== "crops") return properties?.name;

    const stage = properties?.crop_stage as string | null | undefined;
    if (stage === "ready") return "Crops - Ready to harvest";
    if (stage === "growing") {
      const progress = properties?.crop_progress as number | null | undefined;
      const percent = Number.isFinite(progress) ? Math.round((progress as number) * 100) : null;
      return percent === null ? "Crops - Growing" : `Crops - Growing (${percent}%)`;
    }
    return "Crops - Fallow";
  }
  return properties?.name;
}

// Open communal outdoor space (see watabou_import._import_squares) - a
// warm, paved tone distinct from both a crops Subzone's green (fieldFillFor)
// and a building's default grey, so a plaza reads as open ground rather
// than a structure.
const SQUARE_FILL_COLOR = "#d8c9a8";

// Precomputes per-feature presentation properties (fill/stroke) so map
// styling can stay simple `["get", ...]` paint expressions instead of
// duplicating fieldFillFor's stage/progress logic as a style expression.
export function styledPolygonFeatures(features: GeoJSONFeature[]) {
  return features
    .filter((f) => f.geometry.type === "Polygon")
    .map((f) => {
      const isBoundary = f.properties?.feature_type === "boundary";
      const isCropSubzone =
        f.properties?.feature_type === "subzone" && f.properties?.usage === "crops";
      const isSquareSubzone =
        f.properties?.feature_type === "subzone" && f.properties?.usage === "square";
      const fillColor = isBoundary
        ? "transparent"
        : isCropSubzone
        ? fieldFillFor(
            f.properties?.crop_stage as string | null | undefined,
            f.properties?.crop_progress as number | null | undefined
          )
        : isSquareSubzone
        ? SQUARE_FILL_COLOR
        : "#ddd";
      return {
        type: "Feature" as const,
        geometry: {
          type: f.geometry.type,
          coordinates: coordsToLngLat(f.geometry.coordinates as never),
        },
        properties: { ...f.properties, fillColor },
      };
    });
}

export function styledLineFeatures(features: GeoJSONFeature[]) {
  return features
    .filter((f) => f.geometry.type === "LineString")
    .map((f) => ({
      type: "Feature" as const,
      geometry: {
        type: f.geometry.type,
        coordinates: coordsToLngLat(f.geometry.coordinates as never),
      },
      properties: f.properties,
    }));
}

export function styledPointFeatures(features: GeoJSONFeature[]) {
  return features
    .filter((f) => f.geometry.type === "Point")
    .map((f) => ({
      type: "Feature" as const,
      geometry: {
        type: "Point",
        coordinates: coordsToLngLat(f.geometry.coordinates as never),
      },
      properties: f.properties,
    }));
}
