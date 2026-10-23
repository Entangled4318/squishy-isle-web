"""Songs for the GBA PSG, written with note names.

Each song has two voices: a lead on the wave channel (3) and a bass on
square channel 2. Time is counted in ticks; `tick` is frames per tick
(60 frames = 1 second), and a tick is normally a sixteenth note.

Voice text: tokens separated by spaces. "C5:4" is C in octave 5 for 4
ticks, "r:2" is a rest, "Bb3" or "F#4" use flats and sharps. A token
without ":n" keeps the length of the one before it. "|" (bar line) is
ignored, it only helps reading. Both voices of a song must have the same
length in ticks, so they stay together when the song loops.

Usage: python3 music.py OUTDIR  (writes music_data.c/.h and music_songs.json)
"""
import json
import os
import sys


NOTE = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
CPU_HZ = 16777216

# wave shapes for the lead: 32 samples, 0..15, made from a few harmonics
def _wave(harmonics):
    import math
    v = [sum(a * math.sin(2 * math.pi * k * i / 32 + ph) for k, a, ph in harmonics) for i in range(32)]
    lo, hi = min(v), max(v)
    return [round((x - lo) / (hi - lo) * 15) for x in v]


WAVES = {
    'sine': _wave([(1, 1.0, 0)]),                              # pure and soft (the old melody wave)
    'bell': _wave([(1, 1.0, 0), (2, 0.45, 0), (3, 0.12, 0)]),   # music box: brighter, round
    'hollow': _wave([(1, 1.0, 0), (3, 0.30, 0)]),              # flute-like, a little woody
    'reed': _wave([(1, 1.0, 0), (3, 0.40, 0), (5, 0.15, 0)]),  # clarinet-like: odd harmonics, reedy and warm
}


def midi(name):
    """'C4' -> 60, 'F#5' -> 78, 'Bb3' -> 58."""
    n = NOTE[name[0].upper()]
    rest = name[1:]
    while rest and rest[0] in '#b':
        n += 1 if rest[0] == '#' else -1
        rest = rest[1:]
    return n + 12 * (int(rest) + 1)


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def parse(text, bar=16):
    """Voice text -> list of (midi or 0, ticks). Every bar between "|"
    lines must be exactly `bar` ticks (catches typos); 0 = no check."""
    out, length, in_bar, n_bar = [], 4, 0, 1
    for tok in text.split():
        if tok == '|':
            if bar and in_bar != bar:
                raise ValueError(f'bar {n_bar} is {in_bar} ticks, not {bar}')
            in_bar, n_bar = 0, n_bar + 1
            continue
        name, _, ln = tok.partition(':')
        if ln:
            length = int(ln)
        if not 1 <= length <= 255:
            raise ValueError(f'bad length in {tok!r}')
        out.append((0 if name == 'r' else midi(name), length))
        in_bar += length
    if bar and in_bar != bar:
        raise ValueError(f'bar {n_bar} is {in_bar} ticks, not {bar}')
    return out


SONGS = {}


def song(key, title, tick, lead, bass, bar=16, loop=True, wave='sine', lead_level=0, lead_decay=0,
         lead_gap=2, bass_vol=6, bass_duty=1, bass_step=3, bass_gap=0):
    """lead_level: 0 = 100%, 1 = 75%, 2 = 50%, 3 = 25% wave volume.
    lead_decay: frames per step down (toward 25%), 0 = hold.
    lead_gap: frames at the end of each note where the lead fades out
    (one level per frame; the engine also fades in over 2 frames).
    bass_gap: frames of silence at the end of each bass note (0 = none;
    a hard cut clicks, so prefer a fading envelope).
    bass_vol, bass_step: square envelope start (0..15) and fade step (0 = hold).
    bass_duty: 0 = 12.5%, 1 = 25%, 2 = 50%.
    bar: ticks per bar (16 = 4/4 in sixteenths, 12 = 3/4)."""
    SONGS[key] = dict(title=title, tick=tick, bar=bar, lead=parse(lead, bar), bass=parse(bass, bar), loop=loop, wave=wave,
                      lead_level=lead_level, lead_decay=lead_decay, lead_gap=lead_gap,
                      bass_vol=bass_vol, bass_duty=bass_duty, bass_step=bass_step, bass_gap=bass_gap)


