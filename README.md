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

Planning. No game code yet. The agreed plan is in
[docs/PLAN.md](docs/PLAN.md), and where the work is, in
[docs/HANDOFF.md](docs/HANDOFF.md).

## Design rules

- Every touch gives a happy result. No touch is wrong.
- No fail states, no timers, no reading needed.
- A toddler mashing the screen must never lose progress.
- Only a grown-up can start over.

## Repository layout

- `tools/` the Python art and music tools, copied from the GBA repo at
  v1.6 (`1d99c2e`). See [tools/README.md](tools/README.md).
- `tests/` checks. `check_map.py` checks the map data (Python 3, numpy,
  Pillow): `python3 tests/check_map.py OUTDIR`.
- `docs/` the plan and the handoff.

## License

MIT. See [LICENSE](LICENSE).
