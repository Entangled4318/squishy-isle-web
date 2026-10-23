"""Build the mockup screenshots. Usage: python3 mockups.py OUTDIR [screen ...]"""
import os
import sys

import numpy as np

from gba import new, blit, solid, save_scaled, rgb15, W, H, flip_h, affine
from palette import C, FL
from scene import Scene
from squishies import AREAS, SPECIES, render
from pip import frames as pip_frames
import world
from world import render_terrain, MEADOW_KINDS, tree, cottage, bush, flower, stepping_stone
import props
from props import box16, SPARK_BIG, SPARK_SMALL, SPARK_TINY, shadow, pill, HEART
from font import draw_text, text_width

PIP = pip_frames()
SHADOW_BLEND = (5, 11)


def sq(species, flavor, size, **kw):
    return render(SPECIES[species], flavor, size, **kw)


def hud_count(img, found, total, icon):
    p = pill(50, 15, C['ui_bg'], C['ui_pk'], C['ui_ink'], C['white'])
    blit(img, p, 186, 4)
    blit(img, icon, 186, 3)
    draw_text(img, f'{found}/{total}', 205, 8, C['ui_ink'])


# ------------------------------------------------------------- meadow
MEADOW_CORNERS = [
    'gggggggggggggggg',
    'gggggggggggggggg',
    'ggggggggggggwwgg',
    'gggggggggggwwwwg',
    'ggggggppgggwwwwg',
    'ggggggppggggwwgg',
    'ggggggppgggggggg',
    'ggggggpppppppppp',
    'ggggggpppppppppp',
    'gggggggggggggggg',
    'gggggggggggggggg',
]


def scene_meadow():
    sc = Scene('meadow')
    from world import shape_labels, Capsule, Oval, SmoothUnion
    path = SmoothUnion(10, Capsule(104, 40, 104, 118, 15.5), Capsule(104, 120, 260, 120, 15.5))
    pond = Oval(200, 58, 33, 24, n=2.3)
    lab = shape_labels(W, H, 'g', [('p', path), ('w', pond)])
    ground, lab = render_terrain(None, MEADOW_KINDS, lab=lab)
    objs = new(W, H)
    trees = [('blossom', True, -18, -30), ('green', False, 28, -14), ('green', True, 196, -36),
             ('green', False, -12, 102), ('blossom', False, 208, 122)]
    for kind, big, x, y in trees:
        t = tree(kind, big)
        blit(ground, world.tree_shadow(t.shape[1]), x, y + t.shape[0] - 6)
    # ground decor
    for name, x, y in (('patch_pink', 12, 72), ('patch_yellow', 58, 138), ('patch_mix', 136, 140),
                       ('patch_pink', 176, 146), ('tuft', 6, 58), ('tuft', 128, 72), ('tuft_small', 88, 132),
                       ('tuft', 28, 124), ('tuft_small', 164, 128), ('tuft', 222, 96), ('tuft_small', 136, 92),
                       ('clover', 100, 146), ('clover', 48, 110), ('tuft_small', 60, 90),
                       ('patch_yellow', 150, 58), ('tuft_small', 188, 96)):
        blit(ground, world.decor(name), x, y)
    blit(ground, world.picnic_blanket(), 96, 138)
    blit(ground, world.door_mat(), 98, 61)
    for name, x, y in (('patch_mix', 20, 110), ('patch_pink', 80, 70), ('tuft', 58, 76), ('patch_yellow', 166, 92),
                       ('clover', 16, 128)):
        blit(ground, world.decor(name), x, y)
    for (x, y, f) in ((186, 44, False), (207, 62, True), (176, 64, False)):
        blit(ground, world.lily_pad(f), x, y)
    sc.bg('ground', 3, ground)
    for kind, big, x, y in trees:
        blit(objs, tree(kind, big), x, y)
    blit(objs, cottage(), 72, -2)
    blit(objs, world.decor('tulips'), 44, 38)
    blit(objs, world.decor('tulips'), 58, 40)
    blit(objs, world.fence(2), 38, 48)
    blit(objs, world.reeds(), 162, 34)
    blit(objs, world.reeds(), 228, 66)
    blit(objs, world.rock(True), 150, 80)
    blit(objs, world.rock(), 230, 88)
    blit(objs, bush('green'), 138, 44)
    blit(objs, bush('blossom'), 16, 90)
    blit(objs, world.mailbox(), 124, 42)
    blit(objs, world.mushrooms(), 4, 146)
    blit(objs, world.mushrooms(), 178, 86)
    blit(objs, world.signpost(world.mini_shell()), 218, 88)
    blit(objs, world.basket(), 118, 136)
    sc.bg('objects', 2, objs)

    boxes = [('pink', 40, 96), ('lav', 152, 94), ('mint', 142, 28)]
    for color, x, y in boxes:
        sc.obj(shadow(14, 5), x + 1, y + 13, key=y, blend=SHADOW_BLEND)
        sc.obj(box16(color), x, y)
    for img, x, y in ((SPARK_BIG, 38, 89), (SPARK_SMALL, 55, 104), (SPARK_SMALL, 149, 90),
                      (SPARK_TINY, 167, 104), (SPARK_BIG, 154, 22), (SPARK_TINY, 139, 38)):
        sc.obj(img, x, y, key=999)

    px, py = 104, 92
    sc.obj(shadow(12, 4), px + 2, py + 23, key=py, blend=SHADOW_BLEND)
    sc.obj(PIP['right1'], px, py)
    sc.obj(shadow(12, 4), px - 17, py + 21, key=py - 1, blend=SHADOW_BLEND)
    sc.obj(sq('bunny', 'strawberry', 16), px - 19, py + 9)
    for spc, flv, x, y in (('kitty', 'matcha', 70, 116), ('chick', 'vanilla', 208, 108), ('bear', 'taro', 16, 52)):
        sc.obj(shadow(12, 4), x + 2, y + 13, key=y - 1, blend=SHADOW_BLEND)
        sc.obj(sq(spc, flv, 16), x, y)
    sc.obj(world.butterfly('pink', 0), 66, 70, key=999)
    sc.obj(world.butterfly('yellow', 1), 118, 128, key=999)
    hud = new(W, H)
    hud_count(hud, 7, 20, sq('bunny', 'vanilla', 16))
    sc.bg('hud', 0, hud)
    sc.backdrop = C['g_base']
    return sc


