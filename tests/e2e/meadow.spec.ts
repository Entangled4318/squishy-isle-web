/* M4 sub-step 2: the meadow map and the camera. */
import { expect, test } from '@playwright/test';
import { drive, logHas, open, run } from './helpers';

type M = { meadow(): { pip: [number, number]; cam: [number, number]; area: number }; placePip(x: number, y: number): void; goMeadow(): void };
const MAP_W = 480, MAP_H = 320;

async function toMeadow(page: import('@playwright/test').Page): Promise<void> {
  await open(page, '&title');
  await drive(page, (d) => {
    d.run(10); /* past the title's fade-in: a scene change during a fade is ignored */
    (d as unknown as { goMeadow(): void }).goMeadow();
    d.run(20);
  });
  await page.waitForFunction(() => {
    const d = (window as unknown as { __squishy: { artLoaded(p: string): boolean } }).__squishy;
    return ['maps/meadow-ground.png', 'maps/meadow-overlay.png', 'maps/meadow-glint.png'].every((p) => d.artLoaded(p));
  });
  await run(page, 2);
}

const meadow = (page: import('@playwright/test').Page) => drive(page, (d) => (d as unknown as M).meadow());
const place = (page: import('@playwright/test').Page, x: number, y: number) =>
  drive(page, (d, a: [number, number]) => {
    (d as unknown as M).placePip(a[0], a[1]);
    d.run(1);
  }, [x, y] as [number, number]);

test('a new save starts at the house; the camera follows Pip and stops at the edges', async ({ page }, info) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  await toMeadow(page);
  expect(await drive(page, (d) => d.scene())).toBe('meadow');
  await logHas(page, /restore pip=232,124/);
  const v = await drive(page, (d) => d.view());
  const clamp = (p: number, view: number, size: number) => Math.max(0, Math.min(size - view, p - Math.floor(view / 2)));
  let m = await meadow(page);
  expect(m.pip).toEqual([232, 124]);
  expect(m.cam).toEqual([clamp(232, v.w, MAP_W), clamp(124 - 12, v.h, MAP_H)]);
  /* the view is never wider than the map on these devices, and shows at least the GBA screen */
  expect(v.w).toBeLessThanOrEqual(MAP_W);
  expect(Math.max(v.w, v.h)).toBeGreaterThanOrEqual(240);
  if (process.env.SHOTS) await page.screenshot({ path: `${process.env.SHOTS}/${info.project.name}-meadow.png` });

  await place(page, 20, 20);
  m = await meadow(page);
  expect(m.cam).toEqual([0, 0]);
  await place(page, 470, 310);
  m = await meadow(page);
  expect(m.cam).toEqual([MAP_W - v.w, MAP_H - v.h]);
  if (process.env.SHOTS) await page.screenshot({ path: `${process.env.SHOTS}/${info.project.name}-meadow-corner.png` });
  expect(errors).toEqual([]);
});

test('the water glint cycles every 12 frames', async ({ page }) => {
  await toMeadow(page);
  await place(page, 400, 280); /* near the sea */
  const shot = async () => (await page.screenshot()).toString('base64');
  const a = await shot();
  await run(page, 12);
  const b = await shot();
  expect(a).not.toBe(b);
});
