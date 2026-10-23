/* The map, ported from the GBA viewer.c (v1.6): the area's ground, the
 * water glint, the overlay (tree tops over sprites), the camera, Pip and
 * Momo asleep at a shut gate.
 *
 * Touch (docs/PLAN.md step 2) replaces the D-pad: a touch on the ground
 * walks Pip there by the shortest path (or to the nearest spot he can
 * reach); while the finger stays down and moves, the walk follows it. A
 * tap on Pip is the hop (GBA B), a tap on Momo a giggle. A tap near a
 * thing counts as a tap on the nearest thing (zones of 64 points). The
 * steps themselves are the GBA move(): 1.25 px a frame, the same speed on
 * diagonals, and the movement assist at edges.
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
import { findPath, Grid } from './path';
import { idiv } from '../engine/gba';

const FEET_W = 5; /* half width of Pip's feet box */
const FEET_H = 5;
const AREA_SONG = [SONG.meadow, SONG.woods, SONG.shore, SONG.cloud];
const SHADOW_ALPHA = 5 / 16; /* the GBA blend: shadow 5/16 over the ground's 11/16 */
const SPEED = 320; /* 8.8 fixed: 1.25 px a frame */
const ASSIST = 6; /* px: walking straight into an edge eases sideways into an opening this close */
const HOP_LEN = 16; /* frames of one hop */
const HOP_LAG = 5; /* each follower hops this much later */
const MAX_FOLLOWERS = 3;
const POS_SAVE_WAIT = 60; /* save the position after Pip stands still this long */
const TOUCH_PT = 32; /* tap zone radius in points (64-point zones) */
const RETARGET = 6; /* frames between new paths while a finger drags */
const STUCK = 20; /* frames without progress before a walk gives up */
const hopH = (t: number) => (t >= 0 && t < HOP_LEN ? idiv(t * (HOP_LEN - t), 10) : 0); /* up to 6 px */

export const enum Dir {
  Down,
  Up,
  Right,
  Left,
}

/** One sprite in the world, drawn nearest last (larger y in front). */
interface WorldSpr {
  depth: number;
  draw: (ctx: CanvasRenderingContext2D) => void;
}

export class Meadow implements Scene {
  readonly name = 'meadow';
  A!: AreaData;
  private solid: Uint8Array = new Uint8Array(0);
  /** Pip's feet, 8.8 fixed, in map pixels */
  px8 = 0;
  py8 = 0;
  get pipX(): number {
    return this.px8 >> 8;
  }
  get pipY(): number {
    return this.py8 >> 8;
  }
  dir = Dir.Down;
  walkT = 0;
  private hopT = -1;
  private pipHop = 0;
  private stillT = 0;
  private posDirty = false;
  /** the walk: map-pixel waypoints, next first */
  path: [number, number][] = [];
  private goal: [number, number] | null = null;
  private stuckT = 0;
  private dragT = 0;
  private dragCell = -1;
  private momoPoke = -1;
  private momoGate = -1;
  private step = { x: 0, y: 0, t: 0, sx: 0, sy: 0 };
  camX = 0;
  camY = 0;
  private glint: HTMLCanvasElement[] = [];
  private world: WorldSpr[] = [];
  /** drawn over the world sprites, under the overlay (GBA ui_spr, priority 1) */
  private ui: ((ctx: CanvasRenderingContext2D) => void)[] = [];
  /** the saved position is used once, on the first visit after boot */
  private posRestored = false;

  /** One meadow for the whole run: Pip stays where he was between visits. */
  constructor(private game: Game) {}

  /** A new game starts at the house (GBA meadow_reset). */
  reset(): void {
    const A = this.game.art.index.maps[0];
    this.px8 = A.spawn[0] << 8;
    this.py8 = A.spawn[1] << 8;
    this.dir = Dir.Down;
    this.path = [];
    this.goal = null;
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
    this.path = [];
    this.goal = null;
    this.hopT = -1;
    this.pipHop = 0;
    this.momoPoke = -1;
    this.step.t = 0;
    g.sound.music(AREA_SONG[A.index] ?? SONG.meadow);
    this.updateCamera();
    dbg(`scene meadow pip=${this.pipX},${this.pipY} area=${A.index} cam=${this.camX},${this.camY}`);
  }

