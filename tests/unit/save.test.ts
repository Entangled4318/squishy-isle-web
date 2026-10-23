/* Port of the GBA game's test/test_save.c (v1.6): the two-slot save. A write
 * that stops halfway is modelled by writing only the first k bytes of the
 * new slot, for every k: the next load must find the save before or the new
 * one, never lose both. */
import { describe, expect, it } from 'vitest';
import { MemoryChip, SLOT_SIZE, SaveStatus, SaveStore } from '../../src/rules/save-store';
import { NUM_FRIENDS, OFFSET, SAVE_SIZE, SAVE_VERSION, SaveData, checksumOld, crc32, decodeSave, encodeSave } from '../../src/rules/save-data';

/* a save with recognisable contents: found[] and opens carry the stamp */
function stamp(d: SaveData, n: number): void {
  for (let i = 0; i < NUM_FRIENDS; i++) d.found[i] = (n + i) % 2;
  d.opens = n >>> 0;
  d.rng = Math.imul(n, 2654435761) >>> 0;
  d.area = n % 4;
}

const same = (a: SaveData, b: SaveData) =>
  a.opens === b.opens && a.found.join() === b.found.join() && a.rng === b.rng && a.area === b.area;

/** Changes one slot's raw bytes on the chip. */
function patch(chip: MemoryChip, slot: number, f: (b: Uint8Array) => void): void {
  f(chip.data.subarray(slot * SLOT_SIZE, slot * SLOT_SIZE + SAVE_SIZE));
}

function resign(b: Uint8Array, old = false): void {
  new DataView(b.buffer, b.byteOffset).setUint32(OFFSET.checksum, old ? checksumOld(b) : crc32(b), true);
}

