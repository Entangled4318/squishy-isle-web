"""House rooms (step 6.9): one per area. The four wall shelves hold that
area's 20 gifts, one shelf per species (5 flavors each):
  shelf 0 top left, 1 top right, 2 bottom left, 3 bottom right.
Gift slots are 18 px apart; ROOM below gives the positions the ROM uses."""
import numpy as np

from gba import new, blit, rgb15, W, H
from palette import C
import props

ROOM = {'left_x': 11, 'right_x': 139, 'top_y': 60, 'bottom_y': 100, 'slot': 18, 'floor': 116}

THEMES = {   # wall, pattern, wainscot, rug, rug edge, window glass (top, bottom)
    'meadow': ('#fff0f4', '#ffd6e2', '#ffd2df', '#ffc2d3', '#f09ab4', ('#cfeaff', '#e8f6ff')),
    'woods': ('#eef7e4', '#d4ebc2', '#d0e8bd', '#fcd29e', '#e8a870', ('#cdeebb', '#eaf8dc')),
    'shore': ('#e8f8fa', '#c8eef2', '#c6ecf0', '#bfe0ff', '#86b4e6', ('#9ee2ee', '#d6f4fa')),
    'clouds': ('#f2ecfc', '#ddd0f6', '#e0d4fa', '#d8c6fa', '#a890e0', ('#cfc8f6', '#f4dcf2')),
}


