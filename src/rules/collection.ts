/* The child's collection: which friends are found, the roll for the next
 * container (never a friend already found), the follower line and the
 * letter queue. A port of the GBA game's rom/src/collection.c (v1.6); the
 * C comments name the step that added each rule. Every number is a C u32
 * or u8, so the arithmetic wraps the same way (>>> 0, & 0xff, Math.imul). */
import { MAX_FOLLOWERS, MAX_LETTERS, NUM_FRIENDS, SaveData, emptySave } from './save-data';

export const AREA_COUNT = 4;
export const GATE_NEED = 10; /* friends found in an area that open the way to the next */

export const friendId = (species: number, flavor: number) => species * 5 + flavor;
export const friendSpecies = (id: number) => Math.floor(id / 5);
export const friendFlavor = (id: number) => id % 5;
export const friendArea = (id: number) => Math.floor(id / 20);

/* found[id]: bit 0 = found. Bit 1 (step 9.5) = its letter waits outside the
 * 10-letter queue; it joins the queue as letters are read, so no letter is lost. */
const FOUND = 1;
const LETTER_WAITS = 2;

export class Collection {
  /** The live save. Scenes read it; only these rules change it. */
  s: SaveData = emptySave();

  /** Called after each change that the GBA game saved at once. */
  constructor(public save: () => boolean = () => true) {}

  private rngNext(): number {
    let x = this.s.rng ? this.s.rng >>> 0 : 0x2545f491; /* xorshift32 */
    x = (x ^ (x << 13)) >>> 0;
    x = (x ^ (x >>> 17)) >>> 0;
    x = (x ^ (x << 5)) >>> 0;
    this.s.rng = x;
    return x;
  }

  /** Shared random numbers (saved state). */
  rand(): number {
    return this.rngNext();
  }

  friendFound(id: number): boolean {
    return (this.s.found[id] & FOUND) !== 0;
  }

  /* letters waiting outside the queue fill its free places, lowest friend id first */
  private lettersRefill(): void {
    const s = this.s;
    let n = 0;
    while (n < MAX_LETTERS && s.letters[n]) n++;
    for (let id = 0; id < NUM_FRIENDS && n < MAX_LETTERS; id++)
      if (s.found[id] & LETTER_WAITS) {
        s.found[id] &= ~LETTER_WAITS & 0xff;
        s.letters[n++] = id + 1;
      }
  }

  foundInArea(area: number): number {
    let n = 0;
    for (let id = area * 20; id < area * 20 + 20; id++) n += this.friendFound(id) ? 1 : 0;
    return n;
  }

  foundTotal(): number {
    let n = 0;
    for (let a = 0; a < AREA_COUNT; a++) n += this.foundInArea(a);
    return n;
  }

  /** The meadow always; later areas once the one before has GATE_NEED friends. */
  areaOpen(area: number): boolean {
    return area <= 0 || (area < AREA_COUNT && this.foundInArea(area - 1) >= GATE_NEED);
  }

  /* Sparkle is the rare flavor: weight 1 against 4 for the others, so the
   * Sparkles of an area tend to come last. */
  private static weight(id: number): number {
    return friendFlavor(id) === 4 ? 1 : 4;
  }

  private pick(area: number, r: number): number {
    let total = 0;
    for (let id = area * 20; id < area * 20 + 20; id++) if (!this.friendFound(id)) total += Collection.weight(id);
    if (total === 0) return -1;
    let t = (r >>> 0) % total;
    for (let id = area * 20; id < area * 20 + 20; id++) {
      if (this.friendFound(id)) continue;
      t -= Collection.weight(id);
      if (t < 0) return id;
    }
    return -1;
  }

  /** A friend of the area not found yet, or -1 when the area is full. */
  roll(area: number, entropy: number): number {
    this.s.rng = (this.s.rng ^ Math.imul(entropy >>> 0, 0x9e3779b9)) >>> 0;
    return this.pick(area, this.rngNext());
  }

  /** Records the friend and saves; false if already found. */
  add(id: number): boolean {
    const s = this.s;
    if (id < 0 || id >= NUM_FRIENDS || this.friendFound(id)) return false;
    s.found[id] = FOUND;
    s.opens = (s.opens + 1) >>> 0;
    s.mail = id + 1; /* the newest friend (the house starts on its gift) */
    let n = 0; /* its letter joins the queue; the mailbox flag goes up */
    while (n < MAX_LETTERS && s.letters[n]) n++;
    if (n === MAX_LETTERS) s.found[id] |= LETTER_WAITS; /* 9.5: full, it waits its turn */
    else s.letters[n] = id + 1;
    s.mailNew = 1;
    this.followerJoin(id);
    this.save();
    return true;
  }

