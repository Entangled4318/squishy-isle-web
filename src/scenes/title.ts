/* The title, ported from the GBA title.c (v1.6): the logo letters drop in
 * and bounce, four friends hop on the island, Pip stands in the middle,
 * and twinkles shine. Touch rules (docs/PLAN.md step 2): a tap anywhere
 * plays. The button is "Play" on a new save and "Continue" when the save
 * has friends; there is no "New game" here (the grown-up page does that).
 *
 * Sound can start only on a touch, so the first tap of a visit plays the
 * hello jingle and starts the title song (and the letters hop); the game
 * starts on the next tap. A tap during the letter drop ends the drop. */
import { Game, BUILD } from '../game';
import { Scene } from '../engine/scenes';
import { TouchEvt } from '../engine/input';
import { dbg } from '../engine/log';
import { SONG } from '../engine/audio';
import { idiv, isin } from '../engine/gba';
import { drawFixed } from './backdrop';

const LETTER_GAP = 8; /* frames between letters dropping in */
const DROP_FROM = 90; /* px above the letter's place */
const MENU_WAIT = 10; /* frames after the drop before a tap plays */
const INK = '#8a5a7a'; /* ui_ink */
const WHITE = '#ffffff';

/* species, flavor, x, y (GBA: frog, bunny, whale, star) */
const CAST: [number, number, number, number][] = [
  [4, 0, 32, 100],
  [0, 1, 68, 94],
  [8, 2, 140, 94],
  [13, 4, 176, 98],
];
const TWINKLES: [number, number][] = [
  [202, 92],
  [64, 88],
  [196, 18],
  [34, 30],
  [180, 66],
  [56, 60],
];
const SPARKS = ['spark/tiny', 'spark/small', 'spark/big'];

export class Title implements Scene {
  readonly name = 'title';
  private intro = true;
  private t = 0;
  private menuWait = 0;
  /** the hello jingle has played on this visit (it needs a touch first) */
  private hello = false;
  private ly: number[] = [];
  private lv: number[] = [];
  private landed: boolean[] = [];
  private hopWho = 0;
  private hopT = -1;
  private cast: string[] = [];

  constructor(
    private game: Game,
    private next: () => Scene,
    private onNewGame: () => void = () => {},
  ) {}

  private get bg(): string {
    return this.game.art.index.screens.title;
  }

  enter(): void {
    const g = this.game;
    void g.art.image(this.bg);
    const names = Object.keys(g.art.index.names.species);
    const flavors = g.art.index.names.flavors;
    this.cast = CAST.map(([sp, fl]) => `sq/${names[sp]}/${flavors[fl]}/32`);
    const n = g.art.index.logo.length;
    this.ly = new Array<number>(n).fill(DROP_FROM << 8);
    this.lv = new Array<number>(n).fill(0);
    this.landed = new Array<boolean>(n).fill(false);
    this.intro = true;
    this.t = 0;
    this.hopT = -1;
    this.hello = false;
    dbg(`scene title found=${g.collection.foundTotal()}`);
  }

  /** byTap: a touch came first, so sound had its chance to start. Without a
   * touch the jingle is dropped, and the next tap says hello again. A tap
   * always counts as the hello, so a device with no sound still plays. */
  private sayHello(byTap: boolean): void {
    const s = this.game.sound;
    s.jingle('hello');
    s.music(SONG.title); /* starts when the hello jingle ends */
    this.hello = byTap || s.ctx !== null;
  }

  private finishIntro(byTap: boolean): void {
    this.ly.fill(0);
    this.lv.fill(0);
    this.landed.fill(true);
    this.sayHello(byTap);
    dbg(`title intro done at ${this.t} hello=${this.hello}`);
    this.intro = false;
    this.menuWait = MENU_WAIT;
  }

  private startGame(): void {
    const g = this.game;
    const c = g.collection;
    const fresh = c.foundTotal() === 0;
    if (fresh) {
      c.newGame((Math.imul(g.frame, 2654435761) ^ c.s.rng ^ (c.s.boots << 16)) >>> 0);
      this.onNewGame();
    }
    dbg(`title start ${fresh ? 'new' : 'continue'}`);
    g.sound.chime(4);
    g.sound.stopMusic();
    g.scenes.go(this.next());
  }

