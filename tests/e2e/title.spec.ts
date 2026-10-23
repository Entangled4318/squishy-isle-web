/* M4 sub-step 1: the title. A tap anywhere plays; the first tap of a visit
 * says hello (sound can start only on a touch); Play makes a new game on an
 * empty save, Continue keeps the friends. */
import { expect, test } from '@playwright/test';
import { drive, log, logHas, open, run, tapArt } from './helpers';

type D = { addFriend(id: number): boolean; save(): { rng: number; found: number[] } };

const tap = (page: import('@playwright/test').Page) =>
  drive(page, (d) => {
    d.touch('down', 120, 80);
    d.touch('up', 120, 80);
    d.run(1);
  });

test('the letters drop by themselves; the first tap says hello, the next plays', async ({ page }, info) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  await open(page, '&title');
  await page.waitForFunction(() => (window as unknown as { __squishy: { artLoaded(p: string): boolean } }).__squishy.artLoaded('screens/title.png'));
  await run(page, 60);
  if (process.env.SHOTS) await page.screenshot({ path: `${process.env.SHOTS}/${info.project.name}-title-drop.png` });
  await run(page, 100);
  await logHas(page, /title intro done at 129 hello=false/);
  if (process.env.SHOTS) await page.screenshot({ path: `${process.env.SHOTS}/${info.project.name}-title.png` });
  const rng0 = ((await drive(page, (d) => d.save())) as unknown as D['save'] extends () => infer R ? R : never).rng;
  await tap(page);
  await logHas(page, /title hello at/);
  expect(await drive(page, (d) => d.scene())).toBe('title');
  await run(page, 5);
  await tap(page); /* inside the 10-frame wait: sparkle only */
  expect((await log(page)).some((l) => /title start/.test(l))).toBe(false);
  await run(page, 10);
  await tap(page);
  await logHas(page, /title start new/);
  await run(page, 20);
  expect(await drive(page, (d) => d.scene())).toBe('meadow');
  const s = (await drive(page, (d) => d.save())) as unknown as { rng: number; found: number[] };
  expect(s.rng).not.toBe(rng0);
  expect(s.found.every((b) => b === 0)).toBe(true);
  await tap(page);
  await run(page, 20);
  expect(await drive(page, (d) => d.scene())).toBe('title');
  expect(errors).toEqual([]);
});

test('a real tap during the drop ends it and says hello; the next tap plays', async ({ page }) => {
  await open(page, '&title');
  await run(page, 30);
  await tapArt(page, 40, 40);
  await run(page, 2);
  await logHas(page, /title intro done at \d+ hello=true/);
  await run(page, 12);
  const v = await drive(page, (d) => d.view());
  await tapArt(page, v.w - 20, v.h - 30); /* anywhere plays */
  await run(page, 2);
  await logHas(page, /title start new/);
});

test('with friends in the save the title says Continue and keeps them', async ({ page }, info) => {
  await open(page, '&title');
  await drive(page, (d) => (d as unknown as D).addFriend(3));
  await page.waitForFunction(() => (window as unknown as { __squishy: { artLoaded(p: string): boolean } }).__squishy.artLoaded('screens/title.png'));
  await run(page, 200);
  if (process.env.SHOTS) await page.screenshot({ path: `${process.env.SHOTS}/${info.project.name}-title-continue.png` });
  await tap(page);
  await run(page, 12);
  await tap(page);
  await logHas(page, /title start continue/);
  const s = (await drive(page, (d) => d.save())) as unknown as { found: number[] };
  expect(s.found.some((b) => b !== 0)).toBe(true);
});
