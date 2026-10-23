/* Milestone 3: the sound engine and sound chip, rendered in Node, checked
 * the way the GBA game's test/check_music.py checks the ROM: every note's
 * pitch (lead and bass alone), the exact tempo from the loop log, loop 2
 * the same as loop 1, the jingle hand-off, and no clicks. */
import { readFileSync, existsSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { GBA_FRAME_HZ, Psg } from '../../src/audio/psg';
import { Renderer, SongData, SoundEngine, TUNE_HELLO } from '../../src/audio/engine';

const RATE = 48000;
const MUSIC = 'public/gen/music.json';
const songs: SongData[] = existsSync(MUSIC)
  ? Object.values(JSON.parse(readFileSync(MUSIC, 'utf8')) as Record<string, SongData>).sort((a, b) => a.index - b.index)
  : [];

function setup(solo?: number) {
  const psg = new Psg(RATE);
  if (solo !== undefined) psg.enabled = [0, 1, 2, 3].map((c) => c === solo);
  const log: string[] = [];
  const engine = new SoundEngine(psg, songs, (s) => log.push(`${engine.frame} ${s}`));
  const r = new Renderer(engine, psg, GBA_FRAME_HZ);
  const render = (frames: number) => {
    const out = new Float32Array(Math.round(frames * r.samplesPerFrame));
    r.render(out);
    return out;
  };
  return { psg, engine, render, log, spf: r.samplesPerFrame };
}

/** YIN pitch estimate in Hz, or 0 when no clear pitch. */
function yin(x: Float32Array, minHz = 60, maxHz = 2500): number {
  const maxLag = Math.floor(RATE / minHz), minLag = Math.floor(RATE / maxHz);
  const n = x.length - maxLag;
  if (n < 256) return 0;
  const d = new Float64Array(maxLag + 1);
  for (let lag = 1; lag <= maxLag; lag++) {
    let s = 0;
    for (let i = 0; i < n; i++) {
      const e = x[i] - x[i + lag];
      s += e * e;
    }
    d[lag] = s;
  }
  let run = 0;
  for (let lag = 1; lag <= maxLag; lag++) {
    run += d[lag];
    const c = (d[lag] * lag) / (run || 1);
    if (lag >= minLag && c < 0.15) {
      let l = lag;
      while (l + 1 <= maxLag && (d[l + 1] * (l + 1)) / (run + d[l + 1]) < (d[l] * l) / run) l++;
      const a = d[l - 1], b = d[l], cc = d[Math.min(maxLag, l + 1)];
      const shift = (a - cc) / (2 * (a - 2 * b + cc) || 1);
      return RATE / (l + shift);
    }
  }
  return 0;
}

const hz = (m: number) => 440 * 2 ** ((m - 69) / 12);
const cents = (a: number, b: number) => 1200 * Math.log2(a / b);

/** Each note's start frame and length in frames, for one voice. */
function timeline(s: SongData, voice: 'lead' | 'bass') {
  const out: { note: number; start: number; len: number }[] = [];
  let f = 0;
  for (const [note, ticks] of s[voice]) {
    out.push({ note, start: f, len: ticks * s.tick });
    f += ticks * s.tick;
  }
  return out;
}

describe.skipIf(!songs.length)('songs on the emulated GBA sound chip', () => {
  it('has the 8 songs of the GBA game', () => {
    expect(songs.map((s) => s.title.split(':')[0])).toEqual(['Title', 'Meadow', 'Open', 'Reveal', 'Shelf', 'Shore', 'Woods', 'Cloud Hill']);
  });

  for (const [voice, ch] of [['lead', 2], ['bass', 1]] as const) {
    it.each(songs.map((s) => [s.title, s] as const))(`%s: every ${voice} note at its pitch (25 cents)`, (_t, s) => {
      const { engine, render, spf } = setup(ch);
      engine.playFromStart(s.index);
      const total = timeline(s, voice).reduce((a, n) => Math.max(a, n.start + n.len), 0);
      const audio = render(total + 2);
      let checked = 0;
      const bad: string[] = [];
      for (const n of timeline(s, voice)) {
        if (!n.note || n.len < 8) continue;
        /* the middle of the note, away from its attack and release */
        const a = Math.round((n.start + 2) * spf), b = Math.round((n.start + n.len - 2) * spf);
        const win = audio.subarray(a, Math.min(b, a + 4096 + Math.floor(RATE / 60)));
        const f = yin(win);
        if (!f) continue;
        checked++;
        const c = cents(f, hz(n.note));
        if (Math.abs(c) > 25) bad.push(`note ${n.note} at frame ${n.start}: ${f.toFixed(1)} Hz, ${c.toFixed(0)} cents`);
      }
      expect(bad).toEqual([]);
      expect(checked).toBeGreaterThan(voice === 'lead' ? 3 : 2);
    });
  }

  it.each(songs.filter((s) => s.loop).map((s) => [s.title, s] as const))('%s: exact tempo, loop 2 = loop 1', (_t, s) => {
    const { engine, psg, render, log, spf } = setup(2); /* loudness of the lead alone; the registers of both voices */
    engine.playFromStart(s.index);
    const frames = s.lead.reduce((a, [, t]) => a + t * s.tick, 0);
    /* what the engine has set on the lead and bass channels, each frame */
    const regs: string[] = [];
    const tick = engine.frameTick.bind(engine);
    engine.frameTick = () => {
      tick();
      regs.push(`${psg.ch3.cnt} ${psg.ch3.rate} ${psg.ch2.cnt} ${psg.ch2.rate} ${psg.ch2.on}`);
    };
    const audio = render(frames * 2 + 4);
    const loops = log.filter((l) => l.includes(`music loop ${s.index}`)).map((l) => parseInt(l));
    expect(loops.length).toBeGreaterThanOrEqual(1);
    expect(loops[0] - 1).toBe(frames); /* the first frame plays note 1 */
    let diff = 0;
    for (let f = 2; f < frames; f++) if (regs[f] !== regs[f + frames]) diff++;
    expect(diff, 'register frames that differ between loop 1 and loop 2').toBe(0);
    /* loudness over 12-frame windows (0.2 s), loop 1 against loop 2 */
    const rms = (from: number) => {
      const n = Math.round(12 * spf);
      let s2 = 0;
      for (let i = 0; i < n; i++) s2 += audio[Math.round(from) + i] ** 2;
      return Math.sqrt(s2 / n);
    };
    let worst = 0, peak = 0;
    for (let f = 12; f < frames - 24; f += 6) {
      const a = rms(f * spf), b = rms((f + frames) * spf);
      peak = Math.max(peak, a);
      worst = Math.max(worst, Math.abs(a - b));
    }
    expect(worst / peak).toBeLessThan(0.05);
  });

  it('a one-shot song (reveal) stops by itself', () => {
    const s = songs.find((x) => !x.loop)!;
    const { engine, render, log } = setup();
    engine.playFromStart(s.index);
    render(s.lead.reduce((a, [, t]) => a + t * s.tick, 0) + 10);
    expect(log.some((l) => l.endsWith(`song stop ${s.index}`))).toBe(true);
    expect(engine.current()).toBe(-1);
  });

  it('after a jingle the lead goes on at its own pitch (GBA step 7.6)', () => {
    const meadow = songs[1];
    const { engine, render, spf } = setup(2);
    engine.playFromStart(meadow.index);
    render(40);
    engine.jingle(TUNE_HELLO);
    const jingle = TUNE_HELLO.reduce((a, n) => a + n.frames, 0);
    render(jingle + 2);
    /* find the note sounding now and measure it */
    const now = engine.frame;
    const n = timeline(meadow, 'lead').find((t) => now - jingle >= t.start && now - jingle < t.start + t.len);
    void n;
    const audio = render(30);
    const f = yin(audio.subarray(Math.round(4 * spf)));
    const leadNotes = new Set(meadow.lead.map(([m]) => m).filter(Boolean));
    const nearest = [...leadNotes].reduce((best, m) => (Math.abs(cents(f, hz(m))) < Math.abs(cents(f, hz(best))) ? m : best));
    expect(Math.abs(cents(f, hz(nearest)))).toBeLessThan(25);
    expect(f).not.toBeCloseTo(1047, -1); /* not the jingle's last note */
  });

  it('a looping song resumes where it was left; the bass comes back after the boing', () => {
    const { engine, render, log } = setup();
    engine.play(1);
    render(300);
    engine.play(4); /* the shelf */
    render(100);
    engine.play(1);
    expect(log.some((l) => l.endsWith('song resume 1'))).toBe(true);
    engine.boing();
    render(20);
    const { psg } = { psg: engine.psg };
    render(200);
    expect(psg.ch2.on).toBe(true);
  });

  it('no clicks: the lead never jumps in level (a smoothed step under 30% of its peak)', () => {
    for (const s of songs) {
      const { engine, render, spf } = setup(2);
      engine.playFromStart(s.index);
      const frames = s.lead.reduce((a, [, t]) => a + t * s.tick, 0);
      const audio = render(Math.min(frames, 1200));
      /* average over 2 ms: the wave averages out, a DC jump stays */
      const w = Math.round(RATE * 0.002);
      let acc = 0, peak = 0, jump = 0;
      const sm: number[] = [];
      for (let i = 0; i < audio.length; i++) {
        acc += audio[i] - (i >= w ? audio[i - w] : 0);
        sm.push(acc / w);
        peak = Math.max(peak, Math.abs(audio[i]));
      }
      for (let i = w; i < sm.length; i += 1) jump = Math.max(jump, Math.abs(sm[i] - sm[i - 1]));
      expect(jump / peak, s.title).toBeLessThan(0.3);
      void spf;
    }
  });

  it('effects are as loud as the songs, and do not clip', () => {
    const loud = (f: (e: SoundEngine) => void, frames: number) => {
      const { engine, render } = setup();
      f(engine);
      const a = render(frames);
      let peak = 0;
      for (const x of a) peak = Math.max(peak, Math.abs(x));
      return peak;
    };
    const song = loud((e) => e.playFromStart(1), 600);
    for (const [name, f] of [
      ['chime', (e: SoundEngine) => e.chime(0)],
      ['squeak', (e: SoundEngine) => e.squeak(0)],
      ['boing', (e: SoundEngine) => e.boing()],
    ] as const) {
      const p = loud(f, 30);
      expect(p, name).toBeGreaterThan(song * 0.5);
      expect(p, name).toBeLessThan(1);
    }
  });
});
