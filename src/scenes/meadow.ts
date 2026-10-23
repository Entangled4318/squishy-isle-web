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
import { Closeup } from './closeup';
import { friendFlavor, friendSpecies } from '../rules/collection';
import { buttonHit, drawButton } from './button';
import { idiv, isin } from '../engine/gba';

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
const MAX_BOXES = 3;
const BOX_COLORS = 5;
const ARROW_DELAY = 5 * 60; /* frames without an open before the arrow shows */
const ARROW_R = 26; /* px from Pip's middle to the arrow's middle */
const ARROW_BLINK = 60; /* frames on, then the same off */
const RESPAWN = 90; /* frames before a new box replaces an opened one */
const TOUCH = 6; /* px around a box that count as touching */
const COUNT_TEXT_X = 18; /* the count's 32 px text box starts here in the pill */
const TWINKLE_AROUND: [number, number][] = [
  [-10, -15],
  [8, -18],
  [10, -6],
  [-3, -22],
  [-12, -4],
  [4, -12],
];

interface Box {
  /** index into the area's spots, -1 = empty */
  spot: number;
  color: number;
  /** frames until an empty slot gets a new box */
  wait: number;
  /** animation offset */
  phase: number;
}

/** What the open and reveal screens need from the meadow. */
export interface OpenInfo {
  area: number;
  color: number;
  /** the friend inside, or -1 when the area is full */
  friend: number;
}

const MAX_PEN = 20; /* every friend of an area fits in its pen */
const PEN_TRIES = 10; /* random spots tried for each new pen target */
const PEN_ROOM = 13; /* px: pen friends do not walk closer than this */
const PEN_RETARGETS = 3; /* new-target searches a frame at most */
const TRAIL = 64; /* Pip's recent steps, for followers */
const TRAIL_GAP = 14; /* steps between followers in the line */
const POKE_SQUISH = 10; /* frames on the squish frame, then a little hop */
const POKE_LEN = 40; /* frames until the heart has floated away */
const enum Poke {
  Follower = 1,
  Pen,
  Momo,
}

interface Roamer {
  id: number;
  x: number;
  y: number;
  tx: number;
  ty: number;
  wait: number;
  step: number;
  stuck: number;
}

/** little hops while walking */
const hopOf = (step: number) => {
  const ph = Math.floor(step / 5) % 4;
  return ph === 1 ? 2 : ph === 2 ? 3 : 0;
};

const hopH = (t: number) => (t >= 0 && t < HOP_LEN ? idiv(t * (HOP_LEN - t), 10) : 0); /* up to 6 px */

