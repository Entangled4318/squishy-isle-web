/* The sound test (?sound), like the GBA's hidden one: the 8 songs and the
 * effects. A grown-up page: tap a row. */
import { Game } from '../game';
import { Scene } from '../engine/scenes';
import { TouchEvt } from '../engine/input';
import { dbg } from '../engine/log';

const SONGS = ['Title: Hello island', 'Meadow: Sleepy clover', "Open: What's inside?", 'Reveal: New friend!', 'Shelf: Music box', 'Shore: Sea breeze', 'Woods: Acorn trail', 'Cloud Hill: Floating up'];
const EFFECTS = ['jingle', 'ta-da', 'chime', 'squeak', 'boing', 'hop', 'pop', 'stop'] as const;
const ROW = 12;

export class SoundTest implements Scene {
  readonly name = 'soundtest';
  playing = -1;
  private chime = 0;
  private squeak = 0;

  constructor(private game: Game) {}

  enter(): void {
    this.playing = -1;
  }

  update(touches: TouchEvt[]): void {
    const g = this.game;
    const v = g.screen.view;
    const top = v.safe.top + 16;
    for (const e of touches) {
      if (e.kind !== 'down') continue;
      const row = Math.floor((e.y - top) / ROW);
      const right = e.x > v.w / 2;
      if (!right && row >= 0 && row < SONGS.length) {
        this.playing = row;
        g.sound.musicFromStart(row);
        dbg(`soundtest song ${row}`);
      } else if (right && row >= 0 && row < EFFECTS.length) {
        const fx = EFFECTS[row];
        dbg(`soundtest fx ${fx}`);
        if (fx === 'jingle') g.sound.jingle('hello');
        else if (fx === 'ta-da') g.sound.jingle('pop');
        else if (fx === 'chime') g.sound.chime(this.chime++ % 5);
        else if (fx === 'squeak') g.sound.squeak(this.squeak++ % 5);
        else if (fx === 'boing') g.sound.boing();
        else if (fx === 'hop') g.sound.hop();
        else if (fx === 'pop') g.sound.pop();
        else {
          g.sound.stopMusic();
          this.playing = -1;
        }
      }
    }
  }

  draw(ctx: CanvasRenderingContext2D): void {
    const g = this.game;
    const art = g.art;
    const v = g.screen.view;
    ctx.fillStyle = '#f3eefc';
    ctx.fillRect(0, 0, v.w, v.h);
    const top = v.safe.top + 16;
    const x0 = v.safe.left + 6, x1 = Math.floor(v.w / 2) + 6;
    art.text(ctx, `Sound test   ${g.sound.state()}`, x0, v.safe.top + 4, '#5a2a44');
    SONGS.forEach((s, i) => {
      const y = top + i * ROW;
      ctx.fillStyle = i === this.playing ? '#ffd2df' : i % 2 ? '#ffffff' : '#fbf8ff';
      ctx.fillRect(x0 - 2, y, v.w / 2 - x0 - 2, ROW - 1);
      art.text(ctx, `${i + 1}  ${s}`, x0, y + 2, '#5a2a44');
    });
    EFFECTS.forEach((s, i) => {
      const y = top + i * ROW;
      ctx.fillStyle = i % 2 ? '#ffffff' : '#fbf8ff';
      ctx.fillRect(x1 - 2, y, v.w - x1 - v.safe.right - 4, ROW - 1);
      art.text(ctx, s, x1, y + 2, '#5a2a44');
    });
  }
}
