/* The TypeScript rules against the GBA game's C rules (tests/fixtures/rules.json,
 * written by tests/fixtures/gen_rules.c): same rolls, letters, followers,
 * random numbers, sanitize results and save bytes, on 50 games. */
import { describe, expect, it } from 'vitest';
import fixtures from '../fixtures/rules.json';
import { Collection } from '../../src/rules/collection';
import { SAVE_SIZE, checksumOld, crc32, decodeSave, encodeSave, emptySave } from '../../src/rules/save-data';
import { MemoryChip, SLOT_SIZE, SaveStore } from '../../src/rules/save-store';

const hex = (b: Uint8Array) => Array.from(b, (x) => x.toString(16).padStart(2, '0')).join('');
const bytes = (h: string) => Uint8Array.from(h.match(/../g)!.map((x) => parseInt(x, 16)));

describe('same results as the C rules', () => {
  it.each(fixtures.games.map((g) => [g.n, g] as const))('game %i', (_n, g) => {
    const chip = new MemoryChip();
    const store = new SaveStore(chip);
    const c = new Collection();
    c.save = () => store.store(c.s);
    const loaded = store.load();
    c.s = emptySave();
    Object.assign(c.s, loaded.data);
    c.newGame(g.seed);
    let i = 0;
    for (let area = 0; area < 4; area++) {
      for (let k = 0; k < 20; k++, i++) {
        const want = g.steps[i] as { a: number; e: number; id: number; ok: number; letter?: number };
        const id = c.roll(area, want.e);
        expect(id, `roll ${i}`).toBe(want.id);
        expect(c.add(id) ? 1 : 0).toBe(want.ok);
        if (k % 3 === 2) expect(c.letterOpen(), `letter after roll ${i}`).toBe(want.letter);
      }
      c.followerAdd(area * 20 + (g.n % 20));
      c.followerRemove((g.n * 3) % 80);
    }
    expect(c.roll(0, 1)).toBe(g.full);
    expect([c.rand(), c.rand(), c.rand()]).toEqual(g.rand);
    expect(hex(encodeSave(c.s))).toBe(g.save);
    expect(hex(chip.data.subarray(0, SAVE_SIZE))).toBe(g.slot0);
    expect(hex(chip.data.subarray(SLOT_SIZE, SLOT_SIZE + SAVE_SIZE))).toBe(g.slot1);
  });

  it.each(fixtures.sanitize.map((t, i) => [i, t] as const))('sanitize case %i', (_i, t) => {
    const raw = bytes(t.in);
    expect(crc32(raw)).toBe(t.crc);
    expect(checksumOld(raw)).toBe(t.old);
    expect(hex(encodeSave(decodeSave(raw)))).toBe(t.in);
    const c = new Collection();
    c.s = decodeSave(raw);
    c.sanitize();
    c.linesMerge();
    expect(hex(encodeSave(c.s))).toBe(t.out);
  });
});
