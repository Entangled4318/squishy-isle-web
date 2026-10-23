/* The Squishy Shelf, ported from the GBA shelf.c (v1.6): four pages (one
 * per area), 4 species x 5 flavors each. Touch (docs/PLAN.md step 2):
 * - a tap on an area tab turns to that page; a sideways swipe also turns;
 * - a tap on a found friend opens its close-up;
 * - a tap on a silhouette wiggles it, with "Find me!" in the name pill;
 * - the home button goes back to the map.
 * The pen sign's pick mode is M5. The bands round the shelf are the
 * plain wall (a mirrored shelf, or the tabs' edge rows, look odd). */
import { Game } from '../game';
import { Scene } from '../engine/scenes';
import { TouchEvt } from '../engine/input';
import { dbg } from '../engine/log';
import { SONG } from '../engine/audio';
import { idiv, isin } from '../engine/gba';
import { drawFixed, toFixed } from './backdrop';
import { BUTTON_ROOM, buttonHit, drawButton } from './button';
import { friendId } from '../rules/collection';

const INK = '#8a5a7a';
const SPARKS = ['spark/tiny', 'spark/small', 'spark/big'];
const TAB_X = 8; /* tab i at TAB_X + i * TAB_DX, 28 x 24 */
const TAB_DX = 30;
const SWIPE = 30; /* px sideways (screen pixels) that turn a page */

export class Shelf implements Scene {
  readonly name = 'shelf';
  page = 0;
  private pageArea = -1;
  private sel: [number, number] | null = null;
  private wiggle: { r: number; c: number; t: number } | null = null;
  private label = '';
  private swipe: { x: number; y: number; done: boolean } | null = null;
  private homePress = 0;

  constructor(
    private game: Game,
    private toMeadow: () => Scene,
    private toCloseup: (id: number) => Scene,
  ) {}

  private get L() {
    return this.game.art.index.layout.shelf as { x0: number; y0: number; cw: number; ch: number; cols: number; rows: number; pillW: number };
  }

  enter(): void {
    const g = this.game;
    for (let i = 0; i < 4; i++) void g.art.image(g.art.index.screens[`shelf${i}`]);
    g.sound.music(SONG.shelf); /* music box; the close-up keeps it */
    const area = g.collection.s.area;
    if (area !== this.pageArea) {
      this.page = area < 4 ? area : 0; /* after a walk to another area, start on its page */
      this.pageArea = area;
    }
    this.wiggle = null;
    this.homePress = 0;
    this.swipe = null;
    this.setLabel();
    dbg(`scene shelf page=${this.page}`);
  }

  private have(r: number, c: number): boolean {
    return this.game.collection.friendFound(friendId(this.page * 4 + r, c));
  }

  private setLabel(): void {
    const n = this.game.art.index.names;
    if (this.sel && this.have(...this.sel)) {
      const [r, c] = this.sel;
      this.label = `${n.flavorNames[c]} ${n.species[Object.keys(n.species)[this.page * 4 + r]]}`;
    } else this.label = n.areas[this.page].name;
  }

  private turn(to: number): void {
    if (to === this.page) return;
    this.page = (to + 4) & 3;
    this.sel = null;
    this.wiggle = null;
    this.game.sound.chime(this.page);
    this.setLabel();
    dbg(`shelf page=${this.page}`);
  }

  update(touches: TouchEvt[]): void {
    const g = this.game;
    if (this.homePress > 0) this.homePress--;
    if (this.wiggle && ++this.wiggle.t > 30) this.wiggle = null;
    for (const t of touches) {
      const p = toFixed(g, t.x, t.y, BUTTON_ROOM);
      if (t.kind === 'down') {
        this.swipe = { x: p.x, y: p.y, done: false };
        this.tap(t, p.x, p.y);
      } else if (t.kind === 'move' && this.swipe && !this.swipe.done) {
        const dx = p.x - this.swipe.x, dy = p.y - this.swipe.y;
        if (Math.abs(dx) > SWIPE && Math.abs(dx) > Math.abs(dy) * 1.5) {
          this.swipe.done = true;
          this.turn(this.page + (dx < 0 ? 1 : -1));
        }
      } else if (t.kind === 'up') this.swipe = null;
    }
  }

