/* M4 sub-step 4: containers on the map, the guide arrow, the open screen,
 * the reveal and the counter. */
import { expect, test, Page } from '@playwright/test';
import { drive, log, logHas, open, run } from './helpers';

type D = {
  meadow(): { pip: [number, number]; cam: [number, number] };
  goMeadow(): void;
  placePip(x: number, y: number): void;
  boxes(): ([number, number] | null)[];
  arrow(): number;
  stage(): { popT: number; landed: number; squishes: number; leave: number };
  save(): { found: number[]; opens: number; pipX: number; pipY: number };
};

async function toMeadow(page: Page): Promise<void> {
  await open(page, '&title');
  await drive(page, (d) => {
    d.run(10);
    (d as unknown as D).goMeadow();
    d.run(20);
  });
}
async function tapMap(page: Page, x: number, y: number): Promise<void> {
  await drive(page, (d, a: [number, number]) => {
    const m = (d as unknown as D).meadow();
    d.touch('down', a[0] - m.cam[0], a[1] - m.cam[1]);
    d.touch('up', a[0] - m.cam[0], a[1] - m.cam[1]);
    d.run(1);
  }, [x, y] as [number, number]);
}
const tapAny = (page: Page) =>
  drive(page, (d) => {
    d.touch('down', 100, 80);
    d.touch('up', 100, 80);
    d.run(1);
  });
/** Runs until the scene is `name` (or n frames); returns the frames used. */
const runUntil = (page: Page, name: string, n = 900) =>
  drive(page, (d, a: [string, number]) => {
    for (let i = 0; i < a[1]; i++) {
      if (d.scene() === a[0] && !d.fading()) return i;
      d.run(1);
    }
    return -1;
  }, [name, n] as [string, number]);
const shot = async (page: Page, name: string, project: string) => {
  if (process.env.SHOTS) await page.screenshot({ path: `${process.env.SHOTS}/${project}-${name}.png` });
};

test('tap the first box: Pip walks over, it opens in 3 taps, the friend is revealed and counted', async ({ page }, info) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  await toMeadow(page);
  await page.waitForFunction(() => (window as unknown as { __squishy: { artLoaded(p: string): boolean } }).__squishy.artLoaded('maps/meadow-ground.png'));
  const boxes = await drive(page, (d) => (d as unknown as D).boxes());
  expect(boxes[0]).toEqual([210, 150]); /* the first box of a game sits by the cottage */
  expect(boxes.filter(Boolean).length).toBe(3);
  await run(page, 2);
  await shot(page, 'box', info.project.name);
  await tapMap(page, 210, 142);
  expect(await runUntil(page, 'open')).toBeGreaterThan(0);
  await logHas(page, /box 0 open friend \d+/);
  await page.waitForFunction(() => (window as unknown as { __squishy: { artLoaded(p: string): boolean } }).__squishy.artLoaded('screens/open.png'));
  await tapAny(page);
  await run(page, 8);
  await shot(page, 'open-jump', info.project.name);
  await run(page, 10);
  await tapAny(page);
  await run(page, 15);
  await tapAny(page);
  await logHas(page, /open pop friend \d+ found 1/);
  await run(page, 6);
  await shot(page, 'open-pop', info.project.name);
  expect(await runUntil(page, 'reveal')).toBeGreaterThanOrEqual(0);
  await page.waitForFunction(() => (window as unknown as { __squishy: { artLoaded(p: string): boolean } }).__squishy.artLoaded('screens/closeup.png'));
  await run(page, 30);
  await logHas(page, /reveal landed/);
  await shot(page, 'reveal', info.project.name);
  await run(page, 25); /* taps in the first 20 frames after landing only sparkle (GBA) */
  for (let i = 0; i < 3; i++) {
    await tapAny(page);
    await run(page, 26);
  }
  await logHas(page, /reveal squish 3/);
  expect(await runUntil(page, 'meadow')).toBeGreaterThanOrEqual(0);
  await logHas(page, /reveal leave \(squished\)/);
  const s = await drive(page, (d) => (d as unknown as D).save());
  expect(s.found.filter((b) => b).length).toBe(1);
  expect(s.opens).toBe(1);
  /* the opened box comes back somewhere else after 1.5 s */
  expect((await drive(page, (d) => (d as unknown as D).boxes())).filter(Boolean).length).toBe(2);
  await run(page, 95);
  expect((await drive(page, (d) => (d as unknown as D).boxes())).filter(Boolean).length).toBe(3);
  await shot(page, 'counter', info.project.name);
  expect(errors).toEqual([]);
});

test('with no taps the box opens itself and the friend hops away by itself', async ({ page }) => {
  await toMeadow(page);
  await drive(page, (d) => (d as unknown as D).placePip(210, 158));
  await tapMap(page, 210, 142);
  expect(await runUntil(page, 'open')).toBeGreaterThanOrEqual(0);
  expect(await runUntil(page, 'reveal', 900)).toBeGreaterThan(0);
  await logHas(page, /open press 3 \(auto\)/);
  expect(await runUntil(page, 'meadow', 900)).toBeGreaterThan(0);
  await logHas(page, /reveal leave \(waited\)/);
});

test('the guide arrow shows after 5 s and a tap on it walks to the nearest box', async ({ page }, info) => {
  await toMeadow(page);
  await drive(page, (d) => (d as unknown as D).placePip(300, 260));
  await run(page, 305);
  const a = await drive(page, (d) => (d as unknown as D).arrow());
  expect(a).toBeGreaterThanOrEqual(0);
  await shot(page, 'arrow', info.project.name);
  /* the arrow floats 26 px from Pip's middle toward the box: tap there */
  const at = await drive(page, (d) => {
    const m = (d as unknown as D).meadow();
    const b = (d as unknown as D).boxes()[(d as unknown as D).arrow()]!;
    const dx = b[0] - m.pip[0], dy = b[1] - 8 - (m.pip[1] - 12);
    const len = Math.hypot(dx, dy);
    return [m.pip[0] + (dx * 27) / len, m.pip[1] - 12 + (dy * 27) / len];
  });
  await tapMap(page, at[0], at[1]);
  await logHas(page, /tap arrow/);
  expect(await runUntil(page, 'open', 1200)).toBeGreaterThan(0);
});

test('taps on the map during the open fade only sparkle; a mash on the open screen pops once', async ({ page }) => {
  await toMeadow(page);
  await drive(page, (d) => (d as unknown as D).placePip(210, 158));
  await tapMap(page, 210, 142);
  await runUntil(page, 'open');
  for (let i = 0; i < 60; i++) await tapAny(page);
  const pops = (await log(page)).filter((l) => /open pop/.test(l)).length;
  expect(pops).toBe(1);
});
