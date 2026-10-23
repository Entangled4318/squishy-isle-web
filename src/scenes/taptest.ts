/* Milestone 1's "tap test": every tap sparkles and chimes, the tap count is
 * the real save's `squishes` counter (so it goes through the two-slot save
 * and survives a reload), and a panel shows what device checklist 1 needs:
 * display mode, storage, sound, the view and the safe areas. */
import { Game, BUILD } from '../game';
import { Scene } from '../engine/scenes';
import { TouchEvt } from '../engine/input';
import { dbg } from '../engine/log';

/* C major pentatonic, like the GBA open screen's chimes */
const NOTES = [523.25, 587.33, 659.25, 783.99, 880, 1046.5, 1174.66, 1318.51];

export function standalone(): boolean {
  return window.matchMedia('(display-mode: standalone)').matches || (navigator as Navigator & { standalone?: boolean }).standalone === true;
}

export class TapTest implements Scene {
  readonly name = 'taptest';
  private bounce = 0;
  private note = 0;
  private refresh = 0;

  constructor(private game: Game) {}

  enter(): void {
    this.bounce = 0;
    void this.game.chip.refreshUsage();
  }

  update(touches: TouchEvt[]): void {
    const g = this.game;
    for (const t of touches) {
      if (t.kind !== 'down') continue;
      const s = g.collection.s;
      s.squishes = (s.squishes + 1) >>> 0;
      g.collection.save();
      g.sound.chime(NOTES[this.note++ % NOTES.length]);
      this.bounce = 12;
      dbg(`tap ${s.squishes} at ${Math.round(t.x)},${Math.round(t.y)}`);
      if (s.squishes === 1 || s.squishes % 10 === 0) void g.chip.askPersist();
    }
    if (this.bounce > 0) this.bounce--;
    if (++this.refresh % 120 === 0) void g.chip.refreshUsage();
  }

  draw(ctx: CanvasRenderingContext2D): void {
    const g = this.game;
    const v = g.screen.view;
    /* sky and a soft island */
    const sky = ctx.createLinearGradient(0, 0, 0, v.h);
    sky.addColorStop(0, '#cfe9ff');
    sky.addColorStop(1, '#fde3ef');
    ctx.fillStyle = sky;
    ctx.fillRect(0, 0, v.w, v.h);
    ctx.fillStyle = '#bfe8c4';
    ctx.beginPath();
    ctx.ellipse(v.w / 2, v.h * 0.78, v.w * 0.42, v.h * 0.16, 0, 0, Math.PI * 2);
    ctx.fill();

    /* the count, with a hop on each tap */
    const hop = Math.sin((this.bounce / 12) * Math.PI) * 8;
    ctx.fillStyle = '#ffffff';
    ctx.strokeStyle = '#d97aa6';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(v.w / 2, v.h * 0.42 - hop, 28, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = '#8a3b62';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.font = 'bold 22px system-ui, sans-serif';
    ctx.fillText(String(g.collection.s.squishes), v.w / 2, v.h * 0.42 - hop + 1);

    /* safe areas: a dashed frame, and where the shelf / home / gear buttons go */
    const sa = v.safe;
    ctx.setLineDash([2, 2]);
    ctx.strokeStyle = 'rgba(138,59,98,0.5)';
    ctx.lineWidth = 1;
    ctx.strokeRect(sa.left + 0.5, sa.top + 0.5, v.w - sa.left - sa.right - 1, v.h - sa.top - sa.bottom - 1);
    ctx.setLineDash([]);
    const r = 12;
    ctx.fillStyle = 'rgba(255,255,255,0.7)';
    for (const [x, y] of [
      [sa.left + 4 + r, sa.top + 4 + r],
      [v.w - sa.right - 4 - r, sa.top + 4 + r],
      [sa.left + 4 + r, v.h - sa.bottom - 4 - r],
    ]) {
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fill();
    }

    /* the grown-up panel */
    const rep = g.chip.report;
    const lines = [
      `build ${BUILD}`,
      `${standalone() ? 'home screen app' : 'browser tab'}, boots ${g.collection.s.boots}, save ${g.loadStatus}`,
      `local ${rep.local ? 'ok' : 'NO'}, indexedDB ${rep.indexedDB ? 'ok' : 'NO'}, last copy ${rep.lastIdbWrite}`,
      `persist ${rep.persisted}, used ${rep.usage}`,
      `sound ${g.sound.state()}, session ${g.sound.session}`,
      `view ${v.w}x${v.h} art px, x${v.k}, dpr ${v.dpr}, ${v.portrait ? 'portrait' : 'landscape'}`,
      `safe t${sa.top} r${sa.right} b${sa.bottom} l${sa.left}`,
    ];
    ctx.font = '5px ui-monospace, monospace';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';
    const x0 = sa.left + 34; /* clear of the bottom-left button spot */
    let y = v.h - sa.bottom - 6 - lines.length * 6;
    ctx.fillStyle = 'rgba(255,255,255,0.75)';
    ctx.fillRect(x0 - 2, y - 2, Math.min(v.w - x0 - sa.right - 4, 150), lines.length * 6 + 3);
    ctx.fillStyle = '#5a2a44';
    for (const l of lines) {
      ctx.fillText(l, x0, y);
      y += 6;
    }
  }
}
