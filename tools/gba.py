"""GBA-faithful pixel helpers.

Every color passes through 15-bit (5:5:5) quantization so the mockups show
exactly what the hardware can display. Images are numpy RGBA arrays where
alpha is 0 (transparent, palette index 0) or 255 (opaque).
"""
import numpy as np
from PIL import Image

W, H = 240, 160


def q5(v):
    return max(0, min(31, int(round(v * 31 / 255))))


def x8(q):
    return (q << 3) | (q >> 2)


def rgb15(hexstr):
    h = hexstr.lstrip('#')
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return (x8(q5(r)), x8(q5(g)), x8(q5(b)))


def to5(c):
    return tuple(int(v) >> 3 for v in c)


def from5(c):
    return tuple(x8(int(v)) for v in c)


def blend(a, b, eva, evb):
    """GBA alpha blend: (a*eva + b*evb) / 16 per 5-bit channel."""
    a5, b5 = to5(a), to5(b)
    return from5(tuple(min(31, (x * eva + y * evb) >> 4) for x, y in zip(a5, b5)))


def new(w, h):
    return np.zeros((h, w, 4), np.uint8)


def solid(w, h, color):
    img = new(w, h)
    img[..., :3] = color
    img[..., 3] = 255
    return img


def from_ascii(rows, legend):
    """Build an RGBA sprite from strings. '.' and ' ' are transparent."""
    rows = [r for r in rows]
    h = len(rows)
    w = max(len(r) for r in rows)
    img = new(w, h)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch in '. ':
                continue
            if ch not in legend:
                raise KeyError(f'missing legend char {ch!r}')
            img[y, x, :3] = legend[ch]
            img[y, x, 3] = 255
    return img


def flip_h(img):
    return img[:, ::-1].copy()


def flip_v(img):
    return img[::-1].copy()


def blit(dst, src, x, y):
    """Paste opaque pixels of src onto dst at (x, y), clipped."""
    x, y = int(x), int(y)
    sh, sw = src.shape[:2]
    dh, dw = dst.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(dw, x + sw), min(dh, y + sh)
    if x0 >= x1 or y0 >= y1:
        return
    s = src[y0 - y:y1 - y, x0 - x:x1 - x]
    m = s[..., 3] > 0
    d = dst[y0:y1, x0:x1]
    d[m] = s[m]


def blit_blend(dst, src, x, y, eva, evb):
    """Semi-transparent OBJ: blend src over dst using GBA coefficients."""
    x, y = int(x), int(y)
    sh, sw = src.shape[:2]
    dh, dw = dst.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(dw, x + sw), min(dh, y + sh)
    if x0 >= x1 or y0 >= y1:
        return
    s = src[y0 - y:y1 - y, x0 - x:x1 - x]
    d = dst[y0:y1, x0:x1]
    m = s[..., 3] > 0
    a5 = s[..., :3].astype(np.int32) >> 3
    b5 = d[..., :3].astype(np.int32) >> 3
    r5 = np.minimum(31, (a5 * eva + b5 * evb) >> 4)
    r8 = (r5 << 3) | (r5 >> 2)
    d[..., :3][m] = r8[m].astype(np.uint8)
    d[..., 3][m] = 255


def brightness(img, evy, toward_white=True):
    """GBA brightness increase/decrease (evy 0..16)."""
    c5 = img[..., :3].astype(np.int32) >> 3
    if toward_white:
        c5 = c5 + (((31 - c5) * evy) >> 4)
    else:
        c5 = c5 - ((c5 * evy) >> 4)
    img[..., :3] = ((c5 << 3) | (c5 >> 2)).astype(np.uint8)


def recolor(img, mapping):
    """Swap exact colors (palette swap)."""
    out = img.copy()
    for src, dst in mapping.items():
        m = (img[..., 0] == src[0]) & (img[..., 1] == src[1]) & (img[..., 2] == src[2]) & (img[..., 3] > 0)
        out[..., :3][m] = dst
    return out


def colors_of(img):
    m = img[..., 3] > 0
    px = img[..., :3][m]
    return {tuple(int(v) for v in p) for p in px}


def save_scaled(img, path, scale=4):
    rgb = img[..., :3]
    im = Image.fromarray(rgb, 'RGB')
    im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    im.save(path)


def check_obj(img, name, maxc=15):
    n = len(colors_of(img))
    if n > maxc:
        raise ValueError(f'OBJ {name}: {n} colors > {maxc}')
    return n


def pack_tile_palettes(layer, max_pals=16, per_pal=15):
    """Greedy-pack the colors of every 8x8 tile of a BG layer into 16-color
    palettes. Returns palettes or raises if the layer is not GBA-legal."""
    h, w = layer.shape[:2]
    sets = []
    for ty in range(0, h, 8):
        for tx in range(0, w, 8):
            t = layer[ty:ty + 8, tx:tx + 8]
            cs = colors_of(t)
            if len(cs) > per_pal:
                raise ValueError(f'tile ({tx},{ty}) uses {len(cs)} colors')
            if cs:
                sets.append(frozenset(cs))
    uniq = sorted(set(sets), key=len, reverse=True)
    pals = []
    for s in uniq:
        best = None
        for p in pals:
            if s <= p:
                best = p
                break
        if best is not None:
            continue
        cand = [p for p in pals if len(p | s) <= per_pal]
        if cand:
            p = min(cand, key=lambda p: len(p | s))
            pals.remove(p)
            pals.append(p | s)
        else:
            pals.append(set(s))
    if len(pals) > max_pals:
        raise ValueError(f'layer needs {len(pals)} palettes > {max_pals}')
    return pals


def affine(img, sx=1.0, sy=1.0, rot=0.0):
    """Emulate a GBA double-size affine OBJ: nearest-neighbour sampling of
    img through the inverse matrix. Returns a (2h, 2w) RGBA canvas with the
    sprite centred. rot is in degrees, clockwise on screen."""
    import math
    h, w = img.shape[:2]
    out = new(2 * w, 2 * h)
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    # 8.8 fixed point like PA..PD
    pa = int(round(c / sx * 256)) / 256
    pb = int(round(s / sx * 256)) / 256
    pc = int(round(-s / sy * 256)) / 256
    pd = int(round(c / sy * 256)) / 256
    ys, xs = np.mgrid[0:2 * h, 0:2 * w]
    dx = xs - w
    dy = ys - h
    tx = np.floor(pa * dx + pb * dy + w / 2).astype(int)
    ty = np.floor(pc * dx + pd * dy + h / 2).astype(int)
    ok = (tx >= 0) & (tx < w) & (ty >= 0) & (ty < h)
    out[ok] = img[ty[ok], tx[ok]]
    return out