  update(touches: TouchEvt[]): void {
    this.t++;
    const tap = touches.some((t) => t.kind === 'down');
    if (this.intro) {
      if (tap) this.finishIntro(true);
    } else if (this.menuWait > 0) {
      this.menuWait--;
    } else if (tap) {
      if (this.hello) this.startGame();
      else {
        /* the first tap of the visit: hello, and the letters hop */
        this.sayHello(true);
        dbg(`title hello at ${this.t}`);
        this.lv.forEach((_, i) => (this.lv[i] = -(700 + (i & 1) * 200)));
        this.menuWait = MENU_WAIT;
      }
    }
    this.updateLetters();
    if (this.intro && this.t > this.ly.length * LETTER_GAP + 40) this.finishIntro(false);
    const f = this.game.frame;
    if (this.hopT < 0 && f % 90 === 0) {
      this.hopWho = Math.floor(f / 90) * 3 % 4; /* not the save's random numbers */
      this.hopT = 0;
    }
    if (this.hopT >= 0 && ++this.hopT > 16) this.hopT = -1;
  }

  private updateLetters(): void {
    const { ly, lv, landed } = this;
    for (let i = 0; i < ly.length; i++) {
      if (this.intro && this.t < i * LETTER_GAP) continue;
      if (landed[i] && ly[i] === 0 && lv[i] === 0) continue;
      lv[i] += 80; /* gravity, 8.8 */
      ly[i] -= lv[i];
      if (ly[i] <= 0) {
        /* bounce, smaller each time */
        ly[i] = 0;
        if (!landed[i]) {
          landed[i] = true;
          this.game.sound.chime(i % 5);
        }
        lv[i] = lv[i] > 500 ? idiv(-lv[i] * 2, 5) : 0;
      }
    }
  }

  draw(ctx: CanvasRenderingContext2D): void {
    const g = this.game;
    const art = g.art;
    const f = g.frame;
    drawFixed(g, ctx, art.cached(this.bg), () => {
      /* twinkles */
      TWINKLES.forEach(([x, y], i) => {
        const ph = (f + i * 17) % 50;
        const k = ph < 8 ? 0 : ph < 16 ? 1 : ph < 24 ? 2 : ph < 32 ? 1 : ph < 40 ? 0 : -1;
        if (k < 0) return;
        const s = art.size(SPARKS[k]);
        art.draw(ctx, SPARKS[k], x + idiv(8 - s.w, 2), y + idiv(8 - s.h, 2));
      });
      /* Pip, then the friends, one hopping at a time */
      art.draw(ctx, 'pip/down0', 112, 99);
      CAST.forEach(([, , x, y], i) => {
        const hop = i === this.hopWho && this.hopT >= 0;
        const lift = hop ? idiv(isin(this.hopT * 2) * 8, 256) : 0;
        art.draw(ctx, `${this.cast[i]}/${hop ? 'open' : 'idle'}`, x, y - lift);
      });
      /* the logo letters */
      art.index.logo.forEach((e, i) => {
        if (this.intro && this.t < i * LETTER_GAP) return;
        const bob = !this.intro && this.ly[i] === 0 ? idiv(isin(f + i * 6) * 3, 2 * 256) : 0;
        art.draw(ctx, e.sprite, e.x, e.y - (this.ly[i] >> 8) + bob);
      });
      if (!this.intro) this.drawButton(ctx);
      const ver = BUILD.split(' ').slice(0, 2).join(' '); /* version and commit */
      art.text(ctx, ver, 120 - idiv(art.textWidth(ver), 2), 153, INK); /* on the island, for a grown-up */
    });
  }

  /** "Play" or "Continue" in white with an ink edge, a heart bobbing each side. */
  private drawButton(ctx: CanvasRenderingContext2D): void {
    const art = this.game.art;
    const txt = this.game.collection.foundTotal() > 0 ? 'Continue' : 'Play';
    const half = idiv(art.textWidth(txt), 2);
    const bob = idiv(isin(this.game.frame * 2) * 2, 256);
    art.textOutlined(ctx, txt, 120 - half, 140, WHITE, INK);
    art.draw(ctx, 'openui/heart_on', 120 - half - 20 + bob + 1, 138 + 1);
    art.draw(ctx, 'openui/heart_on', 120 + half + 5 - bob + 1, 138 + 1);
  }
}
