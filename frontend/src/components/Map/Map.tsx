import type React from "react";
import { useEffect, useImperativeHandle, useMemo, useRef, useState, type Ref } from "react";
import { createRoot, type Root } from "react-dom/client";
import {
  Map as MapLibreMap,
  Marker,
  NavigationControl,
  LngLatBounds,
  setWorkerUrl,
  type GeoJSONSource,
  type MapGeoJSONFeature,
  type MapMouseEvent,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import Tooltip, { TooltipProvider } from "../Tooltip/Tooltip";
import { fromLngLat, quantizeBbox, toLngLat } from "./utils";
import { CharacterTooltipContent } from "./MapTooltips";
import { colourForCharacter, scatterCharacters } from "./characters/placement";
import {
  buildingFootprintRings,
  polygonTooltipContent,
  styledLineFeatures,
  styledPolygonFeatures,
} from "./geojson";
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

// A walker's position is never stepped incrementally frame-to-frame (that
// approach let small per-poll speed mismatches between client and server
// silently accumulate over the whole journey, surfacing as a character
// lagging further and further behind, then snapping/rushing to catch up).
// Instead each poll records a fresh checkpoint - the authoritative position
// the server reported, the remaining path from there, and the client
// timestamp it was received - and every frame recomputes position from
// scratch as a pure function of that checkpoint and elapsed real time.
// Whatever drift builds up within a single poll interval (small, since it's
// only ever one interval's worth) is wiped out by the next poll's fresh
// checkpoint rather than compounding across the journey.
interface WalkerState {
  checkpointPos: [number, number];
  path: [number, number][];
  speed: number;
  receivedAt: number;
}

interface MarkerEntry {
  marker: Marker;
  root: Root;
  element: HTMLDivElement;
}

// Walks `distance` units from `start` along `path`, consuming as many
// waypoints as it reaches rather than stopping at the first one short of the
// full distance - the same carry-over-leftover-budget approach as the
// backend's step_toward (locations/services/movement.py), so a character
// crossing several short segments doesn't visibly slow down at each one.
// Holds at the final point rather than extrapolating past it if `distance`
// exceeds the path's total length (e.g. the client's clock has run ahead of
// the server's capped path preview - the next poll will supply more path).
function positionAlongPath(
  start: [number, number],
  path: [number, number][],
  distance: number
): [number, number] {
  let pos = start;
  let remaining = distance;

  for (const [nx, ny] of path) {
    const dx = nx - pos[0];
    const dy = ny - pos[1];
    const segmentDistance = Math.hypot(dx, dy);

    if (segmentDistance <= remaining) {
      pos = [nx, ny];
      remaining -= segmentDistance;
    } else {
      const factor = segmentDistance === 0 ? 0 : remaining / segmentDistance;
      pos = [pos[0] + dx * factor, pos[1] + dy * factor];
      break;
    }
  }

  return pos;
}

// A camera move fires many intermediate events per drag/zoom gesture -
// debouncing means onViewportChange (and the network fetch it triggers)
// only fires once the camera has actually settled.
const VIEWPORT_DEBOUNCE_MS = 400;

const BOUNDARY_FILL_LAYER = "boundary-fill";
const BOUNDARY_LINE_LAYER = "boundary-line";
const BUILDINGS_FILL_LAYER = "buildings-fill";
const SUBZONES_FILL_LAYER = "subzones-fill";
const PATHS_LINE_LAYER = "paths-line";
const ROADS_LINE_LAYER = "roads-line";
const CLICKABLE_LAYERS = [BOUNDARY_FILL_LAYER, BUILDINGS_FILL_LAYER, SUBZONES_FILL_LAYER];

interface TooltipOverlayState {
  key: string;
  content: React.ReactNode;
  lngLat: [number, number];
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
  const mapRef = useRef<MapLibreMap | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const initialFitDoneRef = useRef(false);

  useImperativeHandle(
    ref,
    () => ({
      flyToPoint: (point) => {
        mapRef.current?.flyTo({ center: toLngLat(point), essential: true });
      },
    }),
    []
  );

  const [tooltip, setTooltip] = useState<TooltipOverlayState | null>(null);
  const tooltipRootRef = useRef<Root | null>(null);
  const tooltipHostRef = useRef<HTMLDivElement | null>(null);

  // Creates the map once. onViewportChange is read via a ref inside the
  // handler below rather than as an effect dep, so the camera event
  // listener isn't torn down and re-attached on every poll.
  const onViewportChangeRef = useRef(onViewportChange);
  useEffect(() => {
    onViewportChangeRef.current = onViewportChange;
  }, [onViewportChange]);

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
        onChange(quantizeBbox([sw[0], sw[1], ne[0], ne[1]]));
      }, VIEWPORT_DEBOUNCE_MS);
    };

    const closeTooltip = () => setTooltip(null);

    map.on("load", () => {
      map.addSource("village", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: BOUNDARY_FILL_LAYER,
        type: "fill",
        source: "village",
        filter: ["==", ["get", "feature_type"], "boundary"],
        paint: { "fill-color": "transparent" },
      });
      map.addLayer({
        id: BOUNDARY_LINE_LAYER,
        type: "line",
        source: "village",
        filter: ["==", ["get", "feature_type"], "boundary"],
        paint: { "line-color": "#888", "line-width": 2 },
      });
      map.addLayer({
        id: SUBZONES_FILL_LAYER,
        type: "fill",
        source: "village",
        filter: ["==", ["get", "feature_type"], "subzone"],
        paint: { "fill-color": ["get", "fillColor"], "fill-outline-color": "#333" },
      });
      map.addLayer({
        id: BUILDINGS_FILL_LAYER,
        type: "fill",
        source: "village",
        filter: ["==", ["get", "feature_type"], "building"],
        paint: { "fill-color": ["get", "fillColor"], "fill-outline-color": "#333" },
      });
      map.addLayer({
        id: PATHS_LINE_LAYER,
        type: "line",
        source: "village",
        filter: ["==", ["get", "feature_type"], "path"],
        // Paths are the Node/Path pathfinding graph's edges (straight lines
        // between two nodes, not real street geometry) - rendered invisible.
        // Kept as a real layer so they're available if visible styling is
        // wanted later, but with no interactivity registered (see
        // CLICKABLE_LAYERS) since an invisible line has nothing worth
        // hovering. Actual street art is the "road" feature_type/layer below.
        paint: { "line-color": "#8b5a2b", "line-width": 2.5, "line-opacity": 0 },
      });
      map.addLayer({
        id: ROADS_LINE_LAYER,
        type: "line",
        source: "village",
        filter: ["==", ["get", "feature_type"], "road"],
        // Roads are the actual imported street polylines (see the Road
        // model / RoadFeatureSerializer) - visible, unlike the pathfinding
        // "path" layer above. Width comes from the source data (metres);
        // scaled down here so it reads as a road rather than a highway.
        paint: {
          "line-color": "#8b5a2b",
          "line-width": ["*", ["coalesce", ["get", "width"], 6], 0.5],
        },
      });

      for (const layerId of CLICKABLE_LAYERS) {
        map.on("click", layerId, (e: MapMouseEvent & { features?: MapGeoJSONFeature[] }) => {
          const feature = e.features?.[0];
          if (!feature) return;
          const content = polygonTooltipContent(
            feature.properties as GeoJSONFeatureProperties
          );
          if (!content) return;
          setTooltip({
            key: `${layerId}-${feature.id ?? JSON.stringify(feature.properties)}`,
            content,
            lngLat: [e.lngLat.lng, e.lngLat.lat],
          });
        });
        map.on("mouseenter", layerId, () => {
          map.getCanvas().style.cursor = "pointer";
        });
        map.on("mouseleave", layerId, () => {
          map.getCanvas().style.cursor = "";
        });
      }

      map.on("click", (e: MapMouseEvent) => {
        // A click that hit one of the clickable layers is handled by the
        // per-layer listeners above and stops here; a click on empty map
        // area closes whatever tooltip is open.
        const hits = map.queryRenderedFeatures(e.point, { layers: CLICKABLE_LAYERS });
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
  }, []);

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

  // Mounts/unmounts a React root into the tooltip host div imperatively,
  // since the host itself lives outside React's tree (positioned by the
  // MapLibre `move` handler above, not by React re-render).
  useEffect(() => {
    const host = tooltipHostRef.current;
    if (!host) return;
    if (!tooltip) {
      tooltipRootRef.current?.unmount();
      tooltipRootRef.current = null;
      return;
    }
    if (!tooltipRootRef.current) {
      tooltipRootRef.current = createRoot(host);
    }
    tooltipRootRef.current.render(
      <div role="tooltip" className={styles.floatingTooltip}>
        {tooltip.content}
      </div>
    );
  }, [tooltip]);

  // Feeds the current geojson (buildings/subzones/boundary/paths) into the
  // map's GeoJSON source whenever it changes.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return;
    const source = map.getSource("village") as GeoJSONSource | undefined;
    if (!source) return;

    source.setData({
      type: "FeatureCollection",
      features: [...styledPolygonFeatures(features), ...styledLineFeatures(features)],
    } as Parameters<GeoJSONSource["setData"]>[0]);
  }, [features, mapReady]);

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

  const buildingFootprints = useMemo(
    () => buildingFootprintRings(features),
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
    () => scatterCharacters(idleFeatures, buildingFootprints),
    [idleFeatures, buildingFootprints]
  );

  // Per-character walker state (current interpolated position, remaining
  // path, speed), keyed by character id. Lives in a ref rather than state -
  // it's updated up to 60x/sec by the animation loop below, and driving that
  // through setState would re-render the map every frame.
  const walkersRef = useRef<Map<string, WalkerState>>(new Map());
  // Live marker instances, keyed by character id - reused across renders so
  // idle wandering keeps its CSS transition and walking motion isn't
  // recreated (and thus reset) every poll.
  const markersRef = useRef<Map<string, MarkerEntry>>(new Map());

  // Resets each walking character's checkpoint to the latest poll whenever
  // the underlying geojson changes: the authoritative position, its
  // remaining path, its speed, and the moment this checkpoint was taken.
  // Unconditional - there's no drift to weigh here, since the animation loop
  // below never accumulates state across polls; it only ever measures time
  // elapsed since this checkpoint.
  useEffect(() => {
    const activeIds = new Set<string>();
    const receivedAt = performance.now();

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

  // Creates/updates/removes one Marker per character feature. Idle
  // characters get their scattered position set directly (the .noTransition
  // class is toggled off so CSS handles the drift-between-polls glide, same
  // MAP_POLL_INTERVAL_MS timing as before). Walking characters are
  // positioned every frame by the rAF loop below instead, via the same
  // marker instance, with transitions suppressed so per-frame updates don't
  // fight a CSS glide.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return;

    const seenIds = new Set<string>();

    const upsertMarker = (
      id: string,
      feature: GeoJSONFeature,
      lngLat: [number, number],
      isWalking: boolean
    ) => {
      seenIds.add(id);
      let entry = markersRef.current.get(id);
      if (!entry) {
        const element = document.createElement("div");
        const marker = new Marker({ element, anchor: "center" }).setLngLat(lngLat).addTo(map);
        const root = createRoot(element);
        entry = { marker, root, element };
        markersRef.current.set(id, entry);
      } else {
        entry.marker.setLngLat(lngLat);
      }

      // Marker's own constructor adds classes to this element (notably
      // "maplibregl-marker", which supplies the `position: absolute` that
      // makes its lngLat-driven transform positioning work at all) -
      // overwriting `className` wholesale would silently strip those and
      // leave the element in normal document flow instead of anchored to
      // the map, so toggle just our own class instead.
      entry.element.classList.add(styles.characterMarker);
      entry.element.classList.toggle(styles.noTransition, isWalking);

      const colour = colourForCharacter(feature.properties?.id);
      // Each marker's element is its own React root (see upsertMarker below)
      // - a separate tree from the one wrapped in the outer <TooltipProvider>
      // in this component's own render, so Radix's context doesn't cross
      // that boundary even though the DOM nodes end up nested. Each marker
      // root needs its own provider instance.
      entry.root.render(
        <TooltipProvider>
          <Tooltip
            content={
              <CharacterTooltipContent
                name={feature.properties?.name as string | undefined}
                home={feature.properties?.home as string | null | undefined}
                work={feature.properties?.work as string | null | undefined}
                hungerLabel={feature.properties?.hunger_label as string | null | undefined}
              />
            }
            disabled={!feature.properties?.name}
          >
            <svg
              width="20"
              height="20"
              viewBox="-4 -6 8 10"
              tabIndex={0}
              role="img"
              aria-label={(feature.properties?.name as string | undefined) || "Character"}
            >
              <ellipse cx={0} cy={2.2} rx={2.2} ry={1.4} fill="rgba(0,0,0,0.15)" />
              <rect x={-1.8} y={-1.8} width={3.6} height={4} rx={1.2} fill={colour} stroke="#000" strokeWidth={0.5} />
              <circle cx={0} cy={-3.2} r={1.8} fill={colour} stroke="#000" strokeWidth={0.5} />
            </svg>
          </Tooltip>
        </TooltipProvider>
      );
    };

    for (const { feature, cx, cy } of positionedCharacters) {
      const id = String(feature.properties?.id);
      upsertMarker(id, feature, toLngLat([cx, cy]), false);
    }
    for (const feature of walkingFeatures) {
      const id = String(feature.properties?.id);
      const [x, y] = feature.geometry.coordinates as [number, number];
      const pos = walkersRef.current.get(id)?.checkpointPos ?? [x, y];
      upsertMarker(id, feature, toLngLat(pos), true);
    }

    // Stale markers' roots are unmounted via queueMicrotask rather than
    // inline here: this same effect just called entry.root.render() above
    // for every surviving marker, and React's createRoot schedules that
    // render work rather than flushing it immediately - synchronously
    // unmounting a *different* root while those renders are still pending
    // trips React's "Attempted to synchronously unmount a root while React
    // was already rendering" warning. Deferring by a microtask lets that
    // render work finish first. Removed from markersRef.current immediately
    // regardless, so a re-run of this effect before the microtask fires
    // doesn't see (or re-schedule cleanup for) these ids.
    const staleEntries: MarkerEntry[] = [];
    for (const [id, entry] of markersRef.current) {
      if (!seenIds.has(id)) {
        staleEntries.push(entry);
        markersRef.current.delete(id);
      }
    }
    if (staleEntries.length > 0) {
      queueMicrotask(() => {
        for (const entry of staleEntries) {
          entry.marker.remove();
          entry.root.unmount();
        }
      });
    }
  }, [positionedCharacters, walkingFeatures, mapReady]);

  // Drives smooth per-frame movement for walking characters between polls.
  // Each frame recomputes position from scratch - the checkpoint plus how
  // much time has passed since it was taken - rather than stepping forward
  // from wherever the previous frame left off, so nothing compounds across
  // frames or across polls (see the WalkerState comment above).
  useEffect(() => {
    let frameId: number;

    const step = () => {
      const now = performance.now();
      walkersRef.current.forEach((walker, id) => {
        const elapsedSeconds = (now - walker.receivedAt) / 1000;
        const pos = positionAlongPath(
          walker.checkpointPos,
          walker.path,
          walker.speed * elapsedSeconds
        );
        markersRef.current.get(id)?.marker.setLngLat(toLngLat(pos));
      });
      frameId = requestAnimationFrame(step);
    };

    frameId = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frameId);
  }, []);

  // Unmount cleanup for any remaining markers/tooltip root when the whole
  // component goes away (not just the map instance effect above, which
  // already tears down the map itself).
  useEffect(() => {
    const markers = markersRef.current;
    return () => {
      for (const entry of markers.values()) {
        entry.marker.remove();
        entry.root.unmount();
      }
      markers.clear();
      tooltipRootRef.current?.unmount();
      tooltipRootRef.current = null;
    };
  }, []);

  return (
    <TooltipProvider>
      <div className={styles.mapWrapper}>
        <div ref={containerRef} className={styles.mapContainer} />
        {tooltip && (
          <div ref={tooltipHostRef} className={styles.tooltipHost} />
        )}
        {children && <div className={styles.controlsOverlay}>{children}</div>}
      </div>
    </TooltipProvider>
  );
}