  private solidAt(x: number, y: number): boolean {
    const A = this.A;
    if (x < 0 || y < 0 || x >= A.w || y >= A.h) return true;
    return this.solid[Math.floor(y / A.cell) * A.cols + Math.floor(x / A.cell)] === 1;
  }

  /** gate i's way is still shut, or opened but Momo has not moved on yet */
  private gateThere(to: number): boolean {
    const c = this.game.collection;
    const shut = to >= 4 || !c.areaOpen(to);
    const built = to <= 0 || (c.s.gates & (1 << (to - 1))) !== 0;
    return shut || !built;
  }

  /** The map and Momo: Pip's feet box touches a solid cell or a shut gate. */
  mapBlocked(fx: number, fy: number): boolean {
    if (this.solidAt(fx - FEET_W, fy - FEET_H) || this.solidAt(fx + FEET_W, fy - FEET_H) || this.solidAt(fx - FEET_W, fy) || this.solidAt(fx + FEET_W, fy))
      return true;
    for (const g of this.A.gates)
      if (this.gateThere(g[4]) && fx + FEET_W >= g[0] && fx - FEET_W < g[0] + g[2] && fy >= g[1] && fy - FEET_H < g[1] + g[3]) return true;
    return false;
  }

  /** Everything that stops a step. Containers join in sub-step 4. */
  blocked(fx: number, fy: number): boolean {
    return this.mapBlocked(fx, fy);
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
    this.px8 = x << 8;
    this.py8 = y << 8;
    dbg(`restore pip=${x},${y}`);
  }

  /** Puts Pip somewhere (test driver, later: travel between areas). */
  place(x: number, y: number): void {
    this.px8 = x << 8;
    this.py8 = y << 8;
    this.path = [];
    this.goal = null;
    this.updateCamera();
  }

  /** Keeps the save's position up to date without a write on every step. */
  private savePos(now: boolean): void {
    if (!this.posDirty || (!now && this.stillT < POS_SAVE_WAIT)) return;
    this.posDirty = false;
    const s = this.game.collection.s;
    s.pipX = this.pipX;
    s.pipY = this.pipY;
    this.game.collection.save();
    dbg(`save pip=${s.pipX},${s.pipY}`);
  }

  /* ---- movement: the GBA move() with its assist ---- */

  /** px to the first spot on side (ox, oy) from where the step (sx, sy) is
   * free, walking only on free ground; 0 = none within ASSIST */
  private reach(fx: number, fy: number, ox: number, oy: number, sx: number, sy: number): number {
    for (let k = 1; k <= ASSIST; k++) {
      const x = fx + ox * k, y = fy + oy * k;
      if (this.mapBlocked(x, y)) return 0;
      if (!this.mapBlocked(x + sx, y + sy)) return k;
    }
    return 0;
  }

  /** -1 / +1: the side where the way on opens within ASSIST px; 0 = none or a tie */
  private opening(fx: number, fy: number, sx: number, sy: number): number {
    const a = sx ? this.reach(fx, fy, 0, -1, sx, 0) : this.reach(fx, fy, -1, 0, 0, sy);
    const b = sx ? this.reach(fx, fy, 0, 1, sx, 0) : this.reach(fx, fy, 1, 0, 0, sy);
    if (a && (!b || a < b)) return -1;
    if (b && (!a || b < a)) return 1;
    return 0;
  }

