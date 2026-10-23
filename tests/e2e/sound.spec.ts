/* Milestone 3: the sound engine runs in the browser's AudioWorklet. A real
 * tap starts the audio; the worklet's engine log comes back to the game. */
import { expect, test } from '@playwright/test';
import { drive, log, open, run, tapArt } from './helpers';

test('sound test: a tap starts the worklet, songs start, loop and stop', async ({ page }) => {
  await open(page, '&sound');
  await run(page, 20);
  const v = await drive(page, (d) => d.view());
  /* row 2 on the left: the meadow song (rows are 12 px from safe top + 16) */
  await tapArt(page, 40, v.safe.top + 16 + 12 * 1 + 4);
  await run(page, 2);
  await expect.poll(async () => (await log(page)).some((l) => /audio worklet ready/.test(l)), { timeout: 10000 }).toBe(true);
  await expect.poll(async () => (await log(page)).some((l) => /song start 1/.test(l)), { timeout: 10000 }).toBe(true);
  /* the stop row on the right */
  await tapArt(page, v.w - 40, v.safe.top + 16 + 12 * 7 + 4);
  await run(page, 2);
  await expect.poll(async () => (await log(page)).some((l) => /song stop 1/.test(l)), { timeout: 10000 }).toBe(true);
  const state = await drive(page, (d) => d.sound());
  expect(state).toContain('worklet ready');
});
