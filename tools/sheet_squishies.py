"""Contact sheet of every species x flavor at all native sizes.

Usage: python3 sheet_squishies.py OUTDIR
"""
import os
import sys

from gba import blit, check_obj, solid, save_scaled, rgb15
from palette import FLAVOR_ORDER
from squishies import SPECIES, render

OUT = sys.argv[1] if len(sys.argv) > 1 else 'out'
os.makedirs(OUT, exist_ok=True)

keys = list(SPECIES)
cell = 68
sheet = solid(cell * len(FLAVOR_ORDER) + 56, cell * len(keys), rgb15('#f4eefa'))
for r, k in enumerate(keys):
    sp = SPECIES[k]
    for c, fl in enumerate(FLAVOR_ORDER):
        for n in (16, 32, 64):
            check_obj(render(sp, fl, n), f'{k}/{fl}/{n}')
        blit(sheet, render(sp, fl, 64), c * cell + 2, r * cell + 2)
    x = len(FLAVOR_ORDER) * cell + 4
    blit(sheet, render(sp, 'strawberry', 32), x, r * cell + 2)
    blit(sheet, render(sp, 'vanilla', 16), x, r * cell + 40)
    blit(sheet, render(sp, 'matcha', 16), x + 20, r * cell + 40)
save_scaled(sheet, os.path.join(OUT, 'squishy_sheet.png'), 2)
print('ok', len(keys), 'species x', len(FLAVOR_ORDER), 'flavors, all sprites within 15 colors')