type Thing = 'pip' | 'momo' | 'box' | 'arrow' | 'follower' | 'pen';

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
  /** the squished friend or tickled Momo (GBA poke) */
  poke = { t: -1, kind: 0, k: 0, x: 0, y: 0 };
  pen: Roamer[] = [];
  followIds: number[] = [];
  private trailX = new Int16Array(TRAIL);
  private trailY = new Int16Array(TRAIL);
  private trailI = 0;
  private penSeed = 12345;
  private step = { x: 0, y: 0, t: 0, sx: 0, sy: 0 };
  boxes: Box[] = [];
  private boxesArea = -1;
  private seekT = 0;
  arrowBox = -1;
  private arrowT = 0;
  touchBox = -1;
  /** the box a tap chose: it opens when Pip arrives */
  pendingBox = -1;
  private countLast = [0, 0, 0, 0];
  private countSeen = 0;
  private countHop = 0;
  /** set when a box opens, for the open and reveal screens */
  open: OpenInfo = { area: 0, color: 0, friend: -1 };
  /** the open screen and the shelf (set by main.ts) */
  openScene: (() => Scene) | null = null;
  shelfScene: (() => Scene) | null = null;
  private shelfPress = 0;
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
    this.boxesArea = -1;
    this.seekT = 0;
    this.arrowBox = this.touchBox = this.pendingBox = -1;
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
    this.poke.t = -1;
    this.step.t = 0;
    this.pendingBox = -1;
    Closeup.resetStreak(); /* GBA 9.3: back on the map, the close-up count starts again */
    const n = g.collection.foundInArea(A.index);
    if (this.countSeen & (1 << A.index) && n > this.countLast[A.index]) this.countHop = 40; /* not when the area changes */
    this.countLast[A.index] = n;
    this.countSeen |= 1 << A.index;
    if (this.boxesArea !== A.index) {
      this.boxes = Array.from({ length: MAX_BOXES }, () => ({ spot: -1, color: 0, wait: 0, phase: 0 }));
      this.boxesArea = A.index;
    }
    this.updateCamera();
    this.boxesFill();
    this.friendsSetup();
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

  /** Everything that stops a step: the map, Momo and the boxes. */
  blocked(fx: number, fy: number): boolean {
    if (this.mapBlocked(fx, fy)) return true;
    for (let i = 0; i < MAX_BOXES; i++) if (this.boxHit(i, fx - FEET_W, fy - FEET_H, fx + FEET_W, fy)) return true;
    return false;
  }

  /* ---- boxes (GBA gift boxes; acorns, shells, capsules in later areas) ---- */

  private spotXY(sp: number): [number, number] {
    return this.A.spots[sp];
  }

  /** box footprint: 14 px wide, 6 px deep at its base */
  private boxHit(i: number, x0: number, y0: number, x1: number, y1: number): boolean {
    const b = this.boxes[i];
    if (!b || b.spot < 0) return false;
    const [bx, by] = this.spotXY(b.spot);
    return x1 >= bx - 7 && x0 <= bx + 7 && y1 >= by - 6 && y0 <= by;
  }

  private boxesWanted(): number {
    return Math.min(20 - this.game.collection.foundInArea(this.A.index), MAX_BOXES);
  }

  private boxesOut(): number {
    return this.boxes.filter((b) => b.spot >= 0).length;
  }

  /** A free spot away from Pip, off screen if it can be, so boxes do not pop
   * up under the child's nose. The very first box of a game sits in view
   * near the cottage. */
  private chooseSpot(): number {
    const c = this.game.collection;
    const v = this.game.screen.view;
    const A = this.A;
    const used = (sp: number) => this.boxes.some((b) => b.spot === sp);
    if (c.foundInArea(A.index) === 0 && this.boxesOut() === 0 && !used(A.firstSpot)) return A.firstSpot;
    let best = -1, bestScore = -1;
    A.spots.forEach(([x, y], sp) => {
      if (used(sp)) return;
      const dx = x - this.pipX, dy = y - this.pipY;
      if (dx * dx + dy * dy < 48 * 48) return;
      const onScreen = x >= this.camX - 8 && x < this.camX + v.w + 8 && y >= this.camY && y < this.camY + v.h + 16;
      const score = (onScreen ? 0 : 100) + (c.rand() % 64);
      if (score > bestScore) [bestScore, best] = [score, sp];
    });
    return best;
  }

  private placeBox(i: number): void {
    const c = this.game.collection;
    const sp = this.chooseSpot();
    if (sp < 0) return;
    let color = c.rand() % BOX_COLORS;
    for (let k = 0; k < BOX_COLORS && this.boxes.some((b) => b.spot >= 0 && b.color === color); k++) color = (color + 1) % BOX_COLORS;
    this.boxes[i] = { spot: sp, color, wait: 0, phase: c.rand() & 255 };
    const [x, y] = this.spotXY(sp);
    dbg(`box ${i} at ${x},${y} color ${color}`);
  }

  private boxesFill(): void {
    for (let i = 0; i < MAX_BOXES && this.boxesOut() < this.boxesWanted(); i++)
      if (this.boxes[i].spot < 0 && this.boxes[i].wait === 0) this.placeBox(i);
  }

  private openBox(i: number): void {
    const g = this.game;
    const c = g.collection;
    const b = this.boxes[i];
    this.open = { area: this.A.index, color: b.color, friend: c.roll(this.A.index, g.frame) };
    b.spot = -1;
    b.wait = RESPAWN;
    this.touchBox = this.arrowBox = this.pendingBox = -1;
    this.seekT = 0;
    this.path = [];
    this.goal = null;
    g.sound.chime(3);
    dbg(`box ${i} open friend ${this.open.friend} pip=${this.pipX},${this.pipY}`);
    this.posDirty = true;
    this.savePos(true);
    if (this.openScene) g.scenes.go(this.openScene());
  }

  private updateBoxes(): void {
    for (const b of this.boxes) if (b.spot < 0 && b.wait > 0) b.wait--;
    this.boxesFill();
    const was = this.touchBox;
    this.touchBox = -1;
    const px = this.pipX, py = this.pipY;
    for (let i = 0; i < MAX_BOXES; i++) if (this.boxHit(i, px - FEET_W - TOUCH, py - FEET_H - TOUCH, px + FEET_W + TOUCH, py + TOUCH)) this.touchBox = i;
    if (this.touchBox >= 0 && this.touchBox !== was) dbg(`touch box ${this.touchBox} pip=${px},${py}`);
    if (this.seekT < ARROW_DELAY) this.seekT++;
    else {
      /* the arrow always points at the nearest box */
      let best = Infinity, near = -1;
      this.boxes.forEach((b, i) => {
        if (b.spot < 0) return;
        const [x, y] = this.spotXY(b.spot);
        const d = (x - px) ** 2 + (y - py) ** 2;
        if (d < best) [best, near] = [d, i];
      });
      if (near !== this.arrowBox) {
        if (this.arrowBox < 0 && near >= 0) this.arrowT = 0;
        this.arrowBox = near;
        dbg(`arrow on box ${near}`);
      }
    }
    if (this.arrowBox >= 0) this.arrowT++;
    if (this.pendingBox >= 0) {
      if (this.boxes[this.pendingBox].spot < 0) this.pendingBox = -1;
      else if (this.touchBox === this.pendingBox && !this.game.scenes.fading()) this.openBox(this.pendingBox);
      else if (!this.path.length && this.walkT === 0 && this.stuckT === 0 && this.touchBox !== this.pendingBox) {
        /* the walk ended short of the box (it could not reach it): forget it */
        dbg(`box ${this.pendingBox} out of reach`);
        this.pendingBox = -1;
      }
    }
  }

  /** Walks to box i; it opens when Pip arrives (at once if he is touching it). */
  private goToBox(i: number): void {
    this.pendingBox = i;
    if (this.touchBox === i) return;
    const [x, y] = this.spotXY(this.boxes[i].spot);
    this.walkTo(x, y + 8);
  }

  /** The arrow's middle on screen, or null when it does not show. */
  private arrowAt(): { x: number; y: number; tile: string; flipX: boolean; flipY: boolean } | null {
    const i = this.arrowBox;
    if (i < 0 || this.boxes[i].spot < 0 || this.touchBox >= 0) return null;
    const pcx = this.pipX - this.camX, pcy = this.pipY - this.camY - 12;
    const [bx, by] = this.spotXY(this.boxes[i].spot);
    const dx = bx - this.camX - pcx, dy = by - this.camY - 8 - pcy;
    const len = Math.floor(Math.sqrt(dx * dx + dy * dy));
    if (len === 0) return null;
    const ax = Math.abs(dx), ay = Math.abs(dy);
    let tile: string, flipX = false, flipY = false;
    if (ax * 5 > ay * 12) {
      tile = 'arrow/right';
      flipX = dx < 0;
    } else if (ay * 5 > ax * 12) {
      tile = 'arrow/up';
      flipY = dy > 0;
    } else {
      tile = 'arrow/upright';
      flipX = dx < 0;
      flipY = dy > 0;
    }
    const r = ARROW_R + idiv((isin(this.game.frame * 2) + 256) * 3, 512); /* a small nudge toward the box */
    return { x: pcx + idiv(dx * r, len), y: pcy + idiv(dy * r, len), tile, flipX, flipY };
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
    if (this.A) this.trailLine(); /* the line stands behind Pip again */
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

  /* ---- friends: a line behind Pip, the rest roam in the pen ---- */

  /** local random numbers: the pen must not use up the saved ones */
  private penRand(n: number): number {
    this.penSeed = (Math.imul(this.penSeed, 1103515245) + 12345) >>> 0;
    return Math.floor(((this.penSeed >>> 16) * n) / 65536);
  }

  /** The roomiest of a few random spots, so many friends spread out. */
  private penTarget(r: Roamer): void {
    const pen = this.A.pen;
    if (!pen) return;
    let best = -1;
    for (let k = 0; k < PEN_TRIES; k++) {
      const x = pen[0] + this.penRand(pen[2] - pen[0]);
      const y = pen[1] + this.penRand(pen[3] - pen[1]);
      let room = 1 << 30;
      for (const o of this.pen) {
        if (o === r) continue;
        room = Math.min(room, (x - o.x) ** 2 + (y - o.y) ** 2, (x - o.tx) ** 2 + (y - o.ty) ** 2);
      }
      if (room > best) {
        best = room;
        r.tx = x;
        r.ty = y;
      }
    }
  }

  /** Lays the follower line out behind Pip (away from where he faces); tries
   * the other sides when the way back is blocked. */
  private trailLine(): void {
    const back = [
      [0, -1],
      [0, 1],
      [-1, 0],
      [1, 0],
    ];
    const order = [
      [0, 2, 3, 1],
      [1, 2, 3, 0],
      [2, 0, 1, 3],
      [3, 0, 1, 2],
    ];
    const px = this.pipX, py = this.pipY;
    let bx = 0, by = 0;
    for (const d of order[this.dir]) {
      let clear = true;
      for (let k = 1; k <= MAX_FOLLOWERS && clear; k++) {
        const s = (k * TRAIL_GAP * SPEED) >> 8;
        for (let t = 4; t <= s && clear; t += 4) clear = !this.blocked(px + back[d][0] * t, py + back[d][1] * t);
      }
      if (clear) {
        [bx, by] = back[d];
        break;
      }
    }
    this.trailI = 0;
    for (let i = 0; i < TRAIL; i++) {
      const t = (this.trailI - i) & (TRAIL - 1), s = (i * SPEED) >> 8;
      this.trailX[t] = px + bx * s;
      this.trailY[t] = py + by * s;
    }
  }

  private friendsSetup(): void {
    const c = this.game.collection;
    const first = this.A.index * 20;
    this.penSeed = (this.penSeed ^ this.game.frame) >>> 0;
    this.followIds = [];
    for (let i = 0; i < MAX_FOLLOWERS; i++) {
      const id = c.followerGet(i);
      if (id >= 0 && c.friendFound(id)) this.followIds.push(id);
    }
    this.pen = [];
    if (this.A.pen)
      for (let id = first; id < first + 20 && this.pen.length < MAX_PEN; id++) {
        if (!c.friendFound(id) || this.followIds.includes(id)) continue;
        const r: Roamer = { id, x: 0, y: 0, tx: 0, ty: 0, wait: 0, step: 0, stuck: 0 };
        this.pen.push(r);
        this.penTarget(r); /* compared only with the friends placed so far */
        r.x = r.tx;
        r.y = r.ty;
        r.wait = this.penRand(120);
        this.penTarget(r);
      }
    dbg(`friends pen=${this.pen.length} follow=${this.followIds.length}`);
    this.trailLine();
  }

  /** True when a step to (nx, ny) takes r closer to a friend that is already near. */
  private penCrowded(r: Roamer, nx: number, ny: number): boolean {
    for (const o of this.pen) {
      if (o === r) continue;
      const d = (nx - o.x) ** 2 + (ny - o.y) ** 2;
      if (d < PEN_ROOM * PEN_ROOM && d < (r.x - o.x) ** 2 + (r.y - o.y) ** 2) return true;
    }
    return false;
  }

  private friendsUpdate(pipMoved: boolean): void {
    let retargets = 0;
    if (pipMoved) {
      this.trailI = (this.trailI + 1) & (TRAIL - 1);
      this.trailX[this.trailI] = this.pipX;
      this.trailY[this.trailI] = this.pipY;
    }
    const f = this.game.frame;
    this.pen.forEach((r, i) => {
      if (r.wait > 0) {
        r.wait--;
        return;
      }
      if (((f + i) & 1) === 0) {
        /* half a pixel a frame: a calm waddle */
        let nx = r.x + Math.sign(r.tx - r.x);
        let ny = r.y + Math.sign(r.ty - r.y);
        if (this.penCrowded(r, nx, ny) && nx !== r.x && !this.penCrowded(r, nx, r.y)) ny = r.y; /* sidestep */
        else if (this.penCrowded(r, nx, ny) && ny !== r.y && !this.penCrowded(r, r.x, ny)) nx = r.x;
        if (this.penCrowded(r, nx, ny)) {
          if (++r.stuck > 30 && retargets < PEN_RETARGETS) {
            retargets++; /* give way; find another spot if stuck */
            r.stuck = 0;
            this.penTarget(r);
          }
        } else {
          r.x = nx;
          r.y = ny;
          r.step++;
          r.stuck = 0;
        }
      }
      if (r.x === r.tx && r.y === r.ty && retargets < PEN_RETARGETS) {
        retargets++;
        r.wait = 60 + this.penRand(180);
        r.step = 0;
        this.penTarget(r);
      }
    });
  }

  followerPos(k: number): { x: number; y: number; hop: number } {
    const t = (this.trailI - (k + 1) * TRAIL_GAP) & (TRAIL - 1);
    let hop = this.walkT > 0 ? hopOf(this.walkT + k * 5) : 0;
    const jump = this.hopT >= 0 ? hopH(this.hopT - (k + 1) * HOP_LAG) : 0; /* hops after Pip */
    if (jump > hop) hop = jump;
    return { x: this.trailX[t], y: this.trailY[t], hop };
  }

  /** A tap on a friend: squeak, the squish frame, a hop and a heart. */
  private pokeFriend(kind: Poke, k: number): void {
    const id = kind === Poke.Follower ? this.followIds[k] : this.pen[k].id;
    const at = kind === Poke.Follower ? this.followerPos(k) : this.pen[k];
    this.poke = { t: 0, kind, k, x: at.x, y: at.y };
    if (kind === Poke.Pen && this.pen[k].wait < POKE_LEN) this.pen[k].wait = POKE_LEN; /* stands still for its squish */
    this.game.sound.squeak(friendFlavor(id));
    dbg(`poke friend ${id}`);
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
  private thingAt(x: number, y: number): { kind: Thing; i: number } | null {
    let best: { kind: Thing; i: number } | null = null, bd = Infinity;
    const consider = (kind: Thing, i: number, cx: number, cy: number, half: number) => {
      const d = Math.hypot(x - cx, y - cy);
      if (d <= this.zone(half) && d < bd) [best, bd] = [{ kind, i }, d];
    };
    consider('pip', 0, this.pipX, this.pipY - 12, 10);
    this.boxes.forEach((b, i) => {
      if (b.spot >= 0) consider('box', i, this.spotXY(b.spot)[0], this.spotXY(b.spot)[1] - 8, 8);
    });
    const arrow = this.arrowAt();
    if (arrow) consider('arrow', 0, arrow.x + this.camX, arrow.y + this.camY, 8);
    this.followIds.forEach((_, k) => {
      const f = this.followerPos(k);
      consider('follower', k, f.x, f.y - 8, 8);
    });
    this.pen.forEach((r, i) => consider('pen', i, r.x, r.y - 8, 8));
    for (const m of this.momos()) consider('momo', m.i, m.x, m.y - 14, 14);
    return best;
  }

  private onTouch(t: TouchEvt): void {
    const x = t.x + this.camX, y = t.y + this.camY;
    if (t.kind === 'down' && buttonHit(this.game, t.x, t.y)) {
      /* the shelf button (GBA START) */
      this.shelfPress = 8;
      this.dragCell = -2; /* this finger does not steer */
      this.game.sound.chime(2);
      dbg(`meadow shelf pip=${this.pipX},${this.pipY}`);
      this.posDirty = true;
      this.savePos(true);
      if (this.shelfScene) this.game.scenes.go(this.shelfScene());
      return;
    }
    if (t.kind === 'move' && this.dragCell === -2) return;
    if (t.kind === 'down') {
      this.dragT = 0;
      this.dragCell = -1;
      const hit = this.thingAt(x, y);
      if (hit?.kind === 'pip') {
        this.hop();
        return;
      }
      if (hit?.kind === 'box') {
        this.goToBox(hit.i);
        return;
      }
      if (hit?.kind === 'arrow') {
        dbg('tap arrow');
        this.goToBox(this.arrowBox);
        return;
      }
      if (hit?.kind === 'follower' || hit?.kind === 'pen') {
        this.pokeFriend(hit.kind === 'follower' ? Poke.Follower : Poke.Pen, hit.i);
        return;
      }
      if (hit?.kind === 'momo') {
        const m = this.momos().find((o) => o.i === hit.i)!;
        this.poke = { t: 0, kind: Poke.Momo, k: hit.i, x: m.x, y: m.y };
        this.game.sound.boing();
        dbg(`poke momo ${hit.i}`);
        return;
      }
      this.pendingBox = -1;
      this.walkTo(x, y);
      this.dragCell = Math.floor(y / this.A.cell) * this.A.cols + Math.floor(x / this.A.cell);
    } else if (t.kind === 'move') {
      const cell = Math.floor(y / this.A.cell) * this.A.cols + Math.floor(x / this.A.cell);
      if (cell !== this.dragCell && this.dragT >= RETARGET) {
        this.dragT = 0;
        this.dragCell = cell;
        this.pendingBox = -1;
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
    if (this.shelfPress > 0) this.shelfPress--;
    for (const t of touches) this.onTouch(t);
    if (this.hopT >= 0) {
      this.pipHop = hopH(this.hopT);
      if (++this.hopT > HOP_LEN + MAX_FOLLOWERS * HOP_LAG) {
        this.hopT = -1;
        this.pipHop = 0;
      }
    }
    if (this.poke.t >= 0 && ++this.poke.t > POKE_LEN) this.poke.t = -1;
    const wasX = this.px8, wasY = this.py8;
    if (this.followPath()) this.walkT++;
    else this.walkT = 0;
    this.friendsUpdate(this.px8 !== wasX || this.py8 !== wasY); /* the line follows real steps only */
    if (this.px8 !== wasX || this.py8 !== wasY) {
      this.stillT = 0;
      this.posDirty = true;
    } else if (this.stillT < POS_SAVE_WAIT) this.stillT++;
    this.savePos(false);
    this.updateCamera();
    if (!this.game.scenes.fading()) this.updateBoxes();
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

  private drawBoxes(): void {
    const art = this.game.art;
    const f = this.game.frame;
    const key = this.game.art.index.names.areas[this.A.index].key;
    this.boxes.forEach((b) => {
      if (b.spot < 0) return;
      const [bx, by] = this.spotXY(b.spot);
      const sx = bx - this.camX, sy = by - this.camY;
      const t = (f + b.phase) % 160;
      const hop = t < 16 ? idiv(isin(t * 2) * 3, 256) : 0; /* a small hop every few seconds */
      this.world.push({ depth: by, draw: (ctx) => art.draw(ctx, `cont16/${key}/${b.color}`, sx - 8, sy - 15 - hop) });
      this.shadow(by - 1, sx, sy);
      /* one gold twinkle walks round the box: small, medium, big, medium */
      const k = Math.floor((f + b.phase) / 24) % 6;
      const fr = Math.floor((f + b.phase) / 6) % 4;
      const tw = `twinkle/${fr === 3 ? 1 : fr}`;
      const sz = art.size(tw);
      this.ui.push((ctx) => art.draw(ctx, tw, sx + TWINKLE_AROUND[k][0] - (sz.w >> 1), sy + TWINKLE_AROUND[k][1] - (sz.h >> 1)));
    });
  }

  private drawFriends(): void {
    const art = this.game.art;
    const n = art.index.names;
    const keys = Object.keys(n.species);
    const sq = (id: number, kind: Poke, k: number, x: number, y: number, hop: number) => {
      let frame = 'idle';
      const p = this.poke;
      if (p.t >= 0 && p.kind === kind && p.k === k) {
        p.x = x;
        p.y = y;
        const t = p.t - POKE_SQUISH;
        if (t < 0) frame = 'squish';
        else if (t < 12) hop = idiv(t * (12 - t), 9);
      }
      const sx = x - this.camX, sy = y - this.camY;
      const name = `sq/${keys[friendSpecies(id)]}/${n.flavors[friendFlavor(id)]}/16/${frame}`;
      this.world.push({ depth: y, draw: (ctx) => art.draw(ctx, name, sx - 8, sy - 15 - hop) });
      this.shadow(y - 1, sx, sy);
    };
    this.pen.forEach((r, i) => sq(r.id, Poke.Pen, i, r.x, r.y, r.wait > 0 ? 0 : hopOf(r.step)));
    this.followIds.forEach((id, k) => {
      const f = this.followerPos(k);
      sq(id, Poke.Follower, k, f.x, f.y, f.hop);
    });
    const p = this.poke;
    if (p.t >= 4 && p.kind !== Poke.Momo) {
      const t = p.t - 4;
      if (!(t > 30 && t & 2)) {
        /* the heart floats up and blinks out */
        const wob = idiv(isin(t * 2) * 2, 256);
        const hx = p.x - this.camX - 4 + wob, hy = p.y - this.camY - 20 - 8 - idiv(t, 2);
        this.ui.push((ctx) => art.draw(ctx, 'heart8', hx, hy));
      }
    }
  }

  /** The guide arrow: over everything, blinking, from Pip toward the nearest box. */
  private drawArrow(ctx: CanvasRenderingContext2D): void {
    const a = this.arrowAt();
    if (!a) return;
    if (Math.floor(this.arrowT / ARROW_BLINK) & 1) return;
    this.game.art.draw(ctx, a.tile, a.x - 8, a.y - 8, { flipX: a.flipX, flipY: a.flipY });
  }

  /** The found counter, top right inside the safe area: the area's icon and "7/20". */
  private drawCounter(ctx: CanvasRenderingContext2D): void {
    const g = this.game;
    const n = g.collection.foundInArea(this.A.index);
    if (!n) return;
    let hop = 0;
    if (this.countHop > 0) {
      this.countHop--;
      const t = this.countHop % 20;
      if (this.countHop < 30) hop = idiv(t * (20 - t), 25); /* two small hops, after the fade-in */
    }
    const v = g.screen.view;
    const key = g.art.index.names.areas[this.A.index].key;
    const pillW = g.art.index.layout.countPillW as number;
    const x = v.w - v.safe.right - 4 - pillW, y = v.safe.top + 3 - hop;
    g.art.draw(ctx, `count_pill/${key}`, x, y);
    const txt = `${n}/20`;
    g.art.text(ctx, txt, x + COUNT_TEXT_X + ((32 - g.art.textWidth(txt)) >> 1), y + 5, '#8a5a7a');
  }

  /** Momo asleep on each shut gate, breathing slowly, z's drifting up.
   * A tap makes Momo giggle and hop (GBA poke). The heart meter is M6. */
  private drawMomos(): void {
    const art = this.game.art;
    const f = this.game.frame;
    for (const m of this.momos()) {
      let x = m.x, hop = 0;
      const p = this.poke;
      if (p.t >= 0 && p.kind === Poke.Momo && p.k === m.i && p.t < 24) {
        const t = p.t % 12; /* tickled: giggles and hops */
        hop = idiv(t * (12 - t), 6);
        x += (p.t / 3) & 1;
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
    this.drawBoxes();
    this.drawFriends();
    this.world.sort((a, b) => a.depth - b.depth).forEach((w) => w.draw(ctx));
    this.ui.forEach((d) => d(ctx));
    if (overlay) ctx.drawImage(overlay, -cx, -cy);
    this.drawArrow(ctx);
    this.drawCounter(ctx);
    drawButton(g, ctx, (bx, by) => g.art.draw(ctx, 'sq/bunny/strawberry/16/idle', bx - 8, by - 8), this.shelfPress / 8);
  }
}
