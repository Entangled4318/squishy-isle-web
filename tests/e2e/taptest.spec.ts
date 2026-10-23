/* Milestone 1: the tap test page, the save through a reload, touch rules,
 * the view on rotation, and offline play. */
import { expect, test } from '@playwright/test';
import { drive, log, logHas, open, run, tapArt } from './helpers';

test('boots into the tap test with a new save', async ({ page }) => {
  await open(page);
  await run(page, 20);
  await logHas(page, /save: new v2 boots=1 found=0/);
  await logHas(page, /scene taptest/);
  expect(await drive(page, (d) => d.storage())).toMatchObject({ local: true, indexedDB: true });
});

test('a tap counts, sparkles and saves; the count survives a reload', async ({ page }) => {
  await open(page);
  await run(page, 20); /* past the fade-in */
  const v = await drive(page, (d) => d.view());
  for (let i = 0; i < 3; i++) {
    await tapArt(page, v.w / 2, v.h / 2);
    await run(page, 2);
  }
  expect(await drive(page, (d) => d.sparkles())).toBeGreaterThan(0);
  await logHas(page, /tap 3 at/);
  expect((await drive(page, (d) => d.save())).squishes).toBe(3);
  await drive(page, (d) => d.flush());
  await page.reload();
  await page.waitForFunction(() => (window as unknown as { __squishy?: { ready: boolean } }).__squishy?.ready === true);
  await logHas(page, /save: loaded v2 boots=2/);
  expect((await drive(page, (d) => d.save())).squishes).toBe(3);
});

test('the save survives losing one store: localStorage cleared, IndexedDB keeps it', async ({ page }) => {
  await open(page);
  await run(page, 20);
  await tapArt(page, 50, 50);
  await run(page, 2);
  await drive(page, (d) => d.flush());
  await page.evaluate(() => Object.keys(localStorage).filter((k) => k.startsWith('squishy-isle-web:slot')).forEach((k) => localStorage.removeItem(k)));
  await page.reload();
  await page.waitForFunction(() => (window as unknown as { __squishy?: { ready: boolean } }).__squishy?.ready === true);
  await logHas(page, /save: loaded/);
  expect((await drive(page, (d) => d.save())).squishes).toBe(1);
});

test('the save survives losing one store: IndexedDB deleted, localStorage keeps it', async ({ page }) => {
  await open(page);
  await run(page, 20);
  await tapArt(page, 50, 50);
  await run(page, 2);
  await drive(page, (d) => d.flush());
  await page.evaluate(() => new Promise((r) => { const q = indexedDB.deleteDatabase('squishy-isle-web'); q.onsuccess = q.onerror = q.onblocked = () => r(null); }));
  await page.reload();
  await page.waitForFunction(() => (window as unknown as { __squishy?: { ready: boolean } }).__squishy?.ready === true);
  expect((await drive(page, (d) => d.save())).squishes).toBe(1);
});

test('only the first finger acts; a second finger only sparkles', async ({ page }) => {
  await open(page);
  await run(page, 20);
  await drive(page, (d) => {
    d.touch('down', 40, 40);
    d.touch('extra', 120, 60);
    d.touch('extra', 140, 80);
    d.run(2);
  });
  expect((await drive(page, (d) => d.save())).squishes).toBe(1);
  expect(await drive(page, (d) => d.sparkles())).toBe(3);
});

test('real two-finger touch: one tap counted', async ({ page }) => {
  await open(page);
  await run(page, 20);
  const cdp = await page.context().newCDPSession(page);
  const p = (id: number, x: number, y: number) => ({ x, y, id, radiusX: 5, radiusY: 5, force: 1 });
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [p(1, 100, 100)] });
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [p(1, 100, 100), p(2, 200, 150)] });
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
  await run(page, 2);
  expect((await drive(page, (d) => d.save())).squishes).toBe(1);
});

test('taps during the fade-in only sparkle', async ({ page }) => {
  await open(page);
  expect(await drive(page, (d) => d.fading())).toBe(true);
  await drive(page, (d) => {
    d.touch('down', 40, 40);
    d.touch('up', 40, 40);
    d.run(1);
  });
  expect((await drive(page, (d) => d.save())).squishes).toBe(0);
  expect(await drive(page, (d) => d.sparkles())).toBe(1);
});

test('the view keeps whole-number scale and at least the GBA screen, in both orientations', async ({ page }) => {
  await open(page);
  const size = page.viewportSize()!;
  for (const [w, h] of [[size.width, size.height], [size.height, size.width]]) {
    await page.setViewportSize({ width: w, height: h });
    await page.waitForTimeout(150);
    const v = await drive(page, (d) => d.view());
    expect(Number.isInteger(v.k) && v.k >= 1).toBe(true);
    expect(v.portrait).toBe(h > w);
    expect(Math.max(v.w, v.h)).toBeGreaterThanOrEqual(240);
    expect(Math.min(v.w, v.h)).toBeGreaterThanOrEqual(160);
    expect(v.w * v.k).toBeLessThanOrEqual(v.devW);
    expect(v.h * v.k).toBeLessThanOrEqual(v.devH);
  }
});

test('no browser zoom, scroll or callout on the page', async ({ page }) => {
  await open(page);
  const css = await page.evaluate(() => {
    const b = getComputedStyle(document.body);
    const c = getComputedStyle(document.getElementById('game')!);
    return { body: b.touchAction, canvas: c.touchAction, select: b.userSelect, overflow: b.overflow };
  });
  expect(css).toEqual({ body: 'none', canvas: 'none', select: 'none', overflow: 'hidden' });
  const meta = await page.getAttribute('meta[name=viewport]', 'content');
  expect(meta).toContain('viewport-fit=cover');
});

test('plays offline after the first visit', async ({ page, context }) => {
  await open(page, '&sw=1');
  await page.evaluate(() => navigator.serviceWorker.ready.then(() => null));
  await page.reload(); /* now the service worker controls the page */
  await page.waitForFunction(() => navigator.serviceWorker.controller !== null);
  await context.setOffline(true);
  await page.reload();
  await page.waitForFunction(() => (window as unknown as { __squishy?: { ready: boolean } }).__squishy?.ready === true);
  await run(page, 20);
  expect(await drive(page, (d) => d.scene())).toBe('taptest');
  const icon = await page.evaluate(() => fetch('./gen/icon-192.png').then((r) => r.status));
  expect(icon).toBe(200);
  await context.setOffline(false);
});

test('install hint: shows for parents, one tap on OK closes it for good', async ({ page }) => {
  await open(page, '&hint=1');
  await expect(page.locator('#install-hint')).toBeVisible();
  await page.locator('#install-hint button').tap();
  await expect(page.locator('#install-hint')).toHaveCount(0);
  const seen = await page.evaluate(() => localStorage.getItem('squishy-isle-web:pref:install-hint'));
  expect(seen).toBe('seen');
  expect((await log(page)).length).toBeGreaterThan(0);
});
