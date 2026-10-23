/* Close-up and reveal, ported from the GBA closeup.c (v1.6): one friend big
 * on the cushion, its name below.
 * - Reveal (after a container pops): the friend drops in, lands with
 *   confetti and a star burst; a tap anywhere squishes; after 3 squishes or
 *   5 s of calm it hops up and away, back to the map.
 * - Close-up (from the shelf): a tap on the friend squishes; 3 squishes go
 *   back to the shelf, and the third close-up in a row ended that way goes
 *   to the map (GBA 9.3), so a child tapping only the friend still plays.
 *   A tap away from the friend (or the home button) goes back. */
import { Game } from '../game';
import { Scene } from '../engine/scenes';
import { TouchEvt } from '../engine/input';
import { dbg } from '../engine/log';
import { SONG } from '../engine/audio';
import { idiv, isin } from '../engine/gba';
import { drawFixed, toFixed } from './backdrop';
import { friendFlavor, friendSpecies } from '../rules/collection';

const N_CONF = 24;
const N_STARS = 6;
const DROP_H = 150; /* the friend starts this far above the cushion */
const REVEAL_WAIT = 300; /* 5 s without a squish, then it hops away */
const SQUISHES = 3;
const CX = 120;
const FLOOR = 121;
const BOTTOM = 29; /* texture rows from the middle to the friend's bottom */
const HEART_OFF = -1000;
const STREAK_HOME = 3;
const SHADOW_ALPHA = 6 / 16;
const INK = '#8a5a7a';
const SPARKS = ['spark/tiny', 'spark/small', 'spark/big'];
const FLAVOR_SPARKLE = 4;

interface Confetti {
  x: number;
  y: number;
  vx: number;
  vy: number;
  tile: number;
  flip: number;
}

export class Closeup implements Scene {
  name = 'closeup';
  /** the friend shown */
  friend = 0;
  private reveal = false;
  private squishT = -1;
  private bounceT = -1;
  private blinkT = 90;
  private idleT = 0;
  private hearts: { t: number; x: number; y: number }[] = [];
  private dropY = 0;
  private dropV = 0;
  landedT = -1;
  squishes = 0;
  private calmT = 0;
  leaveT = -1;
  private conf: Confetti[] = [];
  private static streak = 0;
  private label = '';
  private sprite = '';

  constructor(
    private game: Game,
    private toMeadow: () => Scene,
    private toShelf: () => Scene = toMeadow,
  ) {}

  /** The map resets the close-up streak (GBA viewer enter). */
  static resetStreak(): void {
    Closeup.streak = 0;
  }

  /** Sets what the next enter() shows. */
  show(friend: number, reveal: boolean): this {
    this.friend = friend;
    this.reveal = reveal;
    this.name = reveal ? 'reveal' : 'closeup';
    return this;
  }

  enter(): void {
    const g = this.game;
    const n = g.art.index.names;
    const sp = Object.keys(n.species)[friendSpecies(this.friend)];
    const fl = friendFlavor(this.friend);
    this.label = `${n.flavorNames[fl]} ${n.species[sp]}`;
    this.sprite = `sq/${sp}/${n.flavors[fl]}/64`;
    void g.art.image(g.art.index.screens.closeup);
    this.leaveT = -1;
    this.squishes = this.calmT = 0;
    if (this.reveal) {
      this.dropY = DROP_H << 8;
      this.dropV = 0;
      this.landedT = -1;
    } else this.landedT = 0;
    this.conf = [];
    this.squishT = -1;
    this.bounceT = this.reveal ? -1 : 0; /* arrive with a little bounce */
    this.blinkT = 90;
    this.idleT = 0;
    this.hearts = [0, 1, 2].map(() => ({ t: HEART_OFF, x: 0, y: 0 }));
    dbg(`scene ${this.name} ${this.label}`);
  }

  private spawnHearts(): void {
    const dx = [-30, 26, -6];
    this.hearts = dx.map((d, i) => ({ t: -i * 5, x: CX + d, y: 72 - i * 6 }));
  }

