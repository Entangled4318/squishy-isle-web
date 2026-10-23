/* Sound that starts on the first touch (docs/PLAN.md step 3).
 * - iOS keeps Web Audio silent until a touch: every touch calls unlock().
 * - Safari 17+: audio session "playback", so the iPhone silent switch does
 *   not mute the game (like a video).
 * - A call or a screen lock suspends the context; the next touch resumes it.
 * The real synth for the GBA voices comes in milestone 3; M1 has a soft
 * tick and a chime to prove the path. */
import { dbg } from './log';

type SessionNavigator = Navigator & { audioSession?: { type: string } };

export class Sound {
  ctx: AudioContext | null = null;
  private master: GainNode | null = null;
  private primed = false;
  musicOn = true;
  /** the audio session type we asked for, or 'none' where Safari has no API */
  session = 'none';

  /** Call from every touch handler (it is cheap after the first time). */
  unlock(): void {
    try {
      if (!this.ctx) {
        const nav = navigator as SessionNavigator;
        if (nav.audioSession) {
          try {
            nav.audioSession.type = 'playback';
            this.session = nav.audioSession.type;
          } catch {
            this.session = 'refused';
          }
        }
        const AC = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
        this.ctx = new AC();
        this.master = this.ctx.createGain();
        this.master.gain.value = 0.5;
        this.master.connect(this.ctx.destination);
        dbg(`audio context ${this.ctx.state} session ${this.session}`);
      }
      if (this.ctx.state !== 'running') void this.ctx.resume().then(() => dbg(`audio ${this.ctx?.state}`), () => {});
      if (!this.primed) {
        /* a one-sample silent buffer started inside the touch: older iOS needs it */
        const b = this.ctx.createBuffer(1, 1, 22050);
        const src = this.ctx.createBufferSource();
        src.buffer = b;
        src.connect(this.ctx.destination);
        src.start(0);
        this.primed = true;
      }
    } catch (e) {
      dbg(`audio unlock failed ${String(e)}`);
    }
  }

  state(): string {
    return this.ctx ? this.ctx.state : 'not started';
  }

  /** The app is hidden: stop all sound. */
  suspend(): void {
    if (this.ctx && this.ctx.state === 'running') void this.ctx.suspend();
  }

  /** The app shows again: try to resume (iOS may still wait for a touch). */
  resume(): void {
    if (this.ctx && this.ctx.state !== 'running') void this.ctx.resume().catch(() => {});
  }

  private live(): AudioContext | null {
    return this.ctx && this.ctx.state === 'running' && this.master ? this.ctx : null;
  }

  /** A soft tick where a finger lands. */
  tick(): void {
    const ctx = this.live();
    if (!ctx) return;
    const t = ctx.currentTime;
    const o = ctx.createOscillator();
    const g = ctx.createGain();
    o.type = 'triangle';
    o.frequency.setValueAtTime(1800, t);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(0.12, t + 0.003);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 0.04);
    o.connect(g).connect(this.master!);
    o.start(t);
    o.stop(t + 0.05);
  }

  /** A bright chime, like the GBA game's open-screen presses. */
  chime(hz: number): void {
    const ctx = this.live();
    if (!ctx) return;
    const t = ctx.currentTime;
    for (const [mul, vol] of [[1, 0.22], [2, 0.06]] as const) {
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      o.type = 'square';
      o.frequency.setValueAtTime(hz * mul, t);
      g.gain.setValueAtTime(0.0001, t);
      g.gain.exponentialRampToValueAtTime(vol, t + 0.005);
      g.gain.exponentialRampToValueAtTime(0.0001, t + 0.35);
      o.connect(g).connect(this.master!);
      o.start(t);
      o.stop(t + 0.4);
    }
  }
}
