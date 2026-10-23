/* The open screen, ported from the GBA open.c (v1.6): the container from
 * the map sits big on a cushion. Each tap anywhere makes it jump higher
 * with a rising note; the third tap pops the lid off and sparkles burst
 * out. With no tap, it starts pressing itself after 4 s, so nobody is ever
 * stuck. The GBA's big A button is left out: three hearts fill instead. */
import { Game } from '../game';
import { Scene } from '../engine/scenes';
import { TouchEvt } from '../engine/input';
import { dbg } from '../engine/log';
import { SONG } from '../engine/audio';
import { idiv, isin } from '../engine/gba';
import { drawFixed } from './backdrop';
import type { OpenInfo } from './meadow';

const CX = 120;
const FLOOR = 121; /* cushion top where the box stands */
const BOX_BASE = 61; /* box bottom row inside its 64x64 art */
const PRESSES = 3;
const AUTO_WAIT = 240; /* 4 s without a press, then it opens by itself */
const AUTO_STEP = 70; /* then one self-press every ~1.2 s */
const COOLDOWN = 14; /* frames between counted presses */
const POP_TIME = 70; /* frames after the pop before moving on */
const SHADOW_ALPHA = 6 / 16; /* the GBA blend on this screen */
const SPARKS = ['spark/tiny', 'spark/small', 'spark/big'];

export class Open implements Scene {
  readonly name = 'open';
  private info: OpenInfo = { area: 0, color: 0, friend: -1 };
  private presses = 0;
  private idleT = 0;
  private cool = 0;
  private jumpT = -1;
  private jumpH = 0;
  private landT = 0;
  popT = -1;
  private pressAnim = 0;
  private lid = { x: 0, y: 0, vx: 0, vy: 0, spin: 0 }; /* 8.8 fixed while flying */
  private key = 'meadow';

  constructor(
    private game: Game,
    private getInfo: () => OpenInfo,
    private reveal: () => Scene,
    private meadow: () => Scene,
  ) {}

  enter(): void {
    const g = this.game;
    this.info = { ...this.getInfo() };
    this.key = g.art.index.names.areas[this.info.area]?.key ?? 'meadow';
    void g.art.image(g.art.index.screens.open);
    g.sound.music(SONG.open);
    this.presses = this.idleT = this.cool = this.landT = this.pressAnim = 0;
    this.jumpT = -1;
    this.popT = -1;
    dbg(`scene open color ${this.info.color} friend ${this.info.friend} area ${this.info.area}`);
  }

  private press(byChild: boolean): void {
    const g = this.game;
    this.presses++;
    this.cool = COOLDOWN;
    this.idleT = 0;
    this.pressAnim = 8;
    dbg(`open press ${this.presses}${byChild ? '' : ' (auto)'}`);
    if (this.presses < PRESSES) {
      this.jumpT = 0;
      this.jumpH = this.presses === 1 ? 10 : 18;
      g.sound.chime(this.presses === 1 ? 0 : 2);
      g.sound.boing();
      return;
    }
    /* pop: the lid flies up and off, sparkles burst out */
    this.popT = 0;
    this.jumpT = -1;
    this.lid = { x: CX << 8, y: (FLOOR - BOX_BASE + 32) << 8, vx: g.frame & 1 ? 300 : -300, vy: -6 * 256, spin: 0 };
    g.sound.pop();
    g.sound.jingle('pop');
    if (this.info.friend >= 0) g.collection.add(this.info.friend); /* saves */
    dbg(`open pop friend ${this.info.friend} found ${g.collection.foundTotal()}`);
    g.sound.stopMusic(); /* the ta-da jingle already holds the wave channel */
  }

  update(touches: TouchEvt[]): void {
    const tap = touches.some((t) => t.kind === 'down');
    if (this.cool > 0) this.cool--;
    if (this.pressAnim > 0) this.pressAnim--;
    if (this.popT < 0) {
      this.idleT++;
      if (tap && this.cool === 0) this.press(true);
      else if (this.idleT >= AUTO_WAIT && this.cool === 0 && (this.idleT - AUTO_WAIT) % AUTO_STEP === 0) {
        this.press(false);
        this.idleT = AUTO_WAIT + 1; /* keep pressing by itself at the same pace */
      }
    }
    if (this.jumpT >= 0 && ++this.jumpT > 22) {
      this.jumpT = -1;
      this.landT = 6;
    } else if (this.landT > 0) this.landT--;
    if (this.popT >= 0) {
      this.popT++;
      const l = this.lid;
      l.x += l.vx;
      l.y += l.vy;
      l.vy += 40;
      l.spin += l.vx > 0 ? 900 : -900;
      if (this.popT >= POP_TIME) this.game.scenes.go(this.info.friend >= 0 ? this.reveal() : this.meadow());
    }
  }

