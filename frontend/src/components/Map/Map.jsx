import { useMemo } from "react";
import { computeBounds } from "./utils";
import styles from "./Map.module.scss";

export default function PopulationCentreMap({
  geojson,
  width = 600,
  height = 600,
}) {
  const features = geojson?.features || [];

  // ---- 1. Compute bounds from all features ----
  const { scale, offsetX, offsetY } = useMemo(() =>
    computeBounds(features, width, height),
    [features, width, height]
  );

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

        const isBoundary = f.properties?.type === "boundary";

        return (
          <polygon
            key={i}
            points={transformed}
            fill={isBoundary ? "none" : "#ddd"}
            stroke={isBoundary ? "#888" : "#333"}
            strokeWidth={isBoundary ? 2 : 1}
          />
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
            />
          );
        })}
    </svg>
  );
}
