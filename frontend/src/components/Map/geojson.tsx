import type React from "react";
import { coordsToLngLat, fieldFillFor } from "./utils";
import { BuildingTooltipContent } from "./MapTooltips";
import type { Ring } from "./characters/placement";
import type { GeoJSONFeature, GeoJSONFeatureProperties } from "./Map";

export function buildingFootprintRings(features: GeoJSONFeature[]): Ring[] {
  return features
    .filter(
      (f) => f.properties?.feature_type === "building" && f.geometry.type === "Polygon"
    )
    .map((f) => (f.geometry.coordinates as number[][][])[0])
    .filter((ring): ring is Ring => Boolean(ring?.length));
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

export function polygonTooltipContent(
  properties: GeoJSONFeatureProperties | null | undefined
): React.ReactNode | undefined {
  if (properties?.feature_type === "building") {
    const buildingType = properties?.building_type as string | undefined;
    const label = (buildingType && BUILDING_TYPE_LABELS[buildingType]) || "Building";
    return (
      <BuildingTooltipContent
        label={label}
        buildingType={buildingType}
        workers={properties?.workers as number | null | undefined}
        residents={properties?.residents as number | null | undefined}
        goods={properties?.goods as { good_type?: string; display?: string }[] | null | undefined}
      />
    );
  }
  if (properties?.feature_type === "subzone") {
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
      const fillColor = isBoundary
        ? "transparent"
        : isCropSubzone
        ? fieldFillFor(
            f.properties?.crop_stage as string | null | undefined,
            f.properties?.crop_progress as number | null | undefined
          )
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
