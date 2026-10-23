/* The map, ported from the GBA viewer.c (v1.6). Sub-step 2 of M4: the
 * area's ground, the water glint, the overlay (tree tops over sprites),
 * Pip standing where the save says, and the camera. Movement, containers
 * and friends come in the next sub-steps.
 *
 * Camera: the view is the screen in art pixels (at least 240 x 160, more
 * along the long side, see engine/screen.ts). It follows Pip as on the
 * GBA (Pip 12 px above the middle) and stops at the map's edges. A view
 * larger than the map shows the map centred. */
import { Game } from '../game';
import { Scene } from '../engine/scenes';
import { TouchEvt } from '../engine/input';
import { dbg } from '../engine/log';
import { SONG } from '../engine/audio';
import type { AreaData } from '../engine/art';

const FEET_W = 5; /* half width of Pip's feet box */
const FEET_H = 5;
const AREA_SONG = [SONG.meadow, SONG.woods, SONG.shore, SONG.cloud];
const SHADOW_ALPHA = 5 / 16; /* the GBA blend: shadow 5/16 over the ground's 11/16 */

/** One sprite in the world, drawn nearest last (larger y in front). */
interface WorldSpr {
  depth: number;
  draw: (ctx: CanvasRenderingContext2D) => void;
}

export class Meadow implements Scene {
  readonly name = 'meadow';
  A!: AreaData;
  private solid: Uint8Array = new Uint8Array(0);
  /** Pip's feet, in map pixels */
  pipX = 0;
  pipY = 0;
  camX = 0;
  camY = 0;
  private glint: HTMLCanvasElement[] = [];
  private world: WorldSpr[] = [];
  /** the saved position is used once, on the first visit after boot */
  private posRestored = false;

  /** One meadow for the whole run: Pip stays where he was between visits. */
  constructor(private game: Game) {}

  /** A new game starts at the house (GBA meadow_reset). */
  reset(): void {
    const A = this.game.art.index.maps[0];
    [this.pipX, this.pipY] = A.spawn;
    this.posRestored = true;
  }

  enter(): void {
    const g = this.game;
    const s = g.collection.s;
    const maps = g.art.index.maps;
    this.A = maps[s.area < maps.length ? s.area : 0];
    const A = this.A;
    this.solid = Uint8Array.from(A.solid, (ch) => (ch === '1' ? 1 : 0));
    for (const p of [A.ground, A.overlay, A.glint]) void g.art.image(p);
    this.glint = [];
    this.restorePos();
    g.sound.music(AREA_SONG[A.index] ?? SONG.meadow);
    this.updateCamera();
    dbg(`scene meadow pip=${this.pipX},${this.pipY} area=${A.index} cam=${this.camX},${this.camY}`);
  }

  private solidAt(x: number, y: number): boolean {
    const A = this.A;
    if (x < 0 || y < 0 || x >= A.w || y >= A.h) return true;
    return this.solid[Math.floor(y / A.cell) * A.cols + Math.floor(x / A.cell)] === 1;
  }

  /** The map only: Pip's feet box touches a solid cell. Gates and boxes come later. */
  mapBlocked(fx: number, fy: number): boolean {
    return this.solidAt(fx - FEET_W, fy - FEET_H) || this.solidAt(fx + FEET_W, fy - FEET_H) || this.solidAt(fx - FEET_W, fy) || this.solidAt(fx + FEET_W, fy);
  }

  /** Continue: Pip goes back where the save says, once per boot, if it is
   * walkable; else to the area's start (GBA restore_pos). */
  private restorePos(): void {
    const s = this.game.collection.s;
    const A = this.A;
    if (this.posRestored) return;
    this.posRestored = true;
    let x = s.pipX, y = s.pipY;
    if ((!x && !y) || x >= A.w || y >= A.h || this.mapBlocked(x, y)) [x, y] = A.spawn;
    this.pipX = x;
    this.pipY = y;
    dbg(`restore pip=${x},${y}`);
  }

  /** Puts Pip somewhere (test driver, later: travel between areas). */
  place(x: number, y: number): void {
    this.pipX = x;
    this.pipY = y;
    this.updateCamera();
  }

  updateCamera(): void {
    const v = this.game.screen.view;
    const A = this.A;
    const axis = (p: number, view: number, size: number) => {
      if (view >= size) return Math.floor((size - view) / 2); /* the whole map fits: centre it */
      return Math.max(0, Math.min(size - view, p - Math.floor(view / 2)));
    };
    this.camX = axis(this.pipX, v.w, A.w);
    this.camY = axis(this.pipY - 12, v.h, A.h);
  }

  update(touches: TouchEvt[]): void {
    void touches; /* sub-step 3: tap to walk, drag to steer, the hop */
    this.updateCamera();
  }

  /** The glint mask in each of the area's 4 shimmer colors (made once the mask has loaded). */
  private glintFrames(): HTMLCanvasElement[] | null {
    if (this.glint.length) return this.glint;
    const mask = this.game.art.cached(this.A.glint);
    if (!mask) return null;
    this.glint = this.A.glintCycle.map((color) => {
      const c = document.createElement('canvas');
      c.width = mask.width;
      c.height = mask.height;
      const x = c.getContext('2d')!;
      x.drawImage(mask, 0, 0);
      x.globalCompositeOperation = 'source-in';
      x.fillStyle = color;
      x.fillRect(0, 0, c.width, c.height);
      return c;
    });
    return this.glint;
  }

  private drawPip(): void {
    const art = this.game.art;
    const feet = this.game.art.index.layout.pipFeetRow as number;
    const sx = this.pipX - this.camX, sy = this.pipY - this.camY;
    this.world.push({
      depth: this.pipY - 1,
      draw: (ctx) => {
        ctx.globalAlpha = SHADOW_ALPHA;
        art.draw(ctx, 'shadow12', sx - 6, sy - 3);
        ctx.globalAlpha = 1;
      },
    });
    this.world.push({ depth: this.pipY, draw: (ctx) => art.draw(ctx, 'pip/down0', sx - 8, sy - feet - 1) });
  }

  draw(ctx: CanvasRenderingContext2D): void {
    const g = this.game;
    const v = g.screen.view;
    const A = this.A;
    const ground = g.art.cached(A.ground);
    const overlay = g.art.cached(A.overlay);
    const cx = this.camX, cy = this.camY;
    if (ground) {
      /* outside a map smaller than the view: the map's corner color (the sea) */
      if (cx < 0 || cy < 0 || cx + v.w > A.w || cy + v.h > A.h) ctx.drawImage(ground, 0, 0, 1, 1, 0, 0, v.w, v.h);
      ctx.drawImage(ground, -cx, -cy);
    }
    const glint = this.glintFrames();
    if (glint) ctx.drawImage(glint[Math.floor(g.frame / 12) & 3], -cx, -cy);
    this.world = [];
    this.drawPip();
    this.world.sort((a, b) => a.depth - b.depth).forEach((w) => w.draw(ctx));
    if (overlay) ctx.drawImage(overlay, -cx, -cy);
  }
}
