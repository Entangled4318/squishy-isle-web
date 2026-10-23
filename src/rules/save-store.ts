/* Two alternating save slots, each with a sequence number and a CRC-32, so
 * a write that stops halfway never loses the save before it. A port of the
 * GBA game's rom/src/save.c (v1.6). The slots live on a Chip: a plain
 * memory chip in the tests, and in the browser a memory chip that is copied
 * to localStorage and IndexedDB after each write (src/shell/storage.ts). */
import { SAVE_MAGIC, SAVE_SIZE, SAVE_VERSION, SaveData, checksumOld, crc32, decodeSave, emptySave, encodeSave } from './save-data';

export const SLOT_SIZE = 0x100;

export interface Chip {
  /** The slot's bytes (SLOT_SIZE long). */
  read(slot: number): Uint8Array;
  /** Writes bytes at the start of the slot. */
  write(slot: number, bytes: Uint8Array): void;
}

/** Two slots of 0xFF, like a blank battery save. */
export class MemoryChip implements Chip {
  data = new Uint8Array(2 * SLOT_SIZE).fill(0xff);
  read(slot: number): Uint8Array {
    return this.data.slice(slot * SLOT_SIZE, (slot + 1) * SLOT_SIZE);
  }
  write(slot: number, bytes: Uint8Array): void {
    this.data.set(bytes, slot * SLOT_SIZE);
  }
}

export enum SaveStatus {
  New = 'new',
  Loaded = 'loaded',
  Broken = 'reset',
}

const s16 = (x: number) => (x << 16) >> 16;

function valid(b: Uint8Array): boolean {
  const d = decodeSave(b);
  return (
    d.magic === SAVE_MAGIC &&
    d.version === SAVE_VERSION &&
    (d.checksum === crc32(b) || (!d.crcOnly && d.checksum === checksumOld(b)))
  );
}

/* A save from a newer version of the game: never written over. The C code
 * took any version above 2 but 0xFFFF; a write cut after 5 bytes on a blank
 * (0xFF) slot leaves version 0xFF02, which then locked that slot and made
 * every later write go over the only good save. Real versions are small. */
export const MAX_REAL_VERSION = 0xff;

function newer(b: Uint8Array): boolean {
  const d = decodeSave(b);
  return d.magic === SAVE_MAGIC && d.version > SAVE_VERSION && d.version <= MAX_REAL_VERSION;
}

export class SaveStore {
  /** The slot written last, -1 = none. */
  activeSlot = -1;
  /** A slot that holds a save from a newer version: never written. -1 = none. */
  keepSlot = -1;

  constructor(public chip: Chip) {}

  load(): { status: SaveStatus; data: SaveData } {
    const a = this.chip.read(0).subarray(0, SAVE_SIZE);
    const b = this.chip.read(1).subarray(0, SAVE_SIZE);
    const va = valid(a), vb = valid(b), na = newer(a), nb = newer(b);
    const da = decodeSave(a), db = decodeSave(b);
    this.keepSlot = na && nb ? (s16(da.seq - db.seq) > 0 ? 0 : 1) : na ? 0 : nb ? 1 : -1;
    if (va && (!vb || s16(da.seq - db.seq) > 0)) {
      this.activeSlot = 0;
      return { status: SaveStatus.Loaded, data: da };
    }
    if (vb) {
      this.activeSlot = 1;
      return { status: SaveStatus.Loaded, data: db };
    }
    const blankMagic = (m: number) => m === 0xffffffff || m === 0;
    const blank = blankMagic(da.magic) && blankMagic(db.magic);
    const out = emptySave();
    out.magic = SAVE_MAGIC;
    out.version = SAVE_VERSION;
    this.activeSlot = -1;
    return { status: blank ? SaveStatus.New : SaveStatus.Broken, data: out };
  }

  /** Writes the other slot and reads it back. Changes d's header fields as the C code does. */
  store(d: SaveData): boolean {
    let slot = this.activeSlot === 0 ? 1 : 0;
    if (slot === this.keepSlot) slot ^= 1; /* one slot left: the newer save lives */
    d.magic = SAVE_MAGIC;
    d.version = SAVE_VERSION;
    d.crcOnly = 1;
    d.seq = (d.seq + 1) & 0xffff;
    const bytes = encodeSave(d);
    d.checksum = crc32(bytes);
    bytes.set(encodeSave(d).subarray(140), 140);
    this.chip.write(slot, bytes);
    const check = this.chip.read(slot).subarray(0, SAVE_SIZE);
    for (let i = 0; i < SAVE_SIZE; i++) if (check[i] !== bytes[i]) return false;
    this.activeSlot = slot;
    return true;
  }
}
