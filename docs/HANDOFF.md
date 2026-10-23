# Squishy Isle (web): handoff

Read `CLAUDE.md` and `docs/PLAN.md` first.

## Start here (next session)

- Live site: https://entangled4318.github.io/squishy-isle-web/ (Pages is
  on; each push to `main` deploys). Test pages: `?gallery`, `?sound`,
  `?title` (the game, M4).
- M4 work is on the branch `claude/magical-euler-0drmuw`. It merges to
  `main` at the end of M4. The tap test stays the default page until the
  owner has done device checklist 1 and agrees to make the title the
  default (ask before the switch: it replaces a working page).
- Owner decision: the squishy size on the map is **16 px** (the GBA size).
- Owner approved the M4 sub-steps below and said: proceed with all
  sub-steps unless you need me. Next: sub-step 7, tests and release. Stop after each sub-step with a short report.
- Owner to do: device checklists 1 to 3 (`docs/DEVICE_CHECKLIST.md`) on an
  iPhone and an iPad. Fix what they find inside the closest sub-step.
- New container: `npm install`, `pip install numpy pillow`,
  `npm run assets`, then `npm run check`. If Playwright cannot find
  `chromium_headless_shell-1194`, see "Traps found". The GBA repo
  (`Entangled4318/squishy-isle`) is the reference for M4: port
  `rom/src/viewer.c`, `title.c`, `open.c`, `closeup.c`, `shelf.c`.

## M4 sub-steps (approved)

1. Title screen. Done.
2. Meadow map and camera: sharp whole-number scale, more island along the
   long side, both orientations. Done.
3. Pip moves: tap to walk by the shortest path, drag to steer, the
   movement assist, the hop. Owner added: Momo asleep at the gate. Done.
4. Containers and reveal: containers on the map, the guide arrow, the open
   screen, the reveal, the counter pill, a save at each reveal. Done.
5. Followers and the pen: the follower line, the pen, the poke. Done.
6. Shelf and close-up: shelf pages, close-up, the home button, the other
   save moments. Done.
7. Tests and release: the touch mash test, the first play scripts, the
   `check_text.py` port, then the merge to `main` for the first play test
   with the child.

## Status

| Step | State |
| --- | --- |
| Planning steps 1 to 6 | Done. Decisions and milestones in `docs/PLAN.md` |
| Repo setup | Done. `tools/` from GBA v1.6 (`1d99c2e`), `tests/check_map.py` (20 checks) |
| M1. Foundations | Built; CI green; Pages on. Waits for the owner: device checklist 1 |
| M2. Art pipeline | Built. Owner picked 16 px for the map |
| M3. Music and sound | Built. Waits for the owner: listen on the device (checklist 3) |
| M4. Core loop in the meadow | Sub-steps 1 to 6 of 7 done (title, map, moves, containers, friends, shelf), on branch `claude/magical-euler-0drmuw` |

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

## M4 progress

1. **Title** `src/scenes/title.ts`, from the GBA `title.c`: the letters
   drop and bounce with a chime each, four friends hop one at a time, Pip,
   six twinkles, the letters bob. One button: "Play" on an empty save
   (makes a new game from the frame, the save's random number and the
   boot count), "Continue" when the save has friends. No "New game" here
   (M5 grown-up page). Sound starts only on a touch, so the first tap of a
   visit says hello (jingle, title song, the letters hop) and the next tap
   plays; a tap during the drop ends the drop and is that hello. A tap
   always counts as the hello, so a device with no sound still plays.
   10 frames after the hello, taps only sparkle (GBA `menu_wait`). The
   version and commit show small at the bottom, for a grown-up.
   `src/scenes/meadow.ts` is a stand-in until sub-step 2 (a tap goes back
   to the title).
