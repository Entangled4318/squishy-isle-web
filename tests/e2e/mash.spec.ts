/* The toddler mash test (docs/PLAN.md test 5, after the GBA test/mash.py):
 * from three saves (blank, one meadow friend left, the meadow full), random
 * taps, aimed taps at boxes, drags, palms, long holds, idle spells, rapid
 * mashing and the corner buttons, for 15000 frames from the title. Then:
 * - no error on the page;
 * - the open screen and the reveal always end by themselves in time;
 * - friends count up one at a time, never the same friend twice;
 * - a new game happens only from a save with no friends;
 * - Pip is never inside a wall or a box;
 * - after a reload the save loads, with the same friends. */
import { expect, test } from '@playwright/test';
import { drive, log, open } from './helpers';

const FRAMES = 15000;
const OPEN_MAX = 3 * 240 + 70 + 30 + 12; /* each press restarts the 4 s wait, the pop, the fades */
const REVEAL_MAX = 60 + 3 * 300 + 40 + 30 + 30 + 12; /* drop, each squish restarts the 5 s wait, hop away, fades */

const SAVES: [string, number[]][] = [
  ['blank', []],
  ['one left', Array.from({ length: 19 }, (_, i) => i)],
  ['full', Array.from({ length: 20 }, (_, i) => i)],
];

for (const [name, ids] of SAVES) {
  test(`mash from a ${name} save`, async ({ page }) => {
    test.setTimeout(120_000);
    const errors: string[] = [];
    page.on('pageerror', (e) => errors.push(String(e)));
    await open(page, '&title');
    const r = await drive(page, (d, a: { ids: number[]; frames: number }) => {
      type X = {
        addFriend(id: number): boolean;
        meadow(): { pip: [number, number]; cam: [number, number] };
        boxes(): ([number, number] | null)[];
        blocked(x: number, y: number): boolean;
        button(): [number, number];
      };
      const x = d as unknown as X;
      for (const id of a.ids) x.addFriend(id);
      let seed = 7 + a.ids.length;
      const rnd = (n: number) => ((seed = (Math.imul(seed, 1103515245) + 12345) >>> 0) >>> 8) % n;
      let frame = 0, scene = '', inScene = 0, bad = 0;
      const longest: Record<string, number> = {};
      const step = (n: number) => {
        for (let i = 0; i < n; i++) {
          d.run(1);
          frame++;
          const s = d.scene();
          if (s === scene) inScene++;
          else {
            scene = s;
            inScene = 0;
          }
          longest[s] = Math.max(longest[s] ?? 0, inScene);
          if (s === 'meadow' && !d.fading() && frame % 7 === 0) {
            const p = x.meadow().pip;
            if (x.blocked(p[0], p[1])) bad++;
          }
        }
      };
      const tap = (px: number, py: number, hold = 1) => {
        d.touch('down', px, py);
        step(hold);
        d.touch('up', px, py);
      };
      while (frame < a.frames) {
        const v = d.view();
        const k = rnd(100);
        if (k < 40) tap(rnd(v.w), rnd(v.h), 1 + rnd(8));
        else if (k < 55 && scene === 'meadow') {
          /* aimed at a box, so the game moves on */
          const b = x.boxes().find(Boolean);
          const m = x.meadow();
          if (b) tap(b[0] - m.cam[0], b[1] - 8 - m.cam[1]);
        } else if (k < 65) {
          const px = rnd(v.w), py = rnd(v.h);
          d.touch('down', px, py);
          for (let i = 0, n = 5 + rnd(15); i < n; i++) {
            step(1 + rnd(3));
            d.touch('move', px + (rnd(81) - 40) * (i / n), py + (rnd(81) - 40) * (i / n));
          }
          d.touch('up', px, py);
        } else if (k < 72) {
          /* a palm: one finger counts, the rest only sparkle */
          d.touch('down', rnd(v.w), rnd(v.h));
          for (let i = 0; i < 4; i++) d.touch('extra', rnd(v.w), rnd(v.h));
          step(2);
          d.touch('up', 0, 0);
        } else if (k < 78) tap(rnd(v.w), rnd(v.h), 60 + rnd(180));
        else if (k < 83) step(200 + rnd(500));
        else if (k < 90) {
          const b = x.button();
          tap(b[0] + rnd(9) - 4, b[1] + rnd(9) - 4);
        } else for (let i = 0; i < 20; i++) tap(rnd(v.w), rnd(v.h));
        step(1 + rnd(20));
      }
      return { longest, bad };
    }, { ids, frames: FRAMES });
    const lines = await log(page);
    /* the open screen and the reveal end by themselves */
    expect(r.longest.open ?? 0).toBeLessThanOrEqual(OPEN_MAX);
    expect(r.longest.reveal ?? 0).toBeLessThanOrEqual(REVEAL_MAX);
    expect(r.bad).toBe(0);
    /* friends count up one at a time, never twice the same */
    const pops = lines.map((l) => /open pop friend (-?\d+) found (\d+)/.exec(l)).filter(Boolean) as RegExpExecArray[];
    let found = ids.length;
    const seen = new Set<number>(ids);
    for (const p of pops) {
      const id = Number(p[1]), n = Number(p[2]);
      if (id < 0) continue;
      expect(seen.has(id), `friend ${id} twice`).toBe(false);
      seen.add(id);
      expect(n).toBe(++found);
    }
    /* a new game only from a save with no friends */
    let titleFound = -1;
    for (const l of lines) {
      const m = /scene title found=(\d+)/.exec(l);
      if (m) titleFound = Number(m[1]);
      if (/title start new/.test(l)) expect(titleFound).toBe(0);
    }
    /* the save survives a reload with the same friends */
    const before = (await drive(page, (d) => d.save())) as unknown as { found: number[] };
    await drive(page, (d) => d.flush());
    await page.reload();
    await page.waitForFunction(() => (window as unknown as { __squishy?: { ready: boolean } }).__squishy?.ready === true);
    expect((await log(page)).some((l) => /save: loaded/.test(l))).toBe(true);
    const after = (await drive(page, (d) => d.save())) as unknown as { found: number[] };
    expect(after.found.map((b) => b !== 0)).toEqual(before.found.map((b) => b !== 0));
    expect(errors).toEqual([]);
    console.log(`${name}: ${pops.length} opens, longest ${JSON.stringify(r.longest)}`);
  });
}
