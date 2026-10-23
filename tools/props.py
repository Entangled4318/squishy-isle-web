"""Containers, sparkles and UI pieces."""
import math

import numpy as np

from gba import from_ascii, new, rgb15, blit
from palette import C, ACC
from paint import P, shade_parts
from squishies import Ellipse, Poly, Union, Minus, Clip, HalfPlane, Star
from font import draw_text, text_width

# ---------------------------------------------------------------- gift box
BOX_COLORS = {
    # outline, top light, top, front, front shade, dots, ribbon, ribbon shade
    'pink': ('#b85c82', '#ffe8ef', '#ffd3df', '#ffc2d3', '#f2a0ba', '#fff4f8', '#bff0dc', '#86d2b6'),
    'lav': ('#7864ae', '#f1eaff', '#e2d4fb', '#d4c2f7', '#b8a0ea', '#faf6ff', '#fff0a0', '#f5cf5c'),
    'mint': ('#4f8f76', '#e8fbf2', '#d0f4e4', '#bdeed8', '#94dcc0', '#f4fffa', '#ffc2d3', '#f09ab4'),
    'yellow': ('#b0823a', '#fffbe0', '#fff2b8', '#ffe99a', '#f7d170', '#fffdf0', '#d4c2f7', '#ab93dc'),
    'sky': ('#5a86b8', '#eef8ff', '#d8eeff', '#c6e4fc', '#a2cdf2', '#f6fbff', '#ffc2d3', '#f09ab4'),
}

_BOX16 = [
    '................',
    '....kkk..kkk....',
    '...kRRRkkRRRk...',
    '...kRrrRRrrRk...',
    '...kkRRkkRRkk...',
    '.kkkkkkRRkkkkkk.',
    'kTTTTTTRrTTTTTTk',
    'kttttttRrttttttk',
    'kkkkkkkRrkkkkkkk',
    '.kFhFFFRrFFFFfk.',
    '.kFFFdFRrFFdFfk.',
    '.kFdFFFRrFFFFfk.',
    '.kFFFFFRrFdFFfk.',
    '.kfffffRrfffffk.',
    '..kkkkkkkkkkkk..',
    '................',
]


BOX16_KEYS = 'kTtFfdhRr'       # palette index = position + 1, same in every color


def box16_index():
    """The 16px box as palette indices (shared by all colors)."""
    idx = np.zeros((16, 16), np.uint8)
    for y, row in enumerate(_BOX16):
        for x, ch in enumerate(row):
            if ch != '.':
                idx[y, x] = BOX16_KEYS.index(ch) + 1
    return idx


def box16_palette(color):
    k, T, t, F, f, d, R, r = (rgb15(h) for h in BOX_COLORS[color])
    return [k, T, t, F, f, d, C['white'], R, r]


def guide_arrow(direction):
    """16px guide arrow. direction: 'right', 'up' or 'upright' (flips give the rest)."""
    ink, hi, fill, shade = rgb15('#c25a82'), rgb15('#fffdf0'), rgb15('#ffe07a'), rgb15('#f5b54a')
    shape = [(1.5, 5.5), (8.5, 5.5), (8.5, 1.5), (14.8, 8), (8.5, 14.5), (8.5, 10.5), (1.5, 10.5)]
    ang = {'right': 0.0, 'up': math.pi / 2, 'upright': math.pi / 4}[direction]
    ca, sa = math.cos(ang), math.sin(ang)
    pts = [(8 + (x - 8) * ca + (y - 8) * sa, 8 - (x - 8) * sa + (y - 8) * ca) for x, y in shape]

    def inside(px, py):
        c = False
        for i in range(len(pts)):
            (x1, y1), (x2, y2) = pts[i], pts[i - 1]
            if (y1 > py) != (y2 > py) and px < (x2 - x1) * (py - y1) / (y2 - y1) + x1:
                c = not c
        return c

    m = np.array([[inside(x + 0.5, y + 0.5) for x in range(16)] for y in range(16)])
    img = new(16, 16)
    for y in range(16):
        for x in range(16):
            if not m[y, x]:
                continue
            edge = any(not (0 <= y + dy < 16 and 0 <= x + dx < 16 and m[y + dy, x + dx])
                       for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            if edge:
                col = ink
            elif not m[y - 1, x] or not m[y - 1, x - 1] if y > 0 and x > 0 else False:
                col = hi
            elif not m[y + 1, x] or not m[y + 2, x] if y < 14 else True:
                col = shade
            else:
                col = fill
            img[y, x, :3] = col
            img[y, x, 3] = 255
    return img


def box16(color='pink'):
    k, T, t, F, f, d, R, r = (rgb15(h) for h in BOX_COLORS[color])
    return from_ascii(_BOX16, {'k': k, 'T': T, 't': t, 'F': F, 'f': f, 'd': d, 'h': C['white'],
                               'R': R, 'r': r})


def box64(color='pink', part='all'):
    """Big gift box for the open scene. part: all | body | lid | open"""
    k, T, t, F, f, d, R, r = (rgb15(h) for h in BOX_COLORS[color])
    face = [T, T, F, f, f]
    lidr = [T, T, t, f, f]
    rib = [C['white'], R, R, r, r]
    parts = []
    if part in ('all', 'body', 'open'):
        parts.append(P(Poly([(11, 31), (53, 31), (53, 61), (11, 61)], 0.6), face, z=0, bevel=True))
        parts.append(P(Poly([(28.5, 31), (35.5, 31), (35.5, 61), (28.5, 61)], 0.1), rib, z=1, bevel=True))
    if part in ('all', 'lid'):
        parts.append(P(Poly([(7, 20), (57, 20), (57, 31), (7, 31)], 1.2), lidr, z=2, bevel=True, line=k))
        parts.append(P(Poly([(28.5, 20), (35.5, 20), (35.5, 31), (28.5, 31)], 0.1), rib, z=3, bevel=True))
        loop = lambda cx, rot: Minus(Ellipse(cx, 11, 10, 6.5, rot), Ellipse(cx + (2 if cx < 32 else -2), 11.5, 4.5, 2.2, rot))
        parts.append(P(loop(22, -18), rib, z=4, k=3.5, line=k, levels=(0.95, 0.75, 0.40, 0.15)))
        parts.append(P(loop(42, 18), rib, z=4, k=3.5, line=k, levels=(0.95, 0.75, 0.40, 0.15)))
        parts.append(P(Poly([(29, 17), (26, 26), (23, 24)], 1.0), rib, z=3.5, line=k, bevel=True))
        parts.append(P(Poly([(35, 17), (38, 26), (41, 24)], 1.0), rib, z=3.5, line=k, bevel=True))
        parts.append(P(Ellipse(32, 14.5, 4.6, 4.2), rib, z=5, line=k, k=3.5, levels=(0.95, 0.72, 0.40, 0.15)))
    img = shade_parts(64, 64, parts, outline=k)
    if part in ('all', 'body', 'open'):
        # polka dots
        for (x, y) in ((16, 37), (23, 46), (15, 53), (42, 38), (48, 47), (41, 55), (24, 55)):
            for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1), (-1, 0), (0, -1), (2, 0), (0, 2), (1, -1), (-1, 1), (2, 1), (1, 2)):
                X, Y = x + dx, y + dy
                if img[Y, X, 3] and tuple(img[Y, X, :3]) == F:
                    img[Y, X, :3] = d
        # top-left glint
        for (x, y) in ((13, 33), (14, 33), (13, 34)):
            img[y, x, :3] = C['white']
    if part == 'open':
        # dark interior visible at the top of the body
        for y in range(31, 35):
            for x in range(12, 53):
                if img[y, x, 3]:
                    img[y, x, :3] = k if y == 31 else f
    return img