# ---------------------------------------------------------------- songs
# Title: bright and bouncy, C major (the "hello" jingle before it is C E G C).
# 112 bpm (8 frames per sixteenth), 16 bars: A (bars 1-8) climbs to a high
# C with a skipping dotted rhythm, B (9-16) is softer and stepwise and
# leads back. Chords: C Am F G C Am F-G C | F C F C Dm G C-Am G.
# Bass: plucked oom-pah on root and fifth. About 34 s per loop.
song('title', 'Title: Hello island', 8,
     lead='C5:2 E5:2 G5:3 E5:1 C6:4 G5:4 | A5:3 G5:1 E5:2 C5:2 A4:4 r:4 | '
          'F5:2 A5:2 C6:3 A5:1 F5:4 A5:4 | G5:3 F5:1 D5:2 F5:2 B4:4 D5:4 | '
          'C5:2 E5:2 G5:3 E5:1 C6:4 E6:4 | D6:3 C6:1 B5:2 A5:2 E5:8 | '
          'F5:2 A5:2 C6:2 A5:2 G5:2 B5:2 D6:2 B5:2 | C6:6 G5:2 C5:4 r:4 | '
          'A5:4 C6:4 A5:2 G5:2 F5:4 | G5:4 E5:4 C5:2 D5:2 E5:4 | '
          'A5:4 C6:4 D6:2 C6:2 A5:4 | G5:6 E5:2 G5:8 | '
          'F5:2 E5:2 D5:2 E5:2 F5:4 A5:4 | G5:2 F5:2 D5:2 F5:2 G5:4 B5:4 | '
          'C6:4 B5:2 G5:2 A5:4 E5:4 | B4:4 D5:2 F5:2 G5:4 r:4',
     bass='C3:4 G2 C3 G2 | A2 E3 A2 E3 | F2 C3 F2 C3 | G2 D3 G2 D3 | '
          'C3 G2 C3 G2 | A2 E3 A2 E3 | F2 C3 G2 D3 | C3 G2 C3 r | '
          'F2 C3 F2 C3 | C3 G2 C3 G2 | F2 C3 F2 C3 | C3 G2 C3 G2 | '
          'D3 A2 D3 A2 | G2 D3 G2 D3 | C3 G2 A2 E3 | G2 D3 G2 D3',
     wave='bell', lead_level=1, lead_decay=10, lead_gap=2, bass_vol=6, bass_duty=1, bass_step=3)


# Meadow: a sleepy waltz, F major, 3/4 (12 ticks a bar), 75 bpm (12 frames
# per sixteenth), 24 bars, about 58 s per loop. A (1-8) rises by broken
# chords, B (9-16) steps down in pairs and rests on F, A' (17-24) climbs
# to a high D and settles on A. Chords: F F Bb F Gm C F C | Dm Am Bb F Gm
# F C7 F | F F Bb F Bb F C7 F. Hollow (flute-like) lead that fades on long
# notes, at 50% so it sits under the title song; the bass rocks root -
# fifth - third, soft and round (50% duty), each note ringing most of a beat.
song('meadow', 'Meadow: Sleepy clover', 12,
     lead='C5:4 F5:4 A5:4 | G5:8 F5:4 | D5:4 F5:4 Bb5:4 | A5:12 | '
          'G5:4 Bb5:4 D6:4 | C6:6 Bb5:2 G5:4 | A5:4 G5:4 F5:4 | E5:8 G5:4 | '
          'A5:8 F5:4 | E5:8 C5:4 | D5:4 F5:4 Bb5:4 | A5:8 C6:4 | '
          'Bb5:6 A5:2 G5:4 | A5:6 G5:2 F5:4 | E5:4 G5:4 Bb5:4 | F5:8 r:4 | '
          'C5:4 F5:4 A5:4 | Bb5:6 A5:2 G5:4 | D5:4 F5:4 Bb5:4 | A5:8 C6:4 | '
          'D6:8 Bb5:4 | C6:4 A5:4 F5:4 | G5:6 A5:2 Bb5:4 | A5:8 r:4',
     bass='F2:4 C3 A2 | F2 C3 A2 | Bb2 F3 D3 | F2 C3 A2 | '
          'G2 D3 Bb2 | C3 G3 E3 | F2 C3 A2 | C3 G3 E3 | '
          'D3 A3 F3 | A2 E3 C3 | Bb2 F3 D3 | F2 C3 A2 | '
          'G2 D3 Bb2 | F2 C3 A2 | C3 G3 E3 | F2 C3 A2 | '
          'F2 C3 A2 | F2 C3 A2 | Bb2 F3 D3 | F2 C3 A2 | '
          'Bb2 F3 D3 | F2 C3 A2 | C3 G3 E3 | F2 C3 A2',
     bar=12, wave='hollow', lead_level=2, lead_decay=40, lead_gap=2, bass_vol=4, bass_duty=2, bass_step=7)


