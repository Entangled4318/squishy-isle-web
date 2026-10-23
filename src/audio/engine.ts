/* The GBA game's sound engine (rom/src/sound.c, v1.6), frame for frame:
 * channel 1 short effects, channel 2 the music bass (the boing borrows it),
 * channel 3 (wave) the music lead and jingles, channel 4 clicks. tick()
 * runs once per GBA frame on the audio clock (src/audio/worklet.ts), so a
 * slow game frame never changes the tempo. The register values are the
 * C code's; src/audio/psg.ts turns them into sound. */
import { Psg } from './psg';

export interface SongData {
  title: string;
  tick: number;
  bar: number;
  lead: [number, number][];
  bass: [number, number][];
  loop: boolean;
  wave: string;
  lead_level: number;
  lead_decay: number;
  lead_gap: number;
  bass_vol: number;
  bass_duty: number;
  bass_step: number;
  bass_gap: number;
  index: number;
  wave_samples: number[];
}

export interface Note {
  hz: number;
  frames: number;
  vol: number;
}

const CPU_HZ = 16777216;
const hzOf = (m: number) => 440 * 2 ** ((m - 69) / 12);
/* the music tables round (tools/music.py); the effect macros truncate (sound.c) */
const musicSqRate = (m: number) => (m >= 36 ? 2048 - Math.round(CPU_HZ / 128 / hzOf(m)) : 0);
const musicWaveRate = (m: number) => (m >= 24 ? 2048 - Math.round(CPU_HZ / 256 / hzOf(m)) : 0);
const SQ_RATE = (hz: number) => 2048 - Math.trunc(131072 / hz);
const WAVE_RATE = (hz: number) => 2048 - Math.trunc(65536 / hz);

const ENV = (vol: number, step: number) => (vol << 12) | (step << 8);
const DUTY_12 = 0 << 6;
const DUTY_25 = 1 << 6;
const DUTY_50 = 2 << 6;
const RESTART = 0x8000;

/* C5 E5 G5 C6 . G5 C6: a bright "hello" */
export const TUNE_HELLO: Note[] = [
  { hz: 523, frames: 8, vol: 12 }, { hz: 659, frames: 8, vol: 12 }, { hz: 784, frames: 8, vol: 12 }, { hz: 1047, frames: 14, vol: 12 },
  { hz: 0, frames: 4, vol: 0 }, { hz: 784, frames: 8, vol: 10 }, { hz: 1047, frames: 20, vol: 12 },
];
/* after the pop: a little rising "ta-da" */
export const TUNE_POP: Note[] = [
  { hz: 784, frames: 5, vol: 11 }, { hz: 988, frames: 5, vol: 11 }, { hz: 1175, frames: 5, vol: 11 }, { hz: 1568, frames: 16, vol: 12 },
];

const SQUEAK_CURVE = [620, 760, 900, 1040, 1150, 1220, 1250, 1230, 1180, 1100, 1010, 930];
const HOP_CURVE = [330, 370, 415, 466, 523, 587, 622, 659, 0, 0, 0, 0];
const BOING_CURVE = [262, 330, 415, 494, 523, 494, 440, 392, 349, 311, 277, 262, 247, 233, 220, 208];
const BELL = [1047, 1175, 1319, 1568, 1760];
/* wave volume by level: 0 = 100 %, 1 = 75 %, 2 = 50 %, 3 = 25 %, 4 = off */
const WAVE_VOL = [0x2000, 0x8000, 0x4000, 0x6000, 0];

interface Voice {
  ev: [number, number][];
  n: number;
  index: number;
  left: number;
  len: number;
  age: number;
  note: number;
  level: number;
}

const newVoice = (): Voice => ({ ev: [], n: 0, index: -1, left: 0, len: 0, age: 0, note: 0, level: 4 });

export class SoundEngine {
  private melody: { notes: Note[] | null; index: number; timer: number } = { notes: null, index: 0, timer: 0 };
  private boingT = -1;
  private squeakT = -1;
  private squeakPitch = 256;
  private slide = SQUEAK_CURVE;
  private waveNow: number[] | null = null;
  private song: SongData | null = null;
  private id = -1;
  private lead = newVoice();
  private bass = newVoice();
  private kept: Array<{ ok: boolean; lead: Voice; bass: Voice }>;
  /** true: the song keeps time but makes no sound (tests) */
  mute = false;
  /** frames run so far */
  frame = 0;

  constructor(
    readonly psg: Psg,
    readonly songs: SongData[],
    private log: (s: string) => void = () => {},
  ) {
    this.kept = songs.map(() => ({ ok: false, lead: newVoice(), bass: newVoice() }));
    this.loadWave(songs.find((s) => s.wave === 'sine')?.wave_samples ?? new Array(32).fill(8));
  }

