/* Sound that starts on the first touch (docs/PLAN.md step 3).
 * - iOS keeps Web Audio silent until a touch: every touch calls unlock().
 * - Safari 17+: audio session "playback", so the iPhone silent switch does
 *   not mute the game (like a video).
 * - A call or a screen lock suspends the context; the next touch resumes it.
 * The sound itself is the GBA game's engine and sound chip, in an
 * AudioWorklet (src/audio/). Commands sent before the worklet is ready
 * wait and go in order. */
import workletUrl from '../audio/worklet.ts?worker&url';
import type { SoundCmd } from '../audio/worklet';
import type { SongData } from '../audio/engine';
import { dbg } from './log';

type SessionNavigator = Navigator & { audioSession?: { type: string } };

export const SONG = { title: 0, meadow: 1, open: 2, reveal: 3, shelf: 4, shore: 5, woods: 6, cloud: 7 } as const;

export class Sound {
  ctx: AudioContext | null = null;
  private master: GainNode | null = null;
  private node: AudioWorkletNode | null = null;
  private queue: SoundCmd[] = [];
  private songs: SongData[] | null = null;
  private primed = false;
  /** the audio session type we asked for, or 'none' where Safari has no API */
  session = 'none';
  worklet = 'not started';

  /** The song list (music.json), from the art loader. */
  setSongs(songs: SongData[]): void {
    this.songs = songs;
    if (this.node) this.node.port.postMessage({ cmd: 'init', songs } satisfies SoundCmd);
  }

  /** Call from every touch handler (it is cheap after the first time). */
  unlock(): void {
    try {
      if (!this.ctx) this.create();
      const ctx = this.ctx!;
      if (ctx.state !== 'running') void ctx.resume().then(() => dbg(`audio ${ctx.state}`), () => {});
      if (!this.primed) {
        /* a one-sample silent buffer started inside the touch: older iOS needs it */
        const src = ctx.createBufferSource();
        src.buffer = ctx.createBuffer(1, 1, 22050);
        src.connect(ctx.destination);
        src.start(0);
        this.primed = true;
      }
    } catch (e) {
      dbg(`audio unlock failed ${String(e)}`);
    }
  }

  private create(): void {
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
    const ctx = new AC();
    this.ctx = ctx;
    this.master = ctx.createGain();
    this.master.gain.value = 0.9;
    this.master.connect(ctx.destination);
    dbg(`audio context ${ctx.state} ${ctx.sampleRate} Hz session ${this.session}`);
    if (!ctx.audioWorklet) {
      this.worklet = 'no AudioWorklet';
      dbg('audio: no AudioWorklet, no sound');
      return;
    }
    this.worklet = 'loading';
    ctx.audioWorklet
      .addModule(workletUrl)
      .then(() => {
        const node = new AudioWorkletNode(ctx, 'squishy-psg', { numberOfInputs: 0, outputChannelCount: [2] });
        node.port.onmessage = (e: MessageEvent<{ log?: string }>) => {
          if (e.data.log) dbg(e.data.log);
        };
        node.connect(this.master!);
        this.node = node;
        this.worklet = 'ready';
        if (this.songs) node.port.postMessage({ cmd: 'init', songs: this.songs } satisfies SoundCmd);
        const q = this.queue;
        this.queue = [];
        q.forEach((c) => node.port.postMessage(c));
        dbg('audio worklet ready');
      })
      .catch((e) => {
        this.worklet = 'failed';
        dbg(`audio worklet failed ${String(e)}`);
      });
  }

  private send(c: SoundCmd): void {
    if (this.node) this.node.port.postMessage(c);
    else if (this.queue.length < 32) this.queue.push(c);
  }

  state(): string {
    return this.ctx ? `${this.ctx.state}, worklet ${this.worklet}` : 'not started';
  }

  /** The app is hidden: stop all sound. */
  suspend(): void {
    if (this.ctx && this.ctx.state === 'running') void this.ctx.suspend();
  }

  /** The app shows again: try to resume (iOS may still wait for a touch). */
  resume(): void {
    if (this.ctx && this.ctx.state !== 'running') void this.ctx.resume().catch(() => {});
  }

  music(id: number): void {
    this.send({ cmd: 'play', id });
  }
  musicFromStart(id: number): void {
    this.send({ cmd: 'play', id, fromStart: true });
  }
  stopMusic(): void {
    this.send({ cmd: 'stop' });
  }
  jingle(name: 'hello' | 'pop'): void {
    this.send({ cmd: 'jingle', name });
  }
  /** A soft tick where a finger lands. */
  tick(): void {
    this.send({ cmd: 'sfx', name: 'tick' });
  }
  chime(step: number): void {
    this.send({ cmd: 'sfx', name: 'chime', arg: step });
  }
  squeak(pitch: number): void {
    this.send({ cmd: 'sfx', name: 'squeak', arg: pitch });
  }
  boing(): void {
    this.send({ cmd: 'sfx', name: 'boing' });
  }
  hop(): void {
    this.send({ cmd: 'sfx', name: 'hop' });
  }
  blip(): void {
    this.send({ cmd: 'sfx', name: 'blip' });
  }
  pop(): void {
    this.send({ cmd: 'sfx', name: 'pop' });
  }
}