  /** Forgets all friends and reshuffles. */
  newGame(seed: number): void {
    const s = this.s;
    s.found.fill(0);
    s.followers.fill(0);
    s.lines.forEach((l) => l.fill(0));
    s.opens = 0;
    s.pipX = s.pipY = 0;
    s.area = 0;
    s.gates = 0;
    s.mail = s.mailNew = 0;
    s.letters.fill(0);
    s.letterRead = 0;
    s.parades = 0;
    s.rng = (seed | 1) >>> 0;
    this.save();
  }

  /* Step 9.2: a save can pass its checksum and still hold values the game
   * never writes (a hand-edited file, a future bug). Every scene indexes
   * arrays with these, so they are put in range once, at load. */
  private squeeze(l: number[], needFound: boolean): void {
    let k = 0;
    for (let i = 0; i < l.length; i++)
      if (l[i] && l[i] <= NUM_FRIENDS && (!needFound || this.friendFound(l[i] - 1))) l[k++] = l[i];
    while (k < l.length) l[k++] = 0;
  }

  sanitize(): void {
    const s = this.s;
    for (let i = 0; i < NUM_FRIENDS; i++) s.found[i] = s.found[i] & FOUND ? s.found[i] & (FOUND | LETTER_WAITS) : 0;
    if (s.area >= AREA_COUNT) {
      s.area = 0;
      s.pipX = s.pipY = 0;
    }
    this.squeeze(s.followers, true);
    for (let i = 0; i < 3; i++) this.squeeze(s.lines[i], true);
    this.squeeze(s.letters, false);
    for (let i = 0; i < MAX_LETTERS; i++) /* a letter in the queue does not also wait outside it */
      if (s.letters[i]) s.found[s.letters[i] - 1] &= ~LETTER_WAITS & 0xff;
    this.lettersRefill();
    if (s.mail > NUM_FRIENDS) s.mail = 0;
    if (s.letterRead > NUM_FRIENDS) s.letterRead = 0;
    s.mailNew = s.letters[0] !== 0 || (s.mailNew && s.mail) ? 1 : 0;
  }

  /* A save from before step 8.3 has a line per area: the one line becomes
   * the line of the area Pip is in, else the meadow's. */
  linesMerge(): void {
    const s = this.s;
    const a = s.area;
    const old = s.lines.some((l) => l.some((x) => x !== 0));
    if (!old) return;
    if (a >= 1 && a < AREA_COUNT && s.lines[a - 1][0]) for (let k = 0; k < MAX_FOLLOWERS; k++) s.followers[k] = s.lines[a - 1][k];
    s.lines.forEach((l) => l.fill(0));
  }

  /** The letter the mailbox shows now, without taking it. */
  letterPeek(): number {
    const s = this.s;
    if (s.letters[0]) return s.letters[0] - 1;
    if (s.letterRead) return s.letterRead - 1;
    return s.mail - 1;
  }

  /** The oldest waiting letter (taken off the queue), else the last one read; -1 = none. */
  letterOpen(): number {
    const s = this.s;
    const id = s.letters[0] - 1;
    if (id >= 0) {
      for (let i = 1; i < MAX_LETTERS; i++) s.letters[i - 1] = s.letters[i];
      s.letters[MAX_LETTERS - 1] = 0;
      this.lettersRefill();
      s.letterRead = id + 1;
      s.mailNew = s.letters[0] !== 0 ? 1 : 0;
      this.save();
      return id;
    }
    if (s.letterRead) return s.letterRead - 1;
    return s.mail - 1; /* a save from before 8.2: its one letter */
  }

  /* One line of up to 3 followers walks with Pip in every area (step 8.3). */

  /** Puts id at the front; the oldest drops off when 3 follow. */
  followerAdd(id: number): void {
    const l = this.s.followers;
    let at = MAX_FOLLOWERS - 1; /* drops the oldest unless id is already in line */
    for (let i = 0; i < MAX_FOLLOWERS; i++) if (l[i] === id + 1) at = i;
    for (let i = at; i > 0; i--) l[i] = l[i - 1];
    l[0] = id + 1;
  }

  /** A new friend: joins the end only while the line has room. */
  followerJoin(id: number): void {
    const l = this.s.followers;
    for (let i = 0; i < MAX_FOLLOWERS; i++) {
      if (l[i] === id + 1) return;
      if (l[i] === 0) {
        l[i] = id + 1;
        return;
      }
    }
  }

  /** Friend id at place i of the line, or -1. */
  followerGet(i: number): number {
    return this.s.followers[i] - 1;
  }

  followerHas(id: number): boolean {
    return this.s.followers.includes(id + 1);
  }

  /** Closes the gap; later ones move up. */
  followerRemove(id: number): void {
    const l = this.s.followers;
    let n = 0;
    for (let i = 0; i < MAX_FOLLOWERS; i++) if (l[i] && l[i] !== id + 1) l[n++] = l[i];
    while (n < MAX_FOLLOWERS) l[n++] = 0;
  }
}