# ----------------------------------------------------- open / reveal / squish
def sunburst(a, b, glow, cx=120, cy=78, n=18, rot=0.0, glow_r=44, ring=None):
    import math
    img = new(W, H)
    ys, xs = np.mgrid[0:H, 0:W]
    ang = np.arctan2(ys + 0.5 - cy, xs + 0.5 - cx) + math.radians(rot)
    stripe = (np.floor(ang / (2 * math.pi / n)).astype(int)) % 2
    img[..., :3] = np.where(stripe[..., None] == 0, np.array(a, np.uint8), np.array(b, np.uint8))
    r = np.hypot(xs + 0.5 - cx, ys + 0.5 - cy)
    img[..., :3][r < glow_r] = glow
    # dithered soft edge around the glow
    chk = ((xs + ys) % 2) == 0
    img[..., :3][(r >= glow_r) & (r < glow_r + 3) & chk] = glow
    chk2 = ((xs % 2) == 0) & ((ys % 2) == 0)
    img[..., :3][(r >= glow_r + 3) & (r < glow_r + 6) & chk2] = glow
    img[..., 3] = 255
    return img


def stage(w=104, h=28, top=None, side=None, rim=None):
    """Plush round cushion the container and squishy sit on."""
    top = top or rgb15('#ffd9e5')
    top_hi = rgb15('#ffeef3')
    side = side or rgb15('#f7b6ca')
    side_dk = rgb15('#e99ab4')
    rim = rim or rgb15('#c9789a')
    img = new(w, h)
    X, Y = np.meshgrid(np.arange(w) + 0.5, np.arange(h) + 0.5)
    ex = lambda cy, rx, ry: ((X - w / 2) / rx) ** 2 + ((Y - cy) / ry) ** 2 <= 1
    body = ex(15.5, w / 2 - 1, 11)
    topm = ex(11, w / 2 - 1, 9.5)
    img[body, :3] = side
    img[body & (X > w * 0.62), :3] = side_dk
    img[body, 3] = 255
    img[topm, :3] = top
    img[topm & ~ex(10, w / 2 - 4, 8), :3] = top_hi
    img[topm & (Y > 11) & ~ex(10.5, w / 2 - 3, 8.2), :3] = top
    img[topm, 3] = 255
    # stitch dots around the cushion side
    for i in range(9):
        x = int(10 + i * (w - 20) / 8)
        y = int(21 + 2.2 * (1 - ((x - w / 2) / (w / 2)) ** 2))
        if img[y, x, 3]:
            img[y, x, :3] = top_hi
    m = img[..., 3] > 0
    out = np.zeros_like(m)
    out[1:] |= m[:-1]
    out[:-1] |= m[1:]
    out[:, 1:] |= m[:, :-1]
    out[:, :-1] |= m[:, 1:]
    out &= ~m
    img[out, :3] = rim
    img[out, 3] = 255
    # rim line between top and side
    for x in range(w):
        col = np.nonzero(topm[:, x])[0]
        if len(col):
            y = col[-1] + 1
            if y < h and body[y, x]:
                img[y, x, :3] = side_dk
    return img


def hearts_progress(n_done, total=3):
    """Hearts fill up with each press."""
    from gba import from_ascii
    on = props.HEART
    off = from_ascii([
        '.kk.kk.',
        'kwwkwwk',
        'kwwwwwk',
        'kwwwwwk',
        '.kwwwk.',
        '..kwk..',
        '...k...',
    ], {'k': rgb15('#c25a82'), 'w': C['white']})
    img = new(total * 9, 7)
    for i in range(total):
        blit(img, on if i < n_done else off, i * 9, 0)
    return img


