/* Milestone 2: the art gallery loads every sprite, screen and map with no
 * error. With SHOTS=dir it also saves a screenshot of every page. */
import { expect, test } from '@playwright/test';
import { drive, open, run } from './helpers';

test('every gallery page draws with no error', async ({ page }, info) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  page.on('console', (m) => {
    if (m.type() === 'error') errors.push(m.text());
  });
  await open(page, '&gallery');
  await run(page, 20);
  const titles = await drive(page, (d) => (d as unknown as { pages(): string[] }).pages());
  expect(titles.length).toBeGreaterThan(20);
  const v = await drive(page, (d) => d.view());
  for (let i = 0; i < titles.length; i++) {
    await page.waitForTimeout(i === 0 ? 300 : 60);
    await run(page, 1);
    if (process.env.SHOTS) await page.screenshot({ path: `${process.env.SHOTS}/${info.project.name}-${String(i + 1).padStart(2, '0')}.png` });
    await drive(page, (d, x: number) => {
      d.touch('down', x, 20);
      d.touch('up', x, 20);
      d.run(1);
    }, v.w - 10);
  }
  expect(await drive(page, (d) => (d as unknown as { page(): number }).page())).toBe(0);
  expect(errors).toEqual([]);
});
