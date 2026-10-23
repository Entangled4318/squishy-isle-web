# Squishy Isle (web): handoff

Read `CLAUDE.md` and `docs/PLAN.md` first.

## Start here (next session)

- Live site: https://entangled4318.github.io/squishy-isle-web/ (Pages is
  on; each push to `main` deploys). Test pages: `?gallery`, `?sound`.
- Open question to the owner: the squishy size on the map. Claude
  recommended 16 px (the GBA size): at 32 px the friends are bigger than
  Pip and crowd the 20-friend pen, and tap zones are 64 points either way.
  Ask this first if the owner has not answered.
- Owner to do: device checklists 1 to 3 (`docs/DEVICE_CHECKLIST.md`) on an
  iPhone and an iPad. Fix what they find before or during M4.
- Next work: M4, the core loop in Blossom Meadow (`docs/PLAN.md`). Give
  the owner an overview of the M4 sub-steps and get approval first.
- New container: `npm install`, `pip install numpy pillow`,
  `npm run assets`, then `npm run check`. The GBA repo
  (`Entangled4318/squishy-isle`) is the reference for M4: port
  `rom/src/viewer.c`, `title.c`, `open.c`, `closeup.c`, `shelf.c`.

## Status

| Step | State |
| --- | --- |
| Planning steps 1 to 6 | Done. Decisions and milestones in `docs/PLAN.md` |
| Repo setup | Done. `tools/` from GBA v1.6 (`1d99c2e`), `tests/check_map.py` (20 checks) |
| M1. Foundations | Built; CI green; Pages on. Waits for the owner: device checklist 1 |
| M2. Art pipeline | Built. Waits for the owner: pick the squishy size (gallery page 1) |
| M3. Music and sound | Built. Waits for the owner: listen on the device (checklist 3) |
| M4. Core loop in the meadow | Next, after the owner picks the squishy size |

## Owner notes

- Path C (TypeScript rewrite) in this separate repo. Claude recommended B
  on cost; the owner chose C so the web game can grow apart.
- The repo is public; free GitHub Pages from this repo.
- The owner liked the number gate for the grown-up start-over.
- Owner: "proceed with all steps you can, save the ones you need something
  from me last".

## M1 progress

1. **Rules and save.** `src/rules/`: the 144-byte save record (the GBA
   layout and CRC-32, `save-data.ts`), the collection rules
   (`collection.ts`) and the two-slot store (`save-store.ts`), ported from
   the GBA `collection.c` and `save.c`. `tests/unit/` ports
   `test_collection.c` and `test_save.c` check by check (30 tests), plus
   100 fixture tests: `tests/fixtures/gen_rules.c` runs the GBA C rules on
   50 games and 50 random-byte sanitize cases and writes `rules.json`; the
   TypeScript gives the same rolls, letters, followers, random numbers,
   sanitize results and save bytes. Found by the port: a write cut after 5
   bytes on a blank slot leaves version `0xFF02`, which the C code reads as
   "a newer version" and never writes again, so later writes all go over
   the one good save. The web port takes versions 3..255 only as newer
   (test "a first write cut on a blank chip..."). The same edge exists in
   the GBA ROM (very unlikely: a power cut in the first 5 bytes of the
   first save); not changed there.
2. **Engine.** `src/engine/`: `loop.ts` fixed 60 Hz step (at most 8 steps a
   browser frame; test mode runs steps only from the driver); `screen.ts`
   art pixels at a whole-number device-pixel scale, at least 240 x 160
   (landscape) or 160 x 240 (portrait), safe-area insets read from
   `env()`; `input.ts` touch down acts, first finger only (others are
   `extra`: sparkle only), no zoom, scroll or menus; `scenes.ts` the GBA
   scene manager (white fade 3 of 16 levels a step, input blocked during
   fades); `sparkles.ts`; `audio.ts` (unlock on every touch, audio session
   "playback", suspend when hidden); `log.ts` (`dbg()` lines `f<frame> ...`).
3. **Shell.** `src/shell/storage.ts`: slots in memory, each write to
   localStorage at once and copied to IndexedDB; at load each slot takes
   the better copy (`betterCopy`); `persist()`; keys start with
   `squishy-isle-web:`. `install-hint.ts` (iOS Safari tab only, once).
   `sw-template.js` + the `vite.config.ts` plugin: precache every built
   file, a new version waits for the next cold launch. `index.html`
   (viewport-fit=cover, Safari tags, noindex), `public/manifest.webmanifest`.
   `tools/export_web.py` writes the icons into `public/gen/` (not
   committed; CI runs it).
4. **Tap test** (`src/scenes/taptest.ts`): each tap counts in the save's
   `squishes` field, chimes and hops; a panel shows build, display mode,
   boots, storage, persist, sound, view and safe areas; dashed safe-area
   frame and the three button spots.
5. **Play tests** (`tests/e2e/taptest.spec.ts`, iPhone 13 landscape and
   iPad gen 7 portrait sizes, Chromium with touch): new save, taps count
   and survive a reload, the save survives losing localStorage or
   IndexedDB, second finger only sparkles (driver and real CDP two-finger
   touch), taps during the fade-in only sparkle, whole-number view in both
   orientations, no zoom CSS, offline after the first visit, install hint.
   22 checks pass.
6. **CI** `.github/workflows/deploy.yml`: art, map checks, typecheck, unit
   tests, build, play tests, deploy `main` to Pages.
7. **Device checklist 1** in `docs/DEVICE_CHECKLIST.md`.

Scores: rules port 9 (byte-exact against C), tap test 8.5 (first pass
sparkles 6: pastel on pastel; now a dark pink edge), storage 8.5 (device
check pending).