  /** One step of (dx, dy) in 8.8 px, as on the GBA. */
  move(dx: number, dy: number): void {
    const ox = this.px8, oy = this.py8;
    let fx = this.px8 >> 8, fy = this.py8 >> 8;
    const sx = Math.sign(dx), sy = Math.sign(dy);
    const st = this.step;
    if (st.t > 0 && (sx !== st.sx || sy !== st.sy)) st.t = 0; /* the walk turned elsewhere */
    if (st.t > 0) {
      st.t--;
      if (!this.blocked(fx + st.x, fy + st.y)) {
        this.px8 += st.x << 8;
        this.py8 += st.y << 8;
      }
      fx = this.px8 >> 8;
      fy = this.py8 >> 8;
      if (st.y && !this.blocked((this.px8 + dx) >> 8, fy)) {
        this.px8 += dx;
        st.t = 0;
      }
      if (st.x && !this.blocked(fx, (this.py8 + dy) >> 8)) {
        this.py8 += dy;
        st.t = 0;
      }
      return;
    }
    if (dx && !this.blocked((this.px8 + dx) >> 8, fy)) this.px8 += dx;
    fx = this.px8 >> 8;
    if (dy && !this.blocked(fx, (this.py8 + dy) >> 8)) this.py8 += dy;
    if (this.px8 !== ox || this.py8 !== oy) return;
    if (sx && sy) {
      /* diagonal into a stair step of an edge: step around it */
      if (!this.mapBlocked(fx + sx, fy) || !this.mapBlocked(fx, fy + sy)) return; /* a box: no assist */
      const ky = this.reach(fx, fy, 0, -sy, sx, 0);
      const kx = this.reach(fx, fy, -sx, 0, 0, sy);
      if (!ky && !kx) return;
      const alongY = ky && (!kx || ky <= kx);
      st.x = alongY ? 0 : -sx;
      st.y = alongY ? -sy : 0;
      st.t = alongY ? ky : kx;
      st.sx = sx;
      st.sy = sy;
      return;
    }
    if (sx ? !this.mapBlocked(fx + sx, fy) : !this.mapBlocked(fx, fy + sy)) return; /* a box stopped Pip */
    const d = this.opening(fx, fy, sx, sy); /* straight into an edge: ease toward the opening */
    if (sx) this.py8 += d << 8;
    else this.px8 += d << 8;
  }

  /* ---- the walk: a path of waypoints, then steps toward each ---- */

  private grid(): Grid {
    const A = this.A;
    const half = A.cell >> 1;
    return { cols: A.cols, rows: A.rows, free: (cx, cy) => !this.blocked(cx * A.cell + half, cy * A.cell + half) };
  }

  /** Walks Pip toward map pixel (x, y) by the shortest path. */
  walkTo(x: number, y: number): void {
    const A = this.A;
    const c = A.cell;
    const cells = findPath(this.grid(), [Math.floor(this.pipX / c), Math.floor(this.pipY / c)], [Math.floor(x / c), Math.floor(y / c)]);
    const half = c >> 1;
    this.path = cells.map(([cx, cy]) => [cx * c + half, cy * c + half] as [number, number]);
    /* the last waypoint is the tap itself when Pip can stand there */
    if (this.path.length && !this.blocked(x, y)) {
      const last = this.path[this.path.length - 1];
      if (Math.abs(last[0] - x) <= c && Math.abs(last[1] - y) <= c) this.path[this.path.length - 1] = [Math.round(x), Math.round(y)];
    }
    this.goal = [Math.round(x), Math.round(y)];
    this.stuckT = 0;
    dbg(`walk to ${this.goal[0]},${this.goal[1]} steps=${this.path.length}`);
  }

  /** True when a straight walk from Pip to (x, y) touches nothing. */
  private clearLine(x: number, y: number): boolean {
    const x0 = this.pipX, y0 = this.pipY;
    const n = Math.max(Math.abs(x - x0), Math.abs(y - y0));
    for (let i = 1; i <= n; i++) if (this.blocked(Math.round(x0 + ((x - x0) * i) / n), Math.round(y0 + ((y - y0) * i) / n))) return false;
    return true;
  }

