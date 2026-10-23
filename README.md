# Squishy Isle (web)

A calm collecting game for toddlers (about 2 to 4 years old), made for the
browser and for iPhone and iPad touch screens. The child walks Pip around
a pastel island, opens surprise containers, squishes the mochi friends
inside and fills the Squishy Shelf. There are no fail states and no
timers, and the child does not need to read.

This is the web version of the Game Boy Advance game
[squishy-isle](https://github.com/Entangled4318/squishy-isle) (v1.6). It is
a new game in TypeScript that keeps the same design rules, game rules and
art pipeline.

## Status

Milestone 1 (foundations): the game rules and save, ported from the GBA
game and checked byte for byte against its C code, plus the web engine and
a "tap test" page. The plan is in [docs/PLAN.md](docs/PLAN.md), where the
work is in [docs/HANDOFF.md](docs/HANDOFF.md), and the iPhone and iPad
checks in [docs/DEVICE_CHECKLIST.md](docs/DEVICE_CHECKLIST.md).

## Build and test

Needs Node 22 and Python 3 with numpy and Pillow.

```
npm install
pip install numpy pillow
npm run assets
npm run check
python3 tests/check_map.py build/map
```

`npm run dev` serves the game at http://localhost:5173/squishy-isle-web/.

## Design rules

- Every touch gives a happy result. No touch is wrong.
- No fail states, no timers, no reading needed.
- A toddler mashing the screen must never lose progress.
- Only a grown-up can start over.

## Repository layout

- `src/rules/` game rules and save (ported from the GBA C code).
- `src/engine/` loop, screen, touch, scenes, sound. `src/shell/` storage,
  install hint, service worker. `src/scenes/` the scenes.
- `tools/` the Python art and music tools, copied from the GBA repo at
  v1.6 (`1d99c2e`). See [tools/README.md](tools/README.md).
- `tests/` checks: `unit/` (Vitest), `e2e/` (Playwright), `fixtures/`
  (results from the GBA C rules), `check_map.py` (map data).
- `docs/` the plan and the handoff.

## License

MIT. See [LICENSE](LICENSE).
