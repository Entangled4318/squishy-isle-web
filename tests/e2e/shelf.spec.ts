/* M4 sub-step 6: the shelf button, the shelf (tabs, swipe, silhouettes),
 * the close-up and the home button. */
import { expect, test, Page } from '@playwright/test';
import { drive, logHas, open, run } from './helpers';

type D = {
  goMeadow(): void;
  addFriend(id: number): boolean;
  shelfPage(): number;
  fixedToView(x: number, y: number, room: boolean): [number, number];
  button(): [number, number];
};
const SH = { x0: 11, y0: 26, cw: 44, ch: 32 };

async function meadowWith(page: Page, ids: number[]): Promise<void> {
  await open(page, '&title');
  await drive(page, (d, list: number[]) => {
    for (const id of list) (d as unknown as D).addFriend(id);
    d.run(10);
    (d as unknown as D).goMeadow();
    d.run(20);
  }, ids);
}
const tapView = (page: Page, x: number, y: number) =>
  drive(page, (d, a: [number, number]) => {
    d.touch('down', a[0], a[1]);
    d.touch('up', a[0], a[1]);
    d.run(1);
  }, [x, y] as [number, number]);
const tapButton = async (page: Page) => {
  const b = await drive(page, (d) => (d as unknown as D).button());
  await tapView(page, b[0], b[1]);
};
/** taps a backdrop pixel */
const tapFixed = async (page: Page, x: number, y: number, room = true) => {
  const p = await drive(page, (d, a: [number, number, boolean]) => (d as unknown as D).fixedToView(a[0], a[1], a[2]), [x, y, room] as [number, number, boolean]);
  await tapView(page, p[0], p[1]);
};
const cell = (r: number, c: number): [number, number] => [SH.x0 + c * SH.cw + SH.cw / 2, SH.y0 + r * SH.ch + SH.ch / 2];
const settle = (page: Page) =>
  drive(page, (d) => {
    for (let i = 0; i < 60 && (d.fading() || i < 2); i++) d.run(1);
  });

test('the shelf button opens the shelf; tabs and a swipe turn pages; home goes back', async ({ page }, info) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  await meadowWith(page, [0, 7, 19]);
  await tapButton(page);
  await settle(page);
  expect(await drive(page, (d) => d.scene())).toBe('shelf');
  await page.waitForFunction(() => (window as unknown as { __squishy: { artLoaded(p: string): boolean } }).__squishy.artLoaded('screens/shelf0.png'));
  await run(page, 2);
  if (process.env.SHOTS) await page.screenshot({ path: `${process.env.SHOTS}/${info.project.name}-shelf.png` });
  await tapFixed(page, 8 + 30 * 2 + 14, 10); /* the third tab */
  expect(await drive(page, (d) => (d as unknown as D).shelfPage())).toBe(2);
  const a = await drive(page, (d) => (d as unknown as D).fixedToView(180, 80, true));
  await drive(page, (d, p: [number, number]) => {
    d.touch('down', p[0], p[1]);
    for (let i = 1; i <= 6; i++) d.touch('move', p[0] - i * 12, p[1]);
    d.touch('up', p[0] - 72, p[1]);
    d.run(1);
  }, a);
  expect(await drive(page, (d) => (d as unknown as D).shelfPage())).toBe(3);
  await tapButton(page);
  await settle(page);
  expect(await drive(page, (d) => d.scene())).toBe('meadow');
  expect(errors).toEqual([]);
});

test('a silhouette says Find me; a found friend opens big; 3 squishes go back', async ({ page }, info) => {
  await meadowWith(page, [0, 7]);
  await tapButton(page);
  await settle(page);
  await tapFixed(page, ...cell(3, 4)); /* not found */
  await logHas(page, /shelf find me 19/);
  await run(page, 4);
  if (process.env.SHOTS) await page.screenshot({ path: `${process.env.SHOTS}/${info.project.name}-shelf-findme.png` });
  await tapFixed(page, ...cell(1, 2)); /* friend 7: kitty, matcha */
  await logHas(page, /shelf open 7/);
  await settle(page);
  expect(await drive(page, (d) => d.scene())).toBe('closeup');
  await page.waitForFunction(() => (window as unknown as { __squishy: { artLoaded(p: string): boolean } }).__squishy.artLoaded('screens/closeup.png'));
  await run(page, 2);
  if (process.env.SHOTS) await page.screenshot({ path: `${process.env.SHOTS}/${info.project.name}-closeup.png` });
  for (let i = 0; i < 3; i++) {
    await tapFixed(page, 120, 95);
    await run(page, 26);
  }
  await logHas(page, /closeup squish 3/);
  await run(page, 40);
  await settle(page);
  expect(await drive(page, (d) => d.scene())).toBe('shelf');
});

test('a tap away from the friend goes back; home goes to the map; the third close-up in a row goes to the map', async ({ page }) => {
  await meadowWith(page, [0]);
  await tapButton(page);
  await settle(page);
  await tapFixed(page, ...cell(0, 0));
  await settle(page);
  await tapFixed(page, 220, 40); /* away from the friend */
  await logHas(page, /closeup back/);
  await settle(page);
  expect(await drive(page, (d) => d.scene())).toBe('shelf');
  await tapFixed(page, ...cell(0, 0));
  await settle(page);
  await tapButton(page);
  await settle(page);
  expect(await drive(page, (d) => d.scene())).toBe('meadow');
  /* three close-ups ended by squishes: the third goes to the map */
  await tapButton(page);
  await settle(page);
  for (let k = 0; k < 3; k++) {
    await tapFixed(page, ...cell(0, 0));
    await settle(page);
    for (let i = 0; i < 3; i++) {
      await tapFixed(page, 120, 95);
      await run(page, 26);
    }
    await run(page, 40);
    await settle(page);
  }
  await logHas(page, /closeup streak: back to the map/);
  expect(await drive(page, (d) => d.scene())).toBe('meadow');
});