  /** Steps along the path; false when there is nothing to walk. */
  private followPath(): boolean {
    const p = this.path;
    if (!p.length) return false;
    /* skip waypoints Pip can walk to straight (a few tries a frame) */
    for (let k = 0; k < 4 && p.length > 1 && this.clearLine(p[1][0], p[1][1]); k++) p.shift();
    const [wx, wy] = p[0];
    const ex = (wx << 8) + 128 - this.px8, ey = (wy << 8) + 128 - this.py8;
    const len = Math.hypot(ex, ey);
    if (len <= SPEED) {
      if (!this.blocked(wx, wy)) {
        this.px8 = (wx << 8) + 128;
        this.py8 = (wy << 8) + 128;
      }
      p.shift();
      if (!p.length) this.goal = null;
      return true;
    }
    const dx = Math.round((ex * SPEED) / len), dy = Math.round((ey * SPEED) / len);
    /* face the way of the larger part; keep the facing on near-diagonals */
    const ax = Math.abs(dx), ay = Math.abs(dy);
    const horiz = this.dir === Dir.Left || this.dir === Dir.Right;
    if (ax > ay * (horiz ? 0.8 : 1.25)) this.dir = dx > 0 ? Dir.Right : Dir.Left;
    else this.dir = dy > 0 ? Dir.Down : Dir.Up;
    const bx = this.px8, by = this.py8;
    this.move(dx, dy);
    if (this.px8 === bx && this.py8 === by) {
      if (++this.stuckT > STUCK) {
        dbg(`walk stuck at ${this.pipX},${this.pipY}`);
        this.path = [];
        this.goal = null;
      }
    } else this.stuckT = 0;
    return true;
  }

  /* ---- touch ---- */

  /** Tap zone radius in art pixels: 32 points, or the thing's own half size. */
  private zone(half: number): number {
    const v = this.game.screen.view;
    return Math.max(half, (TOUCH_PT * v.dpr) / v.k);
  }

  /** Momo's feet at each shut gate. */
  private momos(): { i: number; x: number; y: number }[] {
    const out: { i: number; x: number; y: number }[] = [];
    this.A.gates.forEach((g, i) => {
      if (this.gateThere(g[4])) out.push({ i, x: g[0] + (g[2] >> 1), y: g[1] + g[3] });
    });
    return out;
  }

  /** The nearest thing within its zone of map point (x, y), or null. */
  private thingAt(x: number, y: number): { kind: 'pip' | 'momo'; i: number } | null {
    let best: { kind: 'pip' | 'momo'; i: number } | null = null, bd = Infinity;
    const consider = (kind: 'pip' | 'momo', i: number, cx: number, cy: number, half: number) => {
      const d = Math.hypot(x - cx, y - cy);
      if (d <= this.zone(half) && d < bd) [best, bd] = [{ kind, i }, d];
    };
    consider('pip', 0, this.pipX, this.pipY - 12, 10);
    for (const m of this.momos()) consider('momo', m.i, m.x, m.y - 14, 14);
    return best;
  }

  private onTouch(t: TouchEvt): void {
    const x = t.x + this.camX, y = t.y + this.camY;
    if (t.kind === 'down') {
      this.dragT = 0;
      this.dragCell = -1;
      const hit = this.thingAt(x, y);
      if (hit?.kind === 'pip') {
        this.hop();
        return;
      }
      if (hit?.kind === 'momo') {
        if (this.momoPoke < 0 || this.momoPoke > 24) {
          this.momoPoke = 0;
          this.momoGate = hit.i;
          this.game.sound.squeak(1);
          dbg(`poke momo ${hit.i}`);
        }
        return;
      }
      this.walkTo(x, y);
      this.dragCell = Math.floor(y / this.A.cell) * this.A.cols + Math.floor(x / this.A.cell);
    } else if (t.kind === 'move') {
      const cell = Math.floor(y / this.A.cell) * this.A.cols + Math.floor(x / this.A.cell);
      if (cell !== this.dragCell && this.dragT >= RETARGET) {
        this.dragT = 0;
        this.dragCell = cell;
        this.walkTo(x, y);
      }
    }
  }