  draw(ctx: CanvasRenderingContext2D): void {
    const g = this.game;
    drawFixed(g, ctx, g.art.cached(g.art.index.screens.open), () => {
      this.drawBox(ctx);
      this.drawLidAndBurst(ctx);
      this.drawHud(ctx);
    });
  }

  private drawBox(ctx: CanvasRenderingContext2D): void {
    const art = this.game.art;
    const f = this.game.frame;
    let lift = 0, sx = 256, sy = 256;
    if (this.jumpT >= 0) {
      lift = idiv(this.jumpH * isin(idiv(this.jumpT * 32, 22)), 256); /* half sine over 22 frames */
      sx = 256 - lift; /* stretch up while flying */
      sy = 256 + lift * 2;
    } else if (this.landT > 0) {
      sx = 256 + this.landT * 6; /* squash on landing */
      sy = 256 - this.landT * 6;
    }
    const opened = this.popT >= 0;
    const amp = opened ? 0 : 5 + this.presses * 5 + (this.idleT > 120 ? 3 : 0); /* wobble grows with presses and waiting */
    const tilt = idiv(amp * isin(f * (3 + this.presses)), 256); /* 1/256 turn */
    if (opened && this.popT < 12) {
      sx = 256 + (12 - this.popT) * 5; /* the body settles after the pop */
      sy = 256 - (12 - this.popT) * 5;
    }
    const base = FLOOR - lift;
    const cy = base - idiv((BOX_BASE - 32) * sy, 256);
    const cx = CX + idiv(tilt * (BOX_BASE - 32) * 6, 256); /* rotate about the bottom, roughly */
    /* the shadow shrinks as the box rises */
    const sw = 64 - lift;
    ctx.globalAlpha = SHADOW_ALPHA;
    art.draw(ctx, 'shadow64', CX - sw / 2, FLOOR, { sx: sw / 64 });
    ctx.globalAlpha = 1;
    const name = `cont64/${this.key}/${this.info.color}`;
    art.drawAffine(ctx, `${name}/${opened ? 'open' : 'body'}`, cx, cy, tilt, sx / 256, sy / 256);
    if (!opened) art.drawAffine(ctx, `${name}/lid`, cx, cy, tilt, sx / 256, sy / 256); /* the lid rides along, in front */
    if (!opened && (tilt > 6 || tilt < -6)) {
      /* motion arcs beside the box while it wobbles hard */
      const side = tilt > 0 ? 1 : -1;
      for (let k = 0; k < 2; k++) art.draw(ctx, 'openui/arc', CX + side * (40 + k * 4) - 2, cy - 20 + k * 12, { flipX: side > 0 });
    }
  }

  private drawLidAndBurst(ctx: CanvasRenderingContext2D): void {
    if (this.popT < 0) return;
    const art = this.game.art;
    const l = this.lid;
    const t = this.popT;
    if (l.y < (160 + 40) << 8 && l.y > -(64 << 8)) art.drawAffine(ctx, `cont64/${this.key}/${this.info.color}/lid`, l.x / 256, l.y / 256, l.spin >> 8, 1, 1);
    /* sparkles fly out of the box in a ring, then twinkle away */
    const r = t < 30 ? t * 2 + 10 : 70;
    for (let k = 0; k < 10; k++) {
      if (t > 40 + k * 2) continue;
      const a = idiv(k * 64, 10) + 3;
      const x = CX + idiv(isin(a + 16) * r, 256), y = FLOOR - 30 + idiv(isin(a) * r * 3, 4 * 256);
      const sp = SPARKS[t < 14 ? 2 : t < 30 ? 1 : 0];
      const s = art.size(sp);
      art.draw(ctx, sp, x - (s.w >> 1), y - (s.h >> 1));
    }
    /* soft puffs on the cushion */
    if (t < 30)
      for (let k = 0; k < 2; k++) art.draw(ctx, 'openui/puff', CX - 4 + (k ? 1 : -1) * (30 + idiv(t, 2)), FLOOR - 4 - idiv(t, 6), { flipX: k === 1 });
  }

  private drawHud(ctx: CanvasRenderingContext2D): void {
    if (this.popT >= 0) return;
    const art = this.game.art;
    /* three hearts fill up, one per press; the next one bobs while waiting */
    const bob = this.pressAnim ? 0 : isin(this.game.frame * 2) > 180 ? -2 : 0;
    for (let i = 0; i < PRESSES; i++) {
      const on = i < this.presses;
      const name = on ? 'openui/heart_on' : 'openui/heart_off';
      const s = art.size(name);
      art.draw(ctx, name, CX - 27 + i * 18 + 9 - (s.w >> 1), 137 + 8 - (s.h >> 1) + (i === this.presses ? bob : 0));
    }
  }
}
