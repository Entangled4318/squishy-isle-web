/* The first play script (M4 "to try"): a new game in Blossom Meadow, box
 * after box until all 20 friends are found, by taps only; then a reload
 * and Continue keep them. */
import { expect, test, Page } from '@playwright/test';
import { drive, log, logHas, open } from './helpers';

type D = {
  meadow(): { pip: [number, number]; cam: [number, number] };
  boxes(): ([number, number] | null)[];
  friends(): { pen: unknown[]; follow: unknown[] };
  save(): { found: number[] };
};

async function playTo20(page: Page): Promise<number> {
  return drive(page, (d) => {
    const x = d as unknown as D;
    let frames = 0;
    const run = (n: number) => {
      for (let i = 0; i < n; i++, frames++) d.run(1);
    };
    const tap = (px: number, py: number) => {
      d.touch('down', px, py);
      d.touch('up', px, py);
      run(1);
    };
    const until = (name: string, max: number) => {
      for (let i = 0; i < max; i++) {
        if (d.scene() === name && !d.fading()) return true;
        run(1);
      }
      return false;
    };
    const found = () => x.save().found.filter((b) => b).length;
    run(10);
    tap(120, 80); /* hello */
    run(15);
    tap(120, 80); /* Play */
    until('meadow', 120);
    for (let guard = 0; found() < 20 && guard < 40; guard++) {
      run(100); /* a box may be on its way back */
      const m = x.meadow();
      const b = x.boxes().filter(Boolean) as [number, number][];
      if (!b.length) continue;
      b.sort((p, q) => Math.hypot(p[0] - m.pip[0], p[1] - m.pip[1]) - Math.hypot(q[0] - m.pip[0], q[1] - m.pip[1]));
      tap(b[0][0] - m.cam[0], b[0][1] - 8 - m.cam[1]);
      if (!until('open', 1500)) continue;
      for (let i = 0; i < 3; i++) {
        tap(120, 80);
        run(16);
      }
      until('reveal', 200);
      run(60);
      for (let i = 0; i < 3; i++) {
        tap(120, 80);
        run(26);
      }
      until('meadow', 400);
    }
    return frames;
  });
}

test('a new game to all 20 meadow friends by taps; Continue keeps them', async ({ page }, info) => {
  test.setTimeout(120_000);
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  await open(page, '&title');
  const frames = await playTo20(page);
  const s = await drive(page, (d) => (d as unknown as D).save());
  expect(s.found.slice(0, 20).every((b) => b)).toBe(true);
  expect((await log(page)).filter((l) => /open pop friend \d+ found/.test(l)).length).toBe(20);
  expect((await drive(page, (d) => (d as unknown as D).boxes())).filter(Boolean).length).toBe(0);
  const f = await drive(page, (d) => (d as unknown as D).friends());
  expect(f.follow.length + f.pen.length).toBe(20);
  if (process.env.SHOTS) await page.screenshot({ path: `${process.env.SHOTS}/${info.project.name}-full.png` });
  console.log(`20 friends in ${frames} frames (${Math.round(frames / 60)} s of play)`);
  await drive(page, (d) => d.flush());
  await page.reload();
  await page.waitForFunction(() => (window as unknown as { __squishy?: { ready: boolean } }).__squishy?.ready === true);
  await logHas(page, /save: loaded v2 boots=2 found=20/);
  expect(errors).toEqual([]);
});