  private tap(t: TouchEvt, x: number, y: number): void {
    const g = this.game;
    if (g.scenes.fading()) return;
    if (buttonHit(g, t.x, t.y)) {
      this.homePress = 8;
      g.sound.chime(2);
      dbg('shelf home');
      g.scenes.go(this.toMeadow());
      return;
    }
    const v = g.screen.view;
    const zone = (32 * v.dpr) / v.k; /* 32 points, in view pixels (about the same in screen pixels) */
    for (let i = 0; i < 4; i++) {
      const cx = TAB_X + i * TAB_DX + 14;
      if (Math.abs(x - cx) <= Math.max(14, zone / 2) && y <= 24 + 4) {
        this.turn(i);
        return;
      }
    }
    const L = this.L;
    const c = Math.floor((x - L.x0) / L.cw), r = Math.floor((y - L.y0) / L.ch);
    if (c < 0 || c >= L.cols || r < 0 || r >= L.rows) return; /* the wall: a sparkle only */
    if (this.have(r, c)) {
      this.sel = [r, c];
      this.setLabel();
      g.sound.squeak(c);
      const id = friendId(this.page * 4 + r, c);
      dbg(`shelf open ${id}`);
      g.scenes.go(this.toCloseup(id));
    } else {
      this.sel = null;
      this.wiggle = { r, c, t: 0 };
      this.label = 'Find me!';
      g.sound.blip();
      dbg(`shelf find me ${friendId(this.page * 4 + r, c)}`);
    }
  }

  draw(ctx: CanvasRenderingContext2D): void {
    const g = this.game;
    const art = g.art;
    const f = g.frame;
    const L = this.L;
    const n = art.index.names;
    const keys = Object.keys(n.species);
    drawFixed(
      g,
      ctx,
      art.cached(art.index.screens[`shelf${this.page}`]),
      () => {
        const bob = idiv(isin(f * 2) * 2, 256);
        for (let r = 0; r < 4; r++)
          for (let c = 0; c < 5; c++) {
            const sp = keys[this.page * 4 + r];
            const have = this.have(r, c);
            const sel = !!this.sel && this.sel[0] === r && this.sel[1] === c && have;
            let x = L.x0 + c * L.cw + ((L.cw - 32) >> 1);
            let y = L.y0 + r * L.ch + L.ch - 4 - 31;
            if (sel) y -= 2 + Math.max(0, bob);
            const w = this.wiggle;
            if (w && w.r === r && w.c === c) x += Math.round(Math.sin(w.t * 0.9) * 2 * (1 - w.t / 30));
            art.draw(ctx, have ? `sq/${sp}/${n.flavors[c]}/32/${sel ? 'open' : 'idle'}` : `sq/${sp}/sil/32`, x, y);
            if (c === 4 && have) {
              /* sparkle friends twinkle */
              const ph = (f + r * 17) % 72;
              const k = ph < 8 ? 0 : ph < 16 ? 1 : ph < 24 ? 2 : ph < 32 ? 1 : ph < 40 ? 0 : -1;
              if (k >= 0) {
                const s = art.size(SPARKS[k]);
                art.draw(ctx, SPARKS[k], x + 28 - (s.w >> 1), y + 8 - (s.h >> 1));
              }
            }
          }
        if (this.sel) art.draw(ctx, 'frame', L.x0 + this.sel[1] * L.cw - 1, L.y0 + this.sel[0] * L.ch - 1);
        const px = 232 - L.pillW;
        art.text(ctx, this.label, px + ((L.pillW - art.textWidth(this.label)) >> 1), 7, INK);
      },
      0,
      BUTTON_ROOM,
      true,
    );
    drawButton(g, ctx, 'home', this.homePress / 8);
  }
}

