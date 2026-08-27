import type React from "react";

// Shared between Map.tsx and its extracted hooks (useMapInstance,
// useVillageSource, useWalkerAnimation) - split out to avoid a circular
// import between them.

export interface GeoJSONFeatureProperties {
  feature_type?: string;
  name?: string;
  id?: number;
  // Remaining waypoints (capped server-side, see JOURNEY_PATH_PREVIEW_LIMIT
  // in locations/serializers.py) for a character with an active journey;
  // null/absent for an idle character.
  path?: [number, number][] | null;
  effective_speed?: number;
  [key: string]: unknown;
}

export interface GeoJSONFeature {
  geometry: {
    type: string;
    coordinates: unknown;
  };
  properties?: GeoJSONFeatureProperties | null;
}

// The map's second level of progressive disclosure (tooltip -> click "View
// details" -> DetailCard). Only character/building are wired up yet
// (population centres are a later follow-up - see the map entity detail
// card issue).
export type DetailSelection =
  | { type: "character"; id: number }
  | { type: "building"; id: number };

export interface TooltipOverlayState {
  key: string;
  content: React.ReactNode;
  lngLat: [number, number];
  // Which building/character (if any) this tooltip belongs to, so the
  // selection-outline effect below can show a lower-intensity preview of
  // the outline while just the tooltip - not the full DetailCard - is open.
  entity?: DetailSelection;
}
