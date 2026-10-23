/* The heart sign's picker (GBA pick mode, first item of M5): store
 * friends in the pen and swap them with the line. */
import { expect, test, Page } from '@playwright/test';
import { drive, logHas, open, run } from './helpers';

type D = {
  meadow(): { pip: [number, number]; cam: [number, number] };
  goMeadow(): void;
  placePip(x: number, y: number): void;
  addFriend(id: number): boolean;
  friends(): { pen: [number, number, number][]; follow: [number, number, number][] };
  followers(): number[];
  fixedToView(x: number, y: number, room: boolean): [number, number];
  button(): [number, number];
};
const SH = { x0: 11, y0: 26, cw: 44, ch: 32 };
const SIGN = [187, 183];

async function meadowWith(page: Page, ids: number[]): Promise<void> {
  await open(page, '&title');
  await drive(page, (d, list: number[]) => {
    for (const id of list) (d as unknown as D).addFriend(id);
    d.run(10);
    (d as unknown as D).goMeadow();
    d.run(20);
  }, ids);
}
const tapMap = (page: Page, x: number, y: number) =>
  drive(page, (d, a: [number, number]) => {
    const m = (d as unknown as D).meadow();
    d.touch('down', a[0] - m.cam[0], a[1] - m.cam[1]);
    d.touch('up', a[0] - m.cam[0], a[1] - m.cam[1]);
    d.run(1);
  }, [x, y] as [number, number]);
const tapView = (page: Page, x: number, y: number) =>
  drive(page, (d, a: [number, number]) => {
    d.touch('down', a[0], a[1]);
    d.touch('up', a[0], a[1]);
    d.run(1);
  }, [x, y] as [number, number]);
/** taps friend id's shelf cell (meadow page) */
const tapFriend = async (page: Page, id: number) => {
  const r = Math.floor(id / 5), c = id % 5;
  const p = await drive(page, (d, a: [number, number]) => (d as unknown as D).fixedToView(a[0], a[1], true), [SH.x0 + c * SH.cw + 22, SH.y0 + r * SH.ch + 16] as [number, number]);
  await tapView(page, p[0], p[1]);
};
const runUntil = (page: Page, name: string, n = 900) =>
  drive(page, (d, a: [string, number]) => {
    for (let i = 0; i < a[1]; i++) {
      if (d.scene() === a[0] && !d.fading()) return i;
      d.run(1);
    }
    return -1;
  }, [name, n] as [string, number]);
const followers = (page: Page) => drive(page, (d) => (d as unknown as D).followers());
const shot = async (page: Page, name: string, project: string) => {
  if (process.env.SHOTS) await page.screenshot({ path: `${process.env.SHOTS}/${project}-${name}.png` });
};

test('tap the heart sign: Pip walks over and the picker opens; add, swap, remove; the map and the save follow', async ({ page }, info) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  await meadowWith(page, [0, 3, 6, 9, 12]);
  expect(await followers(page)).toEqual([0, 3, 6]);
  await drive(page, (d) => (d as unknown as D).placePip(232, 190));
  await run(page, 2);
  await shot(page, 'sign', info.project.name);
  await tapMap(page, SIGN[0], SIGN[1] - 10);
  await logHas(page, /tap sign/);
  expect(await runUntil(page, 'shelf', 600)).toBeGreaterThanOrEqual(0);
  await logHas(page, /scene shelf page=0 pick=1/);
  await page.waitForFunction(() => (window as unknown as { __squishy: { artLoaded(p: string): boolean } }).__squishy.artLoaded('screens/shelf0.png'));
  await run(page, 2);
  await shot(page, 'picker', info.project.name);
  /* a pen friend joins at the front; the oldest of 3 goes to the pen */
  await tapFriend(page, 9);
  await logHas(page, /pick add 9/);
  expect(await followers(page)).toEqual([9, 0, 3]);
  /* a follower goes back to the pen */
  await tapFriend(page, 0);
  await logHas(page, /pick remove 0/);
  expect(await followers(page)).toEqual([9, 3, -1]);
  /* a silhouette only says Find me */
  await tapFriend(page, 19);
  await logHas(page, /shelf find me 19/);
  expect(await followers(page)).toEqual([9, 3, -1]);
  await run(page, 4);
  await shot(page, 'picker-done', info.project.name);
  const b = await drive(page, (d) => (d as unknown as D).button());
  await tapView(page, b[0], b[1]);
  await logHas(page, /pick done 9 3 -1/);
  expect(await runUntil(page, 'meadow')).toBeGreaterThanOrEqual(0);
  const f = await drive(page, (d) => (d as unknown as D).friends());
  expect(f.follow.map((x) => x[2])).toEqual([9, 3]);
  expect(f.pen.map((x) => x[2]).sort((a, z) => a - z)).toEqual([0, 6, 12]);
  await drive(page, (d) => d.flush());
  await page.reload();
  await page.waitForFunction(() => (window as unknown as { __squishy?: { ready: boolean } }).__squishy?.ready === true);
  expect(await followers(page)).toEqual([9, 3, -1]);
  expect(errors).toEqual([]);
});

test('with no friends the sign shows no heart and a tap there just walks', async ({ page }) => {
  await meadowWith(page, []);
  await tapMap(page, SIGN[0], SIGN[1] - 10);
  await run(page, 300);
  expect(await drive(page, (d) => d.scene())).toBe('meadow');
});

test('a mash in the picker: never more than 3 followers, all found, none twice', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  await meadowWith(page, [0, 1, 2, 5, 8, 11, 14, 17]);
  await drive(page, (d) => (d as unknown as D).placePip(187, 193));
  await tapMap(page, SIGN[0], SIGN[1] - 10);
  expect(await runUntil(page, 'shelf', 300)).toBeGreaterThanOrEqual(0);
  const bad = await drive(page, (d) => {
    const x = d as unknown as D;
    let seed = 3, bad = 0;
    const rnd = (n: number) => ((seed = (Math.imul(seed, 1103515245) + 12345) >>> 0) >>> 8) % n;
    const found = [0, 1, 2, 5, 8, 11, 14, 17];
    const b = x.button();
    for (let i = 0; i < 400; i++) {
      const v = d.view();
      let px = rnd(v.w), py = rnd(v.h);
      if (Math.hypot(px - b[0], py - b[1]) < 40) py = v.h - 5; /* stay in the picker */
      d.touch('down', px, py);
      d.touch('up', px, py);
      d.run(1 + rnd(6));
      const f = x.followers().filter((id) => id >= 0);
      if (f.length > 3 || new Set(f).size !== f.length || f.some((id) => !found.includes(id))) bad++;
    }
    return bad;
  });
  expect(bad).toBe(0);
  expect(await drive(page, (d) => d.scene())).toBe('shelf');
  expect(errors).toEqual([]);
});