describe('two-slot save', () => {
  it('a blank chip (0xFF) or a zeroed chip starts a new save', () => {
    const chip = new MemoryChip();
    let r = new SaveStore(chip).load();
    expect(r.status === SaveStatus.New && r.data.magic !== 0 && r.data.opens === 0).toBe(true);
    chip.data.fill(0);
    r = new SaveStore(chip).load();
    expect(r.status).toBe(SaveStatus.New);
  });

  it('50 saves in a row: every load finds the newest', () => {
    const store = new SaveStore(new MemoryChip());
    const d = store.load().data;
    let wrong = 0;
    for (let n = 1; n <= 50; n++) {
      stamp(d, n);
      store.store(d);
      const got = store.load();
      if (got.status !== SaveStatus.Loaded || !same(got.data, d)) wrong++;
    }
    expect(wrong).toBe(0);
  });

  it('a write cut at every byte (4 x 145 cuts) leaves the old save or the new one', () => {
    const chip = new MemoryChip();
    const store = new SaveStore(chip);
    let lost = 0, oldOk = 0, newOk = 0;
    let d = store.load().data;
    for (let n = 1; n <= 2; n++) {
      stamp(d, n);
      store.store(d); /* as in the C test: both slots hold a save first */
    }
    for (let n = 100; n < 104; n++) {
      for (let k = 0; k <= SAVE_SIZE; k++) {
        const before = store.load().data;
        const saved = chip.data.slice();
        const after = decodeSave(encodeSave(before));
        stamp(after, n * 1000 + k);
        store.store(after);
        const slot = store.activeSlot;
        const full = chip.data.slice(slot * SLOT_SIZE, slot * SLOT_SIZE + SLOT_SIZE);
        chip.data.set(saved); /* undo, then write only k bytes */
        chip.data.set(full.subarray(0, k), slot * SLOT_SIZE);
        const got = store.load();
        if (got.status !== SaveStatus.Loaded) lost++;
        else if (same(got.data, after)) newOk++;
        else if (same(got.data, before)) oldOk++;
        else lost++;
        if (k === SAVE_SIZE && !same(got.data, after)) lost++;
      }
      d = store.load().data;
      stamp(d, n);
      store.store(d); /* a clean save between rounds */
    }
    expect(lost).toBe(0);
    expect(oldOk).toBeGreaterThan(0);
    expect(newOk).toBeGreaterThan(0);
  });

  it('a first write cut on a blank chip never locks a slot as a newer version', () => {
    for (let k = 0; k <= SAVE_SIZE; k++) {
      const chip = new MemoryChip();
      const store = new SaveStore(chip);
      const d = store.load().data;
      stamp(d, 1);
      store.store(d);
      const full = chip.read(0);
      chip.data.fill(0xff);
      chip.data.set(full.subarray(0, k), 0); /* the very first write stops after k bytes */
      const first = store.load();
      expect(store.keepSlot, `cut at ${k}`).toBe(-1);
      stamp(first.data, 2);
      store.store(first.data);
      stamp(first.data, 3);
      store.store(first.data);
      const prev = store.load().data;
      stamp(prev, 4);
      store.store(prev);
      const slot = store.activeSlot;
      chip.data.fill(0xff, slot * SLOT_SIZE + 20, slot * SLOT_SIZE + 30); /* and a later write is cut */
      const got = store.load();
      expect(got.status === SaveStatus.Loaded && got.data.opens === 3, `cut at ${k}, then a later cut`).toBe(true);
    }
  });

  it('the save counter wraps past 65535 and the newest still wins', () => {
    const store = new SaveStore(new MemoryChip());
    const d = store.load().data;
    d.seq = 0xfff8;
    let wrong = 0;
    let got = store.load();
    for (let n = 1; n <= 8; n++) {
      stamp(d, 7000 + n);
      store.store(d);
      got = store.load();
      if (got.status !== SaveStatus.Loaded || !same(got.data, d)) wrong++;
    }
    expect(wrong).toBe(0);
    expect(got.data.seq).toBeLessThan(10);
  });

  it('a flipped bit in the newest slot: the slot before loads; both broken: a reset', () => {
    const chip = new MemoryChip();
    const store = new SaveStore(chip);
    store.load();
    const d = store.load().data;
    stamp(d, 9000);
    store.store(d);
    stamp(d, 9001);
    store.store(d);
    const prev = decodeSave(chip.read(store.activeSlot ^ 1));
    chip.data[store.activeSlot * SLOT_SIZE + 40] ^= 0x10;
    let got = store.load();
    expect(got.status === SaveStatus.Loaded && same(got.data, prev)).toBe(true);
    chip.data[0 * SLOT_SIZE + 20] ^= 1;
    chip.data[1 * SLOT_SIZE + 20] ^= 1;
    got = store.load();
    expect(got.status === SaveStatus.Broken && got.data.opens === 0).toBe(true);
  });

  it('a version 1 save is not read as version 2', () => {
    const chip = new MemoryChip();
    const store = new SaveStore(chip);
    const d = store.load().data;
    stamp(d, 5);
    store.store(d);
    patch(chip, store.activeSlot, (b) => {
      b[OFFSET.version] = 1;
      resign(b);
    });
    expect(store.load().status).not.toBe(SaveStatus.Loaded);
  });

  it('a save with the old checksum still loads; new saves use the CRC-32', () => {
    const chip = new MemoryChip();
    const store = new SaveStore(chip);
    const d = store.load().data;
    stamp(d, 77);
    store.store(d);
    patch(chip, store.activeSlot, (b) => {
      b[OFFSET.crcOnly] = 0; /* as written before GBA step 9.2 */
      resign(b, true);
    });
    const got = store.load();
    expect(got.status === SaveStatus.Loaded && same(got.data, d)).toBe(true);
    const b = chip.read(store.activeSlot);
    expect(decodeSave(b).checksum).not.toBe(crc32(b));
  });

  it('a crcOnly save that only matches the old sum is not loaded', () => {
    const chip = new MemoryChip();
    const store = new SaveStore(chip);
    const d = store.load().data;
    stamp(d, 78);
    store.store(d);
    expect(chip.read(store.activeSlot)[OFFSET.crcOnly]).toBe(1);
    patch(chip, store.activeSlot, (b) => resign(b, true));
    expect(store.load().status).not.toBe(SaveStatus.Loaded);
  });

  it('a save from a newer version is never overwritten', () => {
    const chip = new MemoryChip();
    const store = new SaveStore(chip);
    const d = store.load().data;
    stamp(d, 300);
    store.store(d); /* slot 0 */
    patch(chip, 0, (b) => (b[OFFSET.version] = SAVE_VERSION + 1));
    const v3 = chip.read(0);
    let got = store.load();
    expect(got.status).toBe(SaveStatus.Broken);
    for (let n = 1; n <= 5; n++) {
      stamp(got.data, 400 + n);
      store.store(got.data);
    }
    expect(chip.read(0)).toEqual(v3);
    got = store.load();
    expect(got.status === SaveStatus.Loaded && got.data.opens === 405).toBe(true);
    stamp(got.data, 406);
    store.store(got.data);
    expect(chip.read(0)).toEqual(v3);
  });

  it('both slots newer: the newest of them is kept', () => {
    const chip = new MemoryChip();
    const store = new SaveStore(chip);
    const d = store.load().data;
    for (let n = 1; n <= 2; n++) {
      stamp(d, 500 + n);
      store.store(d);
    }
    for (let k = 0; k < 2; k++) patch(chip, k, (b) => (b[OFFSET.version] = SAVE_VERSION + 1));
    const newest = store.activeSlot;
    const keep = chip.read(newest);
    const got = store.load();
    for (let n = 1; n <= 3; n++) store.store(got.data);
    expect(chip.read(newest)).toEqual(keep);
  });
});
