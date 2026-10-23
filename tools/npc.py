"""Momo, the sleepy panda who lies across the way to the next area until
the child has found enough friends there (owner request, step 6).

One character for every gate, so the map needs one sprite palette for it
(it shares the small shadow's OBJ palette: the maps use all 16)."""
import numpy as np

from gba import new, from_ascii
from palette import C
from squishies import Species, Part, Ellipse, Poly, Mochi, mirror, render

# Soft pastel panda: vanilla body, grey-lilac ears and eye patches (light
# enough that the ink eyes still read), a sky-blue nightcap, a pom in the
# body's own colors (14 colors in all: one OBJ palette after the shadow).
PANDA = Species('momo', 'Momo', [
    Part(Ellipse(15, 26, 8.5), z=0, mat='panda2'),
    Part(mirror(Ellipse(15, 26, 8.5)), z=0, mat='panda2'),
    Part(Mochi(32, 42, 27, 20), z=1),
    Part(Ellipse(21.5, 40.5, 6.5, 5.2, rot=-25), z=2, mat='panda2', line=None, clip=2),
    Part(mirror(Ellipse(21.5, 40.5, 6.5, 5.2, rot=-25)), z=2, mat='panda2', line=None, clip=2),
    Part(Poly([(30, 24), (52, 26), (60, 6)], 2.5, R=3), z=3, mat='sky2'),
    Part(Ellipse(58, 8, 4.8), z=4, mat='bodylt'),
], eyes=(21.5, 40.5), mouth=None, nose=47, blush=(12, 48), shine=(17, 31, 4, 2.2, -35))


def frames():
    """32x32 frames: asleep and awake."""
    return {'sleep': render(PANDA, 'vanilla', 32, expr='sleep'), 'awake': render(PANDA, 'vanilla', 32)}


def zz():
    """Two 8x8 tiles, a small and a big z, in the panda's ink."""
    ink = C['ink2']
    small = from_ascii(['kkk', '..k', '.k.', 'kkk'], {'k': ink})
    big = from_ascii(['kkkkk', '...k.', '..k..', '.k...', 'kkkkk'], {'k': ink})
    out = []
    for z in (small, big):
        t = new(8, 8)
        t[1:1 + z.shape[0], 1:1 + z.shape[1]] = z
        out.append(t)
    return out


def blanket():
    """64x32 sprite, blanket in its bottom 16 rows: a sky-blue quilt (the
    nightcap's colors) that drapes over Momo on its cloud bed, a folded
    cream edge at the top and a wavy hem, so Momo's face peeks out."""
    import math
    from gba import rgb15
    k, w, c, b, d = (rgb15(h) for h in ('#6b5a84', '#fffff7', '#fff7e7', '#bde7ff', '#94ceef'))
    img = new(64, 32)
    cx, top, bot = 32, 17, 30
    m = np.zeros((32, 64), bool)
    for y in range(top, bot + 1):
        t = (y - top) / (bot - top)
        half = 17 + 4 * t ** 0.7                         # drapes wider toward the hem
        for x in range(64):
            dx = x + 0.5 - cx
            if abs(dx) > half:
                continue
            if (y == top and abs(dx) > half - 2) or (y >= bot - 1 and abs(dx) > half - (y - bot + 3)):
                continue                                 # rounded corners
            m[y, x] = True
    out = np.zeros_like(m)
    out[1:] |= m[:-1]; out[:-1] |= m[1:]; out[:, 1:] |= m[:, :-1]; out[:, :-1] |= m[:, 1:]
    inner = m & ~(out & ~m)
    edge = m & ~(np.roll(m, 1, 0) & np.roll(m, -1, 0) & np.roll(m, 1, 1) & np.roll(m, -1, 1))
    for y in range(32):
        for x in range(64):
            if not m[y, x]:
                continue
            img[y, x, 3] = 255
            if edge[y, x]:
                col = k
            elif y <= top + 1:
                col = w
            elif y == top + 2:
                col = c
            elif y == top + 3:
                col = d
            elif not m[y + 1, x] or not m[y + 2, x] or not m[y, x + 2] or not m[y, x - 2]:
                col = d                                          # soft shade at the hem and sides
            elif (x - cx) % 9 == 4 and y >= top + 6:
                col = d                                          # soft folds hanging down
            elif (x - cx) % 9 == 0 and y % 4 == 1 and y < bot - 2:
                col = w                                          # little white dots between the folds
            else:
                col = b
            img[y, x, :3] = col
    return img


if __name__ == '__main__':
    from gba import save_scaled
    f = frames()
    row = np.concatenate([f['sleep'], f['awake']] + [np.pad(z, ((0, 24), (0, 0), (0, 0))) for z in zz()], axis=1)
    cols = {tuple(int(v) for v in p) for p in row[..., :3][row[..., 3] > 0]}
    print(len(cols), 'colors')
    save_scaled(row, 'momo.png', 8)
