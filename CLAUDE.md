# Squishy Isle (web): rules for Claude

Read `docs/PLAN.md` (the agreed plan) and `docs/HANDOFF.md` (where the work
is) first. The GBA game is the reference for how every part looks, sounds
and feels: [squishy-isle](https://github.com/Entangled4318/squishy-isle),
v1.6, its `docs/DESIGN.md` and `docs/HANDOFF.md`.

## Design rules (never break these)

1. Every touch gives a happy result. No touch is wrong.
2. No fail states, no timers, no reading needed for the child.
3. A toddler mashing the screen must never lose progress.
4. Only a grown-up can start over (the number gate, docs/PLAN.md step 2).

## Working rules the owner set

- Work step by step. Give a high-level overview of the steps and ask the
  owner to approve before coding.
- Ask the owner one question at a time.
- Score each part X/10 and iterate until it is 8.5 or higher. Report the
  first pass and what was fixed.
- Send screenshots in chat from the real game, not mockups.
- Commit and push after each sub-step and update `docs/HANDOFF.md`, so a
  new chat can pick up from the exact place.
- Before anything that stops, removes or replaces something that works,
  warn the owner in bold and wait for a yes.
- Write docs in ASD-STE100 Simplified Technical English: short sentences,
  sentence case headings, no em dashes.
- The owner is on limited credit: stop after each sub-step with a short
  report.

## Commands

    pip install numpy pillow
    python3 tests/check_map.py OUTDIR    # map data checks (20 checks)

The web build, unit tests and play tests come with milestone 1
(`docs/PLAN.md`).

## Traps known before the first line of code

- All the owner's GitHub Pages projects share one origin
  (`entangled4318.github.io`), so they share browser storage. Every
  storage key starts with `squishy-isle-web:`.
- Act on touch down, not on release. Count only the first finger until it
  lifts.
- The music schedules notes on the audio clock and the game runs on a fixed
  60 Hz step, so a slow frame or a 120 Hz screen never changes speed.
- Playwright here runs Chromium, not Safari. Safari-only behaviour goes on
  the device checklist.
