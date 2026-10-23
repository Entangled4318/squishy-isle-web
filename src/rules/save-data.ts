/* The save record, byte for byte the same as the GBA game's SaveData
 * (squishy-isle rom/src/save.h, v1.6): 144 bytes, little-endian, CRC-32 at
 * byte 140. Keeping the layout means the CRC matches the C code exactly
 * (tests/unit/fixtures.test.ts proves it), and a save from the GBA game can
 * be imported later. */

export const SAVE_SIZE = 144;
export const SAVE_MAGIC = 0x53495153; /* "SQIS" */
export const SAVE_VERSION = 2;

export const NUM_FRIENDS = 80; /* 16 species x 5 flavors, id = species * 5 + flavor */
export const MAX_FOLLOWERS = 3;
export const MAX_LETTERS = 10;

export interface SaveData {
  magic: number;
  version: number;
  seq: number;
  boots: number;
  flavor: number;
  squishes: number;
  /** bit 0 = found, bit 1 = its letter waits outside the queue */
  found: number[];
  opens: number;
  rng: number;
  /** friend id + 1, 0 = empty; [0] walks nearest Pip */
  followers: number[];
  crcOnly: number;
  pipX: number;
  pipY: number;
  area: number;
  gates: number;
  /** before GBA step 8.3: a follower line per area 1..3; merged at boot */
  lines: number[][];
  mail: number;
  mailNew: number;
  parades: number;
  pad2: number[];
  /** friend id + 1, oldest first, 0 = empty */
  letters: number[];
  letterRead: number;
  pad3: number;
  checksum: number;
}

export const OFFSET = {
  magic: 0,
  version: 4,
  seq: 6,
  boots: 8,
  flavor: 10,
  squishes: 12,
  found: 16,
  opens: 96,
  rng: 100,
  followers: 104,
  crcOnly: 107,
  pipX: 108,
  pipY: 110,
  area: 112,
  gates: 113,
  lines: 114,
  mail: 123,
  mailNew: 124,
  parades: 125,
  pad2: 126,
  letters: 128,
  letterRead: 138,
  pad3: 139,
  checksum: 140,
} as const;

const zeros = (n: number) => new Array<number>(n).fill(0);

export function emptySave(): SaveData {
  return {
    magic: 0,
    version: 0,
    seq: 0,
    boots: 0,
    flavor: 0,
    squishes: 0,
    found: zeros(NUM_FRIENDS),
    opens: 0,
    rng: 0,
    followers: zeros(MAX_FOLLOWERS),
    crcOnly: 0,
    pipX: 0,
    pipY: 0,
    area: 0,
    gates: 0,
    lines: [zeros(MAX_FOLLOWERS), zeros(MAX_FOLLOWERS), zeros(MAX_FOLLOWERS)],
    mail: 0,
    mailNew: 0,
    parades: 0,
    pad2: zeros(2),
    letters: zeros(MAX_LETTERS),
    letterRead: 0,
    pad3: 0,
    checksum: 0,
  };
}

export function cloneSave(s: SaveData): SaveData {
  return {
    ...s,
    found: [...s.found],
    followers: [...s.followers],
    lines: s.lines.map((l) => [...l]),
    pad2: [...s.pad2],
    letters: [...s.letters],
  };
}

