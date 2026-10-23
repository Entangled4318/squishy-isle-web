"""Art for the hardware check ROM. Usage: python3 export_hwcheck.py OUTDIR

Writes OUTDIR/hw_assets.c/.h and OUTDIR/hw_preview.png (the BG art alone).
"""
import os
import sys

import numpy as np

from gba import new, blit, rgb15, from_ascii, save_scaled, W, H
from palette import C, FLAVOR_ORDER, FLAVOR_NAME
from font import draw_text, text_width, G
from logo import word
from props import pill, shadow, SPARK_TINY, SPARK_SMALL, SPARK_BIG
from gbaconv import bg, obj, bgr555, tile4, CWriter
import squishy_export

OUT = sys.argv[1] if len(sys.argv) > 1 else 'build'

INK = C['ui_ink']
PANEL = C['ui_bg']
LINE = C['ui_line']

# BG0 text strips (tile rows, 2 tiles tall; glyph top 3 px below) shared with hwcheck.c
TEXT_ROWS = {'boots': 6, 'squish': 8, 'save': 10, 'emu': 12}
GLYPH_Y = 3
VALUE_COL = 11
FLAVOR_ROW = 16
FLAVOR_COL = 18
FLAVOR_TILES = 11


def rounded_panel(w, h, r, fill, edge):
    img = new(w, h)
    for y in range(h):
        for x in range(w):
            dx = max(r - x - 0.5, 0, x + 0.5 - (w - r))
            dy = max(r - y - 0.5, 0, y + 0.5 - (h - r))
            if dx * dx + dy * dy <= r * r:
                img[y, x, :3] = fill
                img[y, x, 3] = 255
    m = img[..., 3] > 0
    for y in range(h):
        for x in range(w):
            if not m[y, x]:
                continue
            nb = [(y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)]
            if any(not (0 <= a < h and 0 <= b < w) or not m[a, b] for a, b in nb):
                img[y, x, :3] = edge
    return img