## M2 progress

1. **Exporter** `tools/export_web.py` (about 22 s): the GBA art functions
   as RGBA PNG. 929 sprites on 3 atlas pages of 1024 x 1024 (shelf packed,
   1 px gap): every squishy in 5 flavors at 16 (idle, squish), 32 (idle,
   open) and 64 px (idle, blink, open, squish) in the ROM look, the
   silhouettes in each shelf row's tint, 80 gifts, 64 px containers (body,
   open, lid) and 16 px map containers in each area's 5 colors, Pip, Momo,
   the UI, confetti, snacks, the logo letters with their positions. 13
   screens (title, close-up, open, letter back and card, 4 shelf pages, 4
   rooms). 4 maps: ground, overlay and a glint mask, plus the area data in
   `art.json` (collision as a 0/1 string, spawn, spots, pen, sign, signs,
   doors, exits, gates, mailbox, basket, Momo's bed, the glint's 4 colors).
   The 5x7 font (plus `(`, `)` and `_`, which the GBA never printed),
   names, layout numbers (shelf, room, meter, count pill, Pip's feet
   row). `music.json` from `music.py` for M3. 508 KB in all.
2. **Loader** `src/engine/art.ts`: atlases, screens and maps by path,
   `draw(name, x, y, {flipX, sx, sy})`, `text()` and `textWidth()` in the
   pixel font.
3. **Gallery** `?gallery` (`src/scenes/gallery.ts`): 26 pages; page 1 is
   the squishy size on the map (16 px as on the GBA, against 32 px, with
   Apple's 44-point touch ring). Tap the right side for the next page.
   `tests/e2e/gallery.spec.ts` walks every page with no error (`SHOTS=dir`
   saves screenshots).

Score: art export 8.5 (first pass 8: the font had no `(`, `)`, `_`).
Not done in M2: the `check_text.py` port moves to M4, when the game's
strings move to TypeScript.

## M3 progress

1. **Sound chip** `src/audio/psg.ts`: the GBA's four PSG channels (squares
   with duty and envelope, the 32-sample 4-bit wave with mute/100/75/50/25 %,
   noise from the 15/7-bit shift register), positive levels summed at the
   game's master volume 6/7, then a 20 Hz DC block (the output capacitor),
   4 sub-steps a sample against aliasing. No browser API: tests render it
   in Node.
2. **Engine** `src/audio/engine.ts`: `sound.c` (v1.6) line for line, the
   same register values each frame: songs with the lead's one-level fades,
   attack, decay and release; the bass envelope; jingles (`TUNE_HELLO`,
   `TUNE_POP`) that pause the song; the boing that borrows channel 2; the
   squeak, hop, chime, blip, tick and pop; a looping song resumes where it
   was left. Music tables round like `music.py`, effect macros truncate
   like the C macros. `Renderer` runs one engine frame every 1/59.7275 s
   of audio.
3. **Worklet** `src/audio/worklet.ts` (10 KB, own bundle file, in the
   offline cache): the engine on the audio thread, so music keeps time
   whatever the game's frame rate. `src/engine/audio.ts` `Sound` sends
   commands (queued until the worklet is ready) and gets the engine's log
   lines back (`song start N`, `music loop N`, `song stop N`).
4. **Sound test** `?sound`: the 8 songs (left) and the effects (right).
5. **Tests** `tests/unit/audio.test.ts` (29): every lead and bass note of
   the 8 songs within 25 cents (YIN, voice alone), exact tempo from the
   loop log, the register writes of loop 2 equal loop 1, lead loudness of
   loop 2 within 5 % of loop 1, the reveal song stops by itself, the lead
   after a jingle at its own pitch (GBA 7.6), resume and the bass after
   the boing, no clicks (2 ms smoothed step under 30 % of peak), effects
   at least half the songs' peak and not clipping.
   `tests/e2e/sound.spec.ts`: a real tap starts the worklet in Chromium,
   a song starts and stops.

Scores: engine port 9 (register-exact), sound chip 8.5 (pitch and tempo
checked; the timbre still needs the owner's ear on a device). Trap: the
loop check first failed from the test, not the engine (one-frame renders
round 803.6 samples to 804 and drift; record inside `frameTick`). Lead
and bass an octave or a fifth apart add up by phase, so loudness is
compared per voice, as on the GBA.

## Commands

    npm install
    pip install numpy pillow
    npm run assets                      # icons into public/gen
    npm run typecheck && npm test       # 130 unit checks
    npm run build && npm run e2e        # 22 play checks
    python3 tests/check_map.py OUTDIR   # 20 map checks
    # fixtures from the GBA C code (needs ../squishy-isle):
    gcc -O2 -I ../squishy-isle/rom/src tests/fixtures/gen_rules.c -o build/gen_rules
    ./build/gen_rules > tests/fixtures/rules.json

Test mode: `?test=1` (steps only from `window.__squishy.run(n)`), `&sw=1`
registers the service worker, `&hint=1` shows the install hint.

## Traps found

- The squishy renderer draws bodies at any size, but faces (eyes, mouth,
  blush, nose) are pixel stamps for 16, 32 and 64 px only
  (`squishies.py` `EYE`, `MOUTH`, `BLUSH`, `NOSE`). Larger squishies need
  new stamps (M2).
- `npm install` fails with "edgesOut" when Vite and Vitest majors do not
  match. Vite 8 goes with Vitest 5.
- Playwright is pinned to 1.56.1: the container's Chromium is build 1194.
- The e2e helper `drive()` sends its function as text: values from outside
  must go in its `arg`.
- C does not fix the order of a call's arguments: the fixture generator
  makes one `game_rand()` call per statement.
