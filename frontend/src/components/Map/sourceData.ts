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

interface BuildVillageSourceDataArgs {
	features: GeoJSONFeature[];
	characterFeatures: GeoJSONFeature[];
	idleCharacterPositions: Map<string, [number, number]>;
	walkers: Map<string, WalkerState>;
	now: number;
}

export function buildVillageSourceData({
	features,
	characterFeatures,
	idleCharacterPositions,
	walkers,
	now,
}: BuildVillageSourceDataArgs) {
	const characterPointFeatures: LngLatPointFeature[] = characterFeatures.map((feature) => {
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

	return {
		type: "FeatureCollection" as const,
		features: [
			...styledPolygonFeatures(features),
			...styledLineFeatures(features),
			...styledPointFeatures(
				features.filter((feature) => feature.properties?.feature_type !== "character")
			),
			...characterPointFeatures,
		],
	};
}
