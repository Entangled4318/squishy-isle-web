import { describe, expect, it } from 'vitest';
import { findPath, Grid } from '../../src/scenes/path';

/** '#' is solid, '.' is free. */
function grid(rows: string[]): Grid {
  return { cols: rows[0].length, rows: rows.length, free: (x, y) => rows[y][x] === '.' };
}

describe('findPath', () => {
  it('walks straight on open ground', () => {
    const g = grid(['.....', '.....', '.....']);
    expect(findPath(g, [0, 1], [4, 1])).toEqual([[1, 1], [2, 1], [3, 1], [4, 1]]);
  });

  it('goes round a wall by the shortest way', () => {
    const g = grid(['.....', '.###.', '.....']);
    const p = findPath(g, [0, 1], [4, 1]);
    expect(p[p.length - 1]).toEqual([4, 1]);
    expect(p.length).toBe(6); /* up, across the top, down: no diagonal past the wall ends */
  });

  it('never cuts a corner diagonally', () => {
    const g = grid(['.#', '..']);
    expect(findPath(g, [0, 0], [1, 1])).toEqual([[0, 1], [1, 1]]);
  });

  it('stops at the reachable cell nearest a target inside a wall or across water', () => {
    const g = grid(['...#...', '...#...', '...#...']);
    expect(findPath(g, [0, 1], [5, 1]).pop()).toEqual([2, 1]);
    expect(findPath(g, [0, 1], [3, 1]).pop()).toEqual([2, 1]);
  });

  it('is empty when Pip is already there', () => {
    const g = grid(['...']);
    expect(findPath(g, [1, 0], [1, 0])).toEqual([]);
  });

  it('starts from the nearest free cell when Pip stands on a solid cell edge', () => {
    const g = grid(['#...']);
    expect(findPath(g, [0, 0], [3, 0]).pop()).toEqual([3, 0]);
  });
});
