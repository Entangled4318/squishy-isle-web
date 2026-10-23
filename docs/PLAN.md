# Squishy Isle (web): the plan

Agreed with the owner one step at a time. Steps 1 to 4 are decided.
Step 5 (milestones) is next.

## Step 1: the path

Three paths were compared:

- **A.** Run the GBA ROM in a browser emulator (mGBA built for the web).
- **B.** Build the same C code for the browser, with a small layer that
  does the GBA hardware's jobs.
- **C.** Write a new game in TypeScript, with the same rules, design and
  art tools.

Effort estimate, in working sessions (one chat that ends in a commit, a
report and the owner's review):

| Work | B | C |
| --- | --- | --- |
| Build setup, fixed 60 Hz step, save to browser storage | 1 | 2 |
| Drawing | 2 | in the engine |
| Sound | 2 | 2 |
| Game rules | 0 | 1 |
| Scenes | 0 | 8 to 12 |
| Art | 0 | 4 to 8 |
| Touch, grown-up start-over | 2 to 3 | 1 to 2 |
| Tuning back to 8.5 | 0 to 1 | 5 to 8 |
| Tests | 1 to 2 | 4 to 6 |
| Web shell | 1 to 2 | 1 to 2 |
| iPhone and iPad testing | 1 to 2 | 2 to 3 |
| **Total** | **10 to 14** | **30 to 45** |

**Decision: Path C, in this separate repo.** Path A is skipped: on-screen
buttons do not suit a toddler, and the game cannot respond to a tap on a
thing. Claude recommended B on cost. The owner chose C, so the web game can
grow apart from the GBA game. The main risk of C is that bugs the GBA tests
found come back, so the game rules and the toddler mash test are ported
first (step 4).

Note on art: only the squishies and Momo can be drawn at any size. The
maps, trees, houses, props, Pip, rooms and font are fixed-size pixel art
and need 2x redraws for sharp art everywhere.

## Step 2: touch controls

**Tap a thing, and it does its thing.** No aiming twice, no gestures, no
buttons to learn.

Rules for every scene:

- Act on touch down. A tiny sparkle and a soft tick show where each finger
  lands, even where nothing else happens.
- One finger at a time: the first finger counts until it lifts.
- Tap zones of at least 64 points. A tap near a thing counts as a tap on
  the nearest thing.
- No double tap, swipe, pinch or long press is needed. A swipe on the shelf
  turns pages as a bonus only.
- Taps during a fade or a scene change only sparkle.
- One large round home button, in the same corner, in every scene but the
  map and the title.

| Scene | Touch | Result |
| --- | --- | --- |
| Title | Tap anywhere | Continue (or Play on a new save). No "New game" here. |
| Map | Tap the ground | Pip walks there by the shortest path, or to the nearest spot he can reach. |
| Map | Hold and drag | Pip follows the finger. |
| Map | Tap a container | Pip walks to it; it opens when he arrives. |
| Map | Tap a friend | Squish at once: squeak, hop, heart. |
| Map | Tap Pip | Pip hops; the followers hop after him. |
| Map | Tap Momo | Momo giggles; the newest heart hops. |
| Map | Tap the mailbox, basket, heart sign or a door | Pip walks there and it opens. |
| Map | Tap the guide arrow | Pip walks to the nearest container. |
| Map | Tap the shelf button (top corner) | Opens the shelf. |
| Open | Tap anywhere | One press. The third pops it. It opens by itself after 4 s. |
| Reveal | Tap anywhere | Squish. After 3 squishes or 5 s the friend hops away. |
| Shelf | Tap an area tab | Turns to that page. Swipe also works. |
| Shelf | Tap a found friend | Close-up. A silhouette wiggles with "Find me!". |
| Close-up | Tap the friend | Squish. 3 squishes go back; the third close-up in a row goes to the map. |
| Picker | Tap a friend | Adds it to the line or removes it. |
| House | Tap a gift | Hop and squeak; a silhouette wiggles. The door or home button leaves. |
| Letter | Tap anywhere | Skips to the open letter; a tap on the friend squishes it. |
| Gate scene, parade | Tap anywhere | Sparkles only. |

### Grown-up start-over (the number gate)

1. A small gear in a top corner of the title opens only after a 2 s hold
   while a ring fills.
2. The number gate: "Tap four, nine, two, seven" as words, with a 0 to 9
   keypad. New numbers each time. The first wrong tap goes back to the
   title. A non-reader gets past it about 1 time in 10,000 tries, and each
   try needs the 2 s hold again.
3. Start over: "Your friends will go home", then a 3 s hold while six
   hearts fill.

Start-over keeps the old save as a backup ("Bring back the old friends")
until the next start-over. The grown-up page also has save export and
import, the music switch and the storage state.

The parents' help page recommends iOS Guided Access, so a swipe up cannot
leave the game.

## Step 3: web details

### Hosting

The repo is public. A GitHub Actions workflow runs the Python tools, builds
the game and deploys it to GitHub Pages on each push to `main`. The address
is `entangled4318.github.io/squishy-isle-web/` from the first test, so the
home screen install and the save carry on to the release. A "do not index"
tag stays on until launch. The owner turns on Pages (Settings, Pages,
Source: GitHub Actions) once the workflow exists.

### Home screen and offline

- Manifest with `display: standalone`, plus Safari's tags:
  `apple-touch-icon` (180 px), `apple-mobile-web-app-capable`, status bar
  `black-translucent`.
- In a Safari tab, a one-time picture hint for parents: Share, then Add to
  Home Screen. Install first, then play: a home screen app keeps its
  storage apart from Safari's (to confirm on device).
- A service worker stores every file on the first visit. A new version
  downloads in the background and starts on the next cold launch, never
  during play. Target size under 5 MB.

### Sound

- The first touch starts Web Audio. On the title that tap plays the hello
  jingle.
- Audio session "playback" (Safari 17 and later), so the iPhone silent
  switch does not mute the game. A music switch on the grown-up page.
- After a call or a screen lock, the next tap starts the sound again.
  Music stops while the app is hidden.
- Notes are scheduled ahead on the audio clock: a slow frame never changes
  the tempo.

### Screen

- Full screen comes from the home screen install (iPhone Safari cannot
  make a page full screen).
- `viewport-fit=cover`; art fills the whole screen; buttons stay inside
  `env(safe-area-inset-*)`.
- Both orientations work, landscape first. The map camera shows more of
  the island in the long direction. Fixed screens stay centred on their
  backdrop.
- Pinch zoom, double-tap zoom, text select, the long-press menu and
  pull-to-refresh are off. Art is drawn sharp at the device's pixel
  density.

### Saves

- Ported from the GBA: two slots with a sequence number and CRC-32,
  `save_sanitize` at load, and the same save moments, plus a save when the
  app is hidden (`visibilitychange`, `pagehide`).
- IndexedDB, with a copy in localStorage in case IndexedDB fails. Every key
  starts with `squishy-isle-web:`.
- Protection: (1) home screen install, (2) `navigator.storage.persist()` on
  the first play, with the result on the grown-up page, (3) export through
  the iOS share sheet as a small file, or as a text save code, (4) import
  from a file or a code, with a preview ("23 friends"), a 3 s hold, and the
  old save kept as a backup.
- The grown-up page shows the last export date. After 14 days without one,
  a small dot shows on the gear.
- To confirm on device: the 7-day storage exemption for home screen apps,
  persist(), separate storage from Safari.

## Step 4: repo and tests

- `tools/` is a copy of the GBA repo's tools at `1d99c2e` (v1.6), changed
  here for the web. See `tools/README.md`.
- Generated art is not committed. The workflow installs Python with numpy
  and Pillow and runs the tools.
- Stack: TypeScript, Vite, plain canvas (no engine), Vitest, Playwright.
- `CLAUDE.md` holds the working rules. `docs/HANDOFF.md` tracks the work.

Tests, in this order:

1. **Game rules first.** Port `test_collection.c` and `test_save.c` case by
   case to Vitest. Run the C rules on 50 seeds once and commit the results
   as fixtures: the TypeScript port must give the same shuffle, rolls and
   letter order.
2. **Map checks.** `tests/check_map.py` runs as it is (20 checks pass).
3. **Text checks.** Port `check_text.py` to the web font.
4. **Test driver.** In test mode the game runs on a fixed step as fast as
   it can, with a fixed seed, and logs like `dbg()`. Playwright taps,
   holds, drags, rotates, hides the app and reloads.
5. **Toddler mash test, early.** Random taps, palms, long holds, drags,
   rotations, the app hidden mid-write, reloads. Invariants from `mash.py`:
   no stuck scene, friends count up by one with no repeats, no start-over
   without the gate, the save stays valid.
6. **Play scripts** per scene: the 80-friend loop, Continue after a reload,
   each area, Momo, mail, houses, parade.
7. **Audio checks.** Songs rendered offline: pitch, tempo, loops, clicks.

Safari-only behaviour (sound unlock, storage, safe areas, home screen) goes
on a written device checklist for the owner.

## Step 5: milestones

To agree with the owner.
