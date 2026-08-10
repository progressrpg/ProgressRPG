import { toLngLat } from "./utils";
import {
	styledLineFeatures,
	styledPointFeatures,
	styledPolygonFeatures,
} from "./geojson";
import type { GeoJSONFeature, GeoJSONFeatureProperties } from "./Map";

export interface WalkerState {
	checkpointPos: [number, number];
	path: [number, number][];
	speed: number;
	receivedAt: number;
}

type LngLatPointFeature = {
	type: "Feature";
	geometry: {
		type: "Point";
		coordinates: [number, number];
	};
	properties?: GeoJSONFeatureProperties | null;
};

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

// Styled buildings/roads/fields/boundaries - everything except characters.
// This only changes when `features` itself changes (i.e. once per ~2s poll),
// unlike character positions, which are recomputed on every animation frame
// by the walker loop in Map.tsx. Callers should memoize this separately
// (keyed on `features`) rather than folding it into buildVillageSourceData,
// so that per-frame loop isn't re-styling and re-reprojecting every building/
// road/field 60 times a second when only the characters are actually moving.
export function buildStaticVillageFeatures(features: GeoJSONFeature[]) {
	return [
		...styledPolygonFeatures(features),
		...styledLineFeatures(features),
		...styledPointFeatures(
			features.filter((feature) => feature.properties?.feature_type !== "character")
		),
	];
}

interface BuildCharacterPointFeaturesArgs {
	characterFeatures: GeoJSONFeature[];
	idleCharacterPositions: Map<string, [number, number]>;
	walkers: Map<string, WalkerState>;
	now: number;
}

export function buildCharacterPointFeatures({
	characterFeatures,
	idleCharacterPositions,
	walkers,
	now,
}: BuildCharacterPointFeaturesArgs): LngLatPointFeature[] {
	return characterFeatures.map((feature) => {
		const id = String(feature.properties?.id);
		const walker = walkers.get(id);
		const rawPoint = walker
			? positionAlongPath(
				walker.checkpointPos,
				walker.path,
				walker.speed * ((now - walker.receivedAt) / 1000)
			)
			: idleCharacterPositions.get(id) ?? (feature.geometry.coordinates as [number, number]);

		return {
			type: "Feature",
			geometry: {
				type: "Point",
				coordinates: toLngLat(rawPoint),
			},
			properties: feature.properties,
		};
	});
}

interface BuildVillageSourceDataArgs {
	features: GeoJSONFeature[];
	characterFeatures: GeoJSONFeature[];
	idleCharacterPositions: Map<string, [number, number]>;
	walkers: Map<string, WalkerState>;
	now: number;
}

// Full rebuild of the source's FeatureCollection - static features plus
// current character positions. Used on mount and whenever `features` itself
// changes; the per-frame walker loop in Map.tsx calls
// buildCharacterPointFeatures directly against a memoized
// buildStaticVillageFeatures result instead, since that loop only ever needs
// to update character positions, not the static geometry around them.
export function buildVillageSourceData({
	features,
	characterFeatures,
	idleCharacterPositions,
	walkers,
	now,
}: BuildVillageSourceDataArgs) {
	return {
		type: "FeatureCollection" as const,
		features: [
			...buildStaticVillageFeatures(features),
			...buildCharacterPointFeatures({ characterFeatures, idleCharacterPositions, walkers, now }),
		],
	};
}
