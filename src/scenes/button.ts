/* The large round buttons (docs/PLAN.md step 2): the home button, in the
 * same top-left corner of every scene but the map and the title, and the
 * shelf button on the map. Drawn in view art pixels inside the safe area;
 * the tap zone is at least 64 points. Pixel art drawn here (the GBA had no
 * such button): a pink disc with an ink edge and a white shine. */
import { Game } from '../game';

export const BUTTON_D = 21; /* disc size in art pixels */
/** room a fixed screen keeps free for the button (art pixels) */
export const BUTTON_ROOM = BUTTON_D + 5;

const INK = '#8a5a7a';
const PINK = '#ffd2df';
const PINK2 = '#ffb6ca';
const WHITE = '#ffffff';

/* the house icon: k ink, w white, p pink door */
const HOUSE = [
  '.....k.....',
  '....kwk....',
  '...kwwwk...',
  '..kwwwwwk..',
  '.kwwwwwwwk.',
  'kkwwwwwwwkk',
  '.kwwkkkwwk.',
  '.kwwkpkwwk.',
  '.kwwkpkwwk.',
  '.kkkkkkkkk.',
];

/** Top-left corner of the button in view art pixels. */
export function buttonAt(game: Game): { x: number; y: number } {
  const v = game.screen.view;
  return { x: v.safe.left + 3, y: v.safe.top + 3 };
}

/** True when a touch (view art pixels) lands in the button's zone. */
export function buttonHit(game: Game, x: number, y: number): boolean {
  const v = game.screen.view;
  const { x: bx, y: by } = buttonAt(game);
  const r = Math.max(BUTTON_D / 2 + 2, (32 * v.dpr) / v.k);
  return Math.hypot(x - (bx + BUTTON_D / 2), y - (by + BUTTON_D / 2)) <= r;
}

/** Draws the disc; `icon` draws the picture centred on (cx, cy). press: 0..1 pushes it down. */
export function drawButton(game: Game, ctx: CanvasRenderingContext2D, icon: 'home' | ((cx: number, cy: number) => void), press = 0): void {
  const { x, y } = buttonAt(game);
  const d = BUTTON_D, r = d / 2;
  const dy = Math.round(press * 2);
  const row = (yy: number, inset: number, color: string) => {
    const half = Math.sqrt(Math.max(0, inset * inset - (yy + 0.5 - r) ** 2));
    const x0 = Math.round(r - half), x1 = Math.round(r + half);
    if (x1 > x0) {
      ctx.fillStyle = color;
      ctx.fillRect(x + x0, y + dy + yy, x1 - x0, 1);
    }
  };
  for (let yy = 0; yy < d; yy++) row(yy, r, INK);
  for (let yy = 1; yy < d - 1; yy++) row(yy, r - 1, yy > d * 0.6 ? PINK2 : PINK);
  ctx.fillStyle = WHITE;
  ctx.fillRect(x + 5, y + dy + 4, 3, 1);
  ctx.fillRect(x + 4, y + dy + 5, 1, 2);
  const cx = x + Math.floor(r), cy = y + dy + Math.floor(r);
  if (icon === 'home') {
    HOUSE.forEach((line, yy) => {
      for (let xx = 0; xx < line.length; xx++) {
        const ch = line[xx];
        if (ch === '.') continue;
        ctx.fillStyle = ch === 'k' ? INK : ch === 'p' ? PINK2 : WHITE;
        ctx.fillRect(cx - 5 + xx, cy - 5 + yy, 1, 1);
      }
    });
  } else icon(cx, cy);
}
