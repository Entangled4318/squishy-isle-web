/* One scene runs at a time; a change fades to white and back, as in the GBA
 * game's scene.c: 16 levels, 3 a step, so about 6 steps out and 6 in.
 * While a fade runs, touches only sparkle: a tap on a white screen must not
 * act unseen (GBA step 7.1). */
import { TouchEvt } from './input';
import { dbg } from './log';

export interface Scene {
  readonly name: string;
  /** Load the scene. The screen is white while this runs. */
  enter(): void;
  /** One fixed step. touches is empty while a fade runs. */
  update(touches: TouchEvt[]): void;
  /** Draw in art pixels (the context already has the art transform). */
  draw(ctx: CanvasRenderingContext2D): void;
}

const FADE_STEP = 3;

export class Scenes {
  current: Scene | null = null;
  private pending: Scene | null = null;
  /** 0 = clear, 16 = white */
  fadeLevel = 16;
  /** +1 fading out, -1 fading in, 0 idle */
  fadeDir = 0;

  start(first: Scene): void {
    this.current = first;
    this.fadeLevel = 16;
    dbg(`scene ${first.name}`);
    first.enter();
    this.fadeDir = -1;
  }

  fading(): boolean {
    return this.fadeDir !== 0;
  }

  /** Ignored while a fade runs or when next is the scene already showing. */
  go(next: Scene): void {
    if (this.fadeDir || next === this.current) return;
    this.pending = next;
    this.fadeDir = 1;
  }

  /** Fade out and enter the same scene again. */
  reload(): void {
    if (this.fadeDir || !this.current) return;
    this.pending = this.current;
    this.fadeDir = 1;
  }

  step(touches: TouchEvt[]): void {
    if (!this.current) return;
    if (this.fadeDir > 0) {
      this.fadeLevel += FADE_STEP;
      if (this.fadeLevel >= 16) {
        this.fadeLevel = 16;
        this.current = this.pending!;
        dbg(`scene ${this.current.name}`);
        this.current.enter();
        this.fadeDir = -1;
      }
      return;
    }
    if (this.fadeDir < 0) {
      this.fadeLevel -= FADE_STEP;
      if (this.fadeLevel <= 0) {
        this.fadeLevel = 0;
        this.fadeDir = 0;
      }
    }
    this.current.update(this.fadeDir !== 0 ? [] : touches);
  }

  draw(ctx: CanvasRenderingContext2D, w: number, h: number): void {
    this.current?.draw(ctx);
    if (this.fadeLevel > 0) {
      ctx.fillStyle = `rgba(255,255,255,${Math.min(1, this.fadeLevel / 16)})`;
      ctx.fillRect(0, 0, w, h);
    }
  }
}
