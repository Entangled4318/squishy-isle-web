"""World art: autotiled terrain, trees, cottage and small props."""
import math

import numpy as np

from gba import new, from_ascii, rgb15
from palette import C
from paint import P, shade_parts
from squishies import Ellipse, Mochi, Poly, Union, Minus, Silhouette


def ramp(*names):
    return [C[n] for n in names]


GRASS = ramp('g_hi', 'g_lt', 'g_base', 'g_dk', 'g_dk2')
TREE = ramp('t_hi', 't_lt', 't_base', 't_dk', 't_dk2')
BLOSSOM = ramp('b_hi', 'b_lt', 'b_base', 'b_dk', 'b_dk2')
TRUNK = ramp('tr_lt', 'tr_lt', 'tr_base', 'tr_dk', 'tr_dk')
ROOF = ramp('rf_hi', 'rf_lt', 'rf_base', 'rf_dk', 'rf_dk')
WALL = ramp('wl_lt', 'wl_lt', 'wl_base', 'wl_dk', 'wl_dk')
DOOR = ramp('dr_lt', 'dr_lt', 'dr_base', 'dr_dk', 'dr_dk')
WIN = ramp('win_lt', 'win_lt', 'win_base', 'win_dk', 'win_dk')
WOOD = ramp('wd_hi', 'wd_lt', 'wd_base', 'wd_dk', 'wd_dk2')
MOSS = ramp('mg_hi', 'mg_lt', 'mg_base', 'mg_dk', 'mg_dk2')
AUTUMN = ramp('au_hi', 'au_lt', 'au_base', 'au_dk', 'au_dk2')
# canopy ramp, outline and inner line per tree kind
CANOPY = {'green': (TREE, 't_ink', 't_dk'), 'blossom': (BLOSSOM, 'b_ink', 'b_dk'), 'autumn': (AUTUMN, 'au_ink', 'au_dk')}


def _h(x, y, salt=0):
    """Small deterministic hash -> 0..1."""
    n = (x * 374761393 + y * 668265263 + salt * 2246822519) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0


# --------------------------------------------------------------- terrain
TUFTS = [
    # (dx, dy, pattern) inside a 16x16 grass metatile, per variant
    [],
    [(3, 4, 'tuft'), (10, 11, 'tuft')],
    [(9, 3, 'tuft'), (2, 12, 'blade')],
    [(5, 9, 'tuft'), (12, 3, 'blade'), (13, 13, 'speck')],
]
PATTERN = {
    'tuft': ['d.d.', '.dld', '..d.'][:2],
    'blade': ['l..', 'd.d', '.d.'][:3],
    'speck': ['l'],
}
PATTERN = {
    'tuft': ['d...d', '.d.d.'],
    'blade': ['.l.', 'd.d'],
    'speck': ['l'],
}


def corners_to_labels(corners, kinds):
    R = len(corners) - 1
    Cc = len(corners[0]) - 1
    H, W = R * 16, Cc * 16
    ys, xs = np.mgrid[0:H, 0:W]
    tx, ty = xs // 16, ys // 16
    u = ((xs % 16) + 0.5) / 16
    v = ((ys % 16) + 0.5) / 16
    val = {}
    for kch in set(''.join(corners)):
        grid = np.array([[1.0 if ch == kch else 0.0 for ch in row] for row in corners])
        tl = grid[ty, tx]
        tr = grid[ty, tx + 1]
        bl = grid[ty + 1, tx]
        br = grid[ty + 1, tx + 1]
        val[kch] = tl * (1 - u) * (1 - v) + tr * u * (1 - v) + bl * (1 - u) * v + br * u * v
    keys = sorted(val)
    stack = np.stack([val[k] for k in keys])
    lab = np.array(keys)[np.argmax(stack, axis=0)]
    base = kinds['base']
    for k in keys:
        if k == base:
            continue
        lab[(lab == k) & (val[k] < 0.5)] = base
    return lab


def shape_labels(w, h, base, regions):
    """regions: list of (label, Shape). Later regions paint over earlier."""
    lab = np.full((h, w), base)
    X, Y = np.meshgrid(np.arange(w) + 0.5, np.arange(h) + 0.5)
    for k, shp in regions:
        lab[shp.inside(X, Y)] = k
    return lab


def render_terrain(corners, kinds, grass_variant=None, style='meadow', lab=None):
    """Ground layer from a corner grid (autotile) or a label image."""
    if lab is None:
        lab = corners_to_labels(corners, kinds)
    H, W = lab.shape
    R, Cc = (H + 15) // 16, (W + 15) // 16
    img = new(W, H)
    img[..., 3] = 255
    ys, xs = np.mgrid[0:H, 0:W]
    base = kinds['base']

    def is_(k):
        return lab == k

    def sh(m, dy, dx):
        out = np.zeros_like(m)
        H_, W_ = m.shape
        ys0, ys1 = max(0, dy), min(H_, H_ + dy)
        xs0, xs1 = max(0, dx), min(W_, W_ + dx)
        out[ys0:ys1, xs0:xs1] = m[ys0 - dy:ys1 - dy, xs0 - dx:xs1 - dx]
        return out

    base_ramp = kinds['base_ramp']
    img[..., :3] = base_ramp[2]
    # grass / sand texture, tile-periodic so metatiles repeat
    if grass_variant is None:
        grass_variant = lambda x, y: int(_h(x, y, 7) * 4)
    tex_col = {'d': base_ramp[3], 'l': base_ramp[1]}
    for r in range(R):
        for c in range(Cc):
            var = grass_variant(c, r)
            for dx, dy, pat in TUFTS[var]:
                for yy, row in enumerate(PATTERN[pat]):
                    for xx, ch in enumerate(row):
                        if ch == '.':
                            continue
                        X, Y = c * 16 + dx + xx, r * 16 + dy + yy
                        if Y < H and X < W and lab[Y, X] == base:
                            img[Y, X, :3] = tex_col[ch]

    for k, spec in kinds.items():
        if k in ('base', 'base_ramp'):
            continue
        m = is_(k)
        rp = spec['ramp']      # hi, lt, base, dk, dk2, ink
        img[..., :3][m] = rp[2]
        land = ~m
        up1 = sh(land, 1, 0) & m
        up2 = sh(land, 2, 0) & m & ~up1
        lf1 = sh(land, 0, 1) & m
        dn1 = sh(land, -1, 0) & m
        rt1 = sh(land, 0, -1) & m
        if spec.get('deep'):
            up3 = sh(land, 3, 0) & m & ~up1 & ~up2
            img[..., :3][up3 | lf1] = rp[3]
            img[..., :3][up2] = rp[4]
            img[..., :3][up1] = rp[5]
            img[..., :3][dn1 | rt1] = rp[0]
            # bank: land pixel right above water gets a dark lip
            lip = sh(m, -1, 0) & land
            img[..., :3][lip] = kinds['base_ramp'][4]
            # shimmer dashes, tile periodic
            inner = m & ~sh(land, 3, 0) & ~sh(land, -2, 0) & ~sh(land, 0, 2) & ~sh(land, 0, -2)
            shimmer = np.zeros_like(m)
            for (sx, sy, ln, colr) in spec.get('shimmer', []):
                for i in range(ln):
                    shimmer[(xs % 32 == (sx + i) % 32) & (ys % 32 == sy)] = True
            img[..., :3][shimmer & inner] = rp[1]
        else:
            img[..., :3][up1] = rp[4]
            img[..., :3][up2 | lf1] = rp[3]
            img[..., :3][dn1] = rp[1]
            lipg = sh(m, -1, 0) & land
            img[..., :3][lipg] = kinds['base_ramp'][3]
            # pebbles
            for (px, py) in spec.get('pebbles', []):
                pm = (xs % 32 == px) & (ys % 32 == py) & m & ~up1 & ~up2 & ~lf1 & ~dn1
                pm2 = sh(pm, 0, 1) & m & ~up1 & ~dn1
                pm3 = sh(pm, 1, 0) & m & ~dn1
                img[..., :3][pm | pm2] = rp[0]
                img[..., :3][pm3 & ~pm & ~pm2] = rp[3]
    return img, lab


WOODS_KINDS = {
    'base': 'g',
    'base_ramp': MOSS,
    'p': {'ramp': ramp('dt_hi', 'dt_lt', 'dt_base', 'dt_dk', 'dt_dk2', 'dt_dk2'),
          'pebbles': [(5, 6), (20, 13), (12, 24), (27, 27), (28, 4), (3, 18), (16, 30)]},
}

MEADOW_KINDS = {
    'base': 'g',
    'base_ramp': GRASS,
    'p': {'ramp': ramp('p_hi', 'p_lt', 'p_base', 'p_dk', 'p_dk2', 'p_dk2'),
          'pebbles': [(5, 6), (20, 13), (12, 24), (27, 27), (28, 4), (3, 18), (16, 30)]},
    'w': {'ramp': ramp('w_hi', 'w_lt', 'w_base', 'w_dk', 'w_dk2', 'w_ink'), 'deep': True,
          'shimmer': [(4, 8, 4, 'l'), (19, 20, 3, 'l'), (13, 28, 2, 'l')]},
}


