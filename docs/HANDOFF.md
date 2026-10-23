# Squishy Isle (web): handoff

Read `CLAUDE.md` and `docs/PLAN.md` first.

## Status

| Step | State |
| --- | --- |
| Planning steps 1 to 6 | Done. Decisions and milestones in `docs/PLAN.md` |
| Repo setup | Done. `tools/` from GBA v1.6 (`1d99c2e`), `tests/check_map.py` (20 checks) |
| M1. Foundations | Built and tested here. Waits for the owner: turn on Pages, then device checklist 1 |
| M2. Art pipeline | Next |

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
