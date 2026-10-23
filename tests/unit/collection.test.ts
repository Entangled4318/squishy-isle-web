/* Port of the GBA game's test/test_collection.c (v1.6), check by check. */
import { describe, expect, it } from 'vitest';
import { Collection, GATE_NEED, friendFlavor } from '../../src/rules/collection';
import { MAX_LETTERS, NUM_FRIENDS, OFFSET, SAVE_SIZE, cloneSave, emptySave } from '../../src/rules/save-data';

function fresh(seed: number): Collection {
  const c = new Collection();
  c.s = emptySave();
  c.newGame(seed);
  return c;
}

describe('sanitize', () => {
  it('puts every id, flag and area in range', () => {
    const c = new Collection();
    const s = c.s;
    s.found[3] = 5; /* bit 2: not a flag the game uses */
    s.found[9] = 1;
    s.area = 5;
    s.pipX = 300;
    s.followers = [200, 4, 6]; /* out of range, friend 3 found, friend 5 not found */
    s.letters[0] = 0;
    s.letters[1] = 81;
    s.letters[2] = 10;
    s.mail = 99;
    s.letterRead = 250;
    s.lines[1][0] = 90;
    c.sanitize();
    expect(s.found[3] === 1 && s.found[9] === 1 && c.foundTotal() === 2, 'found flags become 0 or 1').toBe(true);
    expect(s.area === 0 && s.pipX === 0, 'an area past Cloud Hill becomes the meadow start').toBe(true);
    expect(s.followers, 'followers keep only found friends, closed up').toEqual([4, 0, 0]);
    expect(s.letters[0] === 10 && !s.letters[1] && s.mailNew === 1, 'bad letters drop, the queue closes up, the flag follows').toBe(true);
    expect(!s.mail && !s.letterRead && !s.lines[1][0], 'mail, letterRead and old lines in range').toBe(true);
  });

  it('does not change a normal save', () => {
    const c = fresh(1);
    c.add(4);
    const before = cloneSave(c.s);
    c.sanitize();
    expect(c.s).toEqual(before);
  });

  it('keeps waiting bits only on found friends whose letter is not queued', () => {
    const c = fresh(10);
    c.add(5);
    c.s.found[6] = 2;
    c.s.found[5] |= 2;
    c.sanitize();
    expect(c.s.found[6] === 0 && c.s.found[5] === 1 && c.s.letters[0] === 6 && !c.s.letters[1]).toBe(true);
  });
});

describe('rolls', () => {
  it('20 opens per area give 20 different friends of that area, then -1', () => {
    let repeats = 0, outside = 0, shortArea = 0, extra = 0;
    for (let seed = 1; seed <= 2000; seed++) {
      const c = fresh(seed);
      for (let area = 0; area < 4; area++) {
        for (let k = 0; k < 20; k++) {
          const id = c.roll(area, (seed * 7 + k) >>> 0);
          if (id < area * 20 || id >= area * 20 + 20) {
            outside++;
            continue;
          }
          if (!c.add(id)) repeats++;
        }
        if (c.foundInArea(area) !== 20) shortArea++;
        if (c.roll(area, 5) !== -1) extra++;
      }
    }
    expect({ repeats, outside, shortArea, extra }).toEqual({ repeats: 0, outside: 0, shortArea: 0, extra: 0 });
  });

  it('each new game has its own order', () => {
    const first = new Array(20).fill(0);
    let sameOrder = 0;
    let prev: number[] = [];
    for (let seed = 1; seed <= 200; seed++) {
      const c = fresh(Math.imul(seed, 2654435761) >>> 0);
      const order: number[] = [];
      for (let k = 0; k < 20; k++) {
        order.push(c.roll(0, k));
        c.add(order[k]);
      }
      first[order[0] % 20]++;
      if (seed > 1 && order.join() === prev.join()) sameOrder++;
      prev = order;
    }
    const kinds = first.filter((n) => n > 0).length;
    expect(sameOrder).toBe(0);
    expect(kinds).toBeGreaterThanOrEqual(12);
  });

  it('Sparkles tend to come later', () => {
    let sp = 0, other = 0;
    for (let seed = 1; seed <= 2000; seed++) {
      const c = fresh(seed * 97);
      for (let k = 0; k < 20; k++) {
        const id = c.roll(0, k);
        c.add(id);
        if (friendFlavor(id) === 4) sp += k;
        else other += k;
      }
    }
    sp /= 2000 * 4;
    other /= 2000 * 16;
    expect(sp).toBeGreaterThan(other + 3);
  });
});

describe('collection', () => {
  it('refuses a friend found before', () => {
    const c = fresh(5);
    const a = c.add(7), b = c.add(7);
    expect(a && !b && c.foundTotal() === 1 && c.s.opens === 1).toBe(true);
  });

  it('new game clears friends, followers, opens, position, area and gates', () => {
    const c = fresh(5);
    c.add(7);
    c.add(8);
    c.s.pipX = 300;
    c.s.pipY = 200;
    c.s.area = 2;
    c.s.gates = 3;
    c.newGame(1234);
    expect(c.foundTotal() === 0 && c.followerGet(0) === -1 && c.s.opens === 0).toBe(true);
    expect(c.s.pipX === 0 && c.s.pipY === 0 && c.s.area === 0 && c.s.gates === 0).toBe(true);
  });

  it('the woods open at GATE_NEED meadow friends, the shore stays shut', () => {
    const c = fresh(5);
    for (let id = 0; id < GATE_NEED - 1; id++) c.add(id);
    const shut = !c.areaOpen(1);
    c.add(GATE_NEED - 1);
    expect(c.areaOpen(0) && shut && c.areaOpen(1) && !c.areaOpen(2)).toBe(true);
  });
});

