/* Shortest walks on the map's cell grid (docs/PLAN.md step 2: "Pip walks
 * there by the shortest path, or to the nearest spot he can reach").
 * Breadth-first search over 8 neighbours; a diagonal step needs both
 * straight neighbours free, so a walk never cuts a corner. */

export interface Grid {
  cols: number;
  rows: number;
  /** true where Pip's feet can stand with the cell's middle as his feet */
  free(cx: number, cy: number): boolean;
}

const DIRS: [number, number][] = [
  [1, 0],
  [-1, 0],
  [0, 1],
  [0, -1],
  [1, 1],
  [1, -1],
  [-1, 1],
  [-1, -1],
];

/** The free cell nearest to (cx, cy) within r cells, or null. */
export function nearestFree(g: Grid, cx: number, cy: number, r = 3): [number, number] | null {
  let best: [number, number] | null = null, bd = Infinity;
  for (let y = cy - r; y <= cy + r; y++)
    for (let x = cx - r; x <= cx + r; x++) {
      if (x < 0 || y < 0 || x >= g.cols || y >= g.rows || !g.free(x, y)) continue;
      const d = (x - cx) ** 2 + (y - cy) ** 2;
      if (d < bd) [best, bd] = [[x, y], d];
    }
  return best;
}

/** Cells from `from` (left out) to the reachable cell nearest `to`
 * (straight-line distance; the shorter walk wins a tie). Empty when Pip is
 * already there or nothing is reachable. */
export function findPath(g: Grid, from: [number, number], to: [number, number]): [number, number][] {
  const { cols, rows } = g;
  const start = g.free(from[0], from[1]) ? from : nearestFree(g, from[0], from[1]);
  if (!start) return [];
  const prev = new Int32Array(cols * rows).fill(-2);
  const dist = new Int32Array(cols * rows);
  const queue = new Int32Array(cols * rows);
  let head = 0, tail = 0;
  const s = start[1] * cols + start[0];
  prev[s] = -1;
  queue[tail++] = s;
  let best = s;
  const far = (i: number) => ((i % cols) - to[0]) ** 2 + (Math.floor(i / cols) - to[1]) ** 2;
  let bestFar = far(s);
  while (head < tail) {
    const i = queue[head++];
    const x = i % cols, y = Math.floor(i / cols);
    const f = far(i);
    if (f < bestFar || (f === bestFar && dist[i] < dist[best])) [best, bestFar] = [i, f];
    if (f === 0) break;
    for (const [dx, dy] of DIRS) {
      const nx = x + dx, ny = y + dy;
      if (nx < 0 || ny < 0 || nx >= cols || ny >= rows) continue;
      const j = ny * cols + nx;
      if (prev[j] !== -2 || !g.free(nx, ny)) continue;
      if (dx && dy && (!g.free(x + dx, y) || !g.free(x, y + dy))) continue;
      prev[j] = i;
      dist[j] = dist[i] + 1;
      queue[tail++] = j;
    }
  }
  const out: [number, number][] = [];
  for (let i = best; i !== -1; i = prev[i]) out.push([i % cols, Math.floor(i / cols)]);
  out.reverse();
  if (out.length && out[0][0] === from[0] && out[0][1] === from[1]) out.shift();
  return out;
}
