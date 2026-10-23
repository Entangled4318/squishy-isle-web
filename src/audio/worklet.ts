/* Runs the GBA sound engine on the audio thread: one engine frame every
 * 1/59.73 s of audio, so the music keeps time whatever the game's frame
 * rate. The game sends commands; the engine's log lines come back. */
import { GBA_FRAME_HZ, Psg } from './psg';
import { Renderer, SongData, SoundEngine, TUNE_HELLO, TUNE_POP } from './engine';

declare const sampleRate: number;
declare function registerProcessor(name: string, ctor: unknown): void;
declare class AudioWorkletProcessor {
  readonly port: MessagePort;
}

export type SoundCmd =
  | { cmd: 'init'; songs: SongData[] }
  | { cmd: 'play'; id: number; fromStart?: boolean }
  | { cmd: 'stop' }
  | { cmd: 'sfx'; name: 'squeak' | 'hop' | 'chime' | 'blip' | 'tick' | 'pop' | 'boing'; arg?: number }
  | { cmd: 'jingle'; name: 'hello' | 'pop' }
  | { cmd: 'mute'; on: boolean };

class PsgProcessor extends AudioWorkletProcessor {
  private psg = new Psg(sampleRate);
  private engine: SoundEngine | null = null;
  private renderer: Renderer | null = null;
  private pending: SoundCmd[] = [];

  constructor() {
    super();
    this.port.onmessage = (e: MessageEvent<SoundCmd>) => this.handle(e.data);
  }

  private handle(c: SoundCmd): void {
    if (c.cmd === 'init') {
      this.engine = new SoundEngine(this.psg, c.songs, (s) => this.port.postMessage({ log: s }));
      this.renderer = new Renderer(this.engine, this.psg, GBA_FRAME_HZ);
      const q = this.pending;
      this.pending = [];
      q.forEach((p) => this.handle(p));
      return;
    }
    const e = this.engine;
    if (!e) {
      this.pending.push(c);
      return;
    }
    switch (c.cmd) {
      case 'play':
        if (c.fromStart) e.playFromStart(c.id);
        else e.play(c.id);
        break;
      case 'stop':
        e.stop();
        break;
      case 'jingle':
        e.jingle(c.name === 'hello' ? TUNE_HELLO : TUNE_POP);
        break;
      case 'mute':
        e.mute = c.on;
        break;
      case 'sfx':
        if (c.name === 'squeak') e.squeak(c.arg ?? 0);
        else if (c.name === 'chime') e.chime(c.arg ?? 0);
        else e[c.name]();
        break;
    }
  }

  process(_inputs: Float32Array[][], outputs: Float32Array[][]): boolean {
    const out = outputs[0];
    if (!out || !out[0]) return true;
    if (this.renderer) this.renderer.render(out[0]);
    else out[0].fill(0);
    for (let ch = 1; ch < out.length; ch++) out[ch].set(out[0]);
    return true;
  }
}

registerProcessor('squishy-psg', PsgProcessor);