# Open screen: "What's inside?", a tip-toe loop while the child presses.
# C major pentatonic (C D E G A), so the press chimes (C6, E6) and the pop
# chime (A6) always fit. 112 bpm, 4 bars (8.5 s), plucked bell notes with
# rests between, like tiptoeing; bass oom-pah on short plucks. It stops at
# the pop, where the G major "ta-da" (tune_pop) leads into the reveal.
song('open', "Open: What's inside?", 8,
     lead='C5:2 r:2 E5:2 r:2 G5:2 r:2 E5:2 r:2 | D5:2 r:2 G5:2 r:2 A5:2 r:2 G5:2 r:2 | '
          'E5:2 r:2 G5:2 r:2 C6:2 r:2 A5:2 r:2 | G5:2 A5:2 G5:2 E5:2 D5:4 r:4',
     bass='C3:4 G2 C3 G2 | G2 D3 G2 D3 | C3 G2 A2 E3 | G2 D3 G2 B2',
     wave='bell', lead_level=1, lead_decay=4, lead_gap=2, bass_vol=5, bass_duty=1, bass_step=2)

# Reveal: "New friend!", played once when the friend lands on the cushion.
# Resolves the pop's G major ta-da to C. 150 bpm (6 frames a tick), 2 bars
# (3.2 s): a climbing arpeggio, a skip, and home on a held high C.
song('reveal', 'Reveal: New friend!', 6,
     lead='C5:2 E5:2 G5:2 C6:4 G5:2 C6:2 E6:2 | D6:3 C6:1 D6:2 E6:2 C6:8',
     bass='C3:4 G2 C3 E3 | G2 G2 C3:8',
     loop=False, wave='bell', lead_level=1, lead_decay=12, lead_gap=2, bass_vol=6, bass_duty=1, bass_step=3)


def alberti(chords):
    """Music box accompaniment: each chord as "G3:B3:D3" (low, middle,
    high) gives low-high-middle-high in eighth notes (2 ticks), twice per
    chord; "|" passes through as a bar line."""
    out = []
    for c in chords.split():
        if c == '|':
            out.append('|')
            continue
        lo, mid, hi = c.split(':')
        out += [f'{lo}:2', hi, mid, hi]
    return ' '.join(out)


