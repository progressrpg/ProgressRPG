import type React from "react";
import {
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
  type Ref,
} from "react";
import { createPortal } from "react-dom";
import { LngLatBounds, setWorkerUrl } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { toLngLat } from "./utils";
import { scatterCharacters } from "./characters/placement";
import {
  buildingFootprintRings,
  buildingTypeLabel,
  cropSubzoneRingsByShelterBuilding,
  polygonAnchorLngLat,
} from "./geojson";
import {
  SELECTED_BUILDING_OUTLINE_LAYER,
  SELECTED_CHARACTER_HIGHLIGHT_LAYER,
  setFilterWithFade,
  TOOLTIP_ONLY_SELECTION_OPACITY,
} from "./layers";
import { buildStaticVillageFeatures, type WalkerState } from "./sourceData";
import { useMapInstance } from "./hooks/useMapInstance";
import { useVillageSource } from "./hooks/useVillageSource";
import { useWalkerAnimation } from "./hooks/useWalkerAnimation";
import MapDetailCard from "../MapDetailCard/MapDetailCard";
import CharacterDetail from "../CharacterDetail/CharacterDetail";
import BuildingDetail from "../BuildingDetail/BuildingDetail";
import styles from "./Map.module.scss";
import type { DetailSelection, GeoJSONFeature, TooltipOverlayState } from "./mapTypes";

export type { GeoJSONFeature, GeoJSONFeatureProperties } from "./mapTypes";

// maplibre-gl loads its own tile-processing worker via a runtime
// `new URL('./${name}.mjs', import.meta.url)` where `name` is a variable,
// not a string literal - Vite/Rollup's static asset analysis only bundles
// (and emits) worker URLs it can resolve at build time, so this pattern
// silently produces no build output for the production build (dev mode
// isn't affected - see the optimizeDeps.exclude comment in vite.config.ts,
// which addresses a different, dev-only version of this same underlying
// problem). Without this fix, the worker request 404s (silently, since the
// static host's SPA fallback serves index.html instead of a real 404) and
// every vector layer (fills/lines - anything that isn't a DOM-positioned
// Marker) renders nothing, with no error surfaced anywhere (issue #624
// investigation, 2026-07-31). vite.config.ts's viteStaticCopy plugin copies
// the worker file and its own sibling import (maplibre-gl-shared.mjs) to a
// fixed, unhashed path verbatim - the exact relative filename the worker's
// own `import "./maplibre-gl-shared.mjs"` expects - and setWorkerUrl is
// maplibre-gl's own public override for exactly this bundler scenario.
setWorkerUrl("/maplibre-gl/maplibre-gl-worker.mjs");

interface GeoJSON {
  features?: GeoJSONFeature[];
  bbox?: [number, number, number, number];
}

// Imperative escape hatch for one-off camera commands (as opposed to the
// declarative geojson/worldBounds props above) - "jump to this point" is an
// action, not state the owner should have to hold and diff.
export interface PopulationCentreMapHandle {
  flyToPoint: (point: [number, number]) => void;
}

interface PopulationCentreMapProps {
  geojson?: GeoJSON | null;
  // Called (debounced) whenever the camera settles on a new viewport, with a
  // quantized "minx,miny,maxx,maxy" bbox in raw 3857 metres - lets the owner
  // (MapPage) drive a bbox-scoped data fetch. Omit for a display-only map
  // (e.g. in tests).
  onViewportChange?: (bbox: string) => void;
  // Padded [minX, minY, maxX, maxY] in raw 3857 metres covering every seeded
  // population centre (MapWorldBoundsView) - limits how far the camera can
  // pan. Arrives asynchronously (a separate one-shot fetch), so it's applied
  // in its own effect below rather than at map construction time.
  worldBounds?: [number, number, number, number] | null;
  // React 19 passes `ref` through as a plain prop - no forwardRef needed.
  ref?: Ref<PopulationCentreMapHandle>;
  // Rendered as a floating overlay inside the map viewport itself (top-left,
  // clear of MapLibre's own NavigationControl at top-right) - lets the owner
  // add map-scoped controls (e.g. MapPage's "find village" button) without
  // this component needing to know what they are.
  children?: React.ReactNode;
}

// MapLibre's flyTo scales its own animation length by distance/zoom delta
// when no duration is given - villages can be many km apart (see
// import_village.py's placement grid), which made "find village" jumps take
// several seconds even once the destination's data was already cached.
// Pinning a fixed duration keeps every jump feeling equally snappy
// regardless of how far apart the two villages are.
const FLY_TO_DURATION_MS = 1200;