# ----------------------------------------------------------------- shell
def shell(color='pink', size=16):
    """Scallop shell: scalloped fan with radial ridges and hinge wings."""
    rp = {'pink': ['#ffffff', '#ffe6ee', '#ffcadb', '#f5a7c2', '#e38aa9', '#b0607e'],
          'peach': ['#ffffff', '#fff0e0', '#ffd9bb', '#f7bb90', '#e89f76', '#b0745a'],
          'lav': ['#ffffff', '#f3ecff', '#e0d2fb', '#c6b0f0', '#aa92dc', '#7864ae'],
          'mint': ['#ffffff', '#e8fbf2', '#c8f0dc', '#9edcc2', '#7cc4a8', '#4f8f76'],
          'yellow': ['#ffffff', '#fff8d8', '#ffe9a8', '#f9d06c', '#e8b24e', '#b0823a']}[color]
    hi, lt, base, dk, dk2, ink = (rgb15(h) for h in rp)
    k = size / 16.0
    img = new(size, size)
    hx, hy = 7.5 * k + 0.5 * (k - 1), 13.2 * k
    n = 7 if size > 16 else 5
    for y in range(size):
        for x in range(size):
            dx, dy = x + 0.5 - hx - 0.5 * k + 0.5, y + 0.5 - hy
            dx = x + 0.5 - (size / 2)
            dy = dy / (1.25 if size <= 16 else 1.0)
            r = math.hypot(dx, dy)
            if dy > 0.3 * k:
                continue
            th = math.atan2(-dy, dx)            # 0..pi across the fan
            t = th / math.pi * n                 # ridge coordinate
            ridge = abs(((t % 1.0) - 0.5)) * 2   # 1 at groove, 0 at ridge centre
            R = ((6.9 + 0.75 * (1 - ridge)) if size > 16 else (6.4 + 1.3 * (1 - ridge) ** 0.7)) * k
            if r <= R:
                img[y, x, 3] = 255
                shade = 0.55 + 0.45 * math.cos(th - 2.2)   # light from upper left
                if ridge > (0.62 if size <= 16 else 0.72) and r > 2.2 * k:
                    c = dk if shade > 0.45 else dk2
                elif shade > 0.93 and r > 3 * k:
                    c = hi if r > R - 1.6 * k and ridge < 0.4 else lt
                elif shade > 0.62:
                    c = lt if ridge < 0.35 else base
                elif shade > 0.3:
                    c = base
                else:
                    c = dk
                img[y, x, :3] = c
    # hinge wings
    for y in range(int(12.2 * k), int(14.6 * k)):
        for x in range(int(4.2 * k), int(11.8 * k)):
            img[y, x, :3] = base if y < int(13.4 * k) else dk
            img[y, x, 3] = 255
    m = img[..., 3] > 0
    out = np.zeros_like(m)
    out[1:] |= m[:-1]
    out[:-1] |= m[1:]
    out[:, 1:] |= m[:, :-1]
    out[:, :-1] |= m[:, 1:]
    out &= ~m
    img[out, :3] = ink
    img[out, 3] = 255
    return img


def shell16(color='pink'):
    return shell(color, 16)


