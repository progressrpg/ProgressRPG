import type React from "react";
import { useEffect, useImperativeHandle, useMemo, useRef, useState, type Ref } from "react";
import { createRoot, type Root } from "react-dom/client";
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
import { CharacterTooltipContent } from "./MapTooltips";
import { scatterCharacters } from "./characters/placement";
import {
  buildingFootprintRings,
  polygonTooltipContent,
  styledLineFeatures,
  styledPolygonFeatures,
} from "./geojson";
import { addCharacterImage, addVillageLayers, CLICKABLE_LAYERS } from "./layers";
import { buildVillageSourceData, type WalkerState } from "./sourceData";
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
  const sourceRef = useRef<GeoJSONSource | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const initialFitDoneRef = useRef(false);

  useImperativeHandle(
    ref,
    () => ({
      flyToPoint: (point) => {
        mapRef.current?.flyTo({
          center: toLngLat(point),
          zoom: 14,
          essential: true
        });
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
        setTooltip({
          key: `character-${feature.id ?? JSON.stringify(feature.properties)}`,
          content: (
            <CharacterTooltipContent
              name={feature.properties?.name as string | undefined}
              home={feature.properties?.home as string | null | undefined}
              work={feature.properties?.work as string | null | undefined}
              hungerLabel={feature.properties?.hunger_label as string | null | undefined}
            />
          ),
          lngLat: [e.lngLat.lng, e.lngLat.lat],
        });
      });
      map.on("mouseenter", "characters", () => {
        map.getCanvas().style.cursor = "pointer";
      });
      map.on("mouseleave", "characters", () => {
        map.getCanvas().style.cursor = "";
      });

      refreshVillageSource();

      for (const layerId of CLICKABLE_LAYERS) {
        map.on("click", layerId, (e: MapMouseEvent & { features?: MapGeoJSONFeature[] }) => {
          const feature = e.features?.[0];
          if (!feature) return;
          e.originalEvent?.stopPropagation?.();
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
        const hits = map.queryRenderedFeatures(e.point, {
          layers: ["characters", ...CLICKABLE_LAYERS],
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
  useEffect(() => {
    const host = tooltipHostRef.current;
    if (!host) return;
    if (!tooltipRootRef.current) {
      tooltipRootRef.current = createRoot(host);
    }
    tooltipRootRef.current.render(
      tooltip ? (
        <div role="tooltip" className={styles.floatingTooltip}>
          {tooltip.content}
        </div>
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

  const idleCharacterPositions = useMemo(() => {
    return new Map(
      positionedCharacters.map(({ feature, cx, cy }) => [
        String(feature.properties?.id),
        [cx, cy] as [number, number],
      ])
    );
  }, [positionedCharacters]);

  function refreshVillageSource() {
    sourceRef.current?.setData(
      buildVillageSourceData({
        features,
        characterFeatures,
        idleCharacterPositions,
        walkers: walkersRef.current,
        now: Date.now(),
      })
    );
  }

  // Per-character walker state (current interpolated position, remaining
  // path, speed), keyed by character id. Lives in a ref rather than state -
  // it's updated up to 60x/sec by the animation loop below.
  const walkersRef = useRef<Map<string, WalkerState>>(new Map());

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
  // frames or across polls (see the WalkerState comment above).
  useEffect(() => {
    const step = () => {
      if (mapReady) {
        refreshVillageSource();
      }
    };

    step();
    const intervalId = window.setInterval(step, 16);
    return () => window.clearInterval(intervalId);
  }, [mapReady, refreshVillageSource]);

  // Unmount cleanup for the tooltip root when the whole component goes away.
  useEffect(() => {
    return () => {
      tooltipRootRef.current?.unmount();
      tooltipRootRef.current = null;
      sourceRef.current = null;
    };
  }, []);

  return (
    <div className={styles.mapWrapper}>
      <div ref={containerRef} className={styles.mapContainer} />
      <div ref={tooltipHostRef} className={styles.tooltipHost} />
      {children && <div className={styles.controlsOverlay}>{children}</div>}
    </div>
  );
}
