/* Blossom Meadow. Sub-step 1 of M4 has only this stand-in: the map, the
 * camera and Pip come in sub-step 2. A tap goes back to the title. */
import { Game } from '../game';
import { Scene } from '../engine/scenes';
import { TouchEvt } from '../engine/input';

export class Meadow implements Scene {
  readonly name = 'meadow';

  constructor(
    private game: Game,
    private back: () => Scene,
  ) {}

  enter(): void {}

  update(touches: TouchEvt[]): void {
    if (touches.some((t) => t.kind === 'down')) this.game.scenes.go(this.back());
  }

  draw(ctx: CanvasRenderingContext2D): void {
    const g = this.game;
    const v = g.screen.view;
    ctx.fillStyle = '#bfe8c4';
    ctx.fillRect(0, 0, v.w, v.h);
    const s = 'The meadow comes next';
    g.art.textOutlined(ctx, s, Math.floor((v.w - g.art.textWidth(s)) / 2), Math.floor(v.h / 2) - 4, '#ffffff', '#8a5a7a');
  }
}