# -------------------------------------------------------------- sparkles
SPARK_BIG = from_ascii([
    '...w...',
    '...w...',
    '..wyw..',
    'wwyWyww',
    '..wyw..',
    '...w...',
    '...w...',
], {'w': rgb15('#fff6c0'), 'y': rgb15('#ffe07a'), 'W': C['white']})
SPARK_SMALL = from_ascii([
    '..w..',
    '.wyw.',
    'wyWyw',
    '.wyw.',
    '..w..',
], {'w': rgb15('#fff6c0'), 'y': rgb15('#ffe07a'), 'W': C['white']})
SPARK_HUGE = from_ascii([
    '.....w.....',
    '.....w.....',
    '....wyw....',
    '....wyw....',
    '..wwyWyww..',
    'wwyyWWWyyww',
    '..wwyWyww..',
    '....wyw....',
    '....wyw....',
    '.....w.....',
    '.....w.....',
], {'w': rgb15('#fff6c0'), 'y': rgb15('#ffe07a'), 'W': C['white']})
SPARK_TINY = from_ascii(['.w.', 'wWw', '.w.'], {'w': rgb15('#fff6c0'), 'W': C['white']})

# Map container twinkles (Brick test, 8.1): the pale ones above vanished on
# sand and cloud. Gold with a tan outline, in colors the sparkle palette
# already holds (it is full), 16x16 frames: small, medium, big.
_MAP_TW = {'o': rgb15('#b5845a'), 'g': rgb15('#f7b54a'), 'y': rgb15('#ffe07a'), 'w': C['white']}
MAP_TWINKLES = [from_ascii(rows, _MAP_TW) for rows in (
    ['..o..', '.oyo.', 'oywyo', '.oyo.', '..o..'],
    ['...o...', '..oyo..', '.oywyo.', 'oywwwyo', '.oywyo.', '..oyo..', '...o...'],
    ['.....o.....', '....ogo....', '....oyo....', '...oyyyo...', '.oooywyooo.', 'ogyywwwyygo',
     '.oooywyooo.', '...oyyyo...', '....oyo....', '....ogo....', '.....o.....'])]


def shadow(w, h, color=None):
    s = new(w, h)
    xs, ys = np.meshgrid(np.arange(w) + 0.5, np.arange(h) + 0.5)
    m = ((xs - w / 2) / (w / 2)) ** 2 + ((ys - h / 2) / (h / 2)) ** 2 <= 1
    s[m, :3] = color or C['shadow']
    s[m, 3] = 255
    return s


HEART = from_ascii([
    '.kk.kk.',
    'kppkppk',
    'kpwpppk',
    'kppppPk',
    '.kpppk.',
    '..kPk..',
    '...k...',
], {'k': rgb15('#c25a82'), 'p': rgb15('#ff9fbd'), 'P': rgb15('#f07aa0'), 'w': C['white']})

HEART_BIG = from_ascii([
    '.kkk.kkk.',
    'kpppkpppk',
    'kpwwpppPk',
    'kpwppppPk',
    'kppppppPk',
    '.kppppPk.',
    '..kppPk..',
    '...kPk...',
    '....k....',
], {'k': rgb15('#c25a82'), 'p': rgb15('#ff9fbd'), 'P': rgb15('#f07aa0'), 'w': C['white']})


# ------------------------------------------------------------- A button
def a_button_big(pressed=False):
    """24px A button prompt for the open screen."""
    rp = [rgb15('#fff0f4'), rgb15('#ffc6d6'), rgb15('#ffa8c0'), rgb15('#f085a6'), rgb15('#d86a8e')]
    ink = rgb15('#9a4a70')
    oy = 2 if pressed else 0
    base = [P(Ellipse(12, 15, 10.5, 7.5), [rp[4]] * 5, z=0, flat=True)]
    top = [P(Ellipse(12, 11 + oy, 10, 9.2), rp, z=1, k=2.2, levels=(0.95, 0.78, 0.45, 0.2))]
    img = shade_parts(24, 25, base + top, outline=ink)
    glyph = ['.####.', '##..##', '##..##', '######', '##..##', '##..##']
    for y, row in enumerate(glyph):
        for x, ch in enumerate(row):
            if ch == '#':
                img[9 + y + oy, 9 + x, :3] = rp[4]
    for y, row in enumerate(glyph):
        for x, ch in enumerate(row):
            if ch == '#':
                img[8 + y + oy, 9 + x, :3] = C['white']
    return img


def a_button(pressed=False):
    rp = [rgb15('#fff0f4'), rgb15('#ffc6d6'), rgb15('#ffa8c0'), rgb15('#f085a6'), rgb15('#d86a8e')]
    ink = rgb15('#9a4a70')
    parts = [P(Ellipse(8, 8 if not pressed else 9, 6.6, 6.2), rp, k=3.0, levels=(0.95, 0.78, 0.45, 0.2))]
    img = shade_parts(16, 17, parts, outline=ink)
    if not pressed:
        # base rim under the button
        for x in range(3, 14):
            img[15, x, :3] = ink
            img[15, x, 3] = 255
        for x in range(2, 14):
            if img[14, x, 3] and tuple(img[14, x, :3]) != ink:
                img[14, x, :3] = rp[4]
    oy = 0 if not pressed else 1
    glyph = ['.##.', '#..#', '####', '#..#', '#..#']
    for y, row in enumerate(glyph):
        for x, ch in enumerate(row):
            if ch == '#':
                img[5 + y + oy, 6 + x, :3] = C['white']
    return img


