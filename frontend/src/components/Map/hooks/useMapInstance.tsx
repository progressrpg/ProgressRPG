import { useEffect, useRef, useState, type RefObject } from "react";
import {
  Map as MapLibreMap,
  NavigationControl,
  type GeoJSONSource,
  type MapGeoJSONFeature,
  type MapMouseEvent,
} from "maplibre-gl";
import { fromLngLat, padBbox, quantizeBbox } from "../utils";
import { CharacterTooltipContent, PopulationCentreTooltipContent } from "../MapTooltips";
import { buildingTypeLabel, polygonAnchorLngLat, polygonTooltipContent } from "../geojson";
import {
  addCharacterImage,
  addVillageLayers,
  BUILDINGS_FILL_LAYER,
  CLICKABLE_LAYERS,
  HOVER_BUILDING_OUTLINE_LAYER,
  HOVER_CHARACTER_HIGHLIGHT_LAYER,
  HOVER_OPACITY,
  setFilterWithFade,
  VILLAGE_LABEL_LAYER,
} from "../layers";
import styles from "../Map.module.scss";
import type { DetailSelection, GeoJSONFeatureProperties, TooltipOverlayState } from "../mapTypes";

// A camera move fires many intermediate events per drag/zoom gesture -
// debouncing means onViewportChange (and the network fetch it triggers)
// only fires once the camera has actually settled.
const VIEWPORT_DEBOUNCE_MS = 400;

interface UseMapInstanceArgs {
  containerRef: RefObject<HTMLDivElement | null>;
  onViewportChange?: (bbox: string) => void;
  openDetail: (selection: DetailSelection) => void;
  setTooltip: (tooltip: TooltipOverlayState | null) => void;
  // Must be referentially stable (see Map.tsx's own indirection via
  // villageSourceRefreshRef) - this hook's map-creation effect only runs
  // once, so it captures whichever function identity it's given at mount
  // and never picks up a later one directly.
  refreshVillageSource: () => void;
  hoveredBuildingIdRef: RefObject<number | null>;
  hoveredCharacterIdRef: RefObject<number | null>;
  // Owned by the caller's "fit camera to first bbox" effect; reset here on
  // teardown so a remounted map does its initial fit again too.
  initialFitDoneRef: RefObject<boolean>;
}

/**
 * Creates and tears down the MapLibre instance once, wires up every map
 * event listener (clicks/hover for characters, buildings, subzones, the
 * village label, and the empty-map-closes-tooltip case), and reports when
 * the map is ready to receive data.
 *
 * onViewportChange and refreshVillageSource are each read via a ref inside
 * the handlers below rather than as effect deps, so the map (and its camera
 * event listener) isn't torn down and recreated on every poll/feature
 * update.
 */
export function useMapInstance({
  containerRef,
  onViewportChange,
  openDetail,
  setTooltip,
  refreshVillageSource,
  hoveredBuildingIdRef,
  hoveredCharacterIdRef,
  initialFitDoneRef,
}: UseMapInstanceArgs) {
  const mapRef = useRef<MapLibreMap | null>(null);
  const sourceRef = useRef<GeoJSONSource | null>(null);
  const [mapReady, setMapReady] = useState(false);

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

      refreshVillageSource();

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
    // openDetail is a useCallback with its own `[]` deps, and callers of
    // this hook must pass a referentially-stable refreshVillageSource (see
    // the arg's own doc comment) - both are stable, so listing openDetail
    // here satisfies exhaustive-deps without changing this effect's actual
    // "run once on mount" behaviour.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [openDetail]);

  // Separate from the effect above (rather than folded into its cleanup) so
  // sourceRef is only ever cleared on the hook's own unmount, matching the
  // pre-extraction behaviour exactly.
  useEffect(() => {
    return () => {
      sourceRef.current = null;
    };
  }, []);

  return { mapRef, sourceRef, mapReady };
}
