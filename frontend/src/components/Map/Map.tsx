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
import { createRoot, type Root } from "react-dom/client";
import { TamaguiProvider } from "tamagui";
import {
  Map as MapLibreMap,
  NavigationControl,
  LngLatBounds,
  setWorkerUrl,
  type GeoJSONSource,
  type MapGeoJSONFeature,
  type MapMouseEvent,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { fromLngLat, quantizeBbox, toLngLat } from "./utils";
import { CharacterTooltipContent, PopulationCentreTooltipContent } from "./MapTooltips";
import { scatterCharacters } from "./characters/placement";
import {
  buildingFootprintRings,
  buildingTypeLabel,
  cropSubzoneRingsByShelterBuilding,
  polygonAnchorLngLat,
  polygonTooltipContent,
} from "./geojson";
import {
  addCharacterImage,
  addVillageLayers,
  BUILDINGS_FILL_LAYER,
  CLICKABLE_LAYERS,
  HOVER_BUILDING_OUTLINE_LAYER,
  HOVER_CHARACTER_HIGHLIGHT_LAYER,
  HOVER_OPACITY,
  SELECTED_BUILDING_OUTLINE_LAYER,
  SELECTED_CHARACTER_HIGHLIGHT_LAYER,
  setFilterWithFade,
  TOOLTIP_ONLY_SELECTION_OPACITY,
  VILLAGE_LABEL_LAYER,
} from "./layers";
import {
  buildCharacterPointFeatures,
  buildStaticVillageFeatures,
  buildVillageSourceData,
  type WalkerState,
} from "./sourceData";
import MapDetailCard from "../MapDetailCard/MapDetailCard";
import CharacterDetail from "../CharacterDetail/CharacterDetail";
import BuildingDetail from "../BuildingDetail/BuildingDetail";
import styles from "./Map.module.scss";

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

// A camera move fires many intermediate events per drag/zoom gesture -
// debouncing means onViewportChange (and the network fetch it triggers)
// only fires once the camera has actually settled.
const VIEWPORT_DEBOUNCE_MS = 400;

// MapLibre's flyTo scales its own animation length by distance/zoom delta
// when no duration is given - villages can be many km apart (see
// import_village.py's placement grid), which made "find village" jumps take
// several seconds even once the destination's data was already cached.
// Pinning a fixed duration keeps every jump feeling equally snappy
// regardless of how far apart the two villages are.
const FLY_TO_DURATION_MS = 1200;

// The map's second level of progressive disclosure (tooltip -> click "View
// details" -> DetailCard). Only character/building are wired up yet
// (population centres are a later follow-up - see the map entity detail
// card issue).
type DetailSelection =
  | { type: "character"; id: number }
  | { type: "building"; id: number };

interface TooltipOverlayState {
  key: string;
  content: React.ReactNode;
  lngLat: [number, number];
  // Which building/character (if any) this tooltip belongs to, so the
  // selection-outline effect below can show a lower-intensity preview of
  // the outline while just the tooltip - not the full DetailCard - is open.
  entity?: DetailSelection;
}

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
  const mapRef = useRef<MapLibreMap | null>(null);
  const sourceRef = useRef<GeoJSONSource | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const initialFitDoneRef = useRef(false);
  // Tracks which building/character the pointer is currently over, so the
  // mousemove handlers below only call setFilterWithFade on an actual
  // change rather than on every pointer movement within the same feature.
  const hoveredBuildingIdRef = useRef<number | null>(null);
  const hoveredCharacterIdRef = useRef<number | null>(null);

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
    []
  );

  const [tooltip, setTooltip] = useState<TooltipOverlayState | null>(null);
  const tooltipRootRef = useRef<Root | null>(null);
  const tooltipHostRef = useRef<HTMLDivElement | null>(null);

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

  // Per-character walker state (current interpolated position, remaining
  // path, speed), keyed by character id. Lives in a ref rather than state -
  // it's updated up to 60x/sec by the animation loop below.
  const walkersRef = useRef<Map<string, WalkerState>>(new Map());

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
  }, [staticVillageFeatures, characterFeatures, idleCharacterPositions]);

  // Creates the map once. onViewportChange and refreshVillageSource are each
  // read via a ref inside the handlers below rather than as effect deps, so
  // the map (and its camera event listener) isn't torn down and recreated on
  // every poll/feature update.
  const onViewportChangeRef = useRef(onViewportChange);
  useEffect(() => {
    onViewportChangeRef.current = onViewportChange;
  }, [onViewportChange]);

  const refreshVillageSourceRef = useRef(refreshVillageSource);
  useEffect(() => {
    refreshVillageSourceRef.current = refreshVillageSource;
  }, [refreshVillageSource]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const map = new MapLibreMap({
      container,
      style: { version: 8, sources: {}, layers: [] },
      center: [0, 0],
      zoom: 2,
    });
    mapRef.current = map;
    map.addControl(new NavigationControl({ showCompass: false }), "top-right");

    let debounceTimer: ReturnType<typeof setTimeout>;
    const handleMoveEnd = () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        const onChange = onViewportChangeRef.current;
        if (!onChange) return;
        const bounds = map.getBounds();
        const sw = fromLngLat([bounds.getWest(), bounds.getSouth()]);
        const ne = fromLngLat([bounds.getEast(), bounds.getNorth()]);
        onChange(quantizeBbox(padBbox([sw[0], sw[1], ne[0], ne[1]])));
      }, VIEWPORT_DEBOUNCE_MS);
    };

    const closeTooltip = () => setTooltip(null);

    map.on("load", () => {
      addCharacterImage(map);
      map.addSource("village", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      sourceRef.current = map.getSource("village") as GeoJSONSource;
      addVillageLayers(map);

      map.on("click", "characters", (e: MapMouseEvent & { features?: MapGeoJSONFeature[] }) => {
        const feature = e.features?.[0];
        if (!feature) return;
        e.originalEvent?.stopPropagation?.();
        // current_location_type/destination_location_type carry the
        // building_type (e.g. "residential", "bakery") of where the
        // character currently is / is walking to, not a bookkeeping name -
        // resolved to the same plain label ("House", "Bakery") shown on
        // that building's own tooltip, via buildingTypeLabel. null means
        // that spot isn't inside a building at all ("outside").
        const currentLocationType = feature.properties?.current_location_type as
          | string
          | null
          | undefined;
        const destinationType = feature.properties?.destination_location_type as
          | string
          | null
          | undefined;
        const characterId = Number(feature.properties?.id);
        setTooltip({
          key: `character-${feature.id ?? JSON.stringify(feature.properties)}`,
          content: (
            <CharacterTooltipContent
              name={feature.properties?.name as string | undefined}
              currentActivity={feature.properties?.current_activity as string | null | undefined}
              isMoving={feature.properties?.is_moving as boolean | null | undefined}
              currentLocationLabel={
                currentLocationType ? buildingTypeLabel(currentLocationType) : null
              }
              destinationLabel={destinationType ? buildingTypeLabel(destinationType) : null}
              onViewDetails={() => openDetail({ type: "character", id: characterId })}
            />
          ),
          // Anchored to the character's own point, not the click position -
          // MapLibre's hit-testing for icon layers uses the full image
          // bounding box (see createCharacterIcon's comment in layers.ts),
          // so a click near an edge of a large (zoomed-in) icon would
          // otherwise leave the tooltip's fixed offset still overlapping it.
          lngLat: feature.geometry.coordinates as [number, number],
          entity: { type: "character", id: characterId },
        });
      });
      map.on("mouseenter", "characters", () => {
        map.getCanvas().style.cursor = "pointer";
      });
      map.on("mouseleave", "characters", () => {
        map.getCanvas().style.cursor = "";
        if (hoveredCharacterIdRef.current === null) return;
        hoveredCharacterIdRef.current = null;
        setFilterWithFade(
          map,
          HOVER_CHARACTER_HIGHLIGHT_LAYER,
          "circle-stroke-opacity",
          ["all", ["==", ["get", "feature_type"], "character"], ["==", ["get", "id"], -1]],
          HOVER_OPACITY
        );
      });
      map.on(
        "mousemove",
        "characters",
        (e: MapMouseEvent & { features?: MapGeoJSONFeature[] }) => {
          const feature = e.features?.[0];
          const characterId = feature ? Number(feature.properties?.id) : null;
          if (characterId === hoveredCharacterIdRef.current) return;
          hoveredCharacterIdRef.current = characterId;
          setFilterWithFade(
            map,
            HOVER_CHARACTER_HIGHLIGHT_LAYER,
            "circle-stroke-opacity",
            [
              "all",
              ["==", ["get", "feature_type"], "character"],
              ["==", ["get", "id"], characterId ?? -1],
            ],
            HOVER_OPACITY
          );
        }
      );

      // Tapping/selecting a village's name label expands it into its
      // progress bar + state (issue #673) - the label itself is coloured by
      // state at rest (see VILLAGE_LABEL_LAYER in layers.ts).
      map.on(
        "click",
        VILLAGE_LABEL_LAYER,
        (e: MapMouseEvent & { features?: MapGeoJSONFeature[] }) => {
          const feature = e.features?.[0];
          if (!feature) return;
          e.originalEvent?.stopPropagation?.();
          setTooltip({
            key: `population-centre-${feature.properties?.population_centre_id ?? JSON.stringify(feature.properties)}`,
            content: (
              <PopulationCentreTooltipContent
                name={feature.properties?.name as string | undefined}
                state={feature.properties?.state as string | null | undefined}
                progress={feature.properties?.progress as number | null | undefined}
              />
            ),
            lngLat: [e.lngLat.lng, e.lngLat.lat],
          });
        }
      );
      map.on("mouseenter", VILLAGE_LABEL_LAYER, () => {
        map.getCanvas().style.cursor = "pointer";
      });
      map.on("mouseleave", VILLAGE_LABEL_LAYER, () => {
        map.getCanvas().style.cursor = "";
      });

      refreshVillageSourceRef.current();

      CLICKABLE_LAYERS.forEach((layerId, index) => {
        // Layers earlier in CLICKABLE_LAYERS take priority when polygons
        // overlap (e.g. a "field_shelter" building's footprint sits inside
        // its crop subzone's boundary) - see the array's own comment.
        const higherPriorityLayers = CLICKABLE_LAYERS.slice(0, index);
        map.on("click", layerId, (e: MapMouseEvent & { features?: MapGeoJSONFeature[] }) => {
          const feature = e.features?.[0];
          if (!feature) return;
          // A village's name label - or a character standing inside a
          // building's footprint - can sit over a building/subzone
          // underneath it, and CLICKABLE_LAYERS entries can overlap each
          // other too - each map.on(type, layerId, ...) delegate queries
          // features independently, so every handler whose layer has a hit
          // fires for the same click (stopPropagation on the DOM event
          // doesn't stop sibling MapLibre delegates). Deferring to the
          // higher-priority handler (registered/run first, so it already
          // set the tooltip) keeps its tooltip from being clobbered.
          if (
            map.queryRenderedFeatures(e.point, { layers: ["characters", VILLAGE_LABEL_LAYER] })
              .length > 0
          ) {
            return;
          }
          if (
            higherPriorityLayers.length > 0 &&
            map.queryRenderedFeatures(e.point, { layers: higherPriorityLayers }).length > 0
          ) {
            return;
          }
          e.originalEvent?.stopPropagation?.();
          const buildingId = Number(feature.properties?.id);
          const content = polygonTooltipContent(
            feature.properties as GeoJSONFeatureProperties,
            feature.properties?.feature_type === "building"
              ? () => openDetail({ type: "building", id: buildingId })
              : undefined
          );
          if (!content) return;
          setTooltip({
            key: `${layerId}-${feature.id ?? JSON.stringify(feature.properties)}`,
            content,
            lngLat: polygonAnchorLngLat(feature.geometry),
            entity:
              feature.properties?.feature_type === "building"
                ? { type: "building", id: buildingId }
                : undefined,
          });
        });
        map.on("mouseenter", layerId, () => {
          map.getCanvas().style.cursor = "pointer";
        });
        map.on("mouseleave", layerId, () => {
          map.getCanvas().style.cursor = "";
          if (layerId !== BUILDINGS_FILL_LAYER) return;
          if (hoveredBuildingIdRef.current === null) return;
          hoveredBuildingIdRef.current = null;
          setFilterWithFade(
            map,
            HOVER_BUILDING_OUTLINE_LAYER,
            "line-opacity",
            ["all", ["==", ["get", "feature_type"], "building"], ["==", ["get", "id"], -1]],
            HOVER_OPACITY
          );
        });
        if (layerId === BUILDINGS_FILL_LAYER) {
          map.on(
            "mousemove",
            layerId,
            (e: MapMouseEvent & { features?: MapGeoJSONFeature[] }) => {
              // A character standing inside a building still sits over its
              // fill layer, so this mousemove keeps firing alongside the
              // "characters" layer's own hover handler - the character's
              // hover outline should take priority rather than showing
              // both at once (mirrors the click-priority check above).
              const overCharacter =
                map.queryRenderedFeatures(e.point, { layers: ["characters"] }).length >
                0;
              const feature = e.features?.[0];
              const buildingId = overCharacter
                ? null
                : feature
                  ? Number(feature.properties?.id)
                  : null;
              if (buildingId === hoveredBuildingIdRef.current) return;
              hoveredBuildingIdRef.current = buildingId;
              setFilterWithFade(
                map,
                HOVER_BUILDING_OUTLINE_LAYER,
                "line-opacity",
                [
                  "all",
                  ["==", ["get", "feature_type"], "building"],
                  ["==", ["get", "id"], buildingId ?? -1],
                ],
                HOVER_OPACITY
              );
            }
          );
        }
      });

      map.on("click", (e: MapMouseEvent) => {
        // A click that hit one of the clickable layers is handled by the
        // per-layer listeners above and stops here; a click on empty map
        // area closes whatever tooltip is open.
        const hits = map.queryRenderedFeatures(e.point, {
          layers: ["characters", VILLAGE_LABEL_LAYER, ...CLICKABLE_LAYERS],
        });
        if (hits.length === 0) closeTooltip();
      });

      map.on("moveend", handleMoveEnd);
      map.on("moveend", () => container.classList.remove(styles.cameraMoving));
      map.on("movestart", closeTooltip);
      // Idle characters glide between polls via a CSS transition (see
      // .characterMarker), but MapLibre also updates each Marker's transform
      // on every camera move to keep it pixel-anchored while panning/
      // zooming - without this, that recalculation gets caught by the same
      // transition and characters visibly lag behind the map instead of
      // moving with it instantly.
      map.on("movestart", () => container.classList.add(styles.cameraMoving));

      setMapReady(true);
    });

    return () => {
      clearTimeout(debounceTimer);
      map.remove();
      mapRef.current = null;
      setMapReady(false);
      initialFitDoneRef.current = false;
    };
    // openDetail is a useCallback with its own `[]` deps, so it's
    // referentially stable - listing it here satisfies exhaustive-deps
    // without changing this effect's actual "run once on mount" behaviour.
  }, [openDetail]);

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
  }, [tooltip]);

  // Renders into a React root mounted on the tooltip host div imperatively,
  // since the host itself lives outside React's tree (positioned by the
  // MapLibre `move` handler above, not by React re-render). The host div is
  // always present in the JSX below (never conditionally rendered) so this
  // effect can rely on the ref and the root it creates staying valid across
  // every open/close cycle - conditionally rendering the host would let
  // React null out the ref (and detach the div) before this effect's next
  // run saw `tooltip` go falsy, leaving a stale root pointed at a removed
  // DOM node that every later tooltip would silently render into instead of
  // the real (new) host div.
  //
  // This root is a separate React tree from the one main.tsx mounts, so it
  // doesn't inherit that tree's <TamaguiProvider> context (React context
  // follows the component tree, not DOM nesting) - PopulationCentreTooltipContent's
  // ProgressBar (#673, #580) would otherwise throw ("Missing tamagui config")
  // the moment a village marker is tapped. Re-providing it here, right at
  // this second root, is the fix.
  useEffect(() => {
    const host = tooltipHostRef.current;
    if (!host) return;
    if (!tooltipRootRef.current) {
      tooltipRootRef.current = createRoot(host);
    }
    tooltipRootRef.current.render(
      tooltip ? (
        <TamaguiProvider config={tamaguiConfig} defaultTheme="light">
          <div role="tooltip" className={styles.floatingTooltip}>
            {tooltip.content}
          </div>
        </TamaguiProvider>
      ) : null
    );
  }, [tooltip]);

  // Feeds the current geojson into the map's GeoJSON source whenever it
  // changes.
  useEffect(() => {
    if (!mapReady) return;
    refreshVillageSource();
  }, [mapReady, refreshVillageSource]);

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
  }, [geojson, mapReady]);

  // Limits panning to a generous area around the seeded world, rather than
  // being fully unbounded (which would strand users in empty space with no
  // way back) - see design decision #6 in the map-viewport plan.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady || !worldBounds) return;
    const [minX, minY, maxX, maxY] = worldBounds;
    map.setMaxBounds(new LngLatBounds(toLngLat([minX, minY]), toLngLat([maxX, maxY])));
  }, [worldBounds, mapReady]);

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
  }, [walkingFeatures]);

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
  }, [characterFeatures, features, idleCharacterPositions, mapReady]);

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

    const step = () => refreshVillageSource();

    step();
    const intervalId = window.setInterval(step, 16);
    return () => window.clearInterval(intervalId);
  }, [mapReady, walkingFeatures.length, refreshVillageSource]);

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
  }, [detail, tooltip, mapReady]);

  // Unmount cleanup for the tooltip root when the whole component goes away.
  useEffect(() => {
    return () => {
      const tooltipRoot = tooltipRootRef.current;
      tooltipRootRef.current = null;
      // Defer nested-root unmount so it does not run during parent-root
      // teardown, which can trigger React's unmount-during-render warning.
      queueMicrotask(() => {
        tooltipRoot?.unmount();
      });
      sourceRef.current = null;
    };
  }, []);

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
  }, [detail, characterFeatures, idleCharacterPositions, selectedBuildingFeature]);

  return (
    <div ref={setMapWrapperEl} className={styles.mapWrapper}>
      <div ref={containerRef} className={styles.mapContainer} />
      <div ref={tooltipHostRef} className={styles.tooltipHost} />
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