# Shelf: "Music box", a tinkly theme while the child looks at the friends.
# G major (the other screens are C and F), 90 bpm (10 frames a tick),
# 16 bars (43 s): A (1-8) states a skipping tune, B (9-16) sings longer
# notes and ends on D7 to lead back. Bell lead that dies away fast like a
# music box comb; the bass voice plays a soft Alberti pattern (low, high,
# middle, high) as eighth-note plinks. Chords: G Em C D G Em Am-D G |
# C G Am D Em C D D7.
song('shelf', 'Shelf: Music box', 10,
     lead='B5:4 G5:2 B5:2 D6:6 B5:2 | B5:4 A5:2 G5:2 E5:8 | C6:4 G5:2 C6:2 E6:6 C6:2 | D6:4 C6:2 A5:2 F#5:8 | '
          'B5:4 G5:2 B5:2 D6:6 G6:2 | G6:4 E6:2 D6:2 B5:8 | C6:2 E6:2 A5:4 D6:2 F#6:2 A5:4 | G6:8 D6:4 B5:4 | '
          'E6:6 D6:2 C6:4 G5:4 | D6:6 C6:2 B5:4 G5:4 | C6:6 B5:2 A5:4 E5:4 | F#5:4 A5:4 D6:8 | '
          'E6:6 D6:2 B5:4 G5:4 | E6:4 C6:4 G6:8 | F#6:6 E6:2 D6:4 A5:4 | C6:4 A5:4 F#5:4 A5:4',
     bass=alberti('G3:B3:D4 G3:B3:D4 | E3:G3:B3 E3:G3:B3 | C3:E3:G3 C3:E3:G3 | D3:F#3:A3 D3:F#3:A3 | '
                  'G3:B3:D4 G3:B3:D4 | E3:G3:B3 E3:G3:B3 | A2:C3:E3 D3:F#3:A3 | G3:B3:D4 G3:B3:D4 | '
                  'C3:E3:G3 C3:E3:G3 | G3:B3:D4 G3:B3:D4 | A2:C3:E3 A2:C3:E3 | D3:F#3:A3 D3:F#3:A3 | '
                  'E3:G3:B3 E3:G3:B3 | C3:E3:G3 C3:E3:G3 | D3:F#3:A3 D3:F#3:A3 | D3:F#3:C4 D3:F#3:C4'),
     wave='bell', lead_level=1, lead_decay=8, lead_gap=2, bass_vol=4, bass_duty=1, bass_step=2)


# ---- area tunes (step 6 plays them; until then they are in the sound test)
# Each area has its own key, meter and lead sound: meadow F 3/4 hollow,
# shore D 6/8 sine, woods A minor 4/4 reed, cloud hill Eb 4/4 slow bell.

# Shore: "Sea breeze", D major, 6/8 (12 ticks a bar, two dotted-quarter
# beats), 10 frames a tick (the swing beat at 60 bpm), 24 bars A B A'
# (48 s). Long-short sways like small waves; soft sine lead; the bass
# rocks root - fifth on each dotted beat. Chords: D G D A D G A D |
# Bm G D A Bm Em G-A A | D G D Bm Em A D A7.
song('shore', 'Shore: Sea breeze', 10,
     lead='A5:4 F#5:2 A5:4 D6:2 | B5:6 G5:6 | A5:4 F#5:2 D5:4 F#5:2 | E5:6 r:2 C#5:2 E5:2 | '
          'A5:4 F#5:2 A5:4 D6:2 | D6:4 B5:2 G5:6 | C#6:4 B5:2 A5:4 G5:2 | F#5:12 | '
          'D6:4 C#6:2 B5:6 | B5:4 A5:2 G5:6 | A5:4 G5:2 F#5:6 | E5:12 | '
          'F#5:4 G5:2 A5:4 B5:2 | G5:6 E5:6 | D5:4 G5:2 E5:4 A5:2 | C#6:4 B5:2 A5:6 | '
          'A5:4 F#5:2 A5:4 D6:2 | B5:6 G5:6 | A5:4 F#5:2 D5:4 F#5:2 | B5:6 F#5:6 | '
          'G5:4 B5:2 E6:6 | E6:4 C#6:2 A5:6 | D6:4 A5:2 F#5:6 | E5:4 C#5:2 E5:4 G5:2',
     bass='D3:6 A2 | G2 D3 | D3 A2 | A2 E3 | D3 A2 | G2 D3 | A2 E3 | D3 A2 | '
          'B2 F#3 | G2 D3 | D3 A2 | A2 E3 | B2 F#3 | E3 B2 | G2 A2 | A2 E3 | '
          'D3 A2 | G2 D3 | D3 A2 | B2 F#3 | E3 B2 | A2 E3 | D3 A2 | A2 E3',
     bar=12, wave='sine', lead_level=2, lead_decay=40, lead_gap=2, bass_vol=4, bass_duty=2, bass_step=7)

