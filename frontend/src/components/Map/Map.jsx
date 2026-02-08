import { useMemo } from "react";
import { computeTransformFromBBox } from "./utils";
import styles from "./Map.module.scss";

export default function PopulationCentreMap({
  geojson,
  width = 600,
  height = 600,
}) {
  const features = geojson?.features || [];

  // ---- 1. Compute bounds from pc boundary ----
  const { scale, offsetX, offsetY } = useMemo(() => {
    if (geojson?.bbox) {
      return computeTransformFromBBox(geojson.bbox, width, height);
    }
  }, [geojson, width, height]);

  // ---- 2. Transform coordinates ----
  const transformPoint = (x, y) => [
    x * scale + offsetX,
    y * scale + offsetY,
  ];


  // ---- 3. Render ----
  return (
    <svg
      className={styles.mapSvg}
      viewBox={`0 0 1000 1000`}
      preserveAspectRatio="xMidYMid meet"

    >
      {/* Polygons */}
      {features
        .filter((f) => f.geometry.type === "Polygon")
        .map((f, i) => {
          const coords = f.geometry.coordinates[0];
          if (!coords?.length) return null;

        const transformed = coords
          .filter(([x, y]) => Number.isFinite(x) && Number.isFinite(y))
          .map(([x, y]) => transformPoint(x, y).join(","))
          .join(" ");

        const isBoundary = f.properties?.feature_type === "boundary";

        return (
          <polygon
            key={i}
            points={transformed}
            fill={isBoundary ? "none" : "#ddd"}
            stroke={isBoundary ? "#888" : "#333"}
            strokeWidth={isBoundary ? 2.5 : 1}
            strokeLinejoin="round"
            strokeLinecap="round"
          >
            <title>{f.properties?.name}</title>
          </polygon>
        );
      })}

      {/* Lines */}
        {features
          .filter((f) => f.geometry.type === "LineString")
          .map((f, i) => {
            const coords = f.geometry.coordinates;
            if (!coords?.length) return null;

            const transformed = coords
              .filter(([x, y]) => Number.isFinite(x) && Number.isFinite(y))
              .map(([x, y]) => transformPoint(x, y).join(","))
              .join(" ");

            const isPath = f.properties?.feature_type === "path";

            return (
              <polyline
                key={`line-${i}`}
                points={transformed}
                fill="none"
                stroke={isPath ? "#8b5a2b" : "#666"}
                strokeWidth={isPath ? 3 : 1.5}
                strokeLinecap="round"
                strokeLinejoin="round"
                opacity={0} // hide paths for now
              >
                <title>{f.properties?.name}</title>
              </polyline>
            );
          })}

      {/* Points */}
      {features
        .filter((f) => f.geometry.type === "Point")
        .map((f, i) => {
          const [cx, cy] = transformPoint(
            f.geometry.coordinates[0],
            f.geometry.coordinates[1]
          );
          return (
            <circle
              key={`pt-${i}`}
              cx={cx}
              cy={cy}
              r={5} // radius
              fill={f.properties?.icon || "red"}
              stroke="#000"
              strokeWidth={1}
              title={f.properties?.name}
            >
              <title>{f.properties?.name}</title>
            </circle>
          );
        })}
    </svg>
  );
}