export default function PopulationCentreMap({
  geojson,
  onViewportChange,
  worldBounds,
  ref,
  children,
}: PopulationCentreMapProps) {
  const features: GeoJSONFeature[] = useMemo(
    () => geojson?.features || [],
    [geojson]
  );

  const containerRef = useRef<HTMLDivElement>(null);
  // Passed to MapDetailCard as DetailSurface's portal `container` so the
  // docked detail panel positions relative to the map itself, not the
  // viewport (see MapDetailCard.module.scss). State (not a plain ref) so
  // the value is available for render once the wrapper mounts.
  const [mapWrapperEl, setMapWrapperEl] = useState<HTMLDivElement | null>(null);
  const initialFitDoneRef = useRef(false);
  // Tracks which building/character the pointer is currently over, so the
  // mousemove handlers below only call setFilterWithFade on an actual
  // change rather than on every pointer movement within the same feature.
  const hoveredBuildingIdRef = useRef<number | null>(null);
  const hoveredCharacterIdRef = useRef<number | null>(null);

  const [tooltip, setTooltip] = useState<TooltipOverlayState | null>(null);
  const tooltipHostRef = useRef<HTMLDivElement | null>(null);
  const [tooltipHostEl, setTooltipHostEl] = useState<HTMLDivElement | null>(null);

  const [detail, setDetail] = useState<DetailSelection | null>(null);
  // Opening the richer detail card obscures the (unreachable, once the
  // card's overlay covers it) floating tooltip behind it - close it rather
  // than leave it lingering under the modal.
  const openDetail = useCallback((selection: DetailSelection) => {
    setTooltip(null);
    setDetail(selection);
  }, []);

  const buildingFootprints = useMemo(
    () => buildingFootprintRings(features),
    [features]
  );

  // Styled buildings/roads/fields/boundaries - everything the map draws
  // except characters. Only recomputed when `features` itself changes (each
  // ~2s poll), unlike character positions, which the walker loop below
  // recomputes on every animation frame - keeping this out of that loop is
  // what keeps a village's buildings/roads/fields from being re-styled and
  // re-reprojected 60 times a second while nothing about them has changed.
  const staticVillageFeatures = useMemo(
    () => buildStaticVillageFeatures(features),
    [features]
  );

  // Lets scatterCharacters spread a field_shelter's idle workers across the
  // crops Subzone(s) it services instead of clustering them at the
  // shelter's own small footprint - see scatterCharacters' own comment.
  const shelterFieldRings = useMemo(
    () => cropSubzoneRingsByShelterBuilding(features),
    [features]
  );

  const characterFeatures = useMemo(
    () => features.filter((f) => f.properties?.feature_type === "character"),
    [features]
  );

  // Characters with an active journey (a non-empty `path` from the backend,
  // see CharacterPointFeatureSerializer) are animated by the walker loop
  // below instead of the idle scatter-inside-building placement, which only
  // makes sense for characters standing still.
  const walkingFeatures = useMemo(
    () => characterFeatures.filter((f) => (f.properties?.path?.length ?? 0) > 0),
    [characterFeatures]
  );
  const idleFeatures = useMemo(
    () => characterFeatures.filter((f) => (f.properties?.path?.length ?? 0) === 0),
    [characterFeatures]
  );

  const positionedCharacters = useMemo(
    () => scatterCharacters(idleFeatures, buildingFootprints, shelterFieldRings),
    [idleFeatures, buildingFootprints, shelterFieldRings]
  );

  const idleCharacterPositions = useMemo(() => {
    return new Map(
      positionedCharacters.map(({ feature, cx, cy }) => [
        String(feature.properties?.id),
        [cx, cy] as [number, number],
      ])
    );
  }, [positionedCharacters]);

  // Shared between useVillageSource (reads it to build character features)
  // and useWalkerAnimation (writes it) - kept here rather than owned by
  // either hook so neither has to depend on the other's call order.
  const walkersRef = useRef<Map<string, WalkerState>>(new Map());

  // useMapInstance needs a refreshVillageSource callback at mount, before
  // useVillageSource (which produces the real one) can be called - it needs
  // mapReady, which only useMapInstance's own return value provides. Broken
  // by the same indirection the pre-split code used internally: a stable
  // wrapper that forwards to whatever's currently in the ref, updated by the
  // effect below once useVillageSource has run.
  const villageSourceRefreshRef = useRef<() => void>(() => {});
  const stableRefreshVillageSource = useCallback(() => {
    villageSourceRefreshRef.current();
  }, []);

  const { mapRef, sourceRef, mapReady } = useMapInstance({
    containerRef,
    onViewportChange,
    openDetail,
    setTooltip,
    refreshVillageSource: stableRefreshVillageSource,
    hoveredBuildingIdRef,
    hoveredCharacterIdRef,
    initialFitDoneRef,
  });

  const { refreshVillageSource } = useVillageSource({
    sourceRef,
    mapReady,
    features,
    staticVillageFeatures,
    characterFeatures,
    idleCharacterPositions,
    walkersRef,
  });

  useEffect(() => {
    villageSourceRefreshRef.current = refreshVillageSource;
  }, [refreshVillageSource]);

  useWalkerAnimation({
    walkingFeatures,
    mapReady,
    refreshVillageSource,
    walkersRef,
  });

  useImperativeHandle(
    ref,
    () => ({
      flyToPoint: (point) => {
        mapRef.current?.flyTo({
          center: toLngLat(point),
          zoom: 14,
          duration: FLY_TO_DURATION_MS,
          essential: true
        });
      },
    }),
    [mapRef]
  );

  // Keeps the tooltip overlay anchored to its map-space point while panning,
  // and reprojects the initial position once opened.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !tooltip) return;
    const updatePosition = () => {
      const point = map.project(tooltip.lngLat);
      const host = tooltipHostRef.current;
      if (host) {
        host.style.transform = `translate(${point.x}px, ${point.y}px)`;
      }
    };
    updatePosition();
    map.on("move", updatePosition);
    return () => {
      map.off("move", updatePosition);
    };
  }, [tooltip, mapRef]);

  // Fits the camera to the first bbox this map ever receives, then leaves
  // the camera alone - later polls update content, not the view, so the
  // user's own pan/zoom is never fought.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady || initialFitDoneRef.current || !geojson?.bbox) return;
    const [minX, minY, maxX, maxY] = geojson.bbox;
    const sw = toLngLat([minX, minY]);
    const ne = toLngLat([maxX, maxY]);
    map.fitBounds(new LngLatBounds(sw, ne), { padding: 40, animate: false });
    initialFitDoneRef.current = true;
  }, [geojson, mapReady, mapRef]);

  // Limits panning to a generous area around the seeded world, rather than
  // being fully unbounded (which would strand users in empty space with no
  // way back) - see design decision #6 in the map-viewport plan.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady || !worldBounds) return;
    const [minX, minY, maxX, maxY] = worldBounds;
    map.setMaxBounds(new LngLatBounds(toLngLat([minX, minY]), toLngLat([maxX, maxY])));
  }, [worldBounds, mapReady, mapRef]);

  // Outlines whichever building/character the detail card currently has
  // open (see SELECTED_BUILDING_OUTLINE_LAYER/SELECTED_CHARACTER_HIGHLIGHT_LAYER
  // in layers.ts) - driven off `detail` rather than a per-feature style
  // expression, since only one selection ever exists at a time. A tooltip
  // alone (without the detail card open) shows the same outline at reduced
  // intensity, as a preview of the same affordance.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return;
    const active = detail ?? tooltip?.entity ?? null;
    const opacity = detail ? 1 : TOOLTIP_ONLY_SELECTION_OPACITY;
    setFilterWithFade(
      map,
      SELECTED_BUILDING_OUTLINE_LAYER,
      "line-opacity",
      [
        "all",
        ["==", ["get", "feature_type"], "building"],
        ["==", ["get", "id"], active?.type === "building" ? active.id : -1],
      ],
      opacity
    );
    setFilterWithFade(
      map,
      SELECTED_CHARACTER_HIGHLIGHT_LAYER,
      "circle-stroke-opacity",
      [
        "all",
        ["==", ["get", "feature_type"], "character"],
        ["==", ["get", "id"], active?.type === "character" ? active.id : -1],
      ],
      opacity
    );
  }, [detail, tooltip, mapReady, mapRef]);

  // Derived from data the map already has loaded (this village's features/
  // characterFeatures) rather than a dedicated fetch - BuildingDetail's
  // residents/workers are every currently-loaded character feature whose
  // home_id/work_id (see CharacterPointFeatureSerializer) matches the
  // selected building.
  const selectedBuildingFeature = useMemo(() => {
    if (!detail || detail.type !== "building") return null;
    return (
      features.find(
        (f) =>
          f.properties?.feature_type === "building" &&
          Number(f.properties?.id) === detail.id
      ) ?? null
    );
  }, [detail, features]);

  const selectedBuildingResidents = useMemo(() => {
    if (!detail || detail.type !== "building") return [];
    return characterFeatures
      .filter((f) => f.properties?.home_id != null && Number(f.properties.home_id) === detail.id)
      .map((f) => ({
        id: Number(f.properties?.id),
        name: (f.properties?.name as string | undefined) ?? "",
        currentActivity: f.properties?.current_activity as string | null | undefined,
        isMoving: f.properties?.is_moving as boolean | null | undefined,
      }));
  }, [detail, characterFeatures]);

  const selectedBuildingWorkers = useMemo(() => {
    if (!detail || detail.type !== "building") return [];
    return characterFeatures
      .filter((f) => f.properties?.work_id != null && Number(f.properties.work_id) === detail.id)
      .map((f) => ({
        id: Number(f.properties?.id),
        name: (f.properties?.name as string | undefined) ?? "",
        currentActivity: f.properties?.current_activity as string | null | undefined,
        isMoving: f.properties?.is_moving as boolean | null | undefined,
      }));
  }, [detail, characterFeatures]);

  const selectedCharacterName = useMemo(() => {
    if (!detail || detail.type !== "character") return "Character";
    const feature = characterFeatures.find(
      (f) => Number(f.properties?.id) === detail.id
    );
    return (feature?.properties?.name as string | undefined) ?? "Character";
  }, [detail, characterFeatures]);

  // Detail card's "fly to" header button - reuses the same flyTo call as the
  // imperative flyToPoint handle, but resolves the point from whichever
  // entity is currently selected rather than a caller-supplied one.
  // idleCharacterPositions gives the exact scattered dot for a stationary
  // character; a walking character falls back to their last known raw node
  // position (close enough to their building - not worth reaching into the
  // walker animation ref for a "fly near" convenience button).
  const handleFlyToDetail = useCallback(() => {
    const map = mapRef.current;
    if (!map || !detail) return;
    let rawPoint: [number, number] | null = null;
    if (detail.type === "character") {
      const feature = characterFeatures.find((f) => Number(f.properties?.id) === detail.id);
      if (feature) {
        rawPoint =
          idleCharacterPositions.get(String(detail.id)) ??
          (feature.geometry.coordinates as [number, number]);
      }
    } else if (detail.type === "building" && selectedBuildingFeature) {
      rawPoint = polygonAnchorLngLat(selectedBuildingFeature.geometry);
    }
    if (!rawPoint) return;
    map.flyTo({
      center: toLngLat(rawPoint),
      zoom: 14,
      duration: FLY_TO_DURATION_MS,
      essential: true,
    });
  }, [detail, characterFeatures, idleCharacterPositions, selectedBuildingFeature, mapRef]);

  return (
    <div ref={setMapWrapperEl} className={styles.mapWrapper}>
      <div ref={containerRef} className={styles.mapContainer} />
      <div
        ref={(el) => {
          tooltipHostRef.current = el;
          setTooltipHostEl(el);
        }}
        className={styles.tooltipHost}
      />
      {tooltip &&
        tooltipHostEl &&
        createPortal(
          <div role="tooltip" className={styles.floatingTooltip}>
            {tooltip.content}
          </div>,
          tooltipHostEl
        )}
      {children && <div className={styles.controlsOverlay}>{children}</div>}
      {detail?.type === "character" && (
        <MapDetailCard
          open
          title={selectedCharacterName}
          onClose={() => setDetail(null)}
          onFlyTo={handleFlyToDetail}
          container={mapWrapperEl}
        >
          <CharacterDetail
            characterId={detail.id}
            onSelectBuilding={(buildingId) => openDetail({ type: "building", id: buildingId })}
            onSelectRelationship={(characterId) => openDetail({ type: "character", id: characterId })}
          />
        </MapDetailCard>
      )}
      {detail?.type === "building" && selectedBuildingFeature && (
        <MapDetailCard
          open
          title={
            (selectedBuildingFeature.properties?.name as string | undefined) ??
            buildingTypeLabel(
              selectedBuildingFeature.properties?.building_type as string | undefined
            )
          }
          onClose={() => setDetail(null)}
          onFlyTo={handleFlyToDetail}
          container={mapWrapperEl}
        >
          <BuildingDetail
            buildingType={selectedBuildingFeature.properties?.building_type as string | undefined}
            residents={selectedBuildingResidents}
            workers={selectedBuildingWorkers}
            workerCount={selectedBuildingFeature.properties?.workers as number | null | undefined}
            residentialCapacity={
              selectedBuildingFeature.properties?.residential_capacity as
                | number
                | null
                | undefined
            }
            goods={
              selectedBuildingFeature.properties?.goods as
                | { good_type?: string; display?: string }[]
                | null
                | undefined
            }
            onSelectResident={(characterId) => openDetail({ type: "character", id: characterId })}
            onSelectWorker={(characterId) => openDetail({ type: "character", id: characterId })}
          />
        </MapDetailCard>
      )}
    </div>
  );
}