# ------------------------------------------------------------------ trees
def trunk(w, h, x0, x1, y0, y1):
    """Straight trunk with a little root flare, lit from the left."""
    img = new(w, h)
    for y in range(y0, y1):
        flare = 1 if y >= y1 - 3 else 0
        flare += 1 if y >= y1 - 1 else 0
        a, b = x0 - flare, x1 + flare
        for x in range(a, b + 1):
            if x == a or x == b:
                c = C['tr_ink']
            elif x == a + 1:
                c = C['tr_lt']
            elif x >= b - 2:
                c = C['tr_dk']
            else:
                c = C['tr_base']
            img[y, x, :3] = c
            img[y, x, 3] = 255
    for x in range(x0 - 2, x1 + 3):
        img[y1, x, :3] = C['tr_ink']
        img[y1, x, 3] = 255
    # bark marks
    for (x, y) in ((x0 + 3, y0 + 4), (x1 - 3, y0 + 7)):
        if y < y1 - 2:
            img[y, x, :3] = C['tr_dk']
            img[y + 1, x, :3] = C['tr_dk']
    return img


def tree(kind='green', big=False):
    rp, ink, inner = CANOPY[kind]
    ink, inner = C[ink], C[inner]
    k = 1.5 if big else 1.0
    w, h = int(32 * k), int(42 * k)
    clumps = [
        (11, 9, 7, 6.5, 0), (21.5, 8.5, 7.5, 6.5, 0),
        (6.5, 18, 6, 6.5, 1), (25.5, 18, 6, 6.5, 1), (16, 14.5, 9, 8, 1.5),
        (9.5, 24.5, 7.5, 5.5, 2), (22.5, 24.5, 7.5, 5.5, 2), (16, 26.5, 7, 5, 2.5),
    ]
    parts = [P(Ellipse(x * k, y * k, rx * k, ry * k), rp, z=z, line=inner, k=5.0,
               levels=(0.96, 0.78, 0.40, 0.12)) for (x, y, rx, ry, z) in clumps]
    can = shade_parts(w, int(33 * k), parts, outline=ink)
    tw = int(3.5 * k)
    img = trunk(w, h, w // 2 - tw, w // 2 + tw - 1, int(26 * k), h - 2)
    m = can[..., 3] > 0
    img[:can.shape[0]][m] = can[m]
    # canopy shadow on the trunk top
    for x in range(w):
        for y in range(can.shape[0], can.shape[0] + 2):
            if img[y, x, 3] and tuple(img[y, x, :3]) in (C['tr_lt'], C['tr_base']):
                img[y, x, :3] = C['tr_dk']
    if kind == 'autumn':                     # a few darker leaves: not a flat orange ball
        for (x, y) in ((9, 9), (21, 6), (24, 17), (12, 14), (6, 20), (18, 21), (26, 22), (11, 26), (20, 27)):
            x, y = int(x * k), int(y * k)
            if img[y, x, 3] and tuple(img[y, x, :3]) not in (ink, inner):
                img[y, x, :3] = C['au_dk']
    if kind == 'blossom':
        for (x, y) in ((8, 8), (19, 5), (25, 15), (13, 12), (5, 19), (17, 20), (27, 21), (10, 25), (21, 26), (15, 29)):
            x, y = int(x * k), int(y * k)
            if img[y, x, 3] and tuple(img[y, x, :3]) not in (ink, inner):
                img[y, x, :3] = C['white']
                if tuple(img[y + 1, x, :3]) not in (ink, inner):
                    img[y + 1, x, :3] = C['b_dk']
    return img


def tree_shadow(w=32, color=None):
    """Shadow blob painted into the ground layer under a tree."""
    s = new(w, 8)
    xs, ys = np.meshgrid(np.arange(w) + 0.5, np.arange(8) + 0.5)
    m = ((xs - w / 2) / (w / 2 - 2)) ** 2 + ((ys - 4) / 3.2) ** 2 <= 1
    s[m, :3] = color or C['g_dk']
    s[m, 3] = 255
    return s


def bush(kind='green'):
    rp, ink, _ = CANOPY[kind]
    img = shade_parts(16, 16, [P(Union(Ellipse(8, 10, 7, 5), Ellipse(5, 8, 4, 4), Ellipse(11, 7.5, 4.5, 4.5)),
                                 rp, levels=(0.97, 0.80, 0.45, 0.2))], outline=C[ink])
    return img


def berry_bush(kind='red'):
    """Green bush dotted with berries (2 px each, a light and a dark pixel)."""
    img = bush('green')
    lt, dk = (C['berry'], C['berry_dk']) if kind == 'red' else (C['bberry'], C['t_ink'])
    for (x, y) in ((5, 6), (10, 5), (3, 10), (8, 9), (12, 10), (6, 12)):
        img[y, x, :3] = lt
        img[y + 1, x, :3] = dk
    img[5, 10, :3] = C['white'] if kind == 'red' else lt
    return img


def fern():
    """Low fern clump: walk-through ground decor in woods greens."""
    return from_ascii([
        '..l.....l..',
        '.ld.l..dl.l',
        'l.dld.ld.d.',
        '.ld.ddd.dl.',
        'ld..ede..dl',
        '...eeeee...',
    ], {'l': C['mg_lt'], 'd': C['mg_dk2'], 'e': C['mg_ink']})


def leaves(seed=0):
    """A few fallen autumn leaves on the forest floor."""
    img = new(12, 7)
    pts = [(1, 2), (5, 0), (9, 3), (3, 5), (7, 5), (10, 1)]
    for i, (x, y) in enumerate(pts[:4 + seed % 3]):
        c = C['au_base'] if (i + seed) % 2 else C['au_dk']
        img[y, x, :3] = c
        img[y, x + 1, :3] = c
        img[y, x, 3] = img[y, x + 1, 3] = 255
    return img


def log(w=30):
    """Fallen log lying across (bark lit from above, rings on the right end)."""
    h = 12
    img = new(w, h)
    for y in range(1, h - 1):
        for x in range(0, w - 5):
            c = C['tr_lt'] if y <= 3 else C['tr_base'] if y <= 7 else C['tr_dk']
            if (x * 7 + y * 3) % 11 == 0 and 2 < y < 9:
                c = C['tr_dk']
            img[y, x, :3] = c
            img[y, x, 3] = 255
    ends = shade_parts(10, h, [P(Ellipse(5, h / 2, 4.2, h / 2 - 0.6), ramp('wd_hi', 'wd_hi', 'wd_lt', 'wd_base', 'wd_dk'),
                                 flat=True, line=C['wd_dk'])], outline=C['tr_ink'])
    m = ends[..., 3] > 0
    img[:, w - 10:][m] = ends[m]
    img[h // 2, w - 5, :3] = C['wd_dk']
    for x in range(0, w - 5):                       # outline top and bottom
        img[0, x, :3] = img[h - 1, x, :3] = C['tr_ink']
        img[0, x, 3] = img[h - 1, x, 3] = 255
    for y in range(0, h):
        img[y, 0, :3] = C['tr_ink']
        img[y, 0, 3] = 255
    return img


def mini_acorn():
    """Sign icon for the woods: same three colors as mini_shell and
    mini_heart, so the meadow sign costs no extra palette."""
    return from_ascii([
        '.kkkkk.',
        'kkwkkkk',
        'kkkkkkk',
        '.kwppk.',
        '..kpk..',
        '...k...',
    ], {'k': rgb15('#b0607e'), 'p': rgb15('#ffcadb'), 'w': C['white']})


# ------------------------------------------------------------------ flowers
FLOWER_ROWS = {
    'pink': ['.a.', 'aya', '.b.'],
    'yellow': ['.c.', 'coc', '.d.'],
    'blue': ['.e.', 'eye', '.f.'],
    'white': ['.w.', 'wyw', '.v.'],
}
FLOWER_LEGEND = {
    'a': C['f_pink'], 'b': C['f_pink_dk'], 'y': C['f_yel'], 'c': C['f_yel'], 'o': C['f_white'],
    'd': C['f_yel_dk'], 'e': C['f_blue'], 'f': C['f_blue_dk'], 'w': C['f_white'], 'v': C['f_lav'],
    's': C['g_dk2'],
}


def flower(kind):
    rows = FLOWER_ROWS[kind] + ['.s.']
    return from_ascii(rows, FLOWER_LEGEND)


# ------------------------------------------------------------------ cottage
def cottage():
    W, H = 64, 64
    from squishies import HalfPlane, Clip
    eave = [Ellipse(x, 35.5, 4.4, 3.2) for x in range(6, 60, 8)]
    roof = Union(Clip(Ellipse(32, 37, 30.5, 32), HalfPlane(0, -1, -36)), *eave)
    parts = [
        P(Poly([(44, 3), (51, 3), (51, 18), (44, 18)], 0.5), ramp('ui_lav', 'ui_lav', 'ui_lav', 'ui_lav2', 'ui_lav2'),
          z=-1, bevel=True),
        P(Poly([(9, 34), (55, 34), (55, 61), (9, 61)], 0.5), WALL, z=0, bevel=True),
        P(roof, ROOF, z=2, line=C['rf_ink'], levels=(0.97, 0.80, 0.42, 0.18)),
        P(Union(Poly([(27, 47), (37, 47), (37, 61), (27, 61)], 0.3), Ellipse(32, 47, 5.3, 5.3)), DOOR, z=1,
          line=C['wl_ink'], bevel=True),
        P(Ellipse(17, 47.5, 5.3), WIN, z=1, line=C['wl_ink'], bevel=True),
        P(Ellipse(47, 47.5, 5.3), WIN, z=1, line=C['wl_ink'], bevel=True),
    ]
    img = shade_parts(W, H, parts, outline=C['rf_ink'])

    def px(x, y, c):
        if 0 <= x < W and 0 <= y < H:
            img[y, x, :3] = c
            img[y, x, 3] = 255

    roofc = (C['rf_base'], C['rf_lt'], C['rf_hi'])
    # scallop shingles: rows of small arcs
    for row, y in enumerate((13, 20, 27)):
        off = 0 if row % 2 == 0 else 4
        for x0 in range(-2 + off, 64, 8):
            for dx, dy in ((0, 0), (1, 1), (2, 1), (3, 1), (4, 1), (5, 0)):
                X, Y = x0 + dx, y + dy
                if 0 <= X < W and img[Y, X, 3] and tuple(img[Y, X, :3]) in roofc:
                    img[Y, X, :3] = C['rf_dk']
    # heart window on the roof
    heart = ['.kk.kk.', 'kbbkbbk', 'kbhbbbk', 'kbbbbbk', '.kbbbk.', '..kbk..', '...k...']
    for y, row in enumerate(heart):
        for x, ch in enumerate(row):
            if ch != '.':
                px(29 + x, 16 + y, {'k': C['rf_ink'], 'b': C['win_base'], 'h': C['white']}[ch])
    # door: planks, knob, little round window
    for y in range(50, 61):
        px(32, y, C['dr_dk'])
    px(35, 55, C['f_yel_dk'])
    px(35, 54, C['f_yel'])
    for (dx, dy) in ((-1, -1), (0, -1), (1, -1), (-1, 0), (0, 0), (1, 0)):
        px(32 + dx, 46 + dy, C['win_base'])
    px(31, 45, C['white'])
    # window cross + glint
    for cx in (17, 47):
        for d in range(-4, 5):
            px(cx, 47 + d, C['wl_lt']) if abs(d) < 5 else None
            px(cx + d, 47, C['wl_lt'])
        px(cx - 3, 45, C['white'])
        px(cx - 2, 44, C['white'])
    # flower boxes
    for cx in (17, 47):
        for x in range(cx - 6, cx + 7):
            px(x, 53, C['wd_lt'])
            px(x, 54, C['wd_base'])
            px(x, 55, C['wd_dk2'])
        for i, x in enumerate(range(cx - 5, cx + 7, 3)):
            col = (C['f_pink'], C['f_yel'], C['f_blue'], C['f_pink'])[i % 4]
            dk = (C['f_pink_dk'], C['f_yel_dk'], C['f_blue_dk'], C['f_pink_dk'])[i % 4]
            px(x, 52, col)
            px(x - 1, 51, col)
            px(x + 1, 51, col)
            px(x, 50, col)
            px(x, 51, C['f_yel'] if col != C['f_yel'] else C['white'])
            px(x + 1, 52, dk)
    # foundation stones along the wall bottom
    for x in range(10, 55):
        if x < 27 or x > 37:
            px(x, 60, C['wl_dk'])
    for x in range(12, 55, 5):
        if x < 26 or x > 38:
            px(x, 59, C['wl_dk'])
    return img


def stepping_stone():
    return shade_parts(8, 6, [P(Ellipse(4, 3, 3.4, 2.2), ramp('pebble', 'pebble', 'pebble', 'p_dk', 'p_dk'),
                                levels=(0.99, 0.95, 0.4, 0.2))], outline=C['p_dk2'])


# ------------------------------------------------------------ ground decor
_DECOR_LEGEND = {
    'P': C['f_pink'], 'Q': C['f_pink_dk'], 'Y': C['f_yel'], 'Z': C['f_yel_dk'],
    'B': C['f_blue'], 'N': C['f_blue_dk'], 'W': C['f_white'], 'V': C['f_lav'], 'U': C['f_lav_dk'],
    'y': C['f_yel'], 'l': C['g_lt'], 'd': C['g_dk'], 'e': C['g_dk2'], 'h': C['g_hi'],
    'r': C['pebble'], 'R': C['p_dk'], 'k': C['p_dk2'],
}

DECOR = {
    'patch_pink': [
        '.P.....P..',
        'PyQ...PyQ.',
        '.Qe.P..Qe.',
        '..ePyQ.e..',
        '.e..Qe..e.',
        '..dd.edd..',
    ],
    'patch_yellow': [
        '..Y....Y..',
        '.YyZ..YyZ.',
        '..Ze.Y.Ze.',
        '.e..YyZe..',
        '..e..Ze...',
        '..dd..ed..',
    ],
    'patch_mix': [
        '.W...B....',
        'WyV.ByN.P.',
        '.Ve..Ne.PyQ',
        '..e.P..e.Qe',
        '.d.PyQ.d.e.',
        '..d.Qe.dd..',
        '....dd.....',
    ],
    'tulips': [
        '.P.P...Y.Y.',
        '.PPP...YYY.',
        '.PPQ...YYZ.',
        '..Q.....Z..',
        '..e..B.B.e.',
        '.le..BBB.e.',
        '..e..BBN.el',
        '.le...N..e.',
        '..e..le....',
        '.....le....',
    ],
    'tuft': [
        '..l...l..',
        '.ld..ld.l',
        'ldd.ldd.d',
        '.dd.dd.dd',
    ],
    'tuft_small': [
        '.l..l.',
        'ld.ld.',
        'dd.dd.',
    ],
    'clover': [
        '.l.l.',
        'lddld',
        '.ded.',
        '..e..',
    ],
    'pebbles': [
        '.rr....',
        'rrrR.r.',
        '.RR.rrR',
        '.....R.',
    ],
}


def decor(name, ground='meadow'):
    """ground='woods' paints the grass bits in the woods' moss greens."""
    legend = dict(_DECOR_LEGEND)
    if ground == 'woods':
        legend.update(l=C['mg_lt'], d=C['mg_dk'], e=C['mg_dk2'], h=C['mg_hi'])
    return from_ascii(DECOR[name], legend)


# fence shares the stone greys so both fit the same background palette
FENCE_LEGEND = {'k': rgb15('#a89cbe'), 'w': C['white'], 's': rgb15('#ebe6f4'), 'd': rgb15('#dcd5ea')}
_FENCE = [
    '...k.......k....',
    '..kwk.....kwk...',
    '..kwk.....kwk...',
    'kkkwkkkkkkkwkkkk',
    'wwwwwwwwwwwwwwww',
    'ssssssssssssssss',
    'kkkwkkkkkkkwkkkk',
    '..kwk.....kwk...',
    'kkkwkkkkkkkwkkkk',
    'wwwwwwwwwwwwwwww',
    'ssssssssssssssss',
    'kkksdkkkkkksdkkk',
    '..kdk.....kdk...',
    '...k.......k....',
]


def fence(n=1):
    rows = [r * n for r in _FENCE]
    return from_ascii(rows, FENCE_LEGEND)


def fence_side(h):
    """Vertical fence run: two rails with a post every 12 px, h px tall."""
    k, w, sd = FENCE_LEGEND['k'], FENCE_LEGEND['w'], FENCE_LEGEND['s']
    img = new(7, h)
    for y in range(h):
        for x, col in ((0, k), (1, w), (2, sd), (3, k), (4, w), (5, sd), (6, k)):
            img[y, x, :3] = col
            img[y, x, 3] = 255
    for y0 in range(0, h - 4, 12):
        for y in range(y0, y0 + 4):
            for x in range(7):
                img[y, x, :3] = w if 0 < x < 6 and y0 < y < y0 + 3 else k
    return img


def lily_pad(flower_on=False):
    rows = [
        '..llll..',
        '.lllhll.',
        'llhllld.',
        'lllll...',
        'lllllldd',
        '.ldddd..',
    ]
    # grass greens, so pads share the pond's palette
    img = from_ascii(rows, {'l': C['g_lt'], 'h': C['g_hi'], 'd': C['g_dk2']})
    if flower_on:
        fl = from_ascii(['.P.', 'PWP', '.P.'], {'P': C['f_pink'], 'W': C['white']})
        from gba import blit as _b
        _b(img, fl, 2, 0)
    return img


def reeds():
    rows = [
        '.b...',
        '.b.b.',
        '.bgb.',
        '.gbg.',
        'lg.gl',
        '.g.g.',
        'lgggl',
        '.lgl.',
    ]
    return from_ascii(rows, {'b': C['tr_dk'], 'g': C['g_dk2'], 'l': C['g_dk']})


STONE = [rgb15(h) for h in ('#fbf9ff', '#ebe6f4', '#dcd5ea', '#c2b8d6', '#a89cbe')]
STONE_INK = rgb15('#7d7094')


def rock(big=False):
    rp = STONE
    w, h = (14, 10) if big else (9, 7)
    return shade_parts(w, h, [P(Ellipse(w / 2, h / 2 + 0.5, w / 2 - 1.2, h / 2 - 1.2), rp, k=2.0,
                                levels=(0.97, 0.8, 0.4, 0.15))], outline=STONE_INK)


BUTTERFLY = {
    'pink': ['#ffb8cc', '#f28db0'],
    'yellow': ['#ffe890', '#f5c563'],
    'blue': ['#bcdcff', '#8fb8f0'],
}


def butterfly(color='pink', frame=0):
    a, b = (rgb15(h) for h in BUTTERFLY[color])
    rows = [['PP.PP', 'PQkQP', '.QkQ.', '..k..'],
            ['.P.P.', '.QkQ.', '.QkQ.', '..k..']][frame]
    return from_ascii(rows, {'P': a, 'Q': b, 'k': C['ink2']})


# ------------------------------------------------------------ SDF regions
class SDF:
    def inside(self, X, Y):
        return self.d(X, Y) <= 0


class Capsule(SDF):
    def __init__(self, ax, ay, bx, by, r):
        self.a, self.b, self.r = (ax, ay), (bx, by), r

    def d(self, X, Y):
        from squishies import _seg_dist
        return _seg_dist(X, Y, *self.a, *self.b) - self.r


class Oval(SDF):
    def __init__(self, cx, cy, rx, ry, n=2.0):
        self.cx, self.cy, self.rx, self.ry, self.n = cx, cy, rx, ry, n

    def d(self, X, Y):
        x = np.abs(X - self.cx) / self.rx
        y = np.abs(Y - self.cy) / self.ry
        return ((x ** self.n + y ** self.n) ** (1 / self.n) - 1) * min(self.rx, self.ry)


class SmoothUnion(SDF):
    def __init__(self, k, *shapes):
        self.k, self.shapes = k, shapes

    def d(self, X, Y):
        d = self.shapes[0].d(X, Y)
        for s in self.shapes[1:]:
            d2 = s.d(X, Y)
            h = np.clip(0.5 + 0.5 * (d2 - d) / self.k, 0, 1)
            d = d2 * (1 - h) + d * h - self.k * h * (1 - h)
        return d


# ------------------------------------------------------------ more props
def mailbox(flag=True):
    """flag=False: without its flag (the ROM draws the flag as a sprite, so
    it can go up when a letter waits)."""
    pink = ramp('rf_hi', 'rf_lt', 'rf_base', 'rf_dk', 'rf_dk')
    parts = [
        P(Poly([(5.5, 11), (8.5, 11), (8.5, 21), (5.5, 21)], 0.2), WOOD, z=0, bevel=True),
        P(Union(Poly([(1.5, 5), (12.5, 5), (12.5, 12), (1.5, 12)], 0.8), Ellipse(7, 5.5, 5.5, 4)), pink, z=1,
          k=2.0, levels=(0.97, 0.8, 0.4, 0.15), line=C['rf_ink']),
        P(Poly([(12.5, 1), (14.5, 1), (14.5, 9), (12.5, 9)], 0.3), ramp('f_yel', 'f_yel', 'f_yel', 'f_yel_dk', 'f_yel_dk'),
          z=2, bevel=True, line=C['rf_ink']),
    ][:3 if flag else 2]
    img = shade_parts(16, 23, parts, outline=C['rf_ink'])
    for x in range(4, 10):
        img[8, x, :3] = C['rf_ink']
    img[10, 6, :3] = C['white']
    img[10, 8, :3] = C['white']
    img[11, 7, :3] = C['white']
    return img


def mini_heart():
    # same three colors as mini_shell, so the sign costs no extra palette
    return from_ascii(['.kk.kk.', 'kwpkppk', 'kpppppk', '.kpppk.', '..kpk..', '...k...'],
                      {'k': rgb15('#b0607e'), 'p': rgb15('#ffcadb'), 'w': C['white']})


def signpost(icon=None):
    parts = [
        P(Poly([(6.5, 11), (9.5, 11), (9.5, 21), (6.5, 21)], 0.2), WOOD, z=0, bevel=True),
        P(Poly([(1, 3), (13, 3), (16, 7.5), (13, 12), (1, 12)], 0.5), WOOD, z=1, bevel=True, line=C['wd_ink']),
    ]
    img = shade_parts(18, 23, parts, outline=C['wd_ink'])
    if icon is not None:
        from gba import blit as _b
        _b(img, icon, 4, 5)
    return img


def picnic_blanket():
    w, h = 34, 20
    img = new(w, h)
    for y in range(h):
        for x in range(w):
            edge = x in (0, w - 1) or y in (0, h - 1)
            cell = ((x - 1) // 4 + (y - 1) // 4) % 2
            c = C['ui_pk2'] if cell else C['white']
            if edge:
                c = C['ui_line']
            img[y, x, :3] = c
            img[y, x, 3] = 255
    for x in range(1, w - 1):
        if (x % 3) == 0:
            img[h - 1, x, :3] = C['ui_pk2']
    return img


def basket():
    parts = [
        P(Minus(Ellipse(7, 5, 5.5, 5), Ellipse(7, 5, 3.5, 3.4)), WOOD, z=1, k=2.0, line=C['wd_ink']),
        P(Poly([(1.5, 5), (12.5, 5), (11, 11), (3, 11)], 0.8), WOOD, z=2, bevel=True, line=C['wd_ink']),
    ]
    img = shade_parts(15, 13, parts, outline=C['wd_ink'])
    for x in range(3, 12, 2):
        for y in range(6, 11):
            if img[y, x, 3] and tuple(img[y, x, :3]) == C['wd_base']:
                img[y, x, :3] = C['wd_dk']
    for (x, y) in ((6, 4), (7, 4), (8, 4)):
        img[y, x, :3] = C['f_pink']
    img[3, 7, :3] = C['white']
    return img


def mini_shell():
    return from_ascii([
        '.k.k.k.',
        'kpwpkpk',
        'kpwpkpk',
        '.kpkpk.',
        '..kkk..',
    ], {'k': rgb15('#b0607e'), 'p': rgb15('#ffcadb'), 'w': C['white']})


# ----------------------------------------------------------------- shore
SAND = ramp('s_hi', 's_lt', 's_base', 's_dk', 's_dk2')
SHORE_KINDS = {
    'base': 's',
    'base_ramp': SAND,
    'e': {'ramp': ramp('sea_hi', 'sea_lt', 'sea_base', 'sea_dk', 'sea_dk2', 'sea_dk2'), 'deep': True,
          'shimmer': [(4, 6, 5, 'l'), (19, 18, 4, 'l'), (11, 27, 3, 'l')]},
    'w': {'ramp': ramp('sea_hi', 'sea_lt', 'sea_base', 'sea_dk', 'sea_dk2', 'sea_dk2'), 'deep': True,
          'shimmer': [(6, 10, 3, 'l')]},
}


def shore_ground(lab):
    """Sand + sea with wet sand band, foam line and sand sparkle texture."""
    img, lab = render_terrain(None, SHORE_KINDS, lab=lab, grass_variant=lambda x, y: 0)
    H, W = lab.shape
    sea = lab == 'e'
    # wet sand: 3 px of darker sand under the sea
    for dy in (1, 2, 3):
        m = np.zeros_like(sea)
        m[dy:] = sea[:-dy]
        m &= (lab == 's')
        img[m, :3] = C['s_dk'] if dy < 3 else C['s_base']
        if dy == 3:
            ys, xs = np.nonzero(m)
            for y, x in zip(ys, xs):
                if (x // 2 + y) % 3 == 0:
                    img[y, x, :3] = C['s_dk']
    # foam: bright wavy line 2px inside the sea edge
    below = np.zeros_like(sea)
    below[:-1] = sea[1:]
    edge = sea & ~below
    ys, xs = np.nonzero(edge)
    for y, x in zip(ys, xs):
        img[y, x, :3] = C['foam']
        off = 3 + int(1.5 * (1 + math.sin(x / 5.0)))
        if y - off >= 0 and sea[y - off, x]:
            img[y - off, x, :3] = C['sea_hi']
        if y - 1 >= 0 and sea[y - 1, x] and (x % 7) in (0, 1, 2, 3):
            img[y - 1, x, :3] = C['foam']
    # sand speckles
    for y in range(0, H, 1):
        for x in range(0, W, 1):
            if lab[y, x] == 's' and tuple(img[y, x, :3]) == C['s_base']:
                h = _h(x % 32, y % 32, 3)
                if h < 0.018:
                    img[y, x, :3] = C['s_dk']
                elif h > 0.985:
                    img[y, x, :3] = C['s_hi']
    return img


PALM_PAD, PALM_TOP = 12, 5   # the crown was wider and taller than the old 40x56 image: fronds were cut (Brick test, 8.1)


def palm(flip=False):
    """A leaning palm, 64x61 px. Before 8.1 it was 40x56 and cut its fronds;
    callers place it PALM_PAD left and PALM_TOP up of the old spot, so the
    trunk (and its solid base, centred) stays where it was."""
    o, t = PALM_PAD, PALM_TOP
    w, h = 40 + 2 * o, 56 + t
    img = new(w, h)
    palm_trunk(img, 18 + o, 54 + t, 42, 7)
    for x in range(14 + o, 25 + o):
        img[55 + t, x, :3] = C['tr_ink']
        img[55 + t, x, 3] = 255
    leaf = ramp('t_hi', 't_lt', 't_base', 't_dk', 't_dk2')
    fronds = [Ellipse(14 + o, 12 + t, 13, 4.2, rot=-25), Ellipse(36 + o, 12 + t, 12, 4.0, rot=28),
              Ellipse(22 + o, 6 + t, 10, 3.8, rot=-70), Ellipse(32 + o, 6 + t, 10, 3.6, rot=65),
              Ellipse(12 + o, 19 + t, 11, 3.6, rot=-50), Ellipse(35 + o, 19 + t, 10, 3.4, rot=55)]
    parts = [P(f, leaf, z=i % 3, line=C['t_dk2'], k=3.0, levels=(0.97, 0.78, 0.40, 0.12)) for i, f in enumerate(fronds)]
    parts.append(P(Union(Ellipse(22 + o, 14 + t, 2.6), Ellipse(27.5 + o, 14.5 + t, 2.6), Ellipse(25 + o, 17.5 + t, 2.6)),
                   ramp('wd_lt', 'wd_lt', 'wd_base', 'wd_dk', 'wd_dk2'), z=5, line=C['wd_ink'], k=2.0))
    ch = 34 + t                                      # the low fronds reach row ~30 (26 cut them)
    crown = shade_parts(w, ch, parts, outline=C['t_ink'])
    m = crown[..., 3] > 0
    img[:ch][m] = crown[m]
    if flip:
        img = img[:, ::-1].copy()
    return img


def umbrella():
    w, h = 50, 46
    img = new(w, h)
    cx, cy = 25, 20
    stripes = 8
    for y in range(h):
        for x in range(w):
            dx, dy = (x + 0.5 - cx) / 23.5, (y + 0.5 - cy) / 17.0
            if dy <= 0 and dx * dx + dy * dy <= 1:
                ang = math.atan2(-(y + 0.5 - cy), x + 0.5 - cx)   # 0..pi
                band = int(ang / (math.pi / stripes))
                pink = band % 2 == 0
                lit = (dx < 0.1 and dy < -0.35)
                if pink:
                    c = C['rf_lt'] if lit else C['rf_base']
                else:
                    c = C['white'] if lit else C['wl_base']
                img[y, x, :3] = c
                img[y, x, 3] = 255
    # scalloped rim: one bump per stripe
    for x in range(1, w - 1):
        t = (x + 0.5 - (cx - 23.5)) / 47.0
        k = t * stripes
        bump = math.sin(math.pi * (k % 1.0))
        ybot = int(cy + 3.5 * bump)
        band = int(k) % 2 == 0
        src = img[int(cy) - 1, x, :3].copy()
        for y in range(int(cy), ybot + 1):
            if img[int(cy) - 1, x, 3]:
                img[y, x, :3] = src
                img[y, x, 3] = 255
        if img[int(cy) - 1, x, 3] and ybot >= int(cy):
            img[ybot, x, :3] = C['rf_dk'] if band else C['wl_dk']
    # pole
    for y in range(20, 44):
        img[y, 24, :3] = C['tr_ink']
        img[y, 25, :3] = C['wd_lt']
        img[y, 26, :3] = C['tr_ink']
        img[y, 24:27, 3] = 255
    img[0:3, 24:27, :3] = C['f_yel']
    img[0:3, 24:27, 3] = 255
    m = img[..., 3] > 0
    out = np.zeros_like(m)
    out[1:] |= m[:-1]
    out[:-1] |= m[1:]
    out[:, 1:] |= m[:, :-1]
    out[:, :-1] |= m[:, 1:]
    out &= ~m
    img[out, :3] = C['rf_ink']
    img[out, 3] = 255
    return img


def beach_ball():
    img = new(13, 13)
    for y in range(13):
        for x in range(13):
            dx, dy = x + 0.5 - 6.5, y + 0.5 - 6.5
            if dx * dx + dy * dy <= 30:
                a = math.atan2(dy, dx)
                seg = int((a + math.pi) / (2 * math.pi / 6)) % 3
                c = (C['f_pink'], C['white'], C['f_blue'])[seg]
                if dx * dx + dy * dy <= 3:
                    c = C['f_yel']
                if dx + dy > 5:
                    c = {C['f_pink']: C['f_pink_dk'], C['white']: C['wl_base'], C['f_blue']: C['f_blue_dk'],
                         C['f_yel']: C['f_yel_dk']}[c]
                img[y, x, :3] = c
                img[y, x, 3] = 255
    img[3, 4, :3] = C['white']
    img[3, 5, :3] = C['white']
    m = img[..., 3] > 0
    out = np.zeros_like(m)
    out[1:] |= m[:-1]
    out[:-1] |= m[1:]
    out[:, 1:] |= m[:, :-1]
    out[:, :-1] |= m[:, 1:]
    out &= ~m
    img[out, :3] = C['ui_ink']
    img[out, 3] = 255
    return img


def sailboat():
    rows = [
        '.......k........',
        '.......kk.......',
        '.......kwk......',
        '.......kwwk.....',
        '.......kppwk....',
        '.......kwwwwk...',
        '.......kppppwk..',
        '.......kwwwwwwk.',
        '.......kkkkkkkkk',
        '.kkkkkkkkkkkkkk.',
        '.kaaaaaaaaaaaak.',
        '..kbbbbbbbbbbk..',
        '...kkkkkkkkkk...',
    ]
    return from_ascii(rows, {'k': C['wd_ink'], 'w': C['white'], 'p': C['f_pink'], 'a': C['wd_lt'], 'b': C['wd_base']})


def towel():
    w, h = 20, 30
    img = new(w, h)
    for y in range(h):
        for x in range(w):
            stripe = (y // 4) % 2
            img[y, x, :3] = C['ui_mint'] if stripe else C['white']
            img[y, x, 3] = 255
    img[0, :, :3] = C['ui_mint2']
    img[-1, :, :3] = C['ui_mint2']
    img[:, 0, :3] = C['ui_mint2']
    img[:, -1, :3] = C['ui_mint2']
    return img


CASTLE = [rgb15(h) for h in ('#fff0d6', '#fbe0b8', '#f1cc98', '#e0b27e', '#cf9c6a')]
CASTLE_INK = rgb15('#a8745a')


def sandcastle():
    SAND = CASTLE
    parts = [
        P(Poly([(4, 16), (28, 16), (28, 27), (4, 27)], 0.5), SAND, z=0, bevel=True),
        P(Poly([(2, 8), (10, 8), (10, 27), (2, 27)], 0.5), SAND, z=1, bevel=True, line=CASTLE_INK),
        P(Poly([(22, 8), (30, 8), (30, 27), (22, 27)], 0.5), SAND, z=1, bevel=True, line=CASTLE_INK),
        P(Poly([(11, 3), (21, 3), (21, 27), (11, 27)], 0.5), SAND, z=2, bevel=True, line=CASTLE_INK),
    ]
    img = shade_parts(33, 29, parts, outline=CASTLE_INK)
    for tx0, tx1, ty in ((2, 10, 8), (22, 30, 8), (11, 21, 3)):
        for x in range(tx0, tx1 + 1, 3):
            if 0 <= ty - 1:
                img[ty - 1, x, :3] = C['s_ink']
                img[ty - 1, x, 3] = 0
    # door + windows
    for y in range(20, 27):
        for x in range(14, 18):
            img[y, x, :3] = CASTLE[4]
    img[19, 15:17, :3] = CASTLE[4]
    img[12, 5:7, :3] = CASTLE[4]
    img[12, 25:27, :3] = CASTLE[4]
    img[9, 15:17, :3] = CASTLE[4]
    # flag
    fl = from_ascii(['k..', 'kpp', 'kpP', 'k..', 'k..'], {'k': C['tr_ink'], 'p': C['f_pink'], 'P': C['f_pink_dk']})
    out = new(33, 34)
    out[5:] = img
    from gba import blit as _b
    _b(out, fl, 15, 1)
    return out


def starfish():
    return from_ascii([
        '...k...',
        '..kok..',
        'kkkookk'[:7],
        'koooook',
        '.kowok.',
        '.kok.k.'[:7],
        '.k...k.',
    ], {'k': rgb15('#d0707a'), 'o': rgb15('#ffab94'), 'w': C['white']})


def tiny_shell(kind=0):
    rows = [['.k.k.', 'kpkpk', '.kkk.'], ['kk.', 'kpk', '.kk']][kind]
    return from_ascii(rows, {'k': rgb15('#e0a0b4'), 'p': C['white']})


def footprints(img, pts):
    """Little wet footprints (pairs of 2x1 dents) in sand."""
    for (x, y) in pts:
        for dx in (0, 1):
            img[y, x + dx, :3] = C['s_dk']
        img[y + 1, x, :3] = C['s_dk']


# ------------------------------------------------------------- cloud hill
def cloud_ground(lab, sky):
    """Walkable cloud platforms over an existing sky image."""
    H, W = lab.shape
    img = sky.copy()
    c = lab == 'c'

    def sh(m, dy, dx):
        out = np.zeros_like(m)
        H_, W_ = m.shape
        ys0, ys1 = max(0, dy), min(H_, H_ + dy)
        xs0, xs1 = max(0, dx), min(W_, W_ + dx)
        out[ys0:ys1, xs0:xs1] = m[ys0 - dy:ys1 - dy, xs0 - dx:xs1 - dx]
        return out

    # cloud side (thickness) below the top surface
    side = np.zeros_like(c)
    for d in range(1, 6):
        side |= sh(c, d, 0)
    side &= ~c
    img[side, :3] = C['cl_dk']
    low = sh(c, 5, 0) & ~sh(c, 4, 0) & ~c
    img[low | (side & ~sh(c, 3, 0)), :3] = C['cl_dk2']
    solid = c | side
    img[c, :3] = C['cl_base']
    # rim light on top, soft shade on the lower part of the top surface
    top = c & ~sh(c, 1, 0)
    img[top, :3] = C['cl_hi']
    lower = c & ~sh(c, -2, 0)
    img[lower & ~top, :3] = C['cl_hi']
    # puffy texture: little arcs, tile periodic
    ys, xs = np.mgrid[0:H, 0:W]
    arc = np.zeros_like(c)
    for (ax, ay) in ((6, 10), (22, 26), (14, 20), (28, 6)):
        for dx, dy in ((0, 0), (1, -1), (2, -1), (3, -1), (4, 0)):
            arc |= ((xs % 32) == (ax + dx) % 32) & ((ys % 32) == (ay + dy) % 32)
    inner = c & sh(c, 3, 0) & sh(c, -3, 0) & sh(c, 0, 3) & sh(c, 0, -3)
    img[arc & inner, :3] = C['cl_dk']
    # outline
    out = np.zeros_like(solid)
    out[1:] |= solid[:-1]
    out[:-1] |= solid[1:]
    out[:, 1:] |= solid[:, :-1]
    out[:, :-1] |= solid[:, 1:]
    out &= ~solid
    img[out, :3] = C['cl_ink']
    return img


def rainbow(w=80, h=48, thick=4):
    cols = ['#ffb3c8', '#ffd3a8', '#fff0a0', '#bff0cc', '#bfe0ff', '#d8c6fa']
    img = new(w, h)
    cx, cy = w / 2, h + 4
    R = w / 2 - 1
    for y in range(h):
        for x in range(w):
            r = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            k = int((R - r) // thick)
            if 0 <= k < len(cols):
                img[y, x, :3] = rgb15(cols[k])
                img[y, x, 3] = 255
    return img


def gacha():
    w, h = 40, 60
    pink = ramp('rf_hi', 'rf_lt', 'rf_base', 'rf_dk', 'rf_dk')
    glass = [C['white'], rgb15('#f2f9ff'), rgb15('#e2f1fc'), rgb15('#c9e3f7'), rgb15('#b0d2ef')]
    parts = [
        P(Poly([(6, 32), (34, 32), (34, 56), (6, 56)], 2.5), pink, z=0, bevel=True),
        P(Poly([(4, 54), (36, 54), (36, 59), (4, 59)], 1.2), ramp('ui_lav', 'ui_lav', 'ui_lav2', 'f_lav_dk', 'f_lav_dk'),
          z=1, bevel=True, line=C['rf_ink']),
        P(Ellipse(20, 20, 15.5, 15), glass, z=2, k=1.6, levels=(0.99, 0.9, 0.45, 0.15), line=C['rf_ink']),
        P(Poly([(8, 30), (32, 30), (32, 35), (8, 35)], 1.2), pink, z=3, bevel=True, line=C['rf_ink']),
    ]
    img = shade_parts(w, h, parts, outline=C['rf_ink'])
    # capsules inside the dome
    caps = [(12, 25, '#ffb3c8', '#ec8fae'), (20, 27, '#fff0a0', '#e8c060'), (28, 25, '#bfe0ff', '#86b4e6'),
            (15, 18, '#bff0cc', '#7cc8a0'), (25, 18, '#d8c6fa', '#a890e0'), (20, 11, '#ffd3a8', '#e8a070'),
            (10, 12, '#ffb3c8', '#ec8fae'), (30, 12, '#fff0a0', '#e8c060')]
    for cx, cy, a, b in caps:
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                if dx * dx + dy * dy <= 10:
                    x, y = cx + dx, cy + dy
                    col = rgb15(a) if dy < 0 else C['white']
                    if dy == 0:
                        col = rgb15(b)
                    if dx * dx + dy * dy > 6:
                        col = rgb15(b) if dy <= 0 else rgb15('#d8d0e8')
                    img[y, x, :3] = col
        img[cy - 2, cx - 1, :3] = C['white']
    # glass glare
    for (x, y) in ((10, 9), (9, 10), (9, 11), (8, 13), (11, 8)):
        img[y, x, :3] = C['white']
    # crank knob
    for dy in range(-4, 5):
        for dx in range(-4, 5):
            d2 = dx * dx + dy * dy
            if d2 <= 18:
                img[44 + dy, 14 + dx, :3] = C['rf_ink'] if d2 > 12 else (C['white'] if dx + dy < 0 else C['wl_base'])
    for x in range(11, 18):
        img[44, x, :3] = C['rf_dk']
    # chute
    for y in range(41, 50):
        for x in range(24, 32):
            edge = y in (41, 49) or x in (24, 31)
            img[y, x, :3] = C['rf_ink'] if edge else rgb15('#b0587c')
    for y in range(45, 49):
        for x in range(25, 31):
            img[y, x, :3] = rgb15('#ffe0a0') if y < 47 else rgb15('#e8c060')
    # star topper
    star = from_ascii(['..k..', '.kyk.', 'kyyyk', '.kyk.', 'k.k.k'][:4], {'k': rgb15('#b27a30'), 'y': rgb15('#ffe07a')})
    out = new(w, h + 4)
    out[4:] = img
    from gba import blit as _b
    _b(out, star, 18, 0)
    return out


def moon():
    rows = [
        '...kkkk..',
        '..kyyyk..',
        '.kyyyk...',
        'kyyyk....',
        'kyyyk....',
        'kyyyyk...',
        '.kyyyykk.',
        '..kyyyyyk',
        '...kkkkk.',
    ]
    return from_ascii(rows, {'k': rgb15('#d8a848'), 'y': rgb15('#fff2b0')})


def star_deco(big=False):
    if big:
        rows = ['...k...', '..kyk..', 'kkyyykk', '.kyyyk.', '.kyky k'.replace(' ', ''), 'kk...kk'][:6]
        rows = ['...k...', '..kyk..', 'kkyyykk', 'kyyyyyk', '.kyyyk.', '.kykyk.', 'kk...kk']
    else:
        rows = ['.k.', 'kyk', '.k.']
    return from_ascii(rows, {'k': rgb15('#e0b050'), 'y': rgb15('#fff0a0')})


class CloudBlob(SDF):
    """Oval with puffy scalloped edges."""

    def __init__(self, cx, cy, rx, ry, bump=7.0, n=None, seed=0):
        import random
        rnd = random.Random(seed)
        self.core = Oval(cx, cy, rx - bump * 0.6, ry - bump * 0.6, n=2.2)
        per = 2 * math.pi * math.sqrt((rx * rx + ry * ry) / 2)
        n = n or max(6, int(per / (bump * 1.5)))
        self.puffs = []
        for i in range(n):
            t = 2 * math.pi * i / n
            r = bump * rnd.uniform(0.85, 1.15)
            self.puffs.append((cx + (rx - bump * 0.8) * math.cos(t), cy + (ry - bump * 0.8) * math.sin(t), r))

    def d(self, X, Y):
        d = self.core.d(X, Y)
        for (px, py, r) in self.puffs:
            d = np.minimum(d, np.hypot(X - px, Y - py) - r)
        return d


class UnionSDF(SDF):
    def __init__(self, *s):
        self.s = s

    def d(self, X, Y):
        d = self.s[0].d(X, Y)
        for t in self.s[1:]:
            d = np.minimum(d, t.d(X, Y))
        return d


CANDY = {
    'pink': ([rgb15(h) for h in ('#fff4f8', '#ffe0ec', '#ffc8dc', '#f6a8c6', '#e48cb0')], rgb15('#b0608c')),
    'blue': ([rgb15(h) for h in ('#f6fbff', '#e0f0ff', '#c8e2fc', '#a8cdf4', '#8cb6ea')], rgb15('#5a86b8')),
}


def candy_tree(kind='pink'):
    rp, ink = CANDY[kind]
    w, h = 32, 44
    clumps = [(16, 12, 11, 10, 0), (9, 17, 7, 6.5, 1), (23, 17, 7, 6.5, 1), (16, 21, 9, 6, 2)]
    parts = [P(Ellipse(x, y, rx, ry), rp, z=z, line=rp[3], k=4.5, levels=(0.96, 0.78, 0.40, 0.12))
             for (x, y, rx, ry, z) in clumps]
    can = shade_parts(w, 30, parts, outline=ink)
    img = new(w, h)
    # striped candy-cane trunk
    for y in range(24, 42):
        for x in range(14, 19):
            edge = x in (14, 18)
            stripe = ((y + x) // 2) % 2 == 0
            img[y, x, :3] = C['rf_ink'] if edge else (C['white'] if stripe else C['f_pink'])
            img[y, x, 3] = 255
    img[42, 13:20, :3] = C['rf_ink']
    img[42, 13:20, 3] = 255
    m = can[..., 3] > 0
    img[:30][m] = can[m]
    for (x, y) in ((10, 8), (20, 6), (24, 16), (13, 17), (7, 18), (18, 22)):
        if img[y, x, 3] and tuple(img[y, x, :3]) not in (ink, rp[3]):
            img[y, x, :3] = C['white']
    return img


def mushrooms():
    rows = [
        '..kkk.......',
        '.krwrk......',
        'krrrrrk.kkk.',
        'kkkkkkkkrwrk',
        '..kck..krrrk',
        '..kck..kkkkk',
        '..kck...kck.',
        '.........k..',
    ]
    return from_ascii(rows, {'k': rgb15('#b0607e'), 'r': rgb15('#ffa8c0'), 'w': C['white'], 'c': C['cream']})


def stump():
    parts = [P(Poly([(2, 5), (15, 5), (15, 13), (2, 13)], 1.0), TRUNK, z=0, bevel=True),
             P(Ellipse(8.5, 5, 6.5, 3.2), ramp('wd_hi', 'wd_hi', 'wd_lt', 'wd_base', 'wd_dk'), z=1, flat=True,
               line=C['tr_ink'])]
    img = shade_parts(18, 16, parts, outline=C['tr_ink'])
    for (x, y) in ((6, 5), (7, 4), (9, 4), (10, 5), (9, 6), (7, 6)):
        img[y, x, :3] = C['wd_base']
    img[5, 8, :3] = C['wd_dk']
    return img


def door_mat():
    rows = ['kkkkkkkkkkkk', 'kppwppppwppk', 'kpwpppppppwk', 'kkkkkkkkkkkk']
    return from_ascii(rows, {'k': C['ui_line'], 'p': C['ui_pk2'], 'w': C['white']})


def bucket():
    rows = [
        '.k.....k..',
        'k.......k.',
        'kkkkkkkkk.',
        'kbbwbbbbk.',
        'kbbbbbbBk.',
        '.kbbbbBk..',
        '.kkkkkkk..',
    ]
    return from_ascii(rows, {'k': rgb15('#5a86b8'), 'b': rgb15('#a8d0f8'), 'B': rgb15('#86b4e6'), 'w': C['white']})


def spade():
    rows = ['..k', '.kk', 'kyk', 'kyk', '.k.', '.k.', '.k.', 'kkk']
    return from_ascii(rows, {'k': C['tr_ink'], 'y': C['f_yel']})


def palm_trunk(img, x0, y0, h, lean):
    """Smooth curved palm trunk with soft bands."""
    for i in range(h):
        t = i / max(1, h - 1)
        cx = x0 + lean * (t ** 1.8)
        y = y0 - i
        band = (i // 3) % 2
        for dx in range(-3, 4):
            x = int(round(cx + dx))
            if dx in (-3, 3):
                c = C['tr_ink']
            elif dx == -2:
                c = C['tr_lt']
            elif dx >= 1:
                c = C['tr_dk'] if band else C['tr_base']
            else:
                c = C['tr_base'] if band else C['tr_lt']
            img[y, x, :3] = c
            img[y, x, 3] = 255


def boardwalk(w, h=14):
    img = new(w, h)
    for y in range(h):
        for x in range(w):
            if y == 0 or y == h - 1:
                c = C['wd_ink']
            elif y == h - 2:
                c = C['wd_dk2']
            elif x % 5 == 4:
                c = C['wd_dk']
            elif y == 1:
                c = C['wd_hi']
            else:
                c = C['wd_lt'] if (x // 5) % 2 == 0 else C['wd_base']
            img[y, x, :3] = c
            img[y, x, 3] = 255
    # nail dots
    for x in range(1, w, 5):
        img[3, x, :3] = C['wd_dk']
        img[h - 4, x, :3] = C['wd_dk']
    # end cap
    for y in range(h):
        img[y, w - 1, :3] = C['wd_ink']
    return img


# ------------------------------------------------ Cloud Hill (step 6.5)
def sky_map(w, h, bands, dither=2):
    """Sky gradient for a whole map: bands of (y_start, color), dithered
    2-row transitions that repeat every 2 px across, so rows share tiles."""
    img = new(w, h)
    img[..., 3] = 255
    ys, xs = np.mgrid[0:h, 0:w]
    for i, (y0, col) in enumerate(bands):
        y1 = bands[i + 1][0] if i + 1 < len(bands) else h
        img[y0:y1, :, :3] = col
        if i > 0:
            prev = bands[i - 1][1]
            m = (ys >= y0) & (ys < y0 + dither) & (((xs + ys) % 2) == 0)
            img[..., :3][m] = prev
            m2 = (ys >= y0 + dither) & (ys < y0 + 2 * dither) & ((xs % 2) == 0) & ((ys % 2) == 0)
            img[..., :3][m2] = prev
    return img


def star_glint(big=False):
    """Cloud Hill star: the fill is st_lt, so it twinkles with the palette glint."""
    if big:
        rows = ['...k...', '..kyk..', 'kkyyykk', 'kyyyyyk', '.kyyyk.', '.kykyk.', 'kk...kk']
    else:
        rows = ['.k.', 'kyk', '.k.']
    return from_ascii(rows, {'k': C['st_ink'], 'y': C['st_lt']})


def glint_moon():
    rows = [
        '...kkkk..',
        '..kyyyk..',
        '.kyyyk...',
        'kyyyk....',
        'kyyyk....',
        'kyyyyk...',
        '.kyyyykk.',
        '..kyyyyyk',
        '...kkkkk.',
    ]
    return from_ascii(rows, {'k': C['st_ink'], 'y': C['st_lt']})


def cloud_bed():
    """Momo's comfy bed on Cloud Hill: a puffy cloud mattress with a round
    pillow at the left (the blanket is a sprite, so it can tuck Momo in)."""
    pillow = [C['cl_hi'], C['cl_hi'], C['cl_base'], C['cl_dk'], C['cl_dk2']]
    mattress = [C['cl_hi'], C['cl_base'], C['cl_dk'], C['cl_dk2'], C['cl_ink']]
    ink = C['cl_ink']
    w, h = 48, 22
    parts = [
        P(Mochi(24, 14, 22, 7.5, nt=2.4, nb=5.0), mattress, z=0, k=3.0, line=ink),
        P(Ellipse(9, 9, 7.5, 5), pillow, z=2, k=3.5, line=ink, levels=(0.95, 0.75, 0.40, 0.15)),
    ]
    img = shade_parts(w, h, parts, outline=ink)
    for (x, y) in ((33, 17), (41, 13)):                        # two little stars stitched on the mattress
        for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            img[y + dy, x + dx, :3] = C['st_lt'] if (dx, dy) == (0, 0) else rgb15('#f5d97a')
    return img


def cloud_puff(w, h, seed=0):
    """Small walkable cloud step for the way up from the shore (outlined)."""
    import random
    rnd = random.Random(seed)
    blobs = [Mochi(w / 2, h * 0.62, w / 2 - 1.5, h * 0.34, nt=2.0, nb=5.0)]
    n = max(3, int(w / 12))                                   # one bump every ~12 px
    for i in range(n):
        cx = 4 + (w - 8) * (i + 0.5) / n
        r = h * rnd.uniform(0.28, 0.36) * (1.2 if i % 2 == 1 else 1.0)
        blobs.append(Ellipse(cx, h * 0.52 - r * 0.4, r, r * 0.9))
    rp = [C['cl_hi'], C['cl_hi'], C['cl_base'], C['cl_dk'], C['cl_dk2']]
    return shade_parts(w, h, [P(Union(*blobs), rp, k=5.0, levels=(0.9, 0.62, 0.30, 0.12))], outline=C['cl_ink'])


def lollipop(kind='pink'):
    """Swirl lollipop on a stick, Cloud Hill decor (8x15)."""
    a, b = {'pink': ('#ffb3c8', '#ec8fae'), 'blue': ('#bfe0ff', '#86b4e6'), 'mint': ('#bff0cc', '#7cc8a0')}[kind]
    rows = [
        '.kkkkk.',
        'kawwaak',
        'kwaawbk',
        'kwbwawk',
        'kbaawbk',
        'kawbbak',
        '.kkkkk.',
        '...s...',
        '...s...',
        '...s...',
        '...s...',
        '..kkk..',
    ]
    return from_ascii(rows, {'k': C['rf_ink'], 'a': rgb15(a), 'b': rgb15(b), 'w': C['white'], 's': C['wl_dk']})


# ------------------------------------------- area houses (step 6.9)
def _door(img, cx, top, bottom, ramp_, ink):
    """Arched door with planks and a knob, bottom centre at cx."""
    parts = [P(Union(Poly([(cx - 5, top + 5), (cx + 5, top + 5), (cx + 5, bottom), (cx - 5, bottom)], 0.3),
                     Ellipse(cx, top + 5, 5.3, 5.3)), ramp_, z=1, line=ink, bevel=True)]
    d = shade_parts(img.shape[1], img.shape[0], parts, outline=ink)
    m = d[..., 3] > 0
    img[m] = d[m]
    for y in range(top + 3, bottom):
        if img[y, cx, 3]:
            img[y, cx, :3] = ramp_[3]
    img[top + 9, cx + 3, :3] = C['f_yel_dk']
    img[top + 8, cx + 3, :3] = C['f_yel']


def mushroom_house():
    """Berry Woods house: a big pink-capped mushroom with white spots, a
    cream stem wall, a round window and an arched mint door (58x60)."""
    W, H = 58, 60
    from squishies import HalfPlane, Clip
    cap = Union(Clip(Ellipse(29, 30, 28, 27), HalfPlane(0, -1, -30)), Ellipse(29, 29, 28, 4.5))
    parts = [
        P(Poly([(12, 29), (46, 29), (48, 58), (10, 58)], 1.0), WALL, z=0, bevel=True),
        P(cap, ROOF, z=2, line=C['rf_ink'], levels=(0.97, 0.80, 0.42, 0.18)),
        P(Ellipse(19, 42, 4.6), WIN, z=1, line=C['wl_ink'], bevel=True),
        P(Ellipse(40, 42, 4.6), WIN, z=1, line=C['wl_ink'], bevel=True),
    ]
    img = shade_parts(W, H, parts, outline=C['rf_ink'])
    for (x, y, r) in ((16, 12, 3.2), (30, 7, 2.6), (42, 14, 3.5), (24, 22, 2.4), (8, 24, 2.0), (50, 25, 2.0),
                      (36, 22, 1.8)):                          # white spots on the cap
        for yy in range(int(y - r), int(y + r) + 1):
            for xx in range(int(x - r), int(x + r) + 1):
                if (xx - x) ** 2 + (yy - y) ** 2 <= r * r and img[yy, xx, 3] and \
                        tuple(img[yy, xx, :3]) != C['rf_ink']:
                    img[yy, xx, :3] = C['white'] if yy < y else C['rf_hi']
    for cx in (19, 40):
        for d in range(-3, 4):
            img[42, cx + d, :3] = C['wl_lt']
            img[42 + d, cx, :3] = C['wl_lt']
        img[40, cx - 2, :3] = C['white']
    _door(img, 29, 42, 58, DOOR, C['wl_ink'])
    for x in range(12, 47):                                       # grass tufts at the foot
        if x % 5 == 0 and not (23 < x < 35):
            img[58, x, :3] = C['mg_dk']
            img[57, x, :3] = C['mg_dk']
    return img


def beach_hut():
    """Seashell Shore house: a wooden hut on stilts with a pink and white
    striped roof, a round window and a mint door (56x56)."""
    W, H = 56, 56
    from squishies import HalfPlane, Clip
    parts = [
        P(Poly([(7, 24), (49, 24), (49, 50), (7, 50)], 0.5), WOOD, z=0, bevel=True),
        P(Poly([(2, 26), (28, 4), (54, 26)], 1.5), ROOF, z=2, line=C['rf_ink'], bevel=True),
        P(Ellipse(16, 36, 4.6), WIN, z=1, line=C['wd_ink'], bevel=True),
        P(Ellipse(40, 36, 4.6), WIN, z=1, line=C['wd_ink'], bevel=True),
    ]
    img = shade_parts(W, H, parts, outline=C['wd_ink'])
    for y in range(4, 28):                                          # roof stripes, white and pink
        for x in range(W):
            if img[y, x, 3] and tuple(img[y, x, :3]) in (C['rf_base'], C['rf_lt'], C['rf_hi']) and ((x - 28) // 5) % 2 == 0:
                img[y, x, :3] = C['white'] if tuple(img[y, x, :3]) != C['rf_hi'] else C['white']
    for y in range(26, 50, 4):                                      # planks
        for x in range(8, 49):
            if img[y, x, 3] and tuple(img[y, x, :3]) in (C['wd_base'], C['wd_lt']):
                img[y, x, :3] = C['wd_dk']
    for cx in (16, 40):
        for d in range(-3, 4):
            img[36, cx + d, :3] = C['wd_lt']
            img[36 + d, cx, :3] = C['wd_lt']
        img[34, cx - 2, :3] = C['white']
    _door(img, 28, 34, 50, DOOR, C['wd_ink'])
    for x in (9, 10, 45, 46):                                       # stilts
        for y in range(50, 55):
            img[y, x, :3] = C['wd_dk2'] if x in (10, 46) else C['wd_base']
            img[y, x, 3] = 255
    for x in range(8, 48):                                          # step and sand line
        img[55, x, :3] = C['s_dk2']
        img[55, x, 3] = 255
    return img


def cloud_cottage():
    """Cloud Hill house: a round lavender cottage under a puffy cloud roof
    with a star window and an arched door (58x58)."""
    W, H = 58, 58
    lav = ramp('ui_lav', 'ui_lav', 'ui_lav2', 'f_lav_dk', 'f_lav_dk')
    roofr = [C['cl_hi'], C['cl_hi'], C['cl_base'], C['cl_dk'], C['cl_dk2']]
    puffs = Union(Ellipse(29, 18, 16, 12), Ellipse(15, 24, 11, 8.5), Ellipse(43, 24, 11, 8.5), Ellipse(8, 30, 7, 5.5),
                  Ellipse(50, 30, 7, 5.5), Ellipse(29, 30, 26, 6))
    parts = [
        P(Mochi(29, 44, 21, 13, nt=2.6, nb=8.0), [C['wl_lt'], C['wl_lt'], C['wl_base'], C['wl_dk'], C['wl_dk']], z=0,
          k=2.0, line=C['cl_ink']),
        P(puffs, roofr, z=2, k=5.0, line=C['cl_ink'], levels=(0.9, 0.62, 0.30, 0.12)),
    ]
    img = shade_parts(W, H, parts, outline=C['cl_ink'])
    star = from_ascii(['...k...', '..kyk..', 'kkyyykk', 'kyyyyyk', '.kyyyk.', '.kykyk.', 'kk...kk'],
                      {'k': C['st_ink'], 'y': C['st_lt']})
    for (sx, sy) in ((10, 38), (41, 38)):                           # star windows
        for y in range(star.shape[0]):
            for x in range(star.shape[1]):
                if star[y, x, 3]:
                    img[sy + y, sx + x, :3] = star[y, x, :3]
    _door(img, 29, 40, 56, lav, C['cl_ink'])
    return img
