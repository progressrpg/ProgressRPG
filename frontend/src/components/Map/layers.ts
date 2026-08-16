import { type FilterSpecification, type MapLibreMap } from "maplibre-gl";

export const BOUNDARY_FILL_LAYER = "boundary-fill";
export const BOUNDARY_LINE_LAYER = "boundary-line";
export const BUILDINGS_FILL_LAYER = "buildings-fill";
export const SUBZONES_FILL_LAYER = "subzones-fill";
export const PATHS_LINE_LAYER = "paths-line";
export const ROADS_LINE_LAYER = "roads-line";
export const VILLAGE_LABEL_LAYER = "village-label";
// BOUNDARY_FILL_LAYER is intentionally excluded - a village boundary tooltip
// added nothing (just repeated the village name) and, since the boundary
// covers the whole village, its click handler collided with
// VILLAGE_LABEL_LAYER's (see Map.tsx).
export const CLICKABLE_LAYERS = [
	BUILDINGS_FILL_LAYER,
	SUBZONES_FILL_LAYER,
];

const CHARACTERS_LAYER = "characters";

// Outlines whichever building/character the detail card (DetailSurface, via
// DetailCard) currently has open, so it's clear which map object an open
// card refers to. Filters start matching nothing (id -1 never occurs) and
// are updated by Map.tsx's own effect via map.setFilter as `detail` changes,
// rather than being rebuilt as regular data layers on every selection.
export const SELECTED_BUILDING_OUTLINE_LAYER = "selected-building-outline";
export const SELECTED_CHARACTER_HIGHLIGHT_LAYER = "selected-character-highlight";

// Lighter-weight versions of the two layers above, driven by pointer
// hover instead of the open detail card - a preview affordance before
// committing to a click.
export const HOVER_BUILDING_OUTLINE_LAYER = "hover-building-outline";
export const HOVER_CHARACTER_HIGHLIGHT_LAYER = "hover-character-highlight";

// Selection/hover highlight colour - mirrors $color-accent /
// $accent-scale(200) in styles/tokens/_colors.scss (MapLibre paint
// expressions live in plain TS and can't import SCSS variables directly).
// Chosen over the more literally-named $color-glowing-outline
// ($primary-scale(500), green) because that token reads as part of the
// map's own green terrain/fields rather than standing out against it.
const SELECTION_HIGHLIGHT_COLOR = "#ff8800"; // c.$color-accent

// A feature only enters a filtered layer's render set the instant
// setFilter matches it, so a paint-property transition (configured via
// the "-transition" keys below) has no prior rendered state to animate
// from and would otherwise snap straight to its final value. Zeroing the
// opacity in the same tick as the filter change, then restoring it a
// frame later, gives the transition something to animate and produces a
// fade-in instead.
export function setFilterWithFade(
	map: MapLibreMap,
	layerId: string,
	opacityProperty: "line-opacity" | "circle-stroke-opacity",
	filter: FilterSpecification,
	targetOpacity = 1
): void {
	map.setPaintProperty(layerId, opacityProperty, 0);
	map.setFilter(layerId, filter);
	requestAnimationFrame(() => {
		map.setPaintProperty(layerId, opacityProperty, targetOpacity);
	});
}

// The selected-* layers' own paint opacity (see addVillageLayers below) is
// the "detail card open" intensity; a tooltip alone (lower rung of the
// tooltip -> DetailCard progressive disclosure - see DetailSelection in
// Map.tsx) uses this reduced intensity instead, via the same layers/effect.
export const TOOLTIP_ONLY_SELECTION_OPACITY = 0.5;

// Resting opacity for the HOVER_* layers below - matches their static
// paint.*-opacity, but setFilterWithFade's zero-then-restore fade needs
// this passed explicitly as targetOpacity, since the function's own
// default (1) is for the SELECTED_* layers' "detail card open" case.
export const HOVER_OPACITY = 0.5;

