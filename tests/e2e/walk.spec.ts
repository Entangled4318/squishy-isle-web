/* M4 sub-step 3: Pip walks by the shortest path, follows a dragging
 * finger, hops when tapped, and stops at Momo's gate. */
import { expect, test, Page } from '@playwright/test';
import { drive, log, logHas, open, run } from './helpers';

type M = {
  meadow(): { pip: [number, number]; cam: [number, number] };
  placePip(x: number, y: number): void;
  goMeadow(): void;
  walk(): { path: number; walking: boolean };
  blocked(x: number, y: number): boolean;
};
const md = (page: Page) => drive(page, (d) => (d as unknown as M).meadow());

async function toMeadow(page: Page): Promise<void> {
  await open(page, '&title');
  await drive(page, (d) => {
    d.run(10);
    (d as unknown as M).goMeadow();
    d.run(20);
  });
}

/** A touch at a map point (moved into the view by the camera). */
async function touchMap(page: Page, kind: 'down' | 'move' | 'up', x: number, y: number): Promise<void> {
  await drive(page, (d, a: [string, number, number]) => {
    const m = (d as unknown as M).meadow();
    d.touch(a[0], a[1] - m.cam[0], a[2] - m.cam[1]);
    d.run(1);
  }, [kind, x, y] as [string, number, number]);
}
async function tapMap(page: Page, x: number, y: number): Promise<void> {
  await touchMap(page, 'down', x, y);
  await touchMap(page, 'up', x, y);
}
/** Runs until Pip stops walking (or n frames). */
async function walkOut(page: Page, n = 900): Promise<void> {
  await drive(page, (d, k: number) => {
    for (let i = 0; i < k; i++) {
      d.run(1);
      if (!(d as unknown as M).walk().walking && (d as unknown as M).walk().path === 0) break;
    }
  }, n);
}
const dist = (a: [number, number], b: [number, number]) => Math.hypot(a[0] - b[0], a[1] - b[1]);

test('a tap walks Pip there; round the house by the shortest path', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  await toMeadow(page);
  await tapMap(page, 300, 140);
  await walkOut(page);
  expect(dist((await md(page)).pip, [300, 140])).toBeLessThanOrEqual(1);
  await drive(page, (d) => (d as unknown as M).placePip(232, 124));
  const before = (await log(page)).length;
  await tapMap(page, 232, 60); /* behind the house */
  await walkOut(page);
  expect(dist((await md(page)).pip, [232, 60])).toBeLessThanOrEqual(1);
  expect((await log(page)).slice(before).some((l) => /walk stuck/.test(l))).toBe(false);
  expect(errors).toEqual([]);
});

test('a tap inside the pen or the pond stops at the nearest spot Pip can reach', async ({ page }) => {
  await toMeadow(page);
  for (const [x, y] of [
    [120, 140],
    [400, 70],
  ]) {
    await tapMap(page, x, y);
    await walkOut(page);
    const p = (await md(page)).pip;
    expect(await drive(page, (d, a: [number, number]) => (d as unknown as M).blocked(a[0], a[1]), p)).toBe(false);
    expect(dist(p, [x, y])).toBeLessThan(70);
  }
  expect((await log(page)).some((l) => /walk stuck/.test(l))).toBe(false);
});

test('a dragging finger leads Pip', async ({ page }) => {
  await toMeadow(page);
  await touchMap(page, 'down', 250, 130);
  for (let i = 0; i <= 20; i++) {
    await touchMap(page, 'move', 250 + i * 4, 130 + i * 2);
    await run(page, 3);
  }
  await touchMap(page, 'up', 330, 170);
  await walkOut(page);
  expect(dist((await md(page)).pip, [330, 170])).toBeLessThanOrEqual(1);
});

test('a tap on Pip hops; a tap on Momo giggles; Momo blocks the bridge', async ({ page }, info) => {
  await toMeadow(page);
  await run(page, 5);
  await tapMap(page, 232, 112); /* Pip's middle */
  await logHas(page, /pip hop/);
  expect((await md(page)).pip).toEqual([232, 124]);
  await drive(page, (d) => (d as unknown as M).placePip(400, 200));
  await run(page, 2);
  if (process.env.SHOTS) await page.screenshot({ path: `${process.env.SHOTS}/${info.project.name}-momo.png` });
  await tapMap(page, 456, 200); /* Momo on the bridge */
  await logHas(page, /poke momo 0/);
  await tapMap(page, 476, 200); /* past Momo: the woods are shut */
  await walkOut(page);
  /* the nearest spot is beside Momo, never on the bridge (gate box 442..470 x 186..214, feet box 5 px) */
  const [px, py] = (await md(page)).pip;
  expect(px + 5 >= 442 && px - 5 < 470 && py >= 186 && py - 5 < 214).toBe(false);
  expect((await log(page)).some((l) => /exit/.test(l))).toBe(false);
});

test("Pip's spot is saved after he stands still a second", async ({ page }) => {
  await toMeadow(page);
  await tapMap(page, 260, 150);
  await walkOut(page);
  await run(page, 70);
  await logHas(page, /save pip=260,150/);
  const s = (await drive(page, (d) => d.save())) as unknown as { pipX: number; pipY: number };
  expect([s.pipX, s.pipY]).toEqual([260, 150]);
});

test('300 random taps and drags: no error, Pip never inside a wall', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  await toMeadow(page);
  const bad = await drive(page, (d) => {
    const m = d as unknown as M;
    let seed = 7, bad = 0;
    const r = (n: number) => ((seed = (seed * 1103515245 + 12345) & 0x7fffffff) % n);
    const v = d.view();
    for (let i = 0; i < 300; i++) {
      const x = r(v.w), y = r(v.h);
      d.touch('down', x, y);
      if (r(3) === 0) for (let k = 0; k < 5; k++) d.touch('move', x + k * 6, y + k * 3);
      d.touch('up', x, y);
      d.run(1 + r(30));
      const p = m.meadow().pip;
      if (m.blocked(p[0], p[1])) bad++;
    }
    return bad;
  });
  expect(bad).toBe(0);
  expect(errors).toEqual([]);
});
