/* Port of the GBA test/check_text.py (step 7.4): every text the game
 * prints fits the place it is printed into, in the web font (art.json,
 * from `npm run assets`), and every letter has a glyph. */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';

const art = JSON.parse(readFileSync(new URL('../../public/gen/art.json', import.meta.url), 'utf8')) as {
  font: { glyphs: Record<string, string[]> };
  names: { species: Record<string, string>; flavorNames: string[]; areas: { name: string }[] };
  layout: { shelf: { pillW: number }; countPillW: number };
};
const glyphs = art.font.glyphs;
const width = (s: string) => [...s].reduce((w, ch) => w + glyphs[ch][0].length + 1, 0) - (s ? 1 : 0);

const NAMES = Object.values(art.names.species).flatMap((sp) => art.names.flavorNames.map((fl) => `${fl} ${sp}`));
const AREAS = art.names.areas.map((a) => a.name);

/* where, room in px, the texts printed there */
const PLACES: [string, number, string[]][] = [
  ['shelf name pill (shelf.ts)', art.layout.shelf.pillW, [...NAMES, ...AREAS, 'Find me!']],
  ['reveal and close-up name pill (closeup.ts, the backdrop pill is 126 px inside)', 126, NAMES],
  ['title button (title.ts, between the two hearts)', 96, ['Play', 'Continue']],
  ['map counter (meadow.ts, 32 px after the icon)', 32, Array.from({ length: 21 }, (_, n) => `${n}/20`)],
  ['title version (title.ts, on the island)', 150, ['0.1.0 abcdef0', '10.10.10 abcdef0']],
];

describe('every text fits and every letter has a glyph', () => {
  it.each(PLACES)('%s', (_where, room, texts) => {
    const missing = texts.flatMap((t) => [...t].filter((ch) => !(ch in glyphs)));
    expect(missing).toEqual([]);
    const over = texts.filter((t) => width(t) > room - 2); /* 1 px clear on each side */
    expect(over).toEqual([]);
  });
});