  /* The GBA stops the wave channel to load new samples; between songs only. */
  private loadWave(w: number[]): void {
    if (w === this.waveNow) return;
    this.waveNow = w;
    this.psg.ch3.writeCnt(0);
    this.psg.ch3.writeSel(0x40);
    this.psg.ch3.load(w);
    this.psg.ch3.writeSel(0x80);
  }

  /** squish: a quick rise and small fall; each flavor a little higher (pitch 0..4) */
  squeak(pitch: number): void {
    this.squeakT = 0;
    this.slide = SQUEAK_CURVE;
    this.squeakPitch = 256 + (pitch % 5) * 20;
    this.psg.ch1.writeCnt(DUTY_25 | ENV(13, 2));
    this.psg.ch1.writeFreq(RESTART | SQ_RATE((SQUEAK_CURVE[0] * this.squeakPitch) >> 8));
  }

  /** Pip's hop: a soft quick rise on channel 1 */
  hop(): void {
    this.squeakT = 0;
    this.slide = HOP_CURVE;
    this.squeakPitch = 256;
    this.psg.ch1.writeCnt(DUTY_50 | ENV(9, 1));
    this.psg.ch1.writeFreq(RESTART | SQ_RATE(HOP_CURVE[0]));
  }

  private squeakTick(): void {
    if (this.squeakT < 0) return;
    if (++this.squeakT >= 12 || !this.slide[this.squeakT]) {
      this.squeakT = -1;
      return;
    }
    this.psg.ch1.writeFreq(SQ_RATE((this.slide[this.squeakT] * this.squeakPitch) >> 8));
  }

  /** soft bell; step selects the note */
  chime(step: number): void {
    this.squeakT = -1;
    this.psg.ch1.writeCnt(DUTY_12 | ENV(14, 2));
    this.psg.ch1.writeFreq(RESTART | SQ_RATE(BELL[step % 5]));
  }

  blip(): void {
    this.squeakT = -1;
    this.psg.ch1.writeCnt(DUTY_50 | ENV(7, 1));
    this.psg.ch1.writeFreq(RESTART | SQ_RATE(392));
  }

  tick(): void {
    this.psg.ch4.writeCnt(ENV(4, 1));
    this.psg.ch4.writeFreq(RESTART | (2 << 4) | 1);
  }

  pop(): void {
    this.psg.ch4.writeCnt(ENV(11, 2));
    this.psg.ch4.writeFreq(RESTART | (4 << 4) | 2);
    this.chime(4);
  }

  boing(): void {
    this.boingT = 0;
    this.psg.ch2.writeCnt(DUTY_50 | ENV(11, 2));
    this.psg.ch2.writeFreq(RESTART | SQ_RATE(262));
  }

  /** a jingle on channel 3: the music waits and goes on after it */
  jingle(notes: Note[]): void {
    this.musicSilence();
    this.melody = { notes, index: 0, timer: 0 };
  }

  private melodyTick(): void {
    const m = this.melody;
    if (!m.notes) return;
    const n = m.notes[m.index];
    if (m.timer === 0) {
      if (n.hz) {
        this.psg.ch3.writeCnt(n.vol >= 8 ? 0x2000 : 0x4000);
        this.psg.ch3.writeFreq(RESTART | WAVE_RATE(n.hz));
      } else this.psg.ch3.writeCnt(0);
    } else if (m.timer === n.frames - 2 && n.hz) {
      this.psg.ch3.writeCnt(0x6000); /* 25 %: soft release */
    }
    if (++m.timer >= n.frames) {
      m.timer = 0;
      if (++m.index >= m.notes.length) {
        m.notes = null;
        this.psg.ch3.writeCnt(0);
      }
    }
  }

  private start(id: number, resume: boolean): void {
    if (id === this.id && this.song) return;
    if (this.song && this.song.loop) this.kept[this.id] = { ok: true, lead: { ...this.lead }, bass: { ...this.bass } };
    this.stop();
    if (id < 0 || id >= this.songs.length) return;
    this.song = this.songs[id];
    this.id = id;
    this.loadWave(this.song.wave_samples);
    const k = this.kept[id];
    if (resume && k.ok) {
      this.lead = { ...k.lead, age: 0, level: 4 };
      this.bass = { ...k.bass, age: 0 };
    } else {
      this.lead = { ...newVoice(), ev: this.song.lead, n: this.song.lead.length };
      this.bass = { ...newVoice(), ev: this.song.bass, n: this.song.bass.length };
    }
    k.ok = false;
    this.log(`song ${resume && this.lead.index >= 0 ? 'resume' : 'start'} ${id}`);
  }

  /** no restart when that song already plays; a looping song goes on where it was left */
  play(id: number): void {
    this.start(id, true);
  }

