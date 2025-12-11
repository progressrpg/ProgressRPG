
export function computeBounds(features, width, height) {
    let minX = Infinity, minY = Infinity;
    let maxX = -Infinity, maxY = -Infinity;

    features.forEach((f) => {
      if (f.geometry.type === "Polygon") {
        const coords = f.geometry.coordinates[0]; // outer ring
        coords.forEach(([x, y]) => {
          minX = Math.min(minX, x);
          minY = Math.min(minY, y);
          maxX = Math.max(maxX, x);
          maxY = Math.max(maxY, y);
        });
      } else if (f.geometry.type === "Point") {
        const [x, y] = f.geometry.coordinates;
        minX = Math.min(minX, x);
        minY = Math.min(minY, y);
        maxX = Math.max(maxX, x);
        maxY = Math.max(maxY, y);
      }
    });

    const geomWidth = maxX - minX || 1;
    const geomHeight = maxY - minY || 1;

    // scale to fit SVG, leaving padding
    const padding = 20;
    const sx = (width - padding * 2) / geomWidth;
    const sy = (height - padding * 2) / geomHeight;
    const scale = Math.min(sx, sy);

    // centre in viewport
    const offsetX = padding - minX * scale + (width - geomWidth * scale) / 2;
    const offsetY = padding - minY * scale + (height - geomHeight * scale) / 2;

    return { scale, offsetX, offsetY };
  }
