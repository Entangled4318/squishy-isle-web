/* The GBA's four PSG sound channels (the Game Boy APU), enough for the
 * game's sound engine (src/audio/engine.ts) to run as it does on the GBA:
 * - channels 1 and 2: square waves, duty 12.5/25/50/75 %, volume envelope;
 * - channel 3: a 32-sample 4-bit wave, volume 100/75/50/25 % or mute;
 * - channel 4: noise from a 15- or 7-bit shift register, volume envelope.
 * The engine writes the same register values as on the GBA. Like the
 * hardware, each channel outputs a positive level (0..15), so turning a
 * voice hard on or off steps the output (a click); a DC-blocking filter
 * plays the part of the output capacitor. Pure TypeScript with no browser
 * API, so the tests render it in Node. */

export const GBA_FRAME_HZ = 16777216 / 280896; /* 59.7275 frames a second */

const DUTY = [
  [0, 0, 0, 0, 0, 0, 0, 1],
  [1, 0, 0, 0, 0, 0, 0, 1],
  [1, 0, 0, 0, 0, 1, 1, 1],
  [0, 1, 1, 1, 1, 1, 1, 0],
];

interface Envelope {
  vol: number;
  dir: number; /* +1 up, -1 down */
  step: number; /* 1/64 s units, 0 = hold */
  t: number; /* seconds to the next step */
}

function envFromCnt(cnt: number): Envelope {
  return { vol: (cnt >> 12) & 15, dir: cnt & 0x800 ? 1 : -1, step: (cnt >> 8) & 7, t: 0 };
}

function envTick(e: Envelope, dt: number): void {
  if (!e.step) return;
  e.t -= dt;
  while (e.t <= 0) {
    e.t += e.step / 64;
    const v = e.vol + e.dir;
    if (v >= 0 && v <= 15) e.vol = v;
  }
}

class Square {
  cnt = 0;
  rate = 0;
  on = false;
  phase = 0; /* 0..8 duty steps */
  env: Envelope = { vol: 0, dir: -1, step: 0, t: 0 };

  writeCnt(v: number): void {
    this.cnt = v & 0xffff;
    /* the DAC is off when the start volume is 0 and the envelope goes down */
    if ((this.cnt & 0xf800) === 0) this.on = false;
  }

  writeFreq(v: number): void {
    this.rate = v & 0x7ff;
    if (v & 0x8000) {
      this.env = envFromCnt(this.cnt);
      this.env.t = this.env.step / 64;
      this.on = (this.cnt & 0xf800) !== 0;
      this.phase = 0;
    }
  }

  hz(): number {
    return 131072 / (2048 - this.rate);
  }

  sample(dt: number): number {
    if (!this.on) return 0;
    this.phase = (this.phase + this.hz() * 8 * dt) % 8;
    const level = DUTY[(this.cnt >> 6) & 3][Math.floor(this.phase)] ? this.env.vol : 0;
    return level;
  }

  tickEnv(dt: number): void {
    if (this.on) envTick(this.env, dt);
  }
}

class Wave {
  sel = 0;
  cnt = 0;
  rate = 0;
  pos = 0; /* 0..32 samples */
  samples: number[] = new Array(32).fill(8);
  on = false;

  writeSel(v: number): void {
    this.sel = v & 0xff;
    if (!(this.sel & 0x80)) this.on = false;
  }

  writeCnt(v: number): void {
    this.cnt = v & 0xffff;
  }

  writeFreq(v: number): void {
    this.rate = v & 0x7ff;
    if (v & 0x8000) {
      this.on = (this.sel & 0x80) !== 0;
      this.pos = 0;
    }
  }

  /** Loads the 32 samples (0..15), as load_wave() does on the GBA. */
  load(samples: number[]): void {
    this.samples = samples.slice(0, 32);
  }

  volumeShift(): number {
    if (this.cnt & 0x8000) return -1; /* forced 75 % */
    return [8, 0, 1, 2][(this.cnt >> 13) & 3]; /* mute, 100 %, 50 %, 25 % */
  }

  sample(dt: number): number {
    if (!this.on) return 0;
    this.pos = (this.pos + (65536 / (2048 - this.rate)) * 32 * dt) % 32;
    const s = this.samples[Math.floor(this.pos)];
    const sh = this.volumeShift();
    if (sh < 0) return (s * 3) >> 2;
    return sh >= 8 ? 0 : s >> sh;
  }
}

class Noise {
  cnt = 0;
  freq = 0;
  on = false;
  lfsr = 0x7fff;
  clock = 0;
  env: Envelope = { vol: 0, dir: -1, step: 0, t: 0 };

  writeCnt(v: number): void {
    this.cnt = v & 0xffff;
    if ((this.cnt & 0xf800) === 0) this.on = false;
  }

  writeFreq(v: number): void {
    this.freq = v & 0xffff;
    if (v & 0x8000) {
      this.env = envFromCnt(this.cnt);
      this.env.t = this.env.step / 64;
      this.on = (this.cnt & 0xf800) !== 0;
      this.lfsr = this.freq & 8 ? 0x7f : 0x7fff;
    }
  }

  hz(): number {
    const r = this.freq & 7;
    const s = (this.freq >> 4) & 15;
    return 524288 / (r === 0 ? 0.5 : r) / 2 ** (s + 1);
  }

  sample(dt: number): number {
    if (!this.on) return 0;
    this.clock += this.hz() * dt;
    const narrow = (this.freq & 8) !== 0;
    while (this.clock >= 1) {
      this.clock -= 1;
      const bit = (this.lfsr ^ (this.lfsr >> 1)) & 1;
      this.lfsr = (this.lfsr >> 1) | (bit << 14);
      if (narrow) this.lfsr = (this.lfsr & ~0x40) | (bit << 6);
    }
    return this.lfsr & 1 ? 0 : this.env.vol;
  }

  tickEnv(dt: number): void {
    if (this.on) envTick(this.env, dt);
  }
}

export class Psg {
  readonly ch1 = new Square();
  readonly ch2 = new Square();
  readonly ch3 = new Wave();
  readonly ch4 = new Noise();
  /** channels heard (tests solo one, like the GBA harness's `solo N`) */
  enabled = [true, true, true, true];
  private dcIn = 0;
  private dcOut = 0;
  private readonly dt: number;
  private readonly sub = 4;
  private readonly dcR: number;

  constructor(readonly sampleRate: number) {
    this.dt = 1 / sampleRate;
    /* DC block: a high-pass at about 20 Hz, like the output capacitor */
    this.dcR = Math.exp((-2 * Math.PI * 20) / sampleRate);
  }

  /** One output sample, -1..1. Four sub-steps are averaged against aliasing. */
  next(): number {
    const d = this.dt / this.sub;
    let acc = 0;
    for (let i = 0; i < this.sub; i++) {
      let s = 0;
      const a = this.ch1.sample(d), b = this.ch2.sample(d), c = this.ch3.sample(d), n = this.ch4.sample(d);
      if (this.enabled[0]) s += a;
      if (this.enabled[1]) s += b;
      if (this.enabled[2]) s += c;
      if (this.enabled[3]) s += n;
      acc += s;
    }
    this.ch1.tickEnv(this.dt);
    this.ch2.tickEnv(this.dt);
    this.ch4.tickEnv(this.dt);
    /* 4 channels x 15 = 60 at most; master volume 6/7 as the game sets it */
    const x = ((acc / this.sub) * (6 / 7)) / 60;
    const y = x - this.dcIn + this.dcR * this.dcOut;
    this.dcIn = x;
    this.dcOut = y;
    return y;
  }
}
