import { type MapLibreMap } from "maplibre-gl";

export const BOUNDARY_FILL_LAYER = "boundary-fill";
export const BOUNDARY_LINE_LAYER = "boundary-line";
export const BUILDINGS_FILL_LAYER = "buildings-fill";
export const SUBZONES_FILL_LAYER = "subzones-fill";
export const PATHS_LINE_LAYER = "paths-line";
export const ROADS_LINE_LAYER = "roads-line";
export const VILLAGE_LABEL_LAYER = "village-label";
export const VILLAGE_MARKER_LAYER = "village-marker";
export const CLICKABLE_LAYERS = [
	BOUNDARY_FILL_LAYER,
	BUILDINGS_FILL_LAYER,
	SUBZONES_FILL_LAYER,
];

const CHARACTERS_LAYER = "characters";

// Marker colour per PopulationCentre.state (see locations/models.py) - a
// placeholder palette (issue #673 explicitly leaves the exact icon/colour
// set as an open design question). Mirrors ProgressBar.module.scss's own
// danger/warning/default/success classes (rather than inventing a separate
// palette) so a village's marker colour and its tooltip progress bar
// (VILLAGE_STATE_PROGRESS_COLORS below) read as the same colour per state.
export const VILLAGE_STATE_COLORS: Record<string, string> = {
	Struggling: "#c62828", // ProgressBar .danger (c.$color-error)
	Recovering: "#ff9800", // ProgressBar .warning (c.$color-warning)
	Stable: "#007a32", // ProgressBar .default (c.$color-progress-bar)
	Thriving: "#00612a", // ProgressBar .success (c.$color-status-success)
};
const VILLAGE_STATE_DEFAULT_COLOR = "#888";

// ProgressBar `color` prop values per state, for the "tap a marker" expanded
// tooltip - see VILLAGE_STATE_COLORS above for how these line up with the
// marker's own fill colour.
export const VILLAGE_STATE_PROGRESS_COLORS: Record<string, string> = {
	Struggling: "danger",
	Recovering: "warning",
	Stable: "default",
	Thriving: "success",
};

function createCharacterIcon(): ImageData {
    const size = 256;
    const scale = 6;

	const canvas = document.createElement("canvas");
    canvas.width = size;
	canvas.height = size;

	const context = canvas.getContext("2d");
	if (!context) {
		return new ImageData(size, size);
	}

	context.translate(size/2, size/2);
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

	return context.getImageData(0, 0, size, size);
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
		id: VILLAGE_MARKER_LAYER,
		type: "circle",
		source: "village",
		filter: [
			"==",
			["get", "feature_type"],
			"population_centre_label",
		],
		paint: {
			"circle-radius": [
				"interpolate",
				["linear"],
				["zoom"],
				2, 3,
				10, 5,
				14, 9,
			],
			"circle-color": [
				"match",
				["get", "state"],
				"Struggling", VILLAGE_STATE_COLORS.Struggling,
				"Recovering", VILLAGE_STATE_COLORS.Recovering,
				"Stable", VILLAGE_STATE_COLORS.Stable,
				"Thriving", VILLAGE_STATE_COLORS.Thriving,
				VILLAGE_STATE_DEFAULT_COLOR,
			],
			"circle-stroke-width": 1.5,
			"circle-stroke-color": "#fff",
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
			"text-color": "#333",
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
