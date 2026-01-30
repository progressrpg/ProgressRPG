
export function computeTransformFromBBox(bbox, width, height) {
  const [minX, minY, maxX, maxY] = bbox;

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
