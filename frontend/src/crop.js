export function clampCrop(x, y, scale) {
  let nextScale = Number(scale);
  if (!Number.isFinite(nextScale)) nextScale = 1;
  nextScale = Math.min(3, Math.max(1, nextScale));
  let nextX = Number(x);
  let nextY = Number(y);
  if (!Number.isFinite(nextX)) nextX = 0;
  if (!Number.isFinite(nextY)) nextY = 0;
  const limit = Math.max(0, (nextScale - 1) / 2);
  nextX = Math.min(limit, Math.max(-limit, nextX));
  nextY = Math.min(limit, Math.max(-limit, nextY));
  return {
    x: Math.round(nextX * 10000) / 10000,
    y: Math.round(nextY * 10000) / 10000,
    scale: Math.round(nextScale * 10000) / 10000,
  };
}