# ---------------------------------------------------------------- pills
def pill(w, h, fill, edge, ink, light=None, r=None):
    """Rounded pill panel with a soft bevel. r: corner radius (default h / 2,
    fully round ends; smaller makes a rounded box, e.g. Momo's heart meter)."""
    img = new(w, h)
    r = h / 2 if r is None else r
    for y in range(h):
        for x in range(w):
            cx = min(max(x + 0.5, r), w - r)
            cy = min(max(y + 0.5, r), h - r)
            if (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 <= (r - 0.2) ** 2:
                img[y, x, :3] = fill
                img[y, x, 3] = 255
    m = img[..., 3] > 0
    out = np.zeros_like(m)
    out[1:] |= m[:-1] & ~m[1:]
    inner = np.zeros_like(m)
    # outline: pixels in m whose 4-neighbour is outside
    for y in range(h):
        for x in range(w):
            if not m[y, x]:
                continue
            nb = [(y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)]
            if any(not (0 <= a < h and 0 <= b < w) or not m[a, b] for a, b in nb):
                img[y, x, :3] = ink
    for y in range(h):
        for x in range(w):
            if m[y, x] and tuple(img[y, x, :3]) != ink:
                if y + 1 < h and tuple(img[y + 1, x, :3]) == ink and y > h // 2:
                    img[y, x, :3] = edge
                elif light is not None and y - 1 >= 0 and tuple(img[y - 1, x, :3]) == ink and y < h // 2:
                    img[y, x, :3] = light
    return img


def badge_new():
    """Star badge that says NEW."""
    rp = [C['white'], rgb15('#fff6c0'), rgb15('#ffe27e'), rgb15('#f7c860'), rgb15('#e6aa48')]
    img = shade_parts(34, 32, [P(Star(17, 17, 16.5, rf=0.62, round_r=2.5, R=6), rp, k=1.2,
                                 levels=(0.99, 0.9, 0.45, 0.2))], outline=rgb15('#b27a30'))
    draw_text(img, 'NEW', 17 - text_width('NEW') // 2, 14, rgb15('#e0607e'), outline=C['white'])
    return img


CONFETTI_COLS = ['#ff9fbd', '#ffe07a', '#9ee2c8', '#b9a4f0', '#9cccf5', '#ffb08a']


CONFETTI_DARK = ['#e07a9c', '#e8b44a', '#62c0a0', '#9178d8', '#6fa8e0', '#e88a60']


def confetti_piece(i):
    col = rgb15(CONFETTI_COLS[i % len(CONFETTI_COLS)])
    dk = rgb15(CONFETTI_DARK[i % len(CONFETTI_DARK)])
    shapes = [['ccc', 'ccd', 'cdd'], ['cccc', 'cddd'], ['cc', 'cd', 'cd', 'dd'], ['.cc.', 'ccdc', '.dd.'],
              ['cc...', 'dccc.', '..ddd'], ['c..', 'cc.', '.cd', '..d']]
    return from_ascii(shapes[i % len(shapes)], {'c': col, 'd': dk})


PAW = from_ascii([
    '..kk.kk...',
    '.kppkppk..',
    '.kppkppk..',
    'kk.kk.kkk.',
    'kpkkkkkppk',
    'kpkpppkppk',
    '.kpppppppk',
    '.kppwwpppk',
    '..kppppkk.',
    '...kkkk...',
], {'k': rgb15('#9a4a70'), 'p': rgb15('#ffb3c8'), 'w': C['white']})

CROWN = from_ascii([
    'k...k...k',
    'kyk.kyk.k'[:9],
    'kyykyyyk.'[:9],
    'kyyyyyyyk',
    'kywyyyyyk',
    'kkkkkkkkk',
], {'k': rgb15('#b27a30'), 'y': rgb15('#ffe07a'), 'w': C['white']})


ACORN_NUTS = {
    # nut ramp light to dark; the cap stays brown so every one reads as an
    # acorn (pastel caps looked like cupcakes)
    'cream': ('#fff0d8', '#ffdcb0', '#f5c28c', '#e0a470', '#c8895a'),
    'pink': ('#fff0f4', '#ffd6e2', '#f9b4c8', '#ea94ae', '#cf7896'),
    'mint': ('#effcf4', '#d2f2e0', '#aee2c6', '#8ccca8', '#6eb08e'),
    'lav': ('#f6f0ff', '#e2d6fa', '#c8b4f0', '#aa94dc', '#8e7ac4'),
    'gold': ('#fff8d8', '#ffe8a0', '#f9d06c', '#e8b24e', '#c8923e'),
}


def acorn16(nut_color='cream'):
    cap = [rgb15(h) for h in ('#e8c9a8', '#d8ae88', '#c49276', '#a0725f', '#8a5e4e')]
    nut = [rgb15(h) for h in ACORN_NUTS[nut_color]]
    ink = rgb15('#6e4a4a')
    parts = [
        P(Ellipse(8, 9.5, 5.2, 5.5), nut, z=0, k=2.5),
        P(Ellipse(8, 7, 6.8, 3.6), cap, z=1, k=2.5, line=ink),
        P(Poly([(7.3, 1.5), (8.7, 1.5), (8.7, 4), (7.3, 4)], 0.2), cap, z=0.5, bevel=True),
    ]
    img = shade_parts(16, 16, parts, outline=ink)
    for (x, y) in ((4, 6), (7, 6), (10, 6), (5, 8), (9, 8), (12, 7)):
        if img[y, x, 3] and tuple(img[y, x, :3]) != ink:
            img[y, x, :3] = cap[3]
    img[10, 5, :3] = C['white']
    img[11, 5, :3] = nut[1]
    return img


CAPSULE_COLORS = {      # top half: light, base, dark (5 capsule colors, as in the machine)
    'pink': ('#ffe0ea', '#ffb3c8', '#ec8fae'),
    'blue': ('#e2f1ff', '#bfe0ff', '#86b4e6'),
    'yellow': ('#fff8d0', '#fff0a0', '#e8c060'),
    'mint': ('#e0f8e8', '#bff0cc', '#7cc8a0'),
    'lav': ('#f0e8ff', '#d8c6fa', '#a890e0'),
}


def capsule16(top='#ffb6cb', top_dk='#ec8fae', top_lt='#ffe0ea'):
    t = [C['white'], rgb15(top_lt), rgb15(top), rgb15(top_dk), rgb15(top_dk)]
    b = [C['white'], C['white'], rgb15('#fbf6ff'), rgb15('#e4dcf2'), rgb15('#cfc4e4')]
    ink = rgb15('#8a5a7a')
    from squishies import Clip, HalfPlane
    ball = Ellipse(8, 8.5, 6.2, 6.2)
    parts = [P(Clip(ball, HalfPlane(0, -1, -8.5)), t, z=1, k=2.5),
             P(Clip(ball, HalfPlane(0, 1, 8.5)), b, z=1, k=2.5)]
    img = shade_parts(16, 16, parts, outline=ink)
    for x in range(2, 15):
        if img[8, x, 3]:
            img[8, x, :3] = ink
    return img


# ------------------------------------------------ 12 px area icons (counter pill)
_ICON12 = {
    'box': [
        '..kkk..kkk..',
        '.kRRRkkRRRk.',
        '.kRrrRRrrRk.',
        '..kkkRRkkk..',
        'kkkkkRrkkkkk',
        'kTTTTRrTTTTk',
        'kttttRrttttk',
        'kkkkkRrkkkkk',
        '.kFhFRrFFfk.',
        '.kFFdRrFdfk.',
        '.kfffRrfffk.',
        '..kkkkkkkk..',
    ],
    'shell': [
        '..kk.kk.kk..',
        '.klhkbbkbdk.',
        '.klhldbbdbk.',
        'klhldlbdbbdk',
        'kllldlbdbbdk',
        'kdlldlbdbbdk',
        '.kdldlbdbdk.',
        '..kdldbdbk..',
        '...kdlbdk...',
        '..kkbbbbkk..',
        '..kddddddk..',
        '...kkkkkk...',
    ],
    'acorn': [
        '.....kk.....',
        '....kCCk....',
        '..kkkCCkkk..',
        '.kcccdcdcck.',
        'kcdcdcdcdcck',
        'kddddddddddk',
        '.kkkkkkkkkk.',
        '.kNwNNNNnnk.',
        '.kNNNNNNnnk.',
        '..knNNNnnk..',
        '...knnnnk...',
        '....kkkk....',
    ],
    'capsule': [
        '....kkkk....',
        '..kkTTTTkk..',
        '.kTwwTTTTtk.',
        '.kTwTTTTTtk.',
        'kTTTTTTTTttk',
        'kkkkkkkkkkkk',
        'kWWWWWWWWggk',
        'kWhWWWWWWggk',
        '.kWWWWWWggk.',
        '.kgWWWWgggk.',
        '..kkggggkk..',
        '....kkkk....',
    ],
}


def icon12(kind):
    """Small area icons for the found counter: box, shell, acorn, capsule."""
    if kind == 'box':
        k, T, t, F, f, d, R, r = (rgb15(h) for h in BOX_COLORS['pink'])
        legend = {'k': k, 'T': T, 't': t, 'F': F, 'f': f, 'd': d, 'h': C['white'], 'R': R, 'r': r}
    elif kind == 'shell':
        legend = {'k': rgb15('#b0607e'), 'h': C['white'], 'l': rgb15('#ffd6e3'), 'b': rgb15('#ffb3cb'),
                  'd': rgb15('#e98aaa')}
    elif kind == 'acorn':
        legend = {'k': rgb15('#6e4a4a'), 'C': rgb15('#a0725f'), 'c': rgb15('#d8ae88'),
                  'd': rgb15('#c49276'), 'N': rgb15('#ffdcb0'), 'n': rgb15('#f5c28c'), 'w': C['white']}
    else:
        legend = {'k': rgb15('#8a5a7a'), 'T': rgb15('#ffb6cb'), 't': rgb15('#ec8fae'), 'w': C['white'],
                  'W': rgb15('#e4dcf2'), 'g': rgb15('#c8b8e4'), 'h': rgb15('#fbf6ff')}
    return from_ascii(_ICON12[kind], legend)


# --------------------------------------- 64 px containers for the open screen
# Each has three parts in one 64x64 frame (bottom row 61, on the cushion):
# 'body' closed, 'open' after the pop (inside showing), 'lid' flies off.
def _outline(img, ink):
    m = img[..., 3] > 0
    out = np.zeros_like(m)
    out[1:] |= m[:-1]
    out[:-1] |= m[1:]
    out[:, 1:] |= m[:, :-1]
    out[:, :-1] |= m[:, 1:]
    out &= ~m
    img[out, :3] = ink
    img[out, 3] = 255
    return img


def acorn64(nut_color='cream', part='all'):
    """Big acorn: a pastel nut under a brown cap with a stem; the cap is the lid."""
    from squishies import Mochi
    cap = [rgb15(h) for h in ('#f2dcc0', '#e8c9a8', '#d8ae88', '#c49276', '#a0725f')]
    nut = [rgb15(h) for h in ACORN_NUTS[nut_color]]
    ink = rgb15('#6e4a4a')
    img = new(64, 64)
    if part in ('all', 'body', 'open'):
        body = shade_parts(64, 64, [P(Mochi(32, 40, 20, 20.5, nt=2.2, nb=1.75), nut, k=3.0)], outline=ink)
        for (x, y) in ((20, 38), (21, 38), (20, 39), (19, 41)):          # glint
            body[y, x, :3] = C['white']
        if part == 'open':                                                # hollow top, seen from above
            hole = shade_parts(64, 64, [P(Ellipse(32, 26, 16, 5), nut[2:] + [nut[4], nut[4]], k=2.0,
                                          levels=(0.99, 0.95, 0.5, 0.2))], outline=ink)
            m = hole[..., 3] > 0
            body[m] = hole[m]
            body[26:28, 22:42][body[26:28, 22:42, 3] > 0, :3] = nut[4]
        blit(img, body, 0, 0)
    if part in ('all', 'lid'):
        parts = [P(Clip(Ellipse(32, 30, 25, 13), HalfPlane(0, -1, -33)), cap, z=1, k=2.5),
                 P(Ellipse(32, 31.5, 24.5, 3.2), cap, z=2, k=2.0, levels=(0.99, 0.6, 0.3, 0.1)),
                 P(Poly([(29.5, 9), (34.5, 8), (34, 19), (30, 19)], 1.2), cap, z=0, bevel=True)]
        lid = shade_parts(64, 64, parts, outline=ink)
        for y in range(19, 32):                                           # cross-hatch scales
            for x in range(8, 57):
                if lid[y, x, 3] and tuple(lid[y, x, :3]) != ink and (x + 2 * y) % 7 == 0 and y % 3 == 1:
                    lid[y, x, :3] = cap[4]
        for (x, y) in ((22, 21), (23, 20), (24, 20)):
            lid[y, x, :3] = cap[0]
        m = lid[..., 3] > 0
        img[m] = lid[m]
    return img


SHELL64 = {     # hi, light, base, dark, darker, ink (as the 16 px shells)
    'pink': ['#ffffff', '#ffe6ee', '#ffcadb', '#f5a7c2', '#e38aa9', '#b0607e'],
    'peach': ['#ffffff', '#fff0e0', '#ffd9bb', '#f7bb90', '#e89f76', '#b0745a'],
    'lav': ['#ffffff', '#f3ecff', '#e0d2fb', '#c6b0f0', '#aa92dc', '#7864ae'],
    'mint': ['#ffffff', '#e8fbf2', '#c8f0dc', '#9edcc2', '#7cc4a8', '#4f8f76'],
    'yellow': ['#ffffff', '#fff8d8', '#ffe9a8', '#f9d06c', '#e8b24e', '#b0823a'],
}


def shell64(color='pink', part='all'):
    """Big clam: a scalloped fan (the lid) closed over a shallow dish; open,
    the dish shows its pearly inside and a pearl."""
    hi, lt, base, dk, dk2, ink = (rgb15(h) for h in SHELL64[color])
    img = new(64, 64)
    if part in ('all', 'body', 'open'):
        dish = new(64, 64)
        for y in range(44, 62):
            for x in range(64):
                dx, dy = (x + 0.5 - 32) / 28.0, (y + 0.5 - 52.5) / 9.0
                if dx * dx + dy * dy <= 1:
                    dish[y, x, 3] = 255
                    ridge = int((x + 0.5 - 32) / 5.5 + 50) % 2
                    dish[y, x, :3] = (base if ridge else lt) if dy < 0.45 else (dk if ridge else base)
        dish = _outline(dish, ink)
        if part == 'open':                                                # pearly inside and a pearl
            for y in range(45, 56):
                for x in range(6, 58):
                    dx, dy = (x + 0.5 - 32) / 25.0, (y + 0.5 - 50) / 5.0
                    if dx * dx + dy * dy <= 1 and dish[y, x, 3]:
                        dish[y, x, :3] = hi if dy < -0.3 else lt
            for y in range(36, 54):
                for x in range(22, 42):
                    d2 = (x + 0.5 - 32) ** 2 + (y + 0.5 - 45) ** 2
                    if d2 <= 64:
                        dish[y, x, :3] = ink if d2 > 49 else (C['white'] if d2 < 30 and x < 32 and y < 45 else
                                                              rgb15('#eee6f8') if d2 < 36 else rgb15('#d8cce8'))
                        dish[y, x, 3] = 255
            for (x, y) in ((29, 41), (28, 42), (29, 42)):
                dish[y, x, :3] = C['white']
        blit(img, dish, 0, 0)
    if part in ('all', 'lid'):
        fan = new(64, 64)
        hx, hy, n = 32.0, 53.0, 7
        for y in range(8, 56):
            for x in range(64):
                dx, dy = x + 0.5 - hx, y + 0.5 - hy
                if dy > -1:
                    continue
                r = math.hypot(dx, dy)
                th = math.atan2(-dy, dx)
                t = th / math.pi * n
                ridge = abs((t % 1.0) - 0.5) * 2
                R = 27.6 + 2.9 * (1 - ridge) ** 0.8          # scallop tips 1 px inside the 64 px frame (8.1: they were cut)
                if r > R:
                    continue
                shade = 0.55 + 0.45 * math.cos(th - 2.2)
                if ridge > 0.74 and r > 7:
                    c = dk if shade > 0.45 else dk2
                elif shade > 0.93 and r > 10:
                    c = hi if r > R - 5 and ridge < 0.4 else lt
                elif shade > 0.62:
                    c = lt if ridge < 0.35 else base
                elif shade > 0.3:
                    c = base
                else:
                    c = dk
                fan[y, x, :3] = c
                fan[y, x, 3] = 255
        for y in range(50, 57):                                           # hinge wings
            for x in range(19, 45):
                fan[y, x, :3] = base if y < 53 else dk
                fan[y, x, 3] = 255
        fan = _outline(fan, ink)
        m = fan[..., 3] > 0
        img[m] = fan[m]
    return img


def capsule64(color='pink', part='all'):
    """Big toy capsule: a colored dome (the lid) on a white half."""
    lt, top, dk = (rgb15(h) for h in CAPSULE_COLORS[color])
    t = [C['white'], lt, top, dk, dk]
    b = [C['white'], C['white'], rgb15('#fbf6ff'), rgb15('#e4dcf2'), rgb15('#cfc4e4')]
    ink = rgb15('#8a5a7a')
    ball = Ellipse(32, 38, 23.5, 23.5)
    img = new(64, 64)
    if part in ('all', 'body', 'open'):
        body = shade_parts(64, 64, [P(Clip(ball, HalfPlane(0, 1, 38)), b, k=2.5)], outline=ink)
        if part == 'open':
            inside = shade_parts(64, 64, [P(Ellipse(32, 38.5, 22, 4.5), [b[3], b[3], b[4], b[4], b[4]], k=1.0)],
                                 outline=ink)
            m = inside[..., 3] > 0
            body[m] = inside[m]
        blit(img, body, 0, 0)
    if part in ('all', 'lid'):
        parts = [P(Clip(ball, HalfPlane(0, -1, -38)), t, z=1, k=2.5),
                 P(Poly([(8.5, 35), (55.5, 35), (55.5, 40), (8.5, 40)], 1.0), [lt, top, dk, dk, dk], z=2, bevel=True)]
        lid = shade_parts(64, 64, parts, outline=ink)
        for (x, y) in ((20, 22), (21, 21), (22, 20), (19, 24), (24, 19)):   # shine
            lid[y, x, :3] = C['white']
        m = lid[..., 3] > 0
        img[m] = lid[m]
    return img


# ------------------------------------------- mailbox and picnic (step 6.7)
# All in the sparkle / heart palette (ui_small) plus a few food colors, so
# the meadow needs no extra OBJ palette (its 16 are in use).
SNACK_LEGEND = {'w': C['white'], 'c': rgb15('#fff6c0'), 'y': rgb15('#ffe07a'), 'Y': rgb15('#f5b54a'),
                'k': rgb15('#c25a82'), 'p': rgb15('#ff9fbd'), 'P': rgb15('#f07aa0'), 'r': rgb15('#ff6f86'),
                't': rgb15('#f0c890'), 'b': rgb15('#b8805a'), 'l': rgb15('#9ee09a'), 'g': rgb15('#5fa870'),
                'd': rgb15('#4a3a5c'), 'f': C['f_yel'], 'F': C['f_yel_dk']}   # f, F: the flag (not the arrow's yellow)

SNACKS = {
    'strawberry': [
        '......g..g......',
        '.....glggl......',
        '....ggllllgg....',
        '...krrgllgrrk...',
        '..krrrrggrrrrk..',
        '..krcrrrrrrcrk..',
        '..krrrrcrrrrrk..',
        '..kwrrrrrrcrrk..',
        '...krrcrrrrrk...',
        '...krrrrrcrrk...',
        '....krrcrrrk....',
        '.....krrrrk.....',
        '......kkkk......',
    ],
    'cookie': [
        '.....bbbbbb.....',
        '...bbttttttbb...',
        '..bttcttttttbb..',
        '.bttctttbbtttb..',
        '.btctbbtbbttttb.',
        'bttttbbtttttttb.',
        'btttttttttbbttb.',
        'bttbbttttttbbttb',
        'bttbbtttbbtttttb',
        '.btttttttbbtttb.',
        '.bbtttbbttttttb.',
        '..bbttbbtttttb..',
        '...bbttttttbb...',
        '.....bbbbbb.....',
    ],
    'apple': [
        '.......b........',
        '.......bgg......',
        '......gbllg.....',
        '..kkkkbkggkkk...',
        '.krrrrbrrrrrrk..',
        'krwwrrrrrrrrrrk.',
        'krwrrrrrrrrrrrk.',
        'krrrrrrrrrrrrrk.',
        'krrrrrrrrrrrrPk.',
        'krrrrrrrrrrrPPk.',
        '.krrrrrrrrrPPk..',
        '.krrrrrrrrPPPk..',
        '..kkrrrkkrrkk...',
        '....kkk..kk.....',
    ],
    'cupcake': [
        '.......kk.......',
        '......krrk......',
        '......krrk......',
        '....kkpkkppk....',
        '...kpwpppppPk...',
        '..kpwppppppPPk..',
        '..kppppppPPPPk..',
        '.kpppppppppppPk.',
        '.kPPPPPPPPPPPPk.',
        '..bttbttbttbtb..',
        '..btYbtYbtYbtb..',
        '...btbttbttbb...',
        '...bbttbttbtb...',
        '....bbbbbbbb....',
    ],
    'melon': [
        'gggggggggggggggg',
        'gllllllllllllllg',
        '.gwwwwwwwwwwwwg.',
        '.krrrrrrrrrrrrk.',
        '..krrdrrrrdrrk..',
        '..krrrrrrrrrrk..',
        '...krrrdrrrrk...',
        '....krrrrrrk....',
        '....krdrrrrk....',
        '.....krrrrk.....',
        '......krrk......',
        '.......kk.......',
    ],
    'donut': [
        '.....bbbbbb.....',
        '...bbppppppbb...',
        '..bppwpyppppPb..',
        '.bpwppppplpppPb.',
        '.bpppppbbppcpPb.',
        'bpppypbttbpppPPb',
        'bpcppbt..tbppyPb',
        'bpppPbt..tbPPPPb',
        'bpplPPbttbPPlPPb',
        '.btPPPPbbPPPPtb.',
        '.bttPPyPPPPPttb.',
        '..bttttttttttb..',
        '...bbttttttbb...',
        '.....bbbbbb.....',
    ],
    'onigiri': [
        '.......dd.......',
        '......dwwd......',
        '.....dwwwwd.....',
        '.....dwwwwd.....',
        '....dwwwwwwd....',
        '...dwwwwwwwwd...',
        '...dwwwwwwwwd...',
        '..dwwwwwwwwwwd..',
        '..dwwwddddwwwd..',
        '.dwwwwddddwwwwd.',
        '.dwwwwddddwwwwd.',
        '.dccwwddddwwccd.',
        '..dddddddddddd..',
    ],
    'icecream': [
        '.....kkkkk......',
        '....kpwppPk.....',
        '...kpwpppPPk....',
        '...kpppppPPk....',
        '..kkPPPPPPPkk...',
        '.kcwccccccccYk..',
        '.kcccccccccYYk..',
        '..kYYYYYYYYYk...',
        '...bttbttbtb....',
        '...btbttbttb....',
        '....bttbttb.....',
        '....btbttbb.....',
        '.....bttbb......',
        '......bbb.......',
        '.......b........',
    ],
}
SNACK_ORDER = ['strawberry', 'cookie', 'apple', 'cupcake', 'melon', 'donut', 'onigiri', 'icecream']


def snack16(kind):
    art = from_ascii(SNACKS[kind], SNACK_LEGEND)
    img = new(16, 16)
    h, w = art.shape[:2]
    blit(img, art, (16 - w) // 2, 16 - h)          # sits on the bottom row
    return img


def envelope16():
    """Small letter that bobs over the mailbox while mail waits."""
    art = from_ascii([
        'kkkkkkkkkkkkkk',
        'kwkcccccccckwk',
        'kwwkccccccckwk'[:14],
        'kwwwkcccckwwwk',
        'kwwwwkcckwwwwk',
        'kwwwwwkkwwwwwk',
        'kwwwwwpPwwwwwk',
        'kwwwwpppPwwwwk',
        'kwwwwwpPwwwwwk',
        'kwwwwwwwwwwwwk',
        'kkkkkkkkkkkkkk',
    ], SNACK_LEGEND)
    img = new(16, 16)
    blit(img, art, 1, 3)
    return img


def mail_flag(up=True):
    """The mailbox's flag (16x16 cell, pole at x 1..2): up = mail waits."""
    img = new(16, 16)
    if up:
        art = from_ascii(['kkkkkkkkk.', 'kbcffffffk', 'kbffffffFk', 'kbfffffFFk', 'kbfffFFFk.', 'kbkkkkkk..',
                          'kbk.......', 'kbk.......', 'kbk.......', 'kbk.......', 'kbk.......', 'kkk.......'],
                         SNACK_LEGEND)
        blit(img, art, 0, 1)
    else:
        art = from_ascii(['kkkkkkkkkk', 'kbbbbbbffk', 'kbbbbbbFFk', 'kkkkkkkkkk'], SNACK_LEGEND)
        blit(img, art, 0, 9)
    return img


def envelope64(opened=False):
    """Big pink letter for the letter scene (64x64, envelope in rows 16..55):
    closed with a heart seal, or with its flap folded up."""
    ink, fill, lt, dk, flap = (rgb15(h) for h in ('#b85c82', '#ffd3df', '#ffe8ef', '#f2a0ba', '#ffc2d3'))
    img = new(64, 64)
    x0, x1, y0, y1 = 5, 59, 18, 55
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            edge = x in (x0, x1) or y in (y0, y1)
            img[y, x, :3] = ink if edge else (lt if y < y0 + 3 else fill)
            img[y, x, 3] = 255
    for y in range(y0 + 1, y1):                         # the two side folds meet in the middle
        for x in range(x0 + 1, x1):
            d = abs(x - 32)
            if abs((y1 - y) - (d * (y1 - y0 - 14) // 27)) == 0 and d < 27:
                img[y, x, :3] = dk
    if not opened:
        for y in range(y0, y0 + 24):                    # flap down with a heart seal
            half = 27 - (y - y0) * 27 // 23
            for x in range(32 - half, 32 + half + 1):
                if x0 <= x <= x1:
                    edge = x in (32 - half, 32 + half) or y == y0
                    img[y, x, :3] = ink if edge else flap
        heart = from_ascii(['.kk.kk.', 'kppkppk', 'kpwpppk', 'kppppPk', '.kpppk.', '..kPk..', '...k...'],
                           {'k': rgb15('#c25a82'), 'p': rgb15('#ff9fbd'), 'P': rgb15('#f07aa0'), 'w': C['white']})
        blit(img, heart, 29, y0 + 17)
    else:
        for y in range(y0 - 16, y0 + 1):                # flap folded up
            half = 27 - (y0 - y) * 27 // 16
            for x in range(32 - half, 32 + half + 1):
                if x0 <= x <= x1:
                    edge = x in (32 - half, 32 + half) or y == y0
                    img[y, x, :3] = ink if edge else dk
                    img[y, x, 3] = 255
        for y in range(y0 + 1, y0 + 6):                 # the letter inside peeks out
            for x in range(x0 + 6, x1 - 5):
                img[y, x, :3] = rgb15('#fffaf0') if y > y0 + 1 else ink
    return img