// Village name-label colour per PopulationCentre.state (see
// locations/models.py) - a placeholder palette (issue #673 explicitly leaves
// the exact colour set as an open design question). Mirrors
// ProgressBar.module.scss's own danger/warning/default/success classes
// (rather than inventing a separate palette) so a village's label colour and
// its tooltip progress bar (VILLAGE_STATE_PROGRESS_COLORS below) read as the
// same colour per state.
export const VILLAGE_STATE_COLORS: Record<string, string> = {
	Struggling: "#c62828", // ProgressBar .danger (c.$color-error)
	Recovering: "#ff9800", // ProgressBar .warning (c.$color-warning)
	Stable: "#007a32", // ProgressBar .default (c.$color-progress-bar)
	Thriving: "#00612a", // ProgressBar .success (c.$color-status-success)
};
const VILLAGE_STATE_DEFAULT_COLOR = "#333"; // matches the label's old fixed text-color

// ProgressBar `color` prop values per state, for the "tap a label" expanded
// tooltip - see VILLAGE_STATE_COLORS above for how these line up with the
// label's own text colour.
export const VILLAGE_STATE_PROGRESS_COLORS: Record<string, string> = {
	Struggling: "danger",
	Recovering: "warning",
	Stable: "default",
	Thriving: "success",
};

// Sized to tightly bound the glyph drawn below (roughly 6x11.9 units, see
// the shape coordinates), plus a small margin - not an arbitrary square
// canvas. MapLibre's click hit-testing for symbol/icon layers uses the
// full image bounding box (scaled by icon-size), not per-pixel alpha, so
// a canvas padded much larger than the visible glyph (e.g. the previous
// 256x256, ~85% transparent margin) made clicks well outside the drawn
// character register as hits on it - see issue #660's tooltip-priority
// follow-up. Shrinking the canvas doesn't change the glyph's on-screen
// size (that's governed by pixelRatio/scale below, not canvas size), only
// how much dead space surrounds it.
function createCharacterIcon(): ImageData {
    const width = 48;
    const height = 88;
    const scale = 6;

	const canvas = document.createElement("canvas");
    canvas.width = width;
	canvas.height = height;

	const context = canvas.getContext("2d");
	if (!context) {
		return new ImageData(width, height);
	}

	context.translate(width/2, height/2);
    context.scale(scale, scale);

	context.fillStyle = "rgba(0,0,0,0.25)";
	context.beginPath();
	context.ellipse(0, 5, 3, 1.2, 0, 0, Math.PI * 2);
	context.fill();

	context.fillStyle = "#3d5a80";
	context.strokeStyle = "#222";
	context.lineWidth = 0.6 / scale;
	context.beginPath();
	context.roundRect(-2.5, -1, 5, 5, 1.5);
	context.fill();
	context.stroke();

	context.fillStyle = "#f2cc8f";
	context.beginPath();
	context.arc(0, -3.5, 2.2, 0, Math.PI * 2);
	context.fill();
	context.stroke();

	return context.getImageData(0, 0, width, height);
}

