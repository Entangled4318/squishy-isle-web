"""Squishy sprites for the ROM with flavor palette swaps.

Each species is rendered with a synthetic "role" flavor whose seven ramp
colors are unique, in ROM mode (two-shade accents, blush tongue). Pixels of
role colors map to fixed palette slots 1-7, so one set of tiles serves all
five flavors: the ROM only swaps palettes.

All four species of an area share one slot layout:
  1-7  flavor roles (hi, light, base, shade, deep shade, outline, blush)
  8    ink (eyes), 9 white (shine)
  10+  the area's accent colors (at most 6)
So one palette per flavor covers a whole shelf page: 5 palettes per area.
"""
import squishies
from gba import colors_of, from5
from gbaconv import bgr555, obj
from palette import FL, FLAVOR_ORDER, C
from squishies import SPECIES, AREAS, render

ROLE = [from5((1, 1, k)) for k in range(1, 8)]
FL['_role'] = ROLE

# (expression, squash) per stored animation frame
FRAMES = {
    'idle': ('happy', (1.0, 1.0)),
    'blink': ('closed', (1.0, 1.0)),
    'open': ('happy_open', (1.0, 1.0)),
    'squish': ('squish', (1.17, 0.74)),
    'hop': ('happy_open', (0.9, 1.08)),
}

# frames stored for each size
SIZE_FRAMES = {
    16: ('idle', 'squish'),
    32: ('idle', 'open'),
    64: ('idle', 'blink', 'open', 'squish'),
}

SILHOUETTE = {  # per shelf row tint: fill, rim
    0: ('#f7d3de', '#ecbfcd'), 1: ('#cfeadb', '#b9dfca'),
    2: ('#ddd3f1', '#cbbdea'), 3: ('#f3e2b8', '#e8d09c'),
}


def _fits(im, size):
    cols = (im[..., 3] > 0).any(0).nonzero()[0]
    return cols.min() >= 1 and cols.max() <= size - 2


def role_render(species, size, frame):
    """One stored frame. The squish widens the friend (squash sx); wide
    friends (chick, crab, shroom...) went past the frame and lost their
    sides (Brick test, step 8.1), so sx shrinks until a 1 px margin is left."""
    expr, (sx, sy) = FRAMES[frame]
    squishies.ROM_MODE = True
    try:
        im = render(SPECIES[species], '_role', size, expr=expr, squash=(sx, sy))
        while not _fits(im, size) and sx > 0.9:
            sx -= 0.01
            im = render(SPECIES[species], '_role', size, expr=expr, squash=(sx, sy))
        return im
    finally:
        squishies.ROM_MODE = False


def area_export(area_key):
    """Returns dict with:
      tiles[species][size] = list of frame tile bytes
      palettes[flavor] = 16 BGR555 entries
      silhouettes[row] = 16 entries (every slot -> silhouette fill, outline -> rim)
      layout = list of slot descriptions
    """
    area = next(a for a in AREAS if a[0] == area_key)
    species = area[3]
    imgs = {}
    fixed = set()
    for sp in species:
        for size, frames in SIZE_FRAMES.items():
            for fr in frames:
                im = role_render(sp, size, fr)
                imgs[(sp, size, fr)] = im
                fixed |= colors_of(im) - set(ROLE)
    face = [C['ink'], C['white']]
    missing = [c for c in face if c not in fixed]
    accents = sorted(fixed - set(face))
    if missing or len(accents) > 6:
        raise ValueError(f'{area_key}: face {missing} accents {len(accents)}')
    slots = [('role', i) for i in range(7)] + [('fixed', c) for c in face + accents]
    lookup = {}
    for n, (kind, v) in enumerate(slots, 1):
        lookup[ROLE[v] if kind == 'role' else v] = n
    tiles = {sp: {size: [obj(imgs[(sp, size, fr)], lookup) for fr in frames]
                  for size, frames in SIZE_FRAMES.items()} for sp in species}
    palettes = {}
    for fl in FLAVOR_ORDER:
        pal = [0] * 16
        for n, (kind, v) in enumerate(slots, 1):
            pal[n] = bgr555(FL[fl][v] if kind == 'role' else v)
        palettes[fl] = pal
    from gba import rgb15
    sil = {}
    for row, (fill, rim) in SILHOUETTE.items():
        pal = [0] + [bgr555(rgb15(fill))] * 15
        pal[6] = bgr555(rgb15(rim))            # outline role -> rim
        sil[row] = pal
    return {'species': species, 'tiles': tiles, 'palettes': palettes, 'silhouettes': sil,
            'layout': slots, 'images': imgs, 'lookup': lookup}


def preview(area_key, flavor):
    """Rebuild RGBA images from exported data for visual checks."""
    import numpy as np
    from gba import new
    ex = area_export(area_key)
    pal = ex['palettes'][flavor]
    inv = {i: c for c, i in ex['lookup'].items()}
    out = {}
    for key, im in ex['images'].items():
        o = new(im.shape[1], im.shape[0])
        for y in range(im.shape[0]):
            for x in range(im.shape[1]):
                if im[y, x, 3]:
                    idx = ex['lookup'][tuple(int(v) for v in im[y, x, :3])]
                    c = pal[idx]
                    o[y, x, :3] = ((c & 31) << 3 | (c & 31) >> 2, ((c >> 5) & 31) << 3 | ((c >> 5) & 31) >> 2,
                                   ((c >> 10) & 31) << 3 | ((c >> 10) & 31) >> 2)
                    o[y, x, 3] = 255
        out[key] = o
    return out