def _pattern(img, key, col):
    ys, xs = np.mgrid[0:H, 0:W]
    wall = ys < ROOM['floor'] - 12
    if key == 'meadow':          # tiny hearts
        heart = ['.k.k.', 'kkkkk', '.kkk.', '..k..']
        for y0 in range(6, 100, 20):
            for x0 in range((y0 // 20) % 2 * 10 + 4, W, 20):
                for dy, row in enumerate(heart):
                    for dx, ch in enumerate(row):
                        if ch == 'k' and y0 + dy < ROOM['floor'] - 12:
                            img[y0 + dy, x0 + dx, :3] = col
    elif key == 'woods':         # little leaves
        leaf = ['..k', '.kk', 'kk.']
        for y0 in range(8, 100, 16):
            for x0 in range((y0 // 16) % 2 * 8 + 3, W, 16):
                for dy, row in enumerate(leaf):
                    for dx, ch in enumerate(row):
                        if ch == 'k' and y0 + dy < ROOM['floor'] - 12:
                            img[y0 + dy, x0 + dx, :3] = col
    elif key == 'shore':         # soft wave lines
        m = wall & (((ys + (np.sin(xs / 4.0) * 1.6).astype(int)) % 16) == 0)
        img[m, :3] = col
    else:                        # twinkle stars
        star = ['.k.', 'kkk', '.k.']
        for y0 in range(6, 100, 18):
            for x0 in range((y0 // 18) % 2 * 12 + 5, W, 24):
                for dy, row in enumerate(star):
                    for dx, ch in enumerate(row):
                        if ch == 'k' and y0 + dy < ROOM['floor'] - 12:
                            img[y0 + dy, x0 + dx, :3] = col


def _shelf(img, x0, y):
    w = 5 * ROOM['slot'] + 2
    img[y:y + 4, x0 - 1:x0 - 1 + w, :3] = C['wd_base']
    img[y, x0 - 1:x0 - 1 + w, :3] = C['wd_hi']
    img[y + 3, x0 - 1:x0 - 1 + w, :3] = C['wd_dk']
    img[y + 4, x0 - 1:x0 - 1 + w, :3] = C['wd_ink']
    for bx in (x0 + 6, x0 + w - 9):                  # brackets
        for k in range(6):
            img[y + 5 + k, bx:bx + 4 - (k * 4) // 6, :3] = C['wd_dk2']
    for i in range(5):                                # soft shadow spot under each gift
        cx = x0 + ROOM['slot'] * i + 9
        img[y - 1, cx - 5:cx + 5, :3] = img[y - 1, cx - 5:cx + 5, :3] // 16 * 15


def room_background(key):
    wall, pat, wains, rug, rug_dk, glass = THEMES[key]
    img = new(W, H)
    img[..., 3] = 255
    img[..., :3] = rgb15(wall)
    _pattern(img, key, rgb15(pat))
    f = ROOM['floor']
    img[f - 12:f, :, :3] = rgb15(wains)                          # wainscot and baseboard
    img[f - 12, :, :3] = C['white']
    img[f - 2:f, :, :3] = C['wd_dk']
    ys, xs = np.mgrid[0:H, 0:W]
    floor = ys >= f
    img[floor, :3] = C['wd_lt']
    img[floor & (((ys - f) % 11) == 0), :3] = C['wd_base']       # boards
    seam = floor & (((xs + ((ys - f) // 11) * 23) % 46) == 0)
    img[seam, :3] = C['wd_base']
    img[floor & (((ys - f) % 11) == 10), :3] = C['wd_dk']
    # rug under Pip
    d = ((xs - 120) / 46.0) ** 2 + ((ys - 141) / 13.0) ** 2
    img[(d <= 1.0), :3] = rgb15(rug_dk)
    img[(d <= 0.8), :3] = rgb15(rug)
    img[(d <= 0.8) & (d > 0.62), :3] = C['white']
    img[(d <= 0.45), :3] = rgb15(rug)
    # window in the middle, between the shelves
    x0, x1, y0, y1 = 106, 134, 24, 58
    img[y0:y1, x0:x1, :3] = C['wd_ink']
    for y in range(y0 + 2, y1 - 2):
        t = (y - y0) / (y1 - y0)
        img[y, x0 + 2:x1 - 2, :3] = rgb15(glass[0] if t < 0.55 else glass[1])
    img[y0 + 2:y1 - 2, (x0 + x1) // 2, :3] = C['wd_lt']
    img[(y0 + y1) // 2, x0 + 2:x1 - 2, :3] = C['wd_lt']
    for (x, y) in ((x0 + 4, y0 + 4), (x0 + 5, y0 + 5), (x0 + 4, y0 + 6)):
        img[y, x, :3] = C['white']
    img[y1 - 1:y1 + 2, x0 - 3:x1 + 3, :3] = C['wd_base']          # sill
    img[y1 + 2, x0 - 3:x1 + 3, :3] = C['wd_ink']
    # corners: a potted plant (left) and a round floor cushion (right)
    from paint import P, shade_parts
    from squishies import Ellipse, Poly, Mochi
    import world
    plant = shade_parts(28, 40, [
        P(Poly([(7, 26), (21, 26), (19, 38), (9, 38)], 1.0), world.WOOD, z=0, bevel=True, line=C['wd_ink']),
        P(Ellipse(14, 14, 11, 12), world.TREE, z=1, line=C['t_ink'], k=3.0)], outline=C['t_ink'])
    for (x, y) in ((9, 9), (18, 12), (12, 19), (16, 5)):
        plant[y, x, :3] = C['f_pink']
    blit(img, plant, 14, f + 4)
    cushion = shade_parts(40, 20, [P(Mochi(20, 11, 18, 8, nt=2.2, nb=3.0),
                                     [C['white'], rgb15(rug), rgb15(rug), rgb15(rug_dk), rgb15(rug_dk)], k=3.0)],
                          outline=C['ui_ink'])
    blit(img, cushion, 190, f + 18)
    for sx, sy in ((ROOM['left_x'], ROOM['top_y']), (ROOM['right_x'], ROOM['top_y']),
                   (ROOM['left_x'], ROOM['bottom_y']), (ROOM['right_x'], ROOM['bottom_y'])):
        _shelf(img, sx, sy)
    # empty name pill at the top (the ROM prints "From Vanilla Bunny" into it)
    blit(img, props.pill(144, 15, C['ui_bg'], C['ui_pk'], C['ui_ink'], C['white']), 48, 3)   # 144: "From Strawberry Shroom" is 121 px
    return img


if __name__ == '__main__':
    from gba import save_scaled
    rows = [room_background(k) for k in THEMES]
    save_scaled(np.concatenate([np.concatenate(rows[:2], axis=1), np.concatenate(rows[2:], axis=1)], axis=0),
                'rooms.png', 2)