def background():
    img = new(W, H)
    img[..., :3] = rgb15('#f1ecfb')
    img[..., 3] = 255
    ys, xs = np.mgrid[0:H, 0:W]
    heart = from_ascii(['k.k', 'kkk', '.k.'], {'k': rgb15('#e3daf6')})
    for y0 in range(4, H, 16):
        for x0 in range(4 + (8 if (y0 // 16) % 2 else 0), W, 16):
            blit(img, heart, x0, y0)
    # logo
    w1 = word('SQUISHY', 16, ['strawberry', 'sparkle', 'matcha', 'sky', 'taro', 'peach', 'strawberry'])
    w2 = word('ISLE', 16, ['sky', 'taro', 'strawberry', 'matcha'])
    total = w1.shape[1] + w2.shape[1] - 6
    blit(img, w1, 120 - total // 2, -4)
    blit(img, w2, 120 - total // 2 + w1.shape[1] - 6, -4)
    t = 'hardware check'
    draw_text(img, t, 120 - text_width(t) // 2, 31, INK, outline=C['white'])
    # left panel with labels and hints
    blit(img, rounded_panel(132, 93, 6, PANEL, LINE), 4, 41)
    for key, label in (('boots', 'Boots'), ('squish', 'Squishes'), ('save', 'Save'), ('emu', 'Emulator')):
        draw_text(img, label, 13, TEXT_ROWS[key] * 8 + GLYPH_Y, INK)
    for x in range(12, 128):
        if x % 2 == 0:
            img[109, x, :3] = C['ui_pk2']
    draw_text(img, 'A squish   B hop', 13, 113, C['ui_line'])
    draw_text(img, 'L R flavor  START tune', 13, 122, C['ui_line'])
    # cushion + flavor name pill on the right
    from mockups import stage
    blit(img, stage(96, 26), 140, 96)
    fp = pill(FLAVOR_TILES * 8, 13, C['white'], C['ui_pk'], LINE, None)
    blit(img, fp, FLAVOR_COL * 8, FLAVOR_ROW * 8)
    # scaling check: 1px stripes around the edge and checker corners
    for x in range(W):
        img[0, x, :3] = C['white'] if x % 2 else C['ui_pk2']
        img[H - 1, x, :3] = C['white'] if x % 2 else C['ui_pk2']
    for y in range(H):
        img[y, 0, :3] = C['white'] if y % 2 else C['ui_pk2']
        img[y, W - 1, :3] = C['white'] if y % 2 else C['ui_pk2']
    for (cx, cy) in ((2, 2), (W - 10, 2), (2, H - 10), (W - 10, H - 10)):
        for y in range(8):
            for x in range(8):
                img[cy + y, cx + x, :3] = C['ink'] if (x + y) % 2 else C['white']
    return img


MINI = {
    'S': ['###', '#..', '###', '..#', '###'], 'T': ['###', '.#.', '.#.', '.#.', '.#.'],
    'A': ['.#.', '#.#', '###', '#.#', '#.#'], 'R': ['##.', '#.#', '##.', '#.#', '#.#'],
    'E': ['###', '#..', '##.', '#..', '###'], 'L': ['#..', '#..', '#..', '#..', '###'],
    'C': ['.##', '#..', '#..', '#..', '.##'],
}
ARROW_UP = ['...#...', '..###..', '.#####.', '#######', '..###..', '..###..', '..###..']

# icon palette roles: 1 fill, 2 edge shade, 3 outline, 4 glyph, 5 light rim
ICON_OFF = [0, bgr555(rgb15('#f5f0fc')), bgr555(rgb15('#ddd2f0')), bgr555(rgb15('#a595c8')),
            bgr555(rgb15('#a595c8')), bgr555(C['white'])] + [0] * 10
ICON_ON = [0, bgr555(rgb15('#ffc2d4')), bgr555(rgb15('#f09ab4')), bgr555(rgb15('#9a4a70')),
           bgr555(C['white']), bgr555(rgb15('#ffe6ee'))] + [0] * 10


def icon(w, glyph=None, text=None, rot=0):
    """Rounded key cap. Returns an 8-bit index image (roles 1-5)."""
    h = 16
    idx = np.zeros((h, w), np.uint8)
    r = 5
    for y in range(1, h - 1):
        for x in range(w):
            dx = max(r - x - 0.5, 0, x + 0.5 - (w - r))
            dy = max(r - (y - 1) - 0.5, 0, (y - 1) + 0.5 - (h - 2 - r))
            if dx * dx + dy * dy <= r * r:
                idx[y, x] = 1
    m = idx > 0
    for y in range(h):
        for x in range(w):
            if not m[y, x]:
                continue
            nb = [(y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)]
            if any(not (0 <= a < h and 0 <= b < w) or not m[a, b] for a, b in nb):
                idx[y, x] = 3
    for y in range(h):
        for x in range(w):
            if idx[y, x] == 1 and y + 1 < h and idx[y + 1, x] == 3:
                idx[y, x] = 2
            elif idx[y, x] == 1 and y - 1 >= 0 and idx[y - 1, x] == 3:
                idx[y, x] = 5
    if glyph is not None:
        g = np.array([[c == '#' for c in row] for row in glyph])
        g = np.rot90(g, -rot)
        gh, gw = g.shape
        oy, ox = (h - gh) // 2, (w - gw) // 2
        idx[oy:oy + gh, ox:ox + gw][g] = 4
    if text is not None:
        tw = len(text) * 4 - 1
        ox = (w - tw) // 2
        for i, ch in enumerate(text):
            for y, row in enumerate(MINI[ch]):
                for x, c in enumerate(row):
                    if c == '#':
                        idx[5 + y, ox + i * 4 + x] = 4
    return idx


def idx_tiles(idx):
    h, w = idx.shape
    return b''.join(tile4(idx[ty:ty + 8, tx:tx + 8]) for ty in range(0, h, 8) for tx in range(0, w, 8))


def main():
    cw = CWriter('hw_assets')
    art = background()
    save_scaled(art, os.path.join(OUT, 'hw_preview.png'), 3)
    b = bg(art, pal_bank=0, max_pals=14)
    cw.u32_bytes('hw_bg_tiles', b['tiles'])
    full = []
    for row in range(20):
        full += b['map'][row * 30:(row + 1) * 30] + [0, 0]
    cw.u16('hw_bg_map', full)
    cw.u16('hw_bg_pal', [c for p in b['palettes'] for c in p])
    cw.define('HW_BG_PALS', len(b['palettes']))
    print(f"background: {b['ntiles']} tiles, {len(b['palettes'])} palettes")

    cw.u16('hw_text_pal', [0, bgr555(INK), bgr555(C['white']), bgr555(LINE)] + [0] * 12)

    ex = squishy_export.area_export('meadow')
    frames64 = ex['tiles']['bunny'][64]
    pals = ex['palettes']
    cw.u32_bytes('hw_bunny_tiles', frames64[0] + frames64[3])     # idle, squish
    cw.u16('hw_bunny_pals', [c for fl in FLAVOR_ORDER for c in pals[fl]])
    for i, fl in enumerate(FLAVOR_ORDER):
        cw.define(f'FLAVOR_{fl.upper()}', i)
    cw.c.append('const char *const hw_flavor_names[5] = {' +
                ', '.join(f'"{FLAVOR_NAME[f]}"' for f in FLAVOR_ORDER) + '};\n')
    cw.h.append('extern const char *const hw_flavor_names[5];\n')

    sh = shadow(32, 8, rgb15('#c9789a'))
    cw.u32_bytes('hw_shadow_tiles', obj(sh, {rgb15('#c9789a'): 1}))
    cw.u16('hw_shadow_pal', [0, bgr555(rgb15('#c9789a'))] + [0] * 14)

    # twinkle frames for the rare Sparkle flavor: 3 frames of 8x8
    frames = []
    lookup = {}
    pal = [0] * 16
    for sp in (SPARK_TINY, SPARK_SMALL, SPARK_BIG):
        for c in sorted({tuple(int(v) for v in p) for p in sp[..., :3][sp[..., 3] > 0]}):
            if c not in lookup:
                lookup[c] = len(lookup) + 1
                pal[lookup[c]] = bgr555(c)
        f = new(8, 8)
        blit(f, sp, (8 - sp.shape[1]) // 2, (8 - sp.shape[0]) // 2)
        frames.append(obj(f, lookup))
    cw.u32_bytes('hw_twinkle_tiles', b''.join(frames))
    cw.u16('hw_twinkle_pal', pal)

    icons = [icon(16, ARROW_UP, rot=3), icon(16, ARROW_UP, rot=0), icon(16, ARROW_UP, rot=2),
             icon(16, ARROW_UP, rot=1), icon(16, G['A']), icon(16, G['B']), icon(16, G['L']),
             icon(16, G['R']), icon(32, text='START'), icon(32, text='SELECT')]
    data = b''.join(idx_tiles(i) for i in icons)
    cw.u32_bytes('hw_icon_tiles', data)
    cw.u16('hw_icon_pal_off', ICON_OFF)
    cw.u16('hw_icon_pal_on', ICON_ON)
    for k, v in TEXT_ROWS.items():
        cw.define(f'ROW_{k.upper()}', v)
    cw.define('VALUE_COL', VALUE_COL)
    cw.define('GLYPH_Y', GLYPH_Y)
    cw.define('FLAVOR_ROW', FLAVOR_ROW)
    cw.define('FLAVOR_COL', FLAVOR_COL)
    cw.define('FLAVOR_TILES', FLAVOR_TILES)
    cw.save(OUT)


if __name__ == '__main__':
    main()
