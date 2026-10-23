/* The tiny sparkle where each finger lands (docs/PLAN.md step 2). It shows
 * for every finger, during fades too, so every touch gives something back. */
import { TouchEvt } from './input';

interface Spark {
  x: number;
  y: number;
  t: number;
  hue: string;
}

const LIFE = 22;
const COLORS = ['#ff8fc4', '#ffd84d', '#6fd3ff', '#b79cff', '#6fe0a0'];
const EDGE = '#b8487e';

export class Sparkles {
  private list: Spark[] = [];
  private n = 0;

  add(e: TouchEvt): void {
    if (e.kind !== 'down' && e.kind !== 'extra') return;
    this.list.push({ x: e.x, y: e.y, t: 0, hue: COLORS[this.n++ % COLORS.length] });
    if (this.list.length > 24) this.list.shift();
  }

  step(): void {
    for (const s of this.list) s.t++;
    this.list = this.list.filter((s) => s.t < LIFE);
  }

  count(): number {
    return this.list.length;
  }

  draw(ctx: CanvasRenderingContext2D): void {
    for (const s of this.list) {
      const p = s.t / LIFE;
      const r = 3 + p * 9;
      ctx.globalAlpha = p < 0.6 ? 1 : 1 - (p - 0.6) / 0.4;
      for (let i = 0; i < 5; i++) {
        const a = (i / 5) * Math.PI * 2 + p * 1.5;
        const x = Math.round(s.x + Math.cos(a) * r);
        const y = Math.round(s.y + Math.sin(a) * r);
        /* a small plus-shaped star with a dark pink edge, so it reads on any pastel */
        ctx.fillStyle = EDGE;
        ctx.fillRect(x - 2, y - 1, 5, 3);
        ctx.fillRect(x - 1, y - 2, 3, 5);
        ctx.fillStyle = s.hue;
        ctx.fillRect(x - 1, y, 3, 1);
        ctx.fillRect(x, y - 1, 1, 3);
      }
      ctx.fillStyle = EDGE;
      ctx.fillRect(Math.round(s.x) - 2, Math.round(s.y) - 2, 4, 4);
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(Math.round(s.x) - 1, Math.round(s.y) - 1, 2, 2);
    }
    ctx.globalAlpha = 1;
  }
}