describe('follower line', () => {
  it('keeps the newest 3, moves a friend in line to the front', () => {
    const c = fresh(5);
    [1, 2, 3, 4].forEach((id) => c.followerAdd(id));
    expect([0, 1, 2].map((i) => c.followerGet(i))).toEqual([4, 3, 2]);
    c.followerAdd(2);
    expect([0, 1, 2].map((i) => c.followerGet(i))).toEqual([2, 4, 3]);
  });

  it('friend id 0 works, empty places read -1', () => {
    const c = fresh(5);
    c.followerAdd(0);
    expect([c.followerGet(0), c.followerGet(1)]).toEqual([0, -1]);
  });

  it('the first 3 found keep following; a new friend fills a free place at the end', () => {
    const c = fresh(5);
    [7, 3, 9, 12].forEach((id) => c.add(id));
    expect([0, 1, 2].map((i) => c.followerGet(i))).toEqual([7, 3, 9]);
    c.followerRemove(3);
    c.add(14);
    expect([0, 1, 2].map((i) => c.followerGet(i))).toEqual([7, 9, 14]);
  });

  it('one line for all areas; remove closes the gap; the sign adds at the front', () => {
    const c = fresh(5);
    [1, 21, 45, 2].forEach((id) => c.add(id));
    expect([0, 1, 2].map((i) => c.followerGet(i))).toEqual([1, 21, 45]);
    c.followerRemove(21);
    expect([0, 1, 2].map((i) => c.followerGet(i))).toEqual([1, 45, -1]);
    c.followerAdd(62);
    expect([0, 1, 2].map((i) => c.followerGet(i))).toEqual([62, 1, 45]);
  });

  it('an old save (a line per area) keeps the line of the area Pip is in', () => {
    const c = fresh(5);
    for (let id = 0; id < 12; id++) c.add(id);
    c.s.lines[0][0] = 21;
    c.s.lines[0][1] = 22;
    c.s.area = 1;
    c.linesMerge();
    expect([0, 1, 2].map((i) => c.followerGet(i))).toEqual([20, 21, -1]);
    expect(c.s.lines[0][0]).toBe(0);
    c.s.lines[1][0] = 41;
    c.s.area = 0;
    c.linesMerge();
    expect(c.followerGet(0) === 20 && !c.s.lines[1][0]).toBe(true);
  });
});

describe('mailbox', () => {
  it('each new friend sends a letter; a friend found again sends none', () => {
    const c = fresh(5);
    expect(c.s.mail === 0 && !c.s.mailNew).toBe(true);
    c.add(4);
    c.add(27);
    expect(c.s.mail === 28 && c.s.mailNew === 1).toBe(true);
    c.s.mailNew = 0;
    c.add(27);
    expect(c.s.mail === 28 && !c.s.mailNew).toBe(true);
  });

  it('letters wait their turn, oldest first; with none waiting A re-reads the last', () => {
    const c = fresh(6);
    [3, 45, 61].forEach((id) => c.add(id));
    const reads = [0, 1, 2, 3].map(() => [c.letterOpen(), c.s.mailNew]);
    expect(reads).toEqual([[3, 1], [45, 1], [61, 0], [61, 0]]);

    /* step 9.5: a full queue keeps every letter; the ones past 10 wait in found[] */
    for (let i = 0; i < MAX_LETTERS; i++) c.add(20 + i);
    c.add(79);
    c.add(50);
    expect(c.s.letters[MAX_LETTERS - 1] === 30 && c.s.found[79] === 3 && c.s.found[50] === 3).toBe(true);
    expect(c.friendFound(79) && c.foundTotal() === 15).toBe(true);
    const got: number[] = [];
    let peekOk = true;
    for (let i = 0; i < MAX_LETTERS + 2; i++) {
      peekOk &&= c.letterPeek() === c.s.letters[0] - 1;
      got.push(c.letterOpen());
    }
    expect(got).toEqual([20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 50, 79]);
    expect(peekOk && !c.s.mailNew && c.s.found[50] === 1 && c.s.found[79] === 1).toBe(true);
    expect(c.letterPeek() === 79 && c.letterOpen() === 79).toBe(true);
  });

  it('80 friends found before the mailbox: all 80 letters, each once', () => {
    const c = fresh(9);
    for (let id = 0; id < NUM_FRIENDS; id++) c.add(id);
    const seen = new Array(NUM_FRIENDS).fill(0);
    let reads = 0;
    while (c.s.letters[0] && reads < 200) {
      seen[c.letterOpen()]++;
      reads++;
    }
    expect(reads).toBe(NUM_FRIENDS);
    expect(seen.every((n) => n === 1)).toBe(true);
  });

  it('new game empties the mailbox', () => {
    const c = fresh(10);
    c.add(5);
    c.letterOpen();
    c.newGame(3);
    expect(c.s.mail === 0 && !c.s.mailNew && !c.s.letters[0] && !c.s.letterRead).toBe(true);
  });
});

describe('save layout', () => {
  it('matches the GBA record', () => {
    expect(SAVE_SIZE).toBe(144);
    expect(OFFSET.area).toBe(112);
    expect(OFFSET.mail).toBe(123);
    expect(OFFSET.checksum).toBe(140);
  });
});
