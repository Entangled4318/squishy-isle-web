/* Fixed screens (title, open, close-up, shelf, rooms) are the GBA's 240 x 160
 * backdrops. They draw at their own whole-number scale, centred (in
 * portrait that scale is smaller than the view's, so they still fit). The
 * bands left and right show the backdrop mirrored, so the scenery runs on
 * (a stretched edge column made stripes where a tree touched the edge);
 * the bands above and below repeat the top and bottom rows (sky, ground). */
import { Game } from '../game';
import { fixedLayout, FixedLayout } from '../engine/screen';

export const FIXED_W = 240;
export const FIXED_H = 160;

/** Draws `img` as a fixed screen, then calls draw() in its pixel space. */
export function drawFixed(
  game: Game,
  ctx: CanvasRenderingContext2D,
  img: HTMLImageElement | undefined,
  draw: () => void,
  /** rows from here down repeat the edge column instead of the mirror
   * (a name pill near the bottom would show half pills at the edges) */
  mirrorRows = FIXED_H,
  /** keep room for the home button (view art pixels), 0 = none */
  button = 0,
  /** true: all the bands are the backdrop's bottom-left pixel (a plain wall) */
  flat = false,
): FixedLayout {
  const v = game.screen.view;
  const f = fixedLayout(v, FIXED_W, FIXED_H, button);
  const W = FIXED_W, H = FIXED_H;
  const x1 = f.ox + W * f.k, y1 = f.oy + H * f.k;
  ctx.imageSmoothingEnabled = false;
  if (img && flat) {
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.drawImage(img, 0, H - 1, 1, 1, 0, 0, v.devW, v.devH);
    ctx.setTransform(f.k, 0, 0, f.k, f.ox, f.oy);
    ctx.drawImage(img, 0, 0);
  } else if (img) {
    if (f.ox > 0) {
      const m = mirrorRows;
      if (m > 0) {
        ctx.setTransform(-f.k, 0, 0, f.k, f.ox, f.oy);
        ctx.drawImage(img, 0, 0, W, m, 0, 0, W, m);
        ctx.setTransform(-f.k, 0, 0, f.k, x1 + W * f.k, f.oy);
        ctx.drawImage(img, 0, 0, W, m, 0, 0, W, m);
      }
      if (m < H) {
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.drawImage(img, 0, m, 1, H - m, 0, f.oy + m * f.k, f.ox, (H - m) * f.k);
        ctx.drawImage(img, W - 1, m, 1, H - m, x1, f.oy + m * f.k, v.devW - x1, (H - m) * f.k);
      }
    }
    ctx.setTransform(f.k, 0, 0, f.k, f.ox, f.oy);
    ctx.drawImage(img, 0, 0);
    /* rows above and below: copy the canvas's own edge rows, corners included */
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    const c = ctx.canvas;
    if (f.oy > 0) ctx.drawImage(c, 0, f.oy, v.devW, 1, 0, 0, v.devW, f.oy);
    if (v.devH > y1) ctx.drawImage(c, 0, y1 - 1, v.devW, 1, 0, y1, v.devW, v.devH - y1);
  }
  ctx.setTransform(f.k, 0, 0, f.k, f.ox, f.oy);
  draw();
  game.screen.artTransform();
  return f;
}

/** A touch in view art pixels, moved into the fixed screen's pixels. */
export function toFixed(game: Game, x: number, y: number, button = 0): { x: number; y: number } {
  const v = game.screen.view;
  const f = fixedLayout(v, FIXED_W, FIXED_H, button);
  return { x: (x * v.k + v.ox - f.ox) / f.k, y: (y * v.k + v.oy - f.oy) / f.k };
}
