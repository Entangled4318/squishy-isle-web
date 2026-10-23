import { Page, expect } from '@playwright/test';

/** Opens the game in test mode and waits for the driver. */
export async function open(page: Page, query = ''): Promise<void> {
  await page.goto(`./?test=1${query}`);
  await page.waitForFunction(() => (window as unknown as { __squishy?: { ready: boolean } }).__squishy?.ready === true);
}

type Driver = {
  run(n: number): void;
  touch(kind: string, x: number, y: number): void;
  log(): string[];
  save(): Record<string, unknown> & { squishes: number; boots: number };
  view(): { w: number; h: number; k: number; portrait: boolean; devW: number; devH: number; ox: number; oy: number; dpr: number };
  scene(): string;
  fading(): boolean;
  sparkles(): number;
  storage(): { local: boolean; indexedDB: boolean };
  flush(): Promise<unknown>;
};

/** Runs f in the page with the test driver. f is sent as text, so it can
 * use only its own arguments: pass outside values as arg (JSON). */
export async function drive<T, A = undefined>(page: Page, f: (d: Driver, arg: A) => T | Promise<T>, arg?: A): Promise<T> {
  return page.evaluate(`(${f.toString()})(window.__squishy, ${JSON.stringify(arg ?? null)})`) as Promise<T>;
}

export const run = (page: Page, n: number) => drive(page, (d, k: number) => d.run(k), n).then(() => undefined);
export const log = (page: Page) => drive(page, (d) => d.log());

export async function logHas(page: Page, re: RegExp): Promise<void> {
  expect((await log(page)).some((l) => re.test(l)), `log line ${re}`).toBe(true);
}

/** Taps a point given in art pixels, with a real touch event at the matching CSS spot. */
export async function tapArt(page: Page, x: number, y: number): Promise<void> {
  const v = await drive(page, (d) => d.view());
  const cx = (x * v.k + v.ox) / v.dpr;
  const cy = (y * v.k + v.oy) / v.dpr;
  await page.touchscreen.tap(cx, cy);
}