  /** confetti rains gently from the top, behind the friend */
  private spawnConfetti(): void {
    const c = this.game.collection;
    this.conf = [];
    for (let i = 0; i < N_CONF; i++) {
      const r = c.rand();
      this.conf.push({
        x: (4 + (r % 224)) << 8,
        y: -(8 + ((r >>> 8) % 90)) << 8,
        vx: ((r >>> 16) % 64) - 32,
        vy: 160 + ((r >>> 20) % 160),
        tile: i % 12,
        flip: (r >>> 24) & 3,
      });
    }
  }

  private squish(): void {
    this.squishT = 0;
    this.idleT = 0;
    this.game.sound.squeak(friendFlavor(this.friend));
    this.spawnHearts();
  }

  update(touches: TouchEvt[]): void {
    const g = this.game;
    const tap = touches.find((t) => t.kind === 'down');
    this.animate();
    if (this.reveal) {
      if (this.landedT < 0) {
        this.dropV += 60; /* gravity */
        this.dropY -= this.dropV;
        if (this.dropY <= 0) {
          this.dropY = 0;
          this.landedT = 0;
          this.bounceT = 0; /* happy bounce on landing */
          g.sound.squeak(friendFlavor(this.friend));
          g.sound.music(SONG.reveal); /* plays once */
          this.spawnConfetti();
          dbg('reveal landed');
        }
      } else if (this.leaveT >= 0) {
        if (++this.leaveT >= 30) g.scenes.go(this.toMeadow());
      } else {
        this.landedT++;
        this.calmT++;
        if (tap && this.landedT > 20 && this.squishes < SQUISHES) {
          this.squish();
          this.squishes++;
          this.calmT = 0;
          dbg(`reveal squish ${this.squishes}`);
        }
        const done = this.squishes >= SQUISHES && this.squishT < 0 && this.calmT > 40;
        if (done || this.calmT > REVEAL_WAIT) {
          this.leaveT = 0;
          g.sound.boing();
          dbg(`reveal leave (${done ? 'squished' : 'waited'})`);
        }
      }
      return;
    }
    this.calmT++;
    if (tap) {
      const p = toFixed(g, tap.x, tap.y);
      const v = g.screen.view;
      const r = Math.max(34, (32 * v.dpr) / v.k); /* the friend, or 32 points round it */
      if (Math.hypot(p.x - CX, p.y - (FLOOR - BOTTOM)) <= r) {
        if (this.squishes < SQUISHES) {
          this.squish();
          this.squishes++;
          this.calmT = 0;
          dbg(`closeup squish ${this.squishes}`);
        }
      } else {
        Closeup.streak = 0;
        g.sound.blip();
        dbg('closeup back');
        g.scenes.go(this.toShelf());
        return;
      }
    }
    const done = this.squishes >= SQUISHES && this.squishT < 0 && this.calmT > 30;
    if (done && !g.scenes.fading()) {
      if (++Closeup.streak >= STREAK_HOME) {
        /* tapping only the friend: shelf, close-up, shelf... would never end. Go play. */
        Closeup.streak = 0;
        g.sound.boing();
        dbg('closeup streak: back to the map');
        g.scenes.go(this.toMeadow());
      } else {
        g.sound.blip();
        g.scenes.go(this.toShelf());
      }
      this.squishes = 0; /* asks once */
    }
  }

  /** The fixed-step parts of the GBA draw(): blink, bounce, squish, hearts, confetti. */
  private animate(): void {
    const f = this.game.frame;
    if (--this.blinkT < 0) this.blinkT = 150 + (f % 60);
    if (this.bounceT >= 0 && ++this.bounceT > 16) this.bounceT = -1;
    if (this.squishT >= 0 && ++this.squishT > 24) this.squishT = -1;
    if (this.squishT < 0 && this.bounceT < 0 && ++this.idleT > 240) {
      this.idleT = 0; /* every few seconds of calm, a small happy hop */
      this.bounceT = 0;
    }
    for (const h of this.hearts) if (h.t !== HEART_OFF && ++h.t > 44) h.t = HEART_OFF;
    for (const c of this.conf) {
      if (c.tile < 0) continue;
      c.x += c.vx;
      c.y += c.vy;
      if (c.y >> 8 > 160) c.tile = -1;
    }
  }

