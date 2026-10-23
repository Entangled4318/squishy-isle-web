/* Browser storage for the two save slots (docs/PLAN.md step 3).
 * - The slots live in memory (a Chip, so src/rules/save-store.ts works as
 *   on the GBA).
 * - Each write goes to localStorage at once. It is synchronous, so a save
 *   made as iOS hides the app is already stored.
 * - Each write is copied to IndexedDB too. At load, each slot takes the
 *   better copy, so either store can be cleared or fail on its own.
 * - Every key starts with "squishy-isle-web:": all github.io projects of
 *   the owner share one origin, so one storage area. */
import { Chip, SLOT_SIZE, recordState } from '../rules/save-store';
import { SAVE_SIZE } from '../rules/save-data';
import { dbg } from '../engine/log';

export const PREFIX = 'squishy-isle-web:';
const DB_NAME = 'squishy-isle-web';
const DB_STORE = 'kv';

const toB64 = (b: Uint8Array) => btoa(String.fromCharCode(...b));
const fromB64 = (s: string) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));

function lsGet(key: string): string | null {
  try {
    return localStorage.getItem(PREFIX + key);
  } catch {
    return null;
  }
}

function lsSet(key: string, value: string): boolean {
  try {
    localStorage.setItem(PREFIX + key, value);
    return true;
  } catch {
    return false;
  }
}

function idbOpen(): Promise<IDBDatabase | null> {
  return new Promise((resolve) => {
    try {
      const req = indexedDB.open(DB_NAME, 1);
      req.onupgradeneeded = () => req.result.createObjectStore(DB_STORE);
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => resolve(null);
      req.onblocked = () => resolve(null);
    } catch {
      resolve(null);
    }
  });
}

function idbGet(db: IDBDatabase, key: string): Promise<string | null> {
  return new Promise((resolve) => {
    try {
      const req = db.transaction(DB_STORE, 'readonly').objectStore(DB_STORE).get(key);
      req.onsuccess = () => resolve(typeof req.result === 'string' ? req.result : null);
      req.onerror = () => resolve(null);
    } catch {
      resolve(null);
    }
  });
}

function idbSet(db: IDBDatabase, key: string, value: string): Promise<boolean> {
  return new Promise((resolve) => {
    try {
      const tx = db.transaction(DB_STORE, 'readwrite');
      tx.objectStore(DB_STORE).put(value, key);
      tx.oncomplete = () => resolve(true);
      tx.onerror = () => resolve(false);
      tx.onabort = () => resolve(false);
    } catch {
      resolve(false);
    }
  });
}

/** Picks the better of two copies of a slot: a valid save with the higher
 * sequence number, else a save from a newer version (kept, never lost),
 * else whatever exists. */
export function betterCopy(a: Uint8Array | null, b: Uint8Array | null): Uint8Array | null {
  if (!a) return b;
  if (!b) return a;
  const ra = recordState(a), rb = recordState(b);
  const rank = (r: ReturnType<typeof recordState>) => (r.kind === 'valid' ? 2 : r.kind === 'newer' ? 1 : 0);
  if (rank(ra) !== rank(rb)) return rank(ra) > rank(rb) ? a : b;
  return ((ra.seq - rb.seq) << 16) >> 16 >= 0 ? a : b;
}

export interface StorageReport {
  local: boolean;
  indexedDB: boolean;
  persisted: string;
  usage: string;
  lastIdbWrite: string;
}

export class BrowserChip implements Chip {
  private mem = new Uint8Array(2 * SLOT_SIZE).fill(0xff);
  private db: IDBDatabase | null = null;
  private idbChain: Promise<unknown> = Promise.resolve();
  report: StorageReport = { local: false, indexedDB: false, persisted: 'unknown', usage: 'unknown', lastIdbWrite: 'none' };

  static async open(): Promise<BrowserChip> {
    const chip = new BrowserChip();
    chip.report.local = lsSet('probe', '1');
    chip.db = await idbOpen();
    chip.report.indexedDB = chip.db !== null;
    for (let slot = 0; slot < 2; slot++) {
      const ls = lsGet(`slot${slot}`);
      const idb = chip.db ? await idbGet(chip.db, `slot${slot}`) : null;
      const pick = betterCopy(ls ? safe(fromB64, ls) : null, idb ? safe(fromB64, idb) : null);
      if (pick) chip.mem.set(pick.subarray(0, SAVE_SIZE), slot * SLOT_SIZE);
      dbg(`storage slot${slot} local=${ls ? 'yes' : 'no'} idb=${idb ? 'yes' : 'no'}`);
    }
    return chip;
  }

  read(slot: number): Uint8Array {
    return this.mem.slice(slot * SLOT_SIZE, (slot + 1) * SLOT_SIZE);
  }

  write(slot: number, bytes: Uint8Array): void {
    this.mem.set(bytes, slot * SLOT_SIZE);
    const value = toB64(this.mem.subarray(slot * SLOT_SIZE, slot * SLOT_SIZE + SAVE_SIZE));
    if (!lsSet(`slot${slot}`, value)) dbg(`storage local write FAILED slot${slot}`);
    const db = this.db;
    if (db)
      this.idbChain = this.idbChain.then(() =>
        idbSet(db, `slot${slot}`, value).then((ok) => {
          this.report.lastIdbWrite = ok ? `slot${slot} ok` : `slot${slot} FAILED`;
          if (!ok) dbg(`storage idb write FAILED slot${slot}`);
        }),
      );
  }

  /** Waits for the IndexedDB copies (tests use it). */
  flush(): Promise<unknown> {
    return this.idbChain;
  }

  /** Asks the browser to keep this site's storage. Safari decides with no prompt. */
  async askPersist(): Promise<void> {
    try {
      if (!navigator.storage?.persist) {
        this.report.persisted = 'no API';
        return;
      }
      const already = await navigator.storage.persisted();
      const granted = already || (await navigator.storage.persist());
      this.report.persisted = granted ? 'granted' : 'refused';
      dbg(`storage persist ${this.report.persisted}`);
    } catch {
      this.report.persisted = 'error';
    }
  }

  async refreshUsage(): Promise<void> {
    try {
      const e = await navigator.storage?.estimate?.();
      if (e) this.report.usage = `${Math.round((e.usage ?? 0) / 1024)} KB of ${Math.round((e.quota ?? 0) / 1048576)} MB`;
    } catch {
      /* keep the last value */
    }
  }
}

function safe<T>(f: (s: string) => T, s: string): T | null {
  try {
    return f(s);
  } catch {
    return null;
  }
}

/** Small per-browser settings (not game progress), for example the install hint. */
export const prefs = {
  get: (key: string) => lsGet(`pref:${key}`),
  set: (key: string, value: string) => lsSet(`pref:${key}`, value),
};