export function addVillageLayers(map: MapLibreMap): void {
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
		paint: { "line-color": "transparent", "line-width": 2 },
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
		id: HOVER_BUILDING_OUTLINE_LAYER,
		type: "line",
		source: "village",
		filter: [
			"all",
			["==", ["get", "feature_type"], "building"],
			["==", ["get", "id"], -1],
		],
		paint: {
			"line-color": SELECTION_HIGHLIGHT_COLOR,
			"line-width": 2,
			"line-opacity": 0.5,
			"line-opacity-transition": { duration: 150, delay: 0 },
		},
	});
	map.addLayer({
		id: SELECTED_BUILDING_OUTLINE_LAYER,
		type: "line",
		source: "village",
		filter: [
			"all",
			["==", ["get", "feature_type"], "building"],
			["==", ["get", "id"], -1],
		],
		paint: {
			"line-color": SELECTION_HIGHLIGHT_COLOR,
			"line-width": 3,
			"line-opacity": 1,
			"line-opacity-transition": { duration: 250, delay: 0 },
		},
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
		layout: {
			"line-cap": "round",
			"line-join": "round",
		},
		paint: {
			"line-color": "#8b5a2b",
			"line-width": ["*", ["coalesce", ["get", "width"], 6], 0.5],
		},
	});
	map.addLayer({
		id: VILLAGE_LABEL_LAYER,
		type: "symbol",
		source: "village",
		filter: [
			"==",
			["get", "feature_type"],
			"population_centre_label",
		],
		minzoom: 10,
		layout: {
			"text-field": ["get", "name"],
			"text-size": [
				"interpolate",
				["linear"],
				["zoom"],
				10, 14,
				14, 24,
			],
			"text-allow-overlap": true,
			"text-anchor": "bottom",
			// "text-offset": [0, -8],
			"text-offset": [
				"interpolate",
				["linear"],
				["zoom"],
				10, ["literal", [0, -4]],
				14, ["literal", [0, -6]],
				15, ["literal", [0, -8]],
			],
		},
		paint: {
			// Tapping/selecting a village label expands it into its progress
			// bar + state label (issue #673) - the label itself is coloured
			// by state at rest (see VILLAGE_STATE_COLORS above).
			"text-color": [
				"match",
				["get", "state"],
				"Struggling", VILLAGE_STATE_COLORS.Struggling,
				"Recovering", VILLAGE_STATE_COLORS.Recovering,
				"Stable", VILLAGE_STATE_COLORS.Stable,
				"Thriving", VILLAGE_STATE_COLORS.Thriving,
				VILLAGE_STATE_DEFAULT_COLOR,
			],
			"text-halo-color": "#fff",
			"text-halo-width": 2,
			"text-opacity": [
				"interpolate",
				["linear"],
				["zoom"],
				11, 0,
				12, 1,
				15, 1,
				16, 0,
			],
		},
	});
	map.addLayer({
		id: HOVER_CHARACTER_HIGHLIGHT_LAYER,
		type: "circle",
		source: "village",
		// Added before CHARACTERS_LAYER so the highlight ring sits beneath the
		// character icon rather than covering it.
		filter: [
			"all",
			["==", ["get", "feature_type"], "character"],
			["==", ["get", "id"], -1],
		],
		paint: {
			"circle-radius": [
				"interpolate",
				["linear"],
				["zoom"],
				12, 6,
				16, 18,
			],
			"circle-color": "transparent",
			"circle-stroke-color": SELECTION_HIGHLIGHT_COLOR,
			"circle-stroke-width": 2,
			"circle-stroke-opacity": 0.5,
			"circle-stroke-opacity-transition": { duration: 150, delay: 0 },
		},
	});
	map.addLayer({
		id: SELECTED_CHARACTER_HIGHLIGHT_LAYER,
		type: "circle",
		source: "village",
		// Added before CHARACTERS_LAYER so the highlight ring sits beneath the
		// character icon rather than covering it.
		filter: [
			"all",
			["==", ["get", "feature_type"], "character"],
			["==", ["get", "id"], -1],
		],
		paint: {
			"circle-radius": [
				"interpolate",
				["linear"],
				["zoom"],
				12, 6,
				16, 18,
			],
			"circle-color": "transparent",
			"circle-stroke-color": SELECTION_HIGHLIGHT_COLOR,
			"circle-stroke-width": 3,
			"circle-stroke-opacity": 1,
			"circle-stroke-opacity-transition": { duration: 250, delay: 0 },
		},
	});
	map.addLayer({
		id: CHARACTERS_LAYER,
		type: "symbol",
		source: "village",
		filter: [
			"==",
			["get", "feature_type"],
			"character",
		],

		//minzoom: 12,

		layout: {
			"icon-image": "character",
			"icon-size": [
				"interpolate",
				["linear"],
				["zoom"],
				12, 0.5,
				16, 3,
			],

			"icon-allow-overlap": true,
		},

		paint: {
			"icon-opacity": [
				"interpolate",
				["linear"],
				["zoom"],
				11, 0,
				12, 1,
			],
		},
	});
}

export function addCharacterImage(map: MapLibreMap): void {
	if (!map.hasImage("character")) {
		map.addImage("character", createCharacterIcon(), {
            pixelRatio: 6,
        });
	}
}
