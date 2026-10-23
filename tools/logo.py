"""Bubble-letter logo drawn from capsule strokes with tube shading."""
import math

import numpy as np

from gba import new, rgb15
from palette import C, FL
from squishies import LIGHT, _seg_dist


def _arc(cx, cy, rx, ry, t0, t1, n=10):
    return [(cx + rx * math.cos(t0 + (t1 - t0) * i / n), cy + ry * math.sin(t0 + (t1 - t0) * i / n)) for i in range(n + 1)]


LETTERS = {
    'S': (0.74, [[(0.64, 0.19), (0.54, 0.07), (0.37, 0.03), (0.20, 0.07), (0.11, 0.19), (0.14, 0.32),
                  (0.28, 0.43), (0.47, 0.52), (0.61, 0.63), (0.64, 0.78), (0.55, 0.91), (0.37, 0.96),
                  (0.19, 0.92), (0.09, 0.80)]]),
    'Q': (0.86, [_arc(0.42, 0.49, 0.33, 0.43, 0, 2 * math.pi, 24), [(0.52, 0.72), (0.80, 0.98)]]),
    'U': (0.78, [[(0.11, 0.04), (0.11, 0.60)] + _arc(0.39, 0.60, 0.28, 0.33, math.pi, 0, 10)[1:] + [(0.67, 0.04)]]),
    'I': (0.30, [[(0.15, 0.04), (0.15, 0.96)]]),
    'H': (0.76, [[(0.11, 0.04), (0.11, 0.96)], [(0.65, 0.04), (0.65, 0.96)], [(0.11, 0.50), (0.65, 0.50)]]),
    'Y': (0.76, [[(0.08, 0.04), (0.38, 0.50)], [(0.68, 0.04), (0.38, 0.50)], [(0.38, 0.50), (0.38, 0.96)]]),
    'L': (0.64, [[(0.12, 0.04), (0.12, 0.94), (0.58, 0.94)]]),
    'E': (0.66, [[(0.58, 0.06), (0.12, 0.06), (0.12, 0.94), (0.58, 0.94)], [(0.12, 0.50), (0.50, 0.50)]]),
}

LETTER_COLORS = ['strawberry', 'sparkle', 'matcha', 'sky', 'taro', 'peach', 'strawberry']
EXTRA = {
    'sky': ['#f4fbff', '#dff1ff', '#c3e3fb', '#a3cff2', '#86b9e6', '#4f7fb8', '#ffa3bc'],
    'peach': ['#fff8f0', '#ffe8d4', '#ffd2b4', '#f6b690', '#e59c76', '#b0664e', '#ffa3bc'],
}


def _ramp(name):
    if name in FL:
        return FL[name]
    return [rgb15(h) for h in EXTRA[name]]


def letter(ch, height, color, stroke=0.15):
    """Render one bubble letter. Returns RGBA with margin for outlines."""
    adv, strokes = LETTERS[ch]
    r = stroke * height
    pad = int(math.ceil(r)) + 3
    w = int(math.ceil(adv * height)) + 2 * pad
    h = int(height) + 2 * pad
    xs = np.arange(w) + 0.5 - pad
    ys = np.arange(h) + 0.5 - pad
    X, Y = np.meshgrid(xs, ys)
    d = np.full(X.shape, 1e9)
    for pts in strokes:
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            d = np.minimum(d, _seg_dist(X, Y, ax * height, ay * height, bx * height, by * height))
    inside = d <= r
    hgt = np.where(inside, np.sqrt(np.clip(1 - (d / r) ** 2, 0, 1)), 0)
    gy, gx = np.gradient(hgt)
    k = r * 0.9
    nx, ny, nz = -gx * k, -gy * k, np.ones_like(hgt)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    I = (nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2]) / ln
    rp = _ramp(color)
    img = new(w, h)
    levels = [(0.97, rp[0]), (0.82, rp[1]), (0.48, rp[2]), (0.20, rp[3]), (-9, rp[4])]
    done = np.zeros_like(inside)
    for thr, col in levels:
        m = inside & (I > thr) & ~done
        img[m, :3] = col
        done |= m
    img[inside, 3] = 255

    def ring(mask):
        o = np.zeros_like(mask)
        o[1:] |= mask[:-1]
        o[:-1] |= mask[1:]
        o[:, 1:] |= mask[:, :-1]
        o[:, :-1] |= mask[:, 1:]
        return o & ~mask

    o1 = ring(inside)
    img[o1, :3] = rp[5]
    img[o1, 3] = 255
    return img, pad


def word(text, height, colors, spacing=0.06, stroke=0.15, white_border=True, shadow=True):
    """Compose a word. Returns (rgba, list of (letter_img, x, y)) so letters can
    also be placed as separate bouncing sprites."""
    pieces = []
    x = 0
    for i, ch in enumerate(text):
        img, pad = letter(ch, height, colors[i % len(colors)], stroke)
        pieces.append((img, x - pad, 0))
        x += int(round((LETTERS[ch][0] + spacing) * height))
    total_w = x + 16
    H_ = int(height) + 16
    out = new(total_w + 8, H_ + 6)
    ox, oy = 4, 2
    mask = np.zeros(out.shape[:2], bool)
    for img, px, py in pieces:
        m = img[..., 3] > 0
        ys, xs = np.nonzero(m)
        mask[ys + py + oy + 2 - 0, xs + px + ox + 6 - 0] = True
    # white outer border + plum drop shadow, shared by all letters
    def grow(m):
        o = m.copy()
        o[1:] |= m[:-1]
        o[:-1] |= m[1:]
        o[:, 1:] |= m[:, :-1]
        o[:, :-1] |= m[:, 1:]
        return o
    border = grow(grow(mask)) if white_border else mask
    if shadow:
        sh = np.zeros_like(border)
        sh[3:] = border[:-3]
        out[sh, :3] = rgb15('#8a6aa8')
        out[sh, 3] = 255
    if white_border:
        out[border, :3] = C['white']
        out[border, 3] = 255
    for img, px, py in pieces:
        m = img[..., 3] > 0
        ys, xs = np.nonzero(m)
        out[ys + py + oy + 2, xs + px + ox + 6] = img[ys, xs]
    return out