def pips(n_done, total=3):
    img = new(total * 10, 8)
    on = from_ascii_pip(True)
    off = from_ascii_pip(False)
    for i in range(total):
        blit(img, on if i < n_done else off, i * 10 + 1, 0)
    return img


def from_ascii_pip(on):
    from gba import from_ascii
    rows = ['.kkk.', 'kpppk', 'kpppk', 'kpppk', '.kkk.'] if on else ['.kkk.', 'kwwwk', 'kwwwk', 'kwwwk', '.kkk.']
    return from_ascii(rows, {'k': rgb15('#c25a82'), 'p': rgb15('#ff9fbd'), 'w': C['white']})


def motion_arcs(side):
    from gba import from_ascii
    rows = ['..kk', '.kk.', 'kk..', 'kk..', 'kk..', '.kk.', '..kk']
    img = from_ascii(rows, {'k': rgb15('#e088a8')})
    return img if side == 'left' else flip_h(img)


PINK_SHADOW = rgb15('#c9789a')


def puff():
    from gba import from_ascii
    return from_ascii(['..kkk....', '.kwwwkkk.', 'kwwwwwwwk', 'kwwwwwwdk', '.kkkkkkk.'],
                      {'k': rgb15('#d8b8e8'), 'w': C['white'], 'd': rgb15('#efe6f8')})


def scene_open():
    sc = Scene('open')
    bg = sunburst(rgb15('#f3edff'), rgb15('#e7ddfb'), rgb15('#fbf8ff'), cy=78, glow_r=48)
    sc.bg('burst', 3, bg)
    sc.bg('stage', 2, _place(stage(), 68, 110))
    box = props.box64('pink')
    wob = affine(box, 1.0, 1.0, -10)
    sc.obj(shadow(60, 10, PINK_SHADOW), 90, 115, key=0, blend=(5, 11))
    # box pivots on its bottom-right corner while wobbling
    sc.obj(wob, 120 - 64 + 2, 84 - 64 + 1, key=1)
    for img, x, y in ((motion_arcs('left'), 62, 70), (motion_arcs('left'), 54, 78), (motion_arcs('left'), 62, 86),
                      (motion_arcs('right'), 172, 60), (motion_arcs('right'), 180, 68), (motion_arcs('right'), 172, 76)):
        sc.obj(img, x, y, key=2)
    for x, y in ((80, 110), (150, 112)):
        sc.obj(puff(), x, y, key=4)
    for img, x, y in ((props.SPARK_HUGE, 44, 26), (SPARK_BIG, 182, 20), (SPARK_SMALL, 196, 80),
                      (SPARK_BIG, 34, 88), (SPARK_TINY, 158, 12), (SPARK_TINY, 70, 12)):
        sc.obj(img, x, y, key=3)
    hud = new(W, H)
    blit(hud, props.a_button_big(pressed=False), 108, 132)
    blit(hud, hearts_progress(1), 136, 142)
    sc.bg('hud', 0, hud)
    return sc


def _place(img, x, y):
    layer = new(W, H)
    blit(layer, img, x, y)
    return layer


def name_pill(text, hearts=1):
    w = text_width(text) + 16 + hearts * 9
    img = pill(w + 8, 15, C['ui_bg'], C['ui_pk'], C['ui_ink'], C['white'])
    draw_text(img, text, 8, 4, C['ui_ink'])
    for i in range(hearts):
        blit(img, HEART, 8 + text_width(text) + 6 + i * 9, 4)
    return img