/** Writes every field as its C type does (values wrap to the field size). */
export function encodeSave(s: SaveData): Uint8Array {
  const b = new Uint8Array(SAVE_SIZE);
  const v = new DataView(b.buffer);
  const u8s = (at: number, a: number[]) => a.forEach((x, i) => (b[at + i] = x & 0xff));
  v.setUint32(OFFSET.magic, s.magic >>> 0, true);
  v.setUint16(OFFSET.version, s.version & 0xffff, true);
  v.setUint16(OFFSET.seq, s.seq & 0xffff, true);
  v.setUint16(OFFSET.boots, s.boots & 0xffff, true);
  v.setUint16(OFFSET.flavor, s.flavor & 0xffff, true);
  v.setUint32(OFFSET.squishes, s.squishes >>> 0, true);
  u8s(OFFSET.found, s.found);
  v.setUint32(OFFSET.opens, s.opens >>> 0, true);
  v.setUint32(OFFSET.rng, s.rng >>> 0, true);
  u8s(OFFSET.followers, s.followers);
  b[OFFSET.crcOnly] = s.crcOnly & 0xff;
  v.setUint16(OFFSET.pipX, s.pipX & 0xffff, true);
  v.setUint16(OFFSET.pipY, s.pipY & 0xffff, true);
  b[OFFSET.area] = s.area & 0xff;
  b[OFFSET.gates] = s.gates & 0xff;
  s.lines.forEach((l, i) => u8s(OFFSET.lines + i * MAX_FOLLOWERS, l));
  b[OFFSET.mail] = s.mail & 0xff;
  b[OFFSET.mailNew] = s.mailNew & 0xff;
  b[OFFSET.parades] = s.parades & 0xff;
  u8s(OFFSET.pad2, s.pad2);
  u8s(OFFSET.letters, s.letters);
  b[OFFSET.letterRead] = s.letterRead & 0xff;
  b[OFFSET.pad3] = s.pad3 & 0xff;
  v.setUint32(OFFSET.checksum, s.checksum >>> 0, true);
  return b;
}

export function decodeSave(b: Uint8Array): SaveData {
  if (b.length < SAVE_SIZE) throw new Error(`save record is ${b.length} bytes, needs ${SAVE_SIZE}`);
  const v = new DataView(b.buffer, b.byteOffset, SAVE_SIZE);
  const u8s = (at: number, n: number) => Array.from(b.subarray(at, at + n));
  return {
    magic: v.getUint32(OFFSET.magic, true),
    version: v.getUint16(OFFSET.version, true),
    seq: v.getUint16(OFFSET.seq, true),
    boots: v.getUint16(OFFSET.boots, true),
    flavor: v.getUint16(OFFSET.flavor, true),
    squishes: v.getUint32(OFFSET.squishes, true),
    found: u8s(OFFSET.found, NUM_FRIENDS),
    opens: v.getUint32(OFFSET.opens, true),
    rng: v.getUint32(OFFSET.rng, true),
    followers: u8s(OFFSET.followers, MAX_FOLLOWERS),
    crcOnly: b[OFFSET.crcOnly],
    pipX: v.getUint16(OFFSET.pipX, true),
    pipY: v.getUint16(OFFSET.pipY, true),
    area: b[OFFSET.area],
    gates: b[OFFSET.gates],
    lines: [0, 1, 2].map((i) => u8s(OFFSET.lines + i * MAX_FOLLOWERS, MAX_FOLLOWERS)),
    mail: b[OFFSET.mail],
    mailNew: b[OFFSET.mailNew],
    parades: b[OFFSET.parades],
    pad2: u8s(OFFSET.pad2, 2),
    letters: u8s(OFFSET.letters, MAX_LETTERS),
    letterRead: b[OFFSET.letterRead],
    pad3: b[OFFSET.pad3],
    checksum: v.getUint32(OFFSET.checksum, true),
  };
}

/* CRC-32 (zlib), 4 bits a step from a 16-entry table, as in save.c. */
const CRC_NIBBLE = [
  0x00000000, 0x1db71064, 0x3b6e20c8, 0x26d930ac, 0x76dc4190, 0x6b6b51f4, 0x4db26158, 0x5005713c,
  0xedb88320, 0xf00f9344, 0xd6d6a3e8, 0xcb61b38c, 0x9b64c2b0, 0x86d3d2d4, 0xa00ae278, 0xbdbdf21c,
];

/** CRC-32 over the bytes before the checksum field. */
export function crc32(b: Uint8Array): number {
  let c = 0xffffffff;
  for (let i = 0; i < OFFSET.checksum; i++) {
    c = (c ^ b[i]) >>> 0;
    c = ((c >>> 4) ^ CRC_NIBBLE[c & 15]) >>> 0;
    c = ((c >>> 4) ^ CRC_NIBBLE[c & 15]) >>> 0;
  }
  return ~c >>> 0;
}

/** The rotate-add sum of GBA saves from before step 7. Still accepted on load. */
export function checksumOld(b: Uint8Array): number {
  let sum = 0x1234abcd;
  for (let i = 0; i < OFFSET.checksum; i++) sum = (((sum << 5) >>> 0) + (sum >>> 27) + b[i]) >>> 0;
  return sum;
}