# Woods: "Acorn trail", A minor turning to C major, 4/4, 11 frames a tick
# (82 bpm), 16 bars (47 s). A (1-8) strolls with dotted steps, B (9-16)
# opens up in major and ends on E to lead back. Reed lead; the bass walks
# the chord in plucked quarter notes. Chords: Am Am Dm E Am F G C |
# F C G Am F C Dm E.
song('woods', 'Woods: Acorn trail', 11,
     lead='E5:3 D5:1 C5:4 A4:4 C5:4 | A4:3 B4:1 C5:4 E5:8 | F5:3 E5:1 D5:4 A4:4 D5:4 | E5:6 D5:2 B4:4 G#4:4 | '
          'A4:3 B4:1 C5:4 E5:4 A5:4 | A5:3 G5:1 F5:4 C5:4 F5:4 | G5:3 F5:1 D5:4 B4:4 D5:4 | C5:8 E5:4 G5:4 | '
          'A5:6 G5:2 F5:4 C5:4 | G5:6 F5:2 E5:4 C5:4 | D5:3 E5:1 F5:4 G5:4 B5:4 | C6:8 A5:8 | '
          'A5:3 G5:1 F5:4 A5:4 C6:4 | G5:3 F5:1 E5:4 G5:4 C6:4 | F5:3 E5:1 D5:4 F5:4 A5:4 | G#5:6 A5:2 B5:4 E5:4',
     bass='A2:4 C3 E3 C3 | A2 C3 E3 C3 | D3 F3 A3 F3 | E2 G#2 B2 G#2 | '
          'A2 C3 E3 C3 | F2 A2 C3 A2 | G2 B2 D3 B2 | C3 E3 G3 E3 | '
          'F2 A2 C3 A2 | C3 E3 G3 E3 | G2 B2 D3 B2 | A2 C3 E3 C3 | '
          'F2 A2 C3 A2 | C3 E3 G3 E3 | D3 F3 A3 F3 | E2 G#2 B2 G#2',
     wave='reed', lead_level=2, lead_decay=30, lead_gap=2, bass_vol=5, bass_duty=1, bass_step=3)

# Cloud Hill: "Floating up", Eb major, 4/4, 12 frames a tick (75 bpm),
# 16 bars (51 s). Wide leaps up and long notes that drift down; bell lead
# with a slow fade (a celesta more than a music box); the bass rolls root -
# fifth - octave - fifth. Chords: Eb Ab Eb Bb Cm Ab Bb Eb | Ab Eb Fm Bb
# Gm Cm Ab Bb.
song('cloud', 'Cloud Hill: Floating up', 12,
     lead='G5:4 Bb5:4 Eb6:8 | C6:4 Eb6:4 Ab5:8 | Bb5:4 Eb6:4 G6:8 | F6:8 D6:4 Bb5:4 | '
          'Eb6:4 D6:4 C6:8 | C6:4 Bb5:4 Ab5:8 | Bb5:4 D6:4 F6:4 D6:4 | Eb6:12 r:4 | '
          'C6:6 Eb6:2 F6:4 Eb6:4 | G6:6 F6:2 Eb6:8 | F6:4 C6:4 Ab5:8 | Bb5:6 C6:2 D6:8 | '
          'D6:4 Bb5:4 G5:8 | Eb6:4 C6:4 G5:8 | Ab5:4 C6:4 Eb6:4 C6:4 | D6:8 Bb5:4 F5:4',
     bass='Eb3:4 Bb3 Eb4 Bb3 | Ab2 Eb3 Ab3 Eb3 | Eb3 Bb3 Eb4 Bb3 | Bb2 F3 Bb3 F3 | '
          'C3 G3 C4 G3 | Ab2 Eb3 Ab3 Eb3 | Bb2 F3 Bb3 F3 | Eb3 Bb3 Eb4 Bb3 | '
          'Ab2 Eb3 Ab3 Eb3 | Eb3 Bb3 Eb4 Bb3 | F2 C3 F3 C3 | Bb2 F3 Bb3 F3 | '
          'G2 D3 G3 D3 | C3 G3 C4 G3 | Ab2 Eb3 Ab3 Eb3 | Bb2 F3 Bb3 F3',
     wave='bell', lead_level=1, lead_decay=24, lead_gap=2, bass_vol=4, bass_duty=2, bass_step=5)


# ---------------------------------------------------------------- export
def sq_rate(f):
    return 2048 - round(CPU_HZ / 128 / f)


def wave_rate(f):
    return 2048 - round(CPU_HZ / 256 / f)


