"""Generic soft-shape painter for props (trees, bushes, rocks, containers).

Shapes are in pixel coordinates. Each part has its own color ramp:
[hi, lt, base, s1, s2]. The dome shading and outline rules match the
squishies so the whole game shares one look.
"""
import numpy as np

from gba import new
from squishies import LIGHT


class P:
    def __init__(self, shape, ramp, z=0, line=None, clip=None, flat=False,
                 levels=(0.985, 0.86, 0.50, 0.22), bevel=False, k=2.3):
        self.shape, self.ramp, self.z, self.line, self.clip = shape, ramp, z, line, clip
        self.flat, self.levels, self.bevel, self.k = flat, levels, bevel, k


def shade_parts(w, h, parts, outline=None, ss=1.0, despeckle=True):
    """Render parts to RGBA. outline: color for the outer silhouette or None."""
    xs = np.arange(w) + 0.5
    ys = np.arange(h) + 0.5
    X, Y = np.meshgrid(xs, ys)
    order = sorted(range(len(parts)), key=lambda i: parts[i].z)
    owner = np.full((h, w), -1)
    masks = {}
    for i in order:
        p = parts[i]
        m = p.shape.inside(X, Y)
        if p.clip is not None:
            m &= parts[p.clip].shape.inside(X, Y)
        masks[i] = m
        owner[m] = i
    img = new(w, h)
    for i in order:
        p = parts[i]
        m = owner == i
        if not m.any():
            continue
        r = p.ramp
        if p.flat:
            col = np.zeros((h, w, 3), np.uint8)
            col[:] = r[2]
        elif p.bevel:
            # flat faces: light top/left edge, dark bottom/right edge
            col = np.zeros((h, w, 3), np.uint8)
            col[:] = r[2]
            mm = masks[i]
            up = np.zeros_like(mm)
            up[1:] = mm[:-1]
            dn = np.zeros_like(mm)
            dn[:-1] = mm[1:]
            lf = np.zeros_like(mm)
            lf[:, 1:] = mm[:, :-1]
            rt = np.zeros_like(mm)
            rt[:, :-1] = mm[:, 1:]
            col[mm & ~up] = r[1]
            col[mm & ~lf] = r[1]
            col[mm & ~dn] = r[3]
            col[mm & ~rt] = r[3]
        else:
            hgt = np.where(masks[i], p.shape.height(X, Y), 0.0)
            gy, gx = np.gradient(hgt, 1.0)
            k = p.k
            nx, ny, nz = -gx * k, -gy * k, np.ones_like(hgt)
            ln = np.sqrt(nx * nx + ny * ny + nz * nz)
            I = (nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2]) / ln
            col = np.zeros((h, w, 3), np.uint8)
            done = np.zeros((h, w), bool)
            for thr, c in zip(list(p.levels) + [-9], r):
                mm = (I > thr) & ~done
                col[mm] = c
                done |= mm
        img[..., :3][m] = col[m]
        img[..., 3][m] = 255

    if despeckle:
        rgb = img[..., :3].copy()
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                o = owner[y, x]
                if o < 0 or parts[o].flat or parts[o].bevel:
                    continue
                c = tuple(rgb[y, x])
                nb = [(y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)]
                cols = [tuple(rgb[a, b]) for a, b in nb if owner[a, b] == o]
                if len(cols) >= 3 and c not in cols:
                    best = max(set(cols), key=cols.count)
                    if cols.count(best) >= 3:
                        img[y, x, :3] = best

    for y in range(h):
        for x in range(w):
            o = owner[y, x]
            if o < 0 or parts[o].line is None:
                continue
            for a, b in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= a < h and 0 <= b < w:
                    q = owner[a, b]
                    if q >= 0 and parts[q].z < parts[o].z:
                        img[y, x, :3] = parts[o].line
                        break

    if outline is not None:
        U = owner >= 0
        out = np.zeros_like(U)
        out[1:, :] |= U[:-1, :]
        out[:-1, :] |= U[1:, :]
        out[:, 1:] |= U[:, :-1]
        out[:, :-1] |= U[:, 1:]
        out &= ~U
        img[..., :3][out] = outline
        img[..., 3][out] = 255
    return img


def dots(img, pts, color):
    for x, y in pts:
        if 0 <= y < img.shape[0] and 0 <= x < img.shape[1] and img[y, x, 3]:
            img[y, x, :3] = color