  /** Pip's happy hop (GBA B); the followers hop after him. */
  hop(): void {
    if (this.hopT >= 0) return;
    this.hopT = 0;
    this.game.sound.hop();
    dbg('pip hop');
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
    this.dragT++;
    for (const t of touches) this.onTouch(t);
    if (this.hopT >= 0) {
      this.pipHop = hopH(this.hopT);
      if (++this.hopT > HOP_LEN + MAX_FOLLOWERS * HOP_LAG) {
        this.hopT = -1;
        this.pipHop = 0;
      }
    }
    if (this.momoPoke >= 0 && ++this.momoPoke > 40) this.momoPoke = -1;
    const wasX = this.px8, wasY = this.py8;
    if (this.followPath()) this.walkT++;
    else this.walkT = 0;
    if (this.px8 !== wasX || this.py8 !== wasY) {
      this.stillT = 0;
      this.posDirty = true;
    } else if (this.stillT < POS_SAVE_WAIT) this.stillT++;
    this.savePos(false);
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
    const feet = art.index.layout.pipFeetRow as number;
    const walking = this.walkT > 0;
    const step = (this.walkT >> 3) & 3;
    const walkDown = [1, 0, 2, 0];
    let name: string, flip = false;
    if (this.dir === Dir.Up) name = `pip/up${walking ? walkDown[step] : 0}`;
    else if (this.dir === Dir.Right || this.dir === Dir.Left) {
      name = `pip/right${walking ? step & 1 : 0}`;
      flip = this.dir === Dir.Left;
    } else name = `pip/down${walking ? walkDown[step] : 0}`;
    const bob = (walking && step & 1 ? 1 : 0) + this.pipHop;
    const sx = this.pipX - this.camX, sy = this.pipY - this.camY;
    this.shadow(this.pipY - 1, sx, sy);
    this.world.push({ depth: this.pipY, draw: (ctx) => art.draw(ctx, name, sx - 8, sy - feet - 1 - bob, { flipX: flip }) });
  }

  private shadow(depth: number, sx: number, sy: number): void {
    const art = this.game.art;
    this.world.push({
      depth,
      draw: (ctx) => {
        ctx.globalAlpha = SHADOW_ALPHA;
        art.draw(ctx, 'shadow12', sx - 6, sy - 3);
        ctx.globalAlpha = 1;
      },
    });
  }

  /** Momo asleep on each shut gate, breathing slowly, z's drifting up.
   * A tap makes Momo giggle and hop (GBA poke). The heart meter is M6. */
  private drawMomos(): void {
    const art = this.game.art;
    const f = this.game.frame;
    for (const m of this.momos()) {
      let x = m.x, hop = 0;
      if (this.momoPoke >= 0 && this.momoGate === m.i && this.momoPoke < 24) {
        const t = this.momoPoke % 12;
        hop = idiv(t * (12 - t), 6);
        x += (this.momoPoke / 3) & 1;
      }
      const sx = x - this.camX, sy = m.y - this.camY;
      const breathe = hop ? 0 : (f / 40) & 1;
      this.shadow(m.y - 1, sx, sy);
      this.world.push({ depth: m.y, draw: (ctx) => art.draw(ctx, hop ? 'momo/awake' : 'momo/sleep', sx - 16, sy - 32 - hop + breathe) });
      this.ui.push((ctx) => {
        for (let k = 0; k < 2; k++) {
          const t = (f + k * 45) % 90;
          if (t <= 70) art.draw(ctx, `momo/z${k}`, sx + 8 + idiv(t, 10), sy - 36 - idiv(t, 3));
        }
      });
    }
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
    this.ui = [];
    this.drawPip();
    this.drawMomos();
    this.world.sort((a, b) => a.depth - b.depth).forEach((w) => w.draw(ctx));
    this.ui.forEach((d) => d(ctx));
    if (overlay) ctx.drawImage(overlay, -cx, -cy);
  }
}