def check_rates():
    """Every note used must land within 12 cents of its true pitch."""
    import math
    used = {m for s in SONGS.values() for v in ('lead', 'bass') for m, _ in s[v] if m}
    for key, s in SONGS.items():
        for v, fn, div in (('lead', wave_rate, 256), ('bass', sq_rate, 128)):
            for m, _ in s[v]:
                if not m:
                    continue
                r = fn(hz(m))
                if not 0 <= r < 2048:
                    raise ValueError(f'{key} {v}: note {m} out of range')
                real = CPU_HZ / div / (2048 - r)
                cents = 1200 * math.log2(real / hz(m))
                if abs(cents) > 12:
                    raise ValueError(f'{key} {v}: note {m} is {cents:.1f} cents off')
    return used


def export(outdir):
    check_rates()
    for key, s in SONGS.items():
        tl, tb = sum(n for _, n in s['lead']), sum(n for _, n in s['bass'])
        if tl != tb:
            raise ValueError(f'{key}: lead is {tl} ticks, bass is {tb}')
    c = ['/* Generated by tools/music.py. Do not edit. */', '#include "music_data.h"', '']
    h = ['/* Generated by tools/music.py. Do not edit. */', '#ifndef MUSIC_DATA_H', '#define MUSIC_DATA_H',
         '#include "sound.h"', '']

    def arr(ctype, ident, values, per=12, fmt='{}'):
        body = ',\n'.join('    ' + ', '.join(fmt.format(v) for v in values[i:i + per])
                          for i in range(0, len(values), per))
        c.append(f'const {ctype} {ident}[{len(values)}] __attribute__((aligned(4))) = {{\n{body}\n}};')
        h.append(f'extern const {ctype} {ident}[{len(values)}];')

    arr('u16', 'music_sq_rate', [sq_rate(hz(m)) if m >= 36 else 0 for m in range(128)], fmt='{:4d}')
    arr('u16', 'music_wave_rate', [wave_rate(hz(m)) if m >= 24 else 0 for m in range(128)], fmt='{:4d}')
    for name, w in WAVES.items():
        words = []
        for i in range(0, 32, 8):          # wave RAM: 2 samples per byte, the high nibble plays first
            v = 0
            for j in range(4):
                v |= ((w[i + 2 * j] << 4) | w[i + 2 * j + 1]) << (8 * j)
            words.append(v)
        arr('u32', f'music_wave_{name}', words, fmt='0x{:08X}')
    for key, sg in SONGS.items():
        for v in ('lead', 'bass'):
            data = []
            for m, n in sg[v]:
                data += [m, n]
            arr('u8', f'song_{key}_{v}', data, per=16)
    for i, key in enumerate(SONGS):
        h.append(f'#define SONG_{key.upper()} {i}')
    h.append(f'#define SONG_COUNT {len(SONGS)}')
    h.append('extern const Song songs[SONG_COUNT];')
    c.append('const Song songs[SONG_COUNT] = {')
    for key, sg in SONGS.items():
        c.append(f'    {{"{sg["title"]}", song_{key}_lead, song_{key}_bass, {len(sg["lead"])}, {len(sg["bass"])},\n'
                 f'     music_wave_{sg["wave"]}, {sg["tick"]}, {int(sg["loop"])}, {sg["lead_level"]}, '
                 f'{sg["lead_decay"]}, {sg["lead_gap"]}, {sg["bass_vol"]}, {sg["bass_duty"]}, '
                 f'{sg["bass_step"]}, {sg["bass_gap"]}}},')
    c.append('};')
    h += ['', '#endif']
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, 'music_data.c'), 'w') as f:
        f.write('\n'.join(c) + '\n')
    with open(os.path.join(outdir, 'music_data.h'), 'w') as f:
        f.write('\n'.join(h) + '\n')
    with open(os.path.join(outdir, 'music_songs.json'), 'w') as f:
        json.dump({k: dict(s, index=i, wave_samples=WAVES[s['wave']]) for i, (k, s) in enumerate(SONGS.items())},
                  f, indent=1)


if __name__ == '__main__':
    export(sys.argv[1] if len(sys.argv) > 1 else 'build')