  draw(ctx: CanvasRenderingContext2D): void {
    const g = this.game;
    drawFixed(g, ctx, g.art.cached(g.art.index.screens.closeup), () => this.drawFriend(ctx), 132); /* the name pill starts below */
  }

  private drawFriend(ctx: CanvasRenderingContext2D): void {
    const art = this.game.art;
    const f = this.game.frame;
    let sx = 256, sy = 256, lift = 0, frame = 'idle';
    const b = isin(f);
    sy += idiv(b, 40);
    sx -= idiv(b, 56);
    if (this.blinkT < 6) frame = 'blink';
    if (this.bounceT >= 0) {
      lift = idiv(14 * isin(this.bounceT * 2), 256);
      frame = 'open';
    }
    if (this.squishT >= 0) {
      if (this.squishT < 7) frame = 'squish';
      else {
        const k = this.squishT - 7;
        const amp = Math.max(0, 44 - k * 3);
        const w = isin(k * 9);
        sy = 256 + idiv(amp * w, 256);
        sx = 256 - idiv(amp * w, 512);
        frame = 'open';
      }
    }
    if (this.reveal && this.landedT < 0) {
      lift = this.dropY >> 8; /* falling in, stretched */
      frame = 'open';
      sx = 230;
      sy = 290;
    }
    if (this.leaveT >= 0) {
      lift = this.leaveT * 7; /* hop up and away */
      frame = 'open';
      sx = 236;
      sy = 280;
    }
    const bottom = FLOOR - lift;
    const cy = bottom - idiv(BOTTOM * sy, 256);
    if (this.reveal) this.drawConfetti(ctx);
    if (lift <= 60) {
      ctx.globalAlpha = SHADOW_ALPHA;
      art.draw(ctx, 'shadow64', CX - 32, FLOOR);
      ctx.globalAlpha = 1;
    }
    art.drawAffine(ctx, `${this.sprite}/${frame}`, CX, cy, 0, sx / 256, sy / 256);
    for (let i = 0; i < 3; i++) {
      const h = this.hearts[i];
      if (h.t === HEART_OFF || h.t < 0) continue;
      art.draw(ctx, 'heart8', h.x + idiv(isin(h.t * 3 + i * 20) * 4, 256), h.y - h.t);
    }
    if (friendFlavor(this.friend) === FLAVOR_SPARKLE) {
      const tw: [number, number][] = [
        [-34, -30],
        [30, -18],
        [-22, 6],
      ];
      tw.forEach(([dx, dy], i) => {
        const ph = (f + i * 23) % 60;
        const k = ph < 10 ? 0 : ph < 20 ? 1 : ph < 30 ? 2 : ph < 40 ? 1 : ph < 48 ? 0 : -1;
        if (k < 0) return;
        const s = art.size(SPARKS[k]);
        art.draw(ctx, SPARKS[k], CX + dx - (s.w >> 1), cy + dy - (s.h >> 1));
      });
    }
    if (this.reveal) this.drawStars(ctx, cy);
    art.text(ctx, this.label, CX - (art.textWidth(this.label) >> 1), 145, INK);
  }

  private drawConfetti(ctx: CanvasRenderingContext2D): void {
    const art = this.game.art;
    const f = this.game.frame;
    this.conf.forEach((c, i) => {
      if (c.tile < 0) return;
      const x = (c.x >> 8) + idiv(isin(f * 2 + i * 7) * 3, 256), y = c.y >> 8;
      if (y < -8) return;
      art.draw(ctx, `confetti/${c.tile}`, x, y, { flipX: (c.flip & 1) !== 0, flipY: (c.flip & 2) !== 0 });
    });
  }

  /** big stars fly out in a ring when the friend lands */
  private drawStars(ctx: CanvasRenderingContext2D, cy: number): void {
    const art = this.game.art;
    for (let i = 0; i < N_STARS; i++) {
      if (this.landedT < 0 || this.landedT > 36 + i * 2) continue;
      const r = 20 + this.landedT * 2;
      const a = idiv(i * 64, N_STARS) + 5;
      const x = CX + idiv(isin(a + 16) * r, 256), y = cy + idiv(isin(a) * r * 2, 3 * 256);
      art.draw(ctx, 'star16', x - 6, y - 6);
    }
  }
}
