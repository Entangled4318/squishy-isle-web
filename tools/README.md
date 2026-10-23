# Art and music tools

These tools are a copy of `tools/` from
[squishy-isle](https://github.com/Entangled4318/squishy-isle) at commit
`1d99c2e` (v1.6, "Merge step 9.7: hardening, v1.6"). They are MIT, the same
as this repo.

The copy is on purpose (docs/PLAN.md, step 4). The web game changes the
tools: PNG atlases instead of 15-bit GBA tiles, larger squishies and 2x
redraws of the world art. Those changes do not go back to the GBA repo.

## State of the copy

The files are as they were at v1.6. The scripts that write GBA C data
(`export_game.py`, `export_hwcheck.py`, `export_font.py`, `gbaconv.py`,
`gbafix.py` and the C part of `music.py`) are kept for reference until the
web exporters replace them. `tests/check_map.py` uses `areas.py` as it is.

| File | What it makes |
| --- | --- |
| `squishies.py` | The 16 species, drawn at any size (`render(sp, flavor, size)`) |
| `npc.py` | Momo, with the squishy renderer |
| `world.py`, `props.py`, `pip.py`, `logo.py`, `font.py` | World art, containers and UI, Pip, the logo, the 5x7 font (fixed-size pixel art) |
| `areas.py` | The four maps: layers, 4x4 px collision grid, spots, doors, exits, gates |
| `rooms.py`, `gifts.py` | House rooms and the 16 gifts |
| `music.py` | The 8 songs as note text, checked and exported |
| `mockups.py`, `scene.py`, `preview.py`, `paint.py`, `palette.py` | Shared builders, mockups and checks |
| `gbaconv.py`, `gba.py`, `gbafix.py`, `export_*.py`, `squishy_export.py` | GBA export (reference only) |

Needs Python 3 with numpy and Pillow.
