"""Quick preview of chosen species at 64/32/16, scaled up."""
import sys
from gba import blit, solid, save_scaled, rgb15, colors_of
from palette import FLAVOR_ORDER
from squishies import SPECIES, render
keys = sys.argv[2].split(',')
out = sys.argv[1]
sheet = solid(70 * 5 + 60, 70 * len(keys), rgb15('#f4eefa'))
for r, k in enumerate(keys):
    for c, fl in enumerate(FLAVOR_ORDER):
        im = render(SPECIES[k], fl, 64)
        n = len(colors_of(im))
        a = im[..., 3]
        if a[0].any() or a[-1].any() or a[:, 0].any() or a[:, -1].any():
            print('EDGE', k, fl)
        if n > 15:
            print('TOO MANY', k, fl, n)
        blit(sheet, im, c * 70 + 3, r * 70 + 3)
    blit(sheet, render(SPECIES[k], 'strawberry', 32), 355, r * 70 + 3)
    blit(sheet, render(SPECIES[k], 'matcha', 16), 355, r * 70 + 45)
    blit(sheet, render(SPECIES[k], 'sparkle', 16), 380, r * 70 + 45)
save_scaled(sheet, out, 3)