2. **Fixed screens** `src/scenes/backdrop.ts`: a 240 x 160 backdrop draws
   at its own whole-number scale, centred (in portrait it is smaller than
   the view's scale, so it fits). The side bands show the backdrop
   mirrored, the bands above and below repeat the edge rows.
   `toFixed()` moves a touch into backdrop pixels. Also
   `src/engine/gba.ts` (`isin`, C integer division) and `textOutlined()`.
3. **Sound before the first touch** is now dropped, not queued: the queue
   played a burst of the title's letter chimes on the first tap.
4. **Tests** `tests/e2e/title.spec.ts` (3 checks a device): the drop ends
   by itself at frame 129, hello then play, the 10-frame wait, a new game
   on an empty save, back from the meadow stand-in; a real tap during the
   drop; Continue keeps the friends. 159 unit and 32 play checks pass.

Score: title 8.5 (first pass 7.5: the side bands stretched the edge
column into dark stripes where the pink tree touches the edge; the
version text crossed the island's edge and then touched a heart; with no
sound, the game could never leave the title).

5. **Meadow map and camera** `src/scenes/meadow.ts`, from the GBA
   `viewer.c`: the ground, the water glint (the mask tinted in the area's
   4 shimmer colors, next color every 12 frames), world sprites sorted by
   feet row (nearest last), then the overlay (tree tops over sprites).
   Pip stands with his shadow at 5/16 (the GBA blend). The camera keeps
   Pip 12 px above the middle and stops at the map's edges; a view larger
   than the map centres it. The view is the screen in art pixels, so a
   wide phone shows more meadow sideways and an iPad in portrait shows
   more upward. The area song plays. Continue puts Pip back at the saved
   spot once per boot if it is walkable, else at the house; a new game
   starts at the house (`reset()`, GBA `meadow_reset`). One `Meadow`
   object lives for the whole run, so Pip keeps his place between visits.
   Taps only sparkle until sub-step 3. Test driver: `meadow()`,
   `placePip(x, y)`, `goMeadow()`.
6. **Tests** `tests/e2e/meadow.spec.ts` (2 checks a device): the start at
   the house, the camera position, both corners clamped, the glint
   changes after 12 frames. 159 unit and 36 play checks pass.

Score: map and camera 8.5 (first pass 8: a new meadow object on each
visit would have lost Pip's place; found before the first run).
Not done yet: Momo asleep at the Berry Woods gate (the bridge, east
edge). The gate blocks Pip in sub-step 3, so Momo must be drawn there
too, or the block is an invisible wall.

7. **Pip moves** (`src/scenes/meadow.ts`, `src/scenes/path.ts`). A touch
   on the ground walks Pip by the shortest path: breadth-first search on
   the 4 px collision cells (8 directions, no corner cutting); a free cell
   is one where Pip's feet box fits at the cell's middle. A target he
   cannot reach (the pen, the pond) gives the nearest reachable cell. The
   path drops waypoints that Pip can walk to in a straight line (up to 4
   checks a frame). Each frame is one GBA `move()` toward the next
   waypoint: 1.25 px (8.8 fixed), same speed on diagonals, the stair-step
   sidestep and the edge assist. Pip faces the larger part of the step,
   with a little stickiness so he does not flicker on diagonals. A finger
   that stays down and moves gets a new path when it enters a new cell,
   at most every 6 frames. A walk with no progress for 20 frames stops.
   A tap on Pip is the hop (GBA B); a tap on Momo a giggle hop and a
   squeak. Tap zones: 32 points round the middle (64-point zones) or the
   thing's half size, the nearest thing wins. Pip's spot saves after he
   stands still 60 frames (GBA `save_pos`). Walk frames and the 1 px bob
   as on the GBA. Momo sleeps on each shut gate (breathing, two z's) and
   the gate blocks Pip as in `map_blocked`; the heart meter is M6.
   Doors and exits wait for M5 (house) and M6 (areas).
8. **Tests**: `tests/unit/path.test.ts` (6) and `tests/e2e/walk.spec.ts`
   (6 a device): a straight walk, round the house, the pen and the pond,
   a drag, the hop, Momo's giggle and the shut bridge, the saved spot,
   300 random taps and drags with Pip never in a wall. 165 unit and 48
   play checks pass.

Score: movement 8.5 (first pass 8.5; two test expectations were wrong,
not the game: the walk round a wall end, and Pip stops beside Momo, not
west of the gate). To judge on a device: walk speed and the drag feel.

9. **Containers** (in `meadow.ts`): 3 boxes at the area's spots (GBA
   `choose_spot`: away from Pip, off screen if possible; the first box of
   a game in view by the cottage), 5 colors with no two alike, a hop
   every few seconds, a gold twinkle walking round each, 90 frames before
   an opened box comes back elsewhere. Boxes block Pip. A tap on a box (or
   near it) walks Pip to it and it opens when he touches it (6 px); a tap
   while touching opens at once. The guide arrow shows after 5 s without
   an open, points from Pip at the nearest box, blinks; a tap on it walks
   to that box. The counter pill (area icon, "n/20") sits top right inside
   the safe area and hops twice when the count went up since the last
   visit. Random numbers come from the save (`collection.rand()`), as the
   GBA used `game_rand()`.
10. **Open screen** `src/scenes/open.ts` (GBA `open.c`): a tap anywhere is
    one press (14-frame cool-down); two jumps with rising chimes and a
    boing, the third pops the lid (spinning, flying), a ring of sparkles
    and puffs, the pop and the ta-da jingle. The friend is added (and the
    save written) at the pop. With no tap it presses itself after 4 s,
    then every 70 frames. The GBA's big A button is left out; the three
    hearts fill and the next one bobs. `art.drawAffine()` does the GBA
    rotate and scale (1/256 turn).
11. **Reveal and close-up** `src/scenes/closeup.ts` (GBA `closeup.c`): the
    friend drops in, lands with a squeak, the reveal song, confetti (from
    the save's random numbers) and a star ring. Taps after 20 frames
    squish (3 at most); after 3 squishes or 5 s it hops away to the map.
    Close-up mode is built for sub-step 6 (tap the friend to squish, tap
    away to go back, the 3-in-a-row rule). The name shows in the pill.
    `drawFixed()` takes a row from which the side bands stretch the edge
    column instead of mirroring (no half pills at the screen edges).
12. **Tests** `tests/e2e/boxes.spec.ts` (4 a device): the whole loop with
    3 taps and 3 squishes, the save and the respawn; the self-opening box
    and the friend leaving by itself; the arrow and a tap on it; 60 taps
    on the open screen pop it once. 165 unit and 56 play checks pass.

Score: containers and reveal 8.5 (first pass 8: the arrow blinked per
browser frame, so twice as fast on a 120 Hz iPad; the reveal's side
bands showed half name pills; the open hearts touched).

13. **Friends on the map** (in `meadow.ts`, GBA `viewer.c`): up to 3
    followers (the save's line) walk 14 of Pip's steps apart on a 64-step
    trail, hop while walking and after Pip's hop; the line is laid out
    behind Pip on entry (other sides if blocked) and after a jump. The
    area's other found friends roam in the pen: the roomiest of 10 random
    spots, half a pixel a frame, sidestep or give way when crowded (13
    px), at most 3 new targets a frame, local random numbers (the save's
    stay untouched). All 16 px, as the owner chose. A tap on a friend
    (zone as for Pip) squishes it at once: squeak in its flavor, the
    squish frame, a hop, a heart that floats up and blinks out; a pen
    friend stands still for it. Momo's tickle now uses the boing (GBA).
14. **Tests** `tests/e2e/friends.spec.ts` (3 a device): 3 follow and the
    rest stay in the pen, the line trails Pip; a tap on a pen friend and
    on a follower; a full page has no boxes and 17 friends spread in the
    pen with none on top of another. 165 unit and 62 play checks pass.

Score: friends 8.5 (first pass 8: after a jump the line stayed where
Pip had been).

15. **Round buttons** `src/scenes/button.ts`: a 21 px pink disc drawn in
    code (the GBA had no such button), top-left inside the safe area, a
    zone of at least 64 points, pushed down for a moment on a tap. The
    home button (a house) is on the shelf and the close-up and goes to
    the map. It is not on the open screen or the reveal: those finish by
    themselves in a few seconds, and leaving them would drop the box.
    The map has the shelf button (a 16 px friend) in the same corner (GBA
    START; Pip's spot saves first). `fixedLayout()` takes the button room:
    the fixed screen moves (or shrinks a step) so the button never covers
    it; only an iPad in landscape shrinks (9 to 8).
16. **Shelf** `src/scenes/shelf.ts` (GBA `shelf.c`): 4 pages, 32 px
    friends or silhouettes, sparkle twinkles, the name pill (the area's
    name, a friend's name, or "Find me!"). A tap on a tab turns to that
    page (chime), a sideways swipe of 30 px turns one page, a tap on a
    found friend shows the frame and its open face and goes to the
    close-up, a tap on a silhouette wiggles it with "Find me!". It opens
    on the current area's page after an area change. The bands round the
    shelf are the wall's own color (`drawFixed(..., flat)`).
17. **Close-up** from the shelf: a tap on the friend squishes it; 3
    squishes go back to the shelf; the third close-up in a row ended that
    way goes to the map; a tap away from it goes back; home goes to the
    map. The map resets the 3-in-a-row count.
18. **Tests** `tests/e2e/shelf.spec.ts` (3 a device): the shelf button,
    a tab, a swipe, home; "Find me!", a close-up and 3 squishes back; a
    tap away, home from the close-up, the 3-in-a-row rule. Test driver:
    `fixedToView()`, `button()`, `shelfPage()`. 165 unit and 68 play
    checks pass.

Score: shelf, close-up and buttons 8.5 (first pass 7.5: on an iPad in
portrait the band above the shelf repeated the active tab as a pink
stripe; a flat band color was a shade off the wall's own color).

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
- This container's Chromium was build 1243, not 1194. Without changing
  the repo, link it for the run:
  `P=/tmp/pwb; mkdir -p $P/chromium_headless_shell-1194/chrome-linux` then
  `ln -s /opt/pw-browsers/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell $P/chromium_headless_shell-1194/chrome-linux/headless_shell`
  and run with `PLAYWRIGHT_BROWSERS_PATH=$P`.
- C does not fix the order of a call's arguments: the fixture generator
  makes one `game_rand()` call per statement.