  playFromStart(id: number): void {
    if (id >= 0 && id < this.songs.length) this.kept[id].ok = false;
    if (id === this.id) this.stop();
    this.start(id, false);
  }

  stop(): void {
    if (this.song) {
      this.log(`song stop ${this.id}`);
      if (!this.melody.notes) this.psg.ch3.writeCnt(0);
      if (this.boingT < 0) {
        this.psg.ch2.writeCnt(0);
        this.psg.ch2.writeFreq(RESTART);
      }
    }
    this.song = null;
    this.id = -1;
  }

  current(): number {
    return this.song ? this.id : -1;
  }

  private musicSilence(): void {
    if (!this.song) return;
    this.lead.level = 4; /* the jingle takes the wave channel: after it the lead strikes again */
    this.psg.ch2.writeCnt(0);
    this.psg.ch2.writeFreq(RESTART);
  }

  private voiceNext(v: Voice, isLead: boolean): boolean {
    const s = this.song!;
    if (++v.index >= v.n) {
      if (!s.loop) return false;
      v.index = 0;
      if (isLead) this.log(`music loop ${this.id}`);
    }
    v.note = v.ev[v.index][0];
    v.len = v.left = v.ev[v.index][1] * s.tick;
    v.age = 0;
    return true;
  }

  private leadFrame(): void {
    const s = this.song!;
    const v = this.lead;
    if (this.melody.notes || this.mute) {
      v.level = 4;
      return;
    }
    let lv = 4;
    if (v.note) {
      lv = s.lead_level;
      if (s.lead_decay) lv += Math.trunc(v.age / s.lead_decay);
      const attack = (s.lead_level < 1 ? 3 : s.lead_level + 2) - v.age;
      if (attack > lv) lv = attack;
      if (v.left <= s.lead_gap) {
        const release = s.lead_level + s.lead_gap - v.left + 1;
        if (release > lv) lv = release;
      }
      if (lv > 3) lv = 3;
      if (v.age === 0 || v.level === 4) {
        const rate = musicWaveRate(v.note);
        if (v.level === 4) {
          if (lv < 3) lv = 3;
          this.psg.ch3.writeCnt(WAVE_VOL[lv]);
          this.psg.ch3.writeFreq(RESTART | rate);
        } else this.psg.ch3.writeFreq(rate);
      }
    }
    if (lv !== v.level) {
      if (lv > v.level + 1) lv = v.level + 1;
      if (lv < v.level - 1) lv = v.level - 1;
      this.psg.ch3.writeCnt(WAVE_VOL[lv]);
      v.level = lv;
    }
  }

  private bassFrame(): void {
    const s = this.song!;
    const v = this.bass;
    if (this.boingT >= 0 || this.melody.notes || this.mute) return;
    if (v.age === 0) {
      if (v.note) {
        this.psg.ch2.writeCnt((s.bass_duty << 6) | ENV(s.bass_vol, s.bass_step));
        this.psg.ch2.writeFreq(RESTART | musicSqRate(v.note));
      } else {
        this.psg.ch2.writeCnt(0);
        this.psg.ch2.writeFreq(RESTART);
      }
    } else if (v.note && s.bass_gap && v.left === s.bass_gap) {
      this.psg.ch2.writeCnt(0);
      this.psg.ch2.writeFreq(RESTART);
    }
  }

  private musicTick(): void {
    if (!this.song || this.melody.notes) return;
    if (this.lead.left === 0 && !this.voiceNext(this.lead, true)) return this.stop();
    if (this.bass.left === 0 && !this.voiceNext(this.bass, false)) return this.stop();
    this.leadFrame();
    this.bassFrame();
    this.lead.age++;
    this.lead.left--;
    this.bass.age++;
    this.bass.left--;
  }

  private boingTick(): void {
    if (this.boingT < 0) return;
    if (this.boingT < 16) this.psg.ch2.writeFreq(SQ_RATE(BOING_CURVE[this.boingT]));
    if (++this.boingT >= 16) this.boingT = -1;
  }

  /** One GBA frame. */
  frameTick(): void {
    this.frame++;
    this.musicTick();
    this.melodyTick();
    this.boingTick();
    this.squeakTick();
  }
}

/** Renders frames of engine time into samples (for the worklet and the tests). */
export class Renderer {
  private toNext = 0;
  readonly samplesPerFrame: number;

  constructor(
    readonly engine: SoundEngine,
    readonly psg: Psg,
    frameHz: number,
  ) {
    this.samplesPerFrame = psg.sampleRate / frameHz;
  }

  render(out: Float32Array): void {
    for (let i = 0; i < out.length; i++) {
      if (this.toNext <= 0) {
        this.engine.frameTick();
        this.toNext += this.samplesPerFrame;
      }
      this.toNext--;
      out[i] = this.psg.next();
    }
  }
}
