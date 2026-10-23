/* M4 sub-step 5: the follower line, the pen and the poke. */
import { expect, test, Page } from '@playwright/test';
import { drive, logHas, open, run } from './helpers';

type D = {
  meadow(): { pip: [number, number]; cam: [number, number] };
  goMeadow(): void;
  placePip(x: number, y: number): void;
  addFriend(id: number): boolean;
  boxes(): ([number, number] | null)[];
  friends(): { pen: [number, number, number][]; follow: [number, number, number][] };
};
const PEN = [64, 118, 168, 168];

async function meadowWith(page: Page, ids: number[]): Promise<void> {
  await open(page, '&title');
  await drive(page, (d, list: number[]) => {
    for (const id of list) (d as unknown as D).addFriend(id);
    d.run(10);
    (d as unknown as D).goMeadow();
    d.run(20);
  }, ids);
}
async function tapMap(page: Page, x: number, y: number): Promise<void> {
  await drive(page, (d, a: [number, number]) => {
    const m = (d as unknown as D).meadow();
    d.touch('down', a[0] - m.cam[0], a[1] - m.cam[1]);
    d.touch('up', a[0] - m.cam[0], a[1] - m.cam[1]);
    d.run(1);
  }, [x, y] as [number, number]);
}
const friends = (page: Page) => drive(page, (d) => (d as unknown as D).friends());
const inPen = ([x, y]: [number, number, number]) => x >= PEN[0] && x <= PEN[2] && y >= PEN[1] && y <= PEN[3];

test('the first 3 friends follow Pip in a line; the others roam in the pen', async ({ page }, info) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  await meadowWith(page, [0, 3, 6, 9, 12, 15, 18]);
  let f = await friends(page);
  expect(f.follow.map((x) => x[2])).toEqual([0, 3, 6]);
  expect(f.pen.length).toBe(4);
  expect(f.pen.every(inPen)).toBe(true);
  /* a walk: the line follows Pip's steps */
  await tapMap(page, 300, 140);
  await run(page, 120);
  f = await friends(page);
  const pip = (await drive(page, (d) => (d as unknown as D).meadow())).pip;
  const d0 = Math.hypot(f.follow[0][0] - pip[0], f.follow[0][1] - pip[1]);
  expect(d0).toBeGreaterThan(10);
  expect(d0).toBeLessThan(24);
  await run(page, 400);
  expect((await friends(page)).pen.every(inPen)).toBe(true);
  await drive(page, (d) => (d as unknown as D).placePip(120, 190));
  await run(page, 30);
  if (process.env.SHOTS) await page.screenshot({ path: `${process.env.SHOTS}/${info.project.name}-friends.png` });
  expect(errors).toEqual([]);
});

test('a tap on a pen friend or a follower squishes it at once', async ({ page }) => {
  await meadowWith(page, [1, 4, 7, 10]);
  await run(page, 2);
  await drive(page, (d) => (d as unknown as D).placePip(120, 190)); /* the pen in view */
  await run(page, 1);
  let f = await friends(page);
  await tapMap(page, f.pen[0][0], f.pen[0][1] - 8);
  await logHas(page, new RegExp(`poke friend ${f.pen[0][2]}`));
  f = await friends(page);
  await tapMap(page, f.follow[1][0], f.follow[1][1] - 8);
  await logHas(page, new RegExp(`poke friend ${f.follow[1][2]}`));
});

test('a full page: no boxes, 17 friends spread out in the pen', async ({ page }) => {
  await meadowWith(page, Array.from({ length: 20 }, (_, i) => i));
  await run(page, 600);
  expect((await drive(page, (d) => (d as unknown as D).boxes())).filter(Boolean).length).toBe(0);
  const f = await friends(page);
  expect(f.pen.length).toBe(17);
  expect(f.pen.every(inPen)).toBe(true);
  /* nobody stands on another friend */
  let close = 0;
  for (let i = 0; i < f.pen.length; i++)
    for (let j = i + 1; j < f.pen.length; j++) if (Math.hypot(f.pen[i][0] - f.pen[j][0], f.pen[i][1] - f.pen[j][1]) < 6) close++;
  expect(close).toBe(0);
});