def scene_reveal():
    sc = Scene('reveal')
    bg = sunburst(rgb15('#fff6d8'), rgb15('#ffeab8'), rgb15('#fffbee'), cy=74, glow_r=48)
    sc.bg('burst', 3, bg)
    sc.bg('stage', 2, _place(stage(), 68, 110))
    lid = affine(props.box64('pink', 'lid')[:34], 1.0, 1.0, 28)
    sc.obj(lid, 162, -10, key=1)
    bun = sq('bunny', 'strawberry', 64, expr='happy_open')
    sc.obj(shadow(46, 8, PINK_SHADOW), 97, 117, key=3, blend=(5, 11))
    sc.obj(bun, 88, 121 - 61, key=4)
    sc.obj(props.badge_new(), 52, 36, key=9)
    import random
    rnd = random.Random(5)
    n = 0
    while n < 30:
        x = rnd.randint(6, 228)
        y = rnd.randint(4, 128)
        if 70 < x < 170 and 24 < y < 132:
            continue
        sc.obj(props.confetti_piece(n), x, y, key=8)
        n += 1
    for img, x, y in ((props.SPARK_HUGE, 154, 48), (SPARK_BIG, 84, 104), (SPARK_SMALL, 164, 96),
                      (SPARK_TINY, 150, 30), (SPARK_SMALL, 80, 30)):
        sc.obj(img, x, y, key=9)
    hud = new(W, H)
    p = name_pill('Strawberry Bunny')
    blit(hud, p, 120 - p.shape[1] // 2, 142)
    sc.bg('hud', 0, hud)
    return sc


def scene_squish():
    sc = Scene('squish')
    bg = sunburst(rgb15('#fff6d8'), rgb15('#ffeab8'), rgb15('#fffbee'), cy=74, rot=6, glow_r=48)
    sc.bg('burst', 3, bg)
    sc.bg('stage', 2, _place(stage(), 68, 110))
    bun = sq('bunny', 'strawberry', 64, expr='squish', squash=(1.17, 0.74))
    sc.obj(shadow(58, 9, PINK_SHADOW), 91, 117, key=3, blend=(5, 11))
    sc.obj(bun, 88, 121 - 61, key=4)
    for img, x, y in ((props.HEART_BIG, 64, 44), (HEART, 162, 36), (props.HEART_BIG, 158, 60),
                      (HEART, 80, 24), (HEART, 122, 30), (props.HEART_BIG, 104, 12)):
        sc.obj(img, x, y, key=9)
    for img, x, y in ((motion_arcs('left'), 48, 84), (motion_arcs('left'), 41, 92),
                      (motion_arcs('right'), 188, 84), (motion_arcs('right'), 195, 92)):
        sc.obj(img, x, y, key=9)
    for x, y in ((72, 112), (160, 112)):
        sc.obj(puff(), x, y, key=9)
    hud = new(W, H)
    p = name_pill('Strawberry Bunny', hearts=2)
    blit(hud, p, 120 - p.shape[1] // 2, 142)
    sc.bg('hud', 0, hud)
    return sc


# ------------------------------------------------------------------ shelf
def silhouette(img, fill, edge):
    out = img.copy()
    m = img[..., 3] > 0
    out[m, :3] = fill
    # darker rim on the silhouette edge
    for y in range(img.shape[0]):
        for x in range(img.shape[1]):
            if not m[y, x]:
                continue
            nb = [(y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)]
            if any(not (0 <= a < img.shape[0] and 0 <= b < img.shape[1]) or not m[a, b] for a, b in nb):
                out[y, x, :3] = edge
    return out


def tab(icon, active):
    from paint import P, shade_parts
    from squishies import Poly
    h = 22 if active else 18
    fill = [C['white'], rgb15('#fff4f7'), rgb15('#ffe2ea') if active else rgb15('#f3e8ee'),
            rgb15('#ffc8d8') if active else rgb15('#e6d6de'), rgb15('#f5aac2')]
    img = shade_parts(28, h + 2, [P(Poly([(1.5, 1.5), (26.5, 1.5), (26.5, h + 4), (1.5, h + 4)], 2.5), fill,
                                    bevel=True)], outline=rgb15('#b98a9e') if not active else C['ui_ink'])
    blit(img, icon, 6, 3 if active else 2)
    return img


SHELF = dict(x0=11, y0=26, cw=44, ch=32, cols=5, rows=4)
SHELF_BACKS = [('#fff0f4', '#fbdde6'), ('#ecf9f2', '#d4efe0'), ('#f3eefc', '#e2d8f6'), ('#fff8e4', '#f7e8c2')]
SHELF_SIL = [('#f7d3de', '#ecbfcd'), ('#cfeadb', '#b9dfca'), ('#ddd3f1', '#cbbdea'), ('#f3e2b8', '#e8d09c')]


def shelf_background(active=0, locked=(), pill_w=None):
    """Wall, wooden shelf, area tabs and an empty name pill (BG art)."""
    img = new(W, H)
    img[..., :3] = rgb15('#dff5ec')
    img[..., 3] = 255
    ys, xs = np.mgrid[0:H, 0:W]
    img[..., :3][((xs % 16) == 3) & ((ys % 16) == 4)] = rgb15('#c6ecdc')
    img[..., :3][((xs % 16) == 11) & ((ys % 16) == 12)] = rgb15('#c6ecdc')
    x0, y0, cw, ch, cols, rows = (SHELF[k] for k in ('x0', 'y0', 'cw', 'ch', 'cols', 'rows'))
    X1, Y1 = x0 + cols * cw, y0 + rows * ch
    img[y0 - 4:Y1 + 4, x0 - 5:X1 + 5, :3] = C['wd_base']
    img[y0 - 4, x0 - 5:X1 + 5, :3] = C['wd_lt']
    img[y0 - 4:Y1 + 4, x0 - 5, :3] = C['wd_lt']
    img[y0 - 4:Y1 + 4, X1 + 4, :3] = C['wd_dk']
    for r in range(rows):
        back, back_top = (rgb15(h) for h in SHELF_BACKS[r])
        for c in range(cols):
            cx, cy = x0 + c * cw, y0 + r * ch
            img[cy:cy + ch - 4, cx + 1:cx + cw - 1, :3] = back
            img[cy:cy + 3, cx + 1:cx + cw - 1, :3] = back_top
            img[cy:cy + ch - 4, cx + 1:cx + 2, :3] = back_top
            img[cy + ch - 4:cy + ch, cx:cx + cw, :3] = C['wd_lt']
            img[cy + ch - 3:cy + ch - 1, cx:cx + cw, :3] = C['wd_base']
            img[cy + ch - 1, cx:cx + cw, :3] = C['wd_dk']
            img[cy:cy + ch - 4, cx, :3] = C['wd_dk']
            img[cy:cy + ch - 4, cx + cw - 1, :3] = C['wd_dk']
    img[y0 - 5, x0 - 5:X1 + 5, :3] = C['wd_ink']
    img[min(H - 1, Y1 + 4), x0 - 5:X1 + 5, :3] = C['wd_ink']
    img[y0 - 5:Y1 + 5, x0 - 6, :3] = C['wd_ink']
    img[y0 - 5:Y1 + 5, X1 + 5, :3] = C['wd_ink']
    for x in range(x0 - 5, X1 + 5):
        depth = [0, 1, 2, 2, 2, 2, 1, 0][(x - (x0 - 5)) % 8]
        for y in range(y0 - 4, y0 - 4 + depth + 1):
            img[y, x, :3] = C['wd_hi'] if y == y0 - 4 else C['wd_lt']
    by_kind = {'box': box16('pink'), 'shell': props.shell('pink', 16), 'acorn': props.acorn16(), 'capsule': props.capsule16()}
    icons = [by_kind[a[2]] for a in AREAS]           # tabs in play order
    for i, ic in enumerate(icons):
        if i in locked:
            ic = silhouette(ic, rgb15('#e6d6de'), rgb15('#cdb8c4'))
        blit(img, tab(ic, i == active), 8 + i * 30, 0 if i == active else 2)
    if pill_w:
        p = pill(pill_w, 15, C['ui_bg'], C['ui_pk'], C['ui_ink'], C['white'])
        blit(img, p, 232 - pill_w, 3)
    return img


def selection_frame():
    cw, ch = SHELF['cw'], SHELF['ch']
    fw, fh = cw + 2, ch - 1
    frame = new(fw, fh)
    for y in range(fh):
        for x in range(fw):
            edge = min(x, y, fw - 1 - x, fh - 1 - y)
            corner = (min(x, fw - 1 - x) + min(y, fh - 1 - y)) < 3
            if corner:
                continue
            if edge <= 1:                       # dark 2 px outline: stands out on every pastel row
                frame[y, x, :3] = rgb15('#2e1a2a')
                frame[y, x, 3] = 255
            elif edge == 2:                     # thin light inner edge keeps it soft
                frame[y, x, :3] = rgb15('#fff4e0')
                frame[y, x, 3] = 255
    return frame


def scene_shelf():
    sc = Scene('shelf')
    x0, y0, cw, ch = SHELF['x0'], SHELF['y0'], SHELF['cw'], SHELF['ch']
    bgimg = shelf_background(0, locked=(2, 3))
    sc.bg('shelf', 2, bgimg)
    species = ['bunny', 'kitty', 'bear', 'chick']
    flavors = ['vanilla', 'strawberry', 'matcha', 'taro', 'sparkle']
    have = {('bunny', 'vanilla'), ('bunny', 'strawberry'), ('bunny', 'taro'), ('kitty', 'strawberry'),
            ('kitty', 'matcha'), ('bear', 'taro'), ('chick', 'vanilla'), ('chick', 'sparkle')}
    crowned = {('bunny', 'strawberry')}
    sel = (1, 2)
    for r, spc in enumerate(species):
        for c, flv in enumerate(flavors):
            if (r, c) == sel:
                continue
            cx, cy = x0 + c * cw, y0 + r * ch
            img = sq(spc, flv, 32)
            px, py = cx + (cw - 32) // 2, cy + ch - 4 - 31
            if (spc, flv) in have:
                sc.obj(img, px, py, key=10)
                if (spc, flv) in crowned:
                    sc.obj(props.CROWN, px + 12, py + 2, key=11)
                if flv == 'sparkle':
                    sc.obj(SPARK_TINY, px + 26, py + 6, key=12)
                    sc.obj(SPARK_TINY, px + 2, py + 18, key=12)
            else:
                sc.obj(silhouette(img, *(rgb15(h) for h in SHELF_SIL[r])), px, py, key=10)
    r, c = sel
    cx, cy = x0 + c * cw, y0 + r * ch
    sc.obj(selection_frame(), cx - 1, cy - 1, key=5)
    sc.obj(shadow(22, 4, rgb15('#d9b89a')), cx + 11, cy + ch - 6, key=9, blend=(6, 10))
    sc.obj(sq(species[r], flavors[c], 32, expr='happy_open'), cx + (cw - 32) // 2, cy + ch - 4 - 31 - 2, key=10)
    sc.obj(SPARK_SMALL, cx + cw - 9, cy + 3, key=30)
    sc.obj(SPARK_TINY, cx + 3, cy + 16, key=30)
    hud = new(W, H)
    p = name_pill('Matcha Kitty', hearts=2)
    blit(hud, p, 232 - p.shape[1], 3)
    sc.bg('hud', 0, hud)
    return sc


# ------------------------------------------------------------------ title
def sky_gradient(bands, dither=2):
    """bands: list of (y_start, color). Dithered 2-row transitions."""
    img = new(W, H)
    img[..., 3] = 255
    ys, xs = np.mgrid[0:H, 0:W]
    for i, (y0, col) in enumerate(bands):
        y1 = bands[i + 1][0] if i + 1 < len(bands) else H
        img[y0:y1, :, :3] = col
        if i > 0:
            prev = bands[i - 1][1]
            m = (ys >= y0) & (ys < y0 + dither) & (((xs + ys) % 2) == 0)
            img[..., :3][m] = prev
            m2 = (ys >= y0 + dither) & (ys < y0 + 2 * dither) & ((xs % 2) == 0) & ((ys % 2) == 0)
            img[..., :3][m2] = prev
    return img


def cloud(w, h, seed=0):
    from paint import P, shade_parts
    from squishies import Ellipse, Union, Mochi
    import random
    rnd = random.Random(seed)
    blobs = [Mochi(w / 2, h * 0.68, w / 2 - 2, h * 0.30, nt=2.0, nb=6.0)]
    n = max(2, int(w / 14))
    for i in range(n):
        cx = 6 + (w - 12) * (i + 0.5) / n + rnd.uniform(-2, 2)
        r = h * rnd.uniform(0.26, 0.40) * (1.25 if 0 < i < n - 1 else 0.95)
        blobs.append(Ellipse(cx, h * 0.62 - r * 0.55, r, r * 0.92))
    rp = [C['cl_hi'], C['cl_hi'], C['cl_base'], C['cl_dk'], C['cl_dk2']]
    return shade_parts(w, h, [P(Union(*blobs), rp, k=6.0, levels=(0.9, 0.62, 0.30, 0.12))], outline=None)


def logo_letters(text, height, colors, x_center, y):
    """Place each bubble letter as its own OBJ so the logo can bounce."""
    from logo import letter, LETTERS
    import numpy as np
    from logo import word
    full = word(text, height, colors)
    x0 = x_center - full.shape[1] // 2
    # split the composed word into per-letter sprites by column ranges
    pieces = []
    xs = 0
    cuts = []
    x = 0
    for i, ch in enumerate(text):
        adv = int(round((LETTERS[ch][0] + 0.06) * height))
        cuts.append((x, x + adv))
        x += adv
    bounds = []
    for i, (a, b) in enumerate(cuts):
        lo = 0 if i == 0 else a + 6 + 4 - 2
        hi = full.shape[1] if i == len(cuts) - 1 else b + 6 + 4 - 2
        bounds.append((lo, hi))
    for lo, hi in bounds:
        pieces.append((full[:, lo:hi], x0 + lo, y))
    return pieces


def scene_title():
    sc = Scene('title')
    sky = sky_gradient([(0, rgb15('#cdc6f4')), (20, rgb15('#d8cff8')), (40, rgb15('#e4d6f8')),
                        (58, rgb15('#f0dcf4')), (76, rgb15('#fae2ee')), (90, rgb15('#ffe8ea')),
                        (100, rgb15('#fff0e4'))])
    sea_top = 104
    sky[sea_top:, :, :3] = C['sea_lt']
    sky[sea_top:sea_top + 2, :, :3] = C['sea_hi']
    for (x, y, l) in ((12, 110, 6), (44, 116, 4), (196, 112, 5), (222, 118, 6), (170, 122, 3), (70, 120, 5)):
        sky[y, x:x + l, :3] = C['sea_hi']
    for (w, h, x, y, sd) in ((66, 28, -14, 58, 1), (74, 30, 178, 52, 2), (40, 18, 146, 80, 3), (38, 16, 34, 84, 4)):
        blit(sky, cloud(w, h, sd), x, y)
    for (x, y) in ((20, 14), (214, 10), (200, 38), (30, 42), (120, 4), (86, 50), (160, 46)):
        sky[y, x, :3] = C['white']
    for (x, y) in ((214, 10), (30, 42)):
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            sky[y + dy, x + dx, :3] = rgb15('#fff6c0')
    sc.bg('sky', 3, sky)
    from paint import P, shade_parts
    from squishies import Ellipse, Union
    hill = shade_parts(236, 60, [P(Union(Ellipse(118, 50, 116, 38), Ellipse(52, 44, 46, 26), Ellipse(186, 44, 48, 26)),
                                  [C['g_hi'], C['g_lt'], C['g_base'], C['g_dk'], C['g_dk2']], k=6.0,
                                  levels=(0.95, 0.75, 0.35, 0.12))], outline=C['g_ink'])
    ground = new(W, H)
    blit(ground, hill, 2, 108)
    for x in range(W):
        col = np.nonzero(ground[:, x, 3])[0]
        if len(col) and col[0] > sea_top + 1:
            sky[col[0] - 1, x, :3] = C['foam']
            if x % 5 < 3:
                sky[col[0] - 2, x, :3] = C['foam']
    for kind, x, y in (('patch_pink', 36, 138), ('patch_yellow', 188, 140), ('tuft', 98, 148),
                       ('patch_mix', 146, 150), ('tuft_small', 64, 152), ('tuft', 210, 150), ('clover', 20, 150)):
        blit(ground, world.decor(kind), x, y)
    blit(ground, tree('blossom'), 0, 88)
    blit(ground, tree('green'), 208, 90)
    sc.bg('island', 2, ground)

    cast = [('whale', 'vanilla', 32, 100, 0), ('bunny', 'strawberry', 68, 94, 4), ('frog', 'matcha', 140, 94, 0),
            ('star', 'sparkle', 176, 98, 6)]
    for spc, flv, x, y, hop in cast:
        img = sq(spc, flv, 32, expr='happy_open' if hop else 'happy')
        sc.obj(shadow(22, 5), x + 5, y + 28, key=y, blend=SHADOW_BLEND)
        sc.obj(img, x, y - hop)
    sc.obj(shadow(12, 4), 114, 124, key=90, blend=SHADOW_BLEND)
    sc.obj(PIP['down0'], 112, 99)
    for img, x, y in ((SPARK_SMALL, 202, 92), (SPARK_TINY, 64, 88), (SPARK_BIG, 196, 18), (SPARK_SMALL, 34, 30),
                      (SPARK_TINY, 180, 66), (SPARK_TINY, 56, 60)):
        sc.obj(img, x, y, key=200)
    bounce = [0, 2, 0, 1, 0, 2, 1]
    for i, (img, x, y) in enumerate(logo_letters('SQUISHY', 28, ['strawberry', 'sparkle', 'matcha', 'sky', 'taro',
                                                                  'peach', 'strawberry'], 121, 2)):
        sc.obj(img, x, y - bounce[i], key=300 + i)
    for i, (img, x, y) in enumerate(logo_letters('ISLE', 22, ['sky', 'taro', 'strawberry', 'matcha'], 120, 45)):
        sc.obj(img, x, y - (1 if i % 2 else 0), key=320 + i)
    hud = new(W, H)
    t = 'PRESS START'
    tw = text_width(t)
    blit(hud, props.a_button(), 120 - tw // 2 - 20, 141)
    draw_text(hud, t, 120 - tw // 2 + 2, 146, C['white'], outline=rgb15('#d86a8e'), shadow=rgb15('#9a4a70'))
    sc.bg('hud', 0, hud)
    return sc


# ------------------------------------------------------------------ shore
def scene_shore():
    from world import shape_labels, Oval, SmoothUnion, SDF, Capsule
    import math

    class Sea(SDF):
        def d(self, X, Y):
            return Y - (34 + 5 * np.sin(X / 23.0) + 3 * np.sin(X / 9.0 + 1.3))

    sc = Scene('shore')
    lab = shape_labels(W, H, 's', [('e', Sea()), ('w', Oval(42, 132, 22, 11, n=2.2))])
    ground = world.shore_ground(lab)
    for (x, y) in ((190, 64), (30, 70), (120, 148)):
        blit(ground, world.starfish(), x, y)
    for (x, y, k) in ((70, 58, 0), (150, 52, 1), (14, 150, 0), (228, 84, 1), (60, 150, 1)):
        blit(ground, world.tiny_shell(k), x, y)
    world.footprints(ground, [(128, 110), (133, 116), (127, 124), (132, 131), (126, 138), (131, 145), (125, 152)])
    blit(ground, world.towel(), 184, 98)
    blit(ground, world.boardwalk(58), 0, 102)
    for (w_, x, y) in ((30, 94, 146), (26, 0, 96), (26, 214, 152), (40, 154, 104)):
        blit(ground, world.tree_shadow(w_, C['s_dk']), x, y)
    sc.bg('ground', 3, ground)
    objs = new(W, H)
    blit(objs, world.palm(), -8 - world.PALM_PAD, 44 - world.PALM_TOP)
    blit(objs, world.palm(flip=True), 204 - world.PALM_PAD, 100 - world.PALM_TOP)
    blit(objs, world.umbrella(), 150, 62)
    blit(objs, world.beach_ball(), 96, 96)
    blit(objs, world.sailboat(), 30, 8)
    blit(objs, world.sandcastle(), 92, 118)
    blit(objs, world.bucket(), 128, 142)
    blit(objs, world.rock(True), 56, 124)
    blit(objs, world.rock(), 20, 122)
    sc.bg('objects', 2, objs)

    shells = [('pink', 124, 60), ('lav', 52, 86), ('peach', 206, 138)]
    for color, x, y in shells:
        sc.obj(shadow(14, 5), x + 1, y + 12, key=y, blend=SHADOW_BLEND)
        sc.obj(props.shell(color, 16), x, y)
    for img, x, y in ((SPARK_BIG, 136, 54), (SPARK_TINY, 122, 70), (SPARK_SMALL, 64, 82),
                      (SPARK_SMALL, 204, 132), (SPARK_TINY, 220, 146)):
        sc.obj(img, x, y, key=999)
    px, py = 124, 76
    sc.obj(shadow(12, 4), px + 2, py + 23, key=py, blend=SHADOW_BLEND)
    sc.obj(PIP['up1'], px, py)
    sc.obj(shadow(12, 4), px + 2, py + 37, key=py + 20, blend=SHADOW_BLEND)
    sc.obj(sq('whale', 'taro', 16), px, py + 26)
    for spc, flv, x, y in (('octo', 'strawberry', 70, 76), ('crab', 'vanilla', 186, 118), ('seal', 'matcha', 152, 128)):
        sc.obj(shadow(12, 4), x + 2, y + 13, key=y - 1, blend=SHADOW_BLEND)
        sc.obj(sq(spc, flv, 16), x, y)
    hud = new(W, H)
    hud_count(hud, 3, 20, sq('whale', 'vanilla', 16))
    sc.bg('hud', 0, hud)
    return sc


# -------------------------------------------------------------- cloud hill
def scene_clouds():
    from world import shape_labels, Oval, CloudBlob, UnionSDF
    sc = Scene('clouds')
    sky = sky_gradient([(0, rgb15('#c4c0f2')), (26, rgb15('#cfc8f6')), (52, rgb15('#dbd0f8')),
                        (80, rgb15('#e8d6f6')), (108, rgb15('#f4dcf2')), (134, rgb15('#fde2ee'))])
    blit(sky, world.rainbow(200, 96, 5), 20, 12)
    for (w, h, x, y, sd) in ((50, 20, 196, 36, 7), (44, 16, 2, 24, 8)):
        blit(sky, cloud(w, h, sd), x, y)
    for (x, y) in ((40, 70), (120, 4), (226, 96), (12, 120), (184, 10), (86, 30)):
        sky[y, x, :3] = C['white']
    blit(sky, world.moon(), 216, 6)
    main = UnionSDF(CloudBlob(120, 96, 104, 44, bump=8, seed=2), CloudBlob(214, 142, 30, 16, bump=6, seed=5))
    small = CloudBlob(30, 146, 26, 12, bump=6, seed=3)
    lab = shape_labels(W, H, 'x', [('c', main), ('c', small)])
    ground = world.cloud_ground(lab, sky)
    for (x, y, big) in ((40, 90, True), (196, 110, False), (78, 128, False), (170, 128, True), (26, 142, False)):
        blit(ground, world.star_deco(big), x, y)
    for (w_, x, y) in ((26, 25, 80), (26, 193, 84), (40, 100, 82)):
        blit(ground, world.tree_shadow(w_, C['cl_dk']), x, y)
    sc.bg('ground', 3, ground)
    objs = new(W, H)
    blit(objs, world.candy_tree('pink'), 22, 40)
    blit(objs, world.candy_tree('blue'), 190, 44)
    blit(objs, world.gacha(), 100, 22)
    sc.bg('objects', 2, objs)
    caps = [('#ffb3c8', '#ec8fae', 58, 92), ('#bfe0ff', '#86b4e6', 176, 90), ('#fff0a0', '#e8c060', 136, 116)]
    for a, b, x, y in caps:
        sc.obj(shadow(12, 4), x + 2, y + 13, key=y, blend=SHADOW_BLEND)
        sc.obj(props.capsule16(a, b), x, y)
    for img, x, y in ((SPARK_BIG, 70, 86), (SPARK_TINY, 56, 104), (SPARK_SMALL, 188, 84), (SPARK_TINY, 148, 112),
                      (SPARK_SMALL, 136, 24)):
        sc.obj(img, x, y, key=999)
    px, py = 96, 96
    sc.obj(shadow(12, 4), px + 2, py + 23, key=py, blend=SHADOW_BLEND)
    sc.obj(PIP['left0'], px, py)
    sc.obj(shadow(12, 4), px + 20, py + 21, key=py - 1, blend=SHADOW_BLEND)
    sc.obj(sq('star', 'strawberry', 16), px + 18, py + 9)
    for spc, flv, x, y in (('cloud', 'taro', 36, 110), ('uni', 'vanilla', 200, 98), ('planet', 'matcha', 158, 62)):
        sc.obj(shadow(12, 4), x + 2, y + 13, key=y - 1, blend=SHADOW_BLEND)
        sc.obj(sq(spc, flv, 16), x, y)
    hud = new(W, H)
    hud_count(hud, 11, 20, sq('star', 'vanilla', 16))
    sc.bg('hud', 0, hud)
    return sc


SCENES = {'title': scene_title, 'shore': scene_shore, 'clouds': scene_clouds, 'meadow': scene_meadow, 'shelf': scene_shelf, 'open': scene_open, 'reveal': scene_reveal, 'squish': scene_squish}

if __name__ == '__main__':
    out = sys.argv[1]
    names = sys.argv[2:] or list(SCENES)
    os.makedirs(out, exist_ok=True)
    for n in names:
        sc = SCENES[n]()
        img, rep = sc.render()
        save_scaled(img, os.path.join(out, f'{n}.png'), 4)
        print(n, '|', '; '.join(rep))
