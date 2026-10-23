"""Procedural squishy art.

Each species is a set of soft shapes in a 64x64 design space. The same
definition renders natively at 16, 32 and 64 px, so every size is real
pixel art (no scaling). Shading is a height-field dome lit from the top
left, quantized to the flavor ramp, then outlined with the flavor's own
dark tone for a soft, candy-like look.
"""
import math
import numpy as np

from gba import new
from palette import FL, ACC, C

LIGHT = np.array([-0.50, -0.62, 0.60])
LIGHT = LIGHT / np.linalg.norm(LIGHT)


# ---------------------------------------------------------------- shapes
def _rot(X, Y, cx, cy, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    x, y = X - cx, Y - cy
    return x * c + y * s, -x * s + y * c


class Shape:
    """inside(X, Y) -> bool mask, height(X, Y) -> 0..1 dome height."""

    def inside(self, X, Y):
        raise NotImplementedError

    def height(self, X, Y):
        raise NotImplementedError


class Ellipse(Shape):
    def __init__(self, cx, cy, rx, ry=None, rot=0, p=2.0):
        self.cx, self.cy, self.rx, self.ry, self.rot, self.p = cx, cy, rx, ry or rx, rot, p

    def _r(self, X, Y):
        x, y = _rot(X, Y, self.cx, self.cy, self.rot)
        return np.sqrt((x / self.rx) ** 2 + (y / self.ry) ** 2)

    def inside(self, X, Y):
        return self._r(X, Y) <= 1.0

    def height(self, X, Y):
        r = np.clip(self._r(X, Y), 0, 1)
        return (1 - r ** (2 * self.p / 2)) ** (1 / self.p) if self.p != 2 else np.sqrt(1 - r * r)


class Mochi(Shape):
    """Superellipse with a flatter bottom: the classic squishy silhouette."""

    def __init__(self, cx, cy, a, b, nt=2.3, nb=3.4, p=2.6):
        self.cx, self.cy, self.a, self.b, self.nt, self.nb, self.p = cx, cy, a, b, nt, nb, p

    def _r(self, X, Y):
        x = np.abs(X - self.cx) / self.a
        y = (Y - self.cy) / self.b
        n = np.where(y < 0, self.nt, self.nb)
        return (x ** n + np.abs(y) ** n) ** (1 / n)

    def inside(self, X, Y):
        return self._r(X, Y) <= 1.0

    def height(self, X, Y):
        r = np.clip(self._r(X, Y), 0, 1)
        return (1 - r ** self.p) ** (1 / self.p)


def _seg_dist(X, Y, ax, ay, bx, by):
    px, py = X - ax, Y - ay
    dx, dy = bx - ax, by - ay
    h = np.clip((px * dx + py * dy) / (dx * dx + dy * dy + 1e-9), 0, 1)
    return np.hypot(px - dx * h, py - dy * h)


class Poly(Shape):
    """Convex polygon grown by a rounding radius."""

    def __init__(self, pts, round_r=2.0, R=6.0):
        self.pts, self.rr, self.R = pts, round_r, R

    def _sdf(self, X, Y):
        pts = self.pts
        d = np.full(X.shape, 1e9)
        inside = np.ones(X.shape, bool)
        n = len(pts)
        area = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
        sgn = 1 if area > 0 else -1
        for i in range(n):
            ax, ay = pts[i]
            bx, by = pts[(i + 1) % n]
            d = np.minimum(d, _seg_dist(X, Y, ax, ay, bx, by))
            cross = (bx - ax) * (Y - ay) - (by - ay) * (X - ax)
            inside &= (cross * sgn) >= 0
        return np.where(inside, -d, d) - self.rr

    def inside(self, X, Y):
        return self._sdf(X, Y) <= 0

    def height(self, X, Y):
        t = np.clip(-self._sdf(X, Y) / self.R, 0, 1)
        return np.sqrt(1 - (1 - t) ** 2)


class Star(Shape):
    def __init__(self, cx, cy, r, rf=0.5, round_r=3.0, R=10.0):
        self.cx, self.cy, self.r, self.rf, self.rr, self.R = cx, cy, r, rf, round_r, R

    def _sdf(self, X, Y):
        k1 = np.array([0.809016994375, -0.587785252292])
        k2 = np.array([-k1[0], k1[1]])
        px = np.abs(X - self.cx)
        py = -(Y - self.cy)
        for k in (k1, k2):
            d = np.maximum(px * k[0] + py * k[1], 0)
            px = px - 2 * d * k[0]
            py = py - 2 * d * k[1]
        px = np.abs(px)
        r = self.r - self.rr
        py = py - r
        bax, bay = self.rf * -k1[1] - 0, self.rf * k1[0] - 1
        h = np.clip((px * bax + py * bay) / (bax * bax + bay * bay), 0, r)
        dist = np.hypot(px - bax * h, py - bay * h)
        s = np.sign(py * bax - px * bay)
        return dist * s - self.rr

    def inside(self, X, Y):
        return self._sdf(X, Y) <= 0

    def height(self, X, Y):
        t = np.clip(-self._sdf(X, Y) / self.R, 0, 1)
        return np.sqrt(1 - (1 - t) ** 2)


class Union(Shape):
    def __init__(self, *shapes):
        self.shapes = shapes

    def inside(self, X, Y):
        m = np.zeros(X.shape, bool)
        for s in self.shapes:
            m |= s.inside(X, Y)
        return m

    def height(self, X, Y):
        h = np.zeros(X.shape)
        for s in self.shapes:
            h = np.maximum(h, np.where(s.inside(X, Y), s.height(X, Y), 0))
        return h


class Silhouette(Shape):
    """Mask from many shapes, shading from one smooth dome (no creases)."""

    def __init__(self, dome, *shapes):
        self.dome, self.shapes = dome, shapes

    def inside(self, X, Y):
        m = np.zeros(X.shape, bool)
        for s in self.shapes:
            m |= s.inside(X, Y)
        return m

    def height(self, X, Y):
        h = self.dome.height(X, Y)
        return np.where(self.dome.inside(X, Y), h, 0.08)


class Minus(Shape):
    def __init__(self, a, b):
        self.a, self.b = a, b

    def inside(self, X, Y):
        return self.a.inside(X, Y) & ~self.b.inside(X, Y)

    def height(self, X, Y):
        return self.a.height(X, Y)


class HalfPlane(Shape):
    """Keep the side where (x,y)·n >= c."""

    def __init__(self, nx, ny, c):
        self.nx, self.ny, self.c = nx, ny, c

    def inside(self, X, Y):
        return X * self.nx + Y * self.ny >= self.c

    def height(self, X, Y):
        return np.ones(X.shape)


class Clip(Shape):
    def __init__(self, a, b):
        self.a, self.b = a, b

    def inside(self, X, Y):
        return self.a.inside(X, Y) & self.b.inside(X, Y)

    def height(self, X, Y):
        return self.a.height(X, Y)


class Part:
    def __init__(self, shape, z=1, mat='body', line='ink', clip=None, flat=False):
        self.shape, self.z, self.mat, self.line, self.clip, self.flat = shape, z, mat, line, clip, flat


def mirror(shape):
    """Mirror a shape across x = 32."""

    class _M(Shape):
        def inside(self, X, Y):
            return shape.inside(64 - X, Y)

        def height(self, X, Y):
            return shape.height(64 - X, Y)

    return _M()


# ----------------------------------------------------------- face pixels
EYE = {
    64: ['.kkk.', 'kwwkk', 'kwwkk', 'kkkkk', 'kkkwk', '.kkk.'],
    32: ['kk', 'wk', 'kk'],
    16: ['k', 'k'],
}
EYE_HAPPY = {
    64: ['.kkk.', 'k...k'],
    32: ['.k.', 'k.k'],
    16: ['kk'],
}
EYE_SLEEP = {                     # asleep: soft lines (the sleepy panda at the gates)
    64: ['k...k', '.kkk.'],
    32: ['k.k', '.k.'],
    16: ['k'],
}
EYE_SQUISH_L = {
    64: ['kk...', '..kk.', '....k', '..kk.', 'kk...'],
    32: ['k..', '.kk', 'k..'],
    16: ['k'],
}
MOUTH = {
    'w': {64: ['k.kk.k', '.k..k.'], 32: ['k..k', '.kk.'], 16: []},
    'u': {64: ['k..k', '.kk.'], 32: ['kk'], 16: []},
    'open': {64: ['kkkkkk', 'kppppk', '.kppk.', '..kk..'], 32: ['kkkk', '.pp.'], 16: []},
    'o': {64: ['.kk.', 'kppk', '.kk.'], 32: ['kk', 'kk'], 16: []},
    'smile': {64: ['k......k', '.kkkkkk.'], 32: ['k....k', '.kkkk.'], 16: []},
}
BLUSH = {
    64: ['.bbbb.', 'bbbbbb', '.bbbb.'],
    32: ['bbb'],
    16: ['b'],
}
NOSE = {64: ['kkkk', '.kk.'], 32: ['kk'], 16: ['kk']}


class Species:
    def __init__(self, key, name, parts, eyes, mouth=('u', 46), blush=None,
                 shine=None, nose=None, extras=None, tweak=None, sym=True):
        self.key, self.name, self.parts = key, name, parts
        self.eyes = eyes          # (x_left, y) design coords, mirrored
        self.mouth = mouth        # (kind, y)  centered on x=32
        self.blush = blush        # (x_left, y)
        self.shine = shine        # (x, y, rx, ry, rot)
        self.nose = nose          # y
        self.extras = extras or []
        self.tweak = tweak or {}  # size -> dict of pixel offsets
        self.sym = sym


# ROM export mode: accents use two shades and the tongue uses the blush
# color, so every species of an area fits one shared 15-color palette layout.
ROM_MODE = False


def _mat_ramp(mat, flavor):
    fl = FL[flavor]
    if mat == 'body':
        return {'hi': fl[0], 'lt': fl[1], 'base': fl[2], 's1': fl[3], 's2': fl[4], 'line': fl[5]}
    if mat == 'bodylt':
        return {'hi': fl[0], 'lt': fl[0], 'base': fl[1], 's1': fl[2], 's2': fl[3], 'line': fl[4]}
    if mat.endswith('2'):
        a = ACC[mat[:-1]]
        return {'hi': a[1], 'lt': a[1], 'base': a[1], 's1': a[2], 's2': a[2], 'line': fl[5]}
    a = ACC[mat]
    if ROM_MODE:
        return {'hi': a[1], 'lt': a[1], 'base': a[1], 's1': a[2], 's2': a[2], 'line': fl[5]}
    return {'hi': a[0], 'lt': a[0], 'base': a[1], 's1': a[2], 's2': a[2], 'line': fl[5]}


def render(sp, flavor, size, expr='happy', squash=(1.0, 1.0)):
    """Render species `sp` in `flavor` at native `size` px. squash scales the
    design around the bottom center (used only for preview frames; the game
    uses OBJ affine for squash)."""
    N = size
    pad = 0 if N >= 64 else 1
    s = 64.0 / (N - 2 * pad)
    sx, sy = squash
    if N <= 16:
        sx *= 0.9   # keep side details (wings, claws, tails) inside 16 px
    idx = (np.arange(N) - pad + 0.5) * s
    X, Y = np.meshgrid(idx, idx)
    # squash about bottom center
    X = 32 + (X - 32) / sx
    Y = 60 + (Y - 60) / sy

    parts = sorted(enumerate(sp.parts), key=lambda t: t[1].z)
    owner = np.full((N, N), -1)
    masks = {}
    for i, p in parts:
        m = p.shape.inside(X, Y)
        if p.clip is not None:
            m &= sp.parts[p.clip].shape.inside(X, Y)
        masks[i] = m
        owner[m] = i

    img = new(N, N)
    fl = FL[flavor]

    # shading
    for i, p in parts:
        m = owner == i
        if not m.any():
            continue
        ramp = _mat_ramp(p.mat, flavor)
        h = np.where(masks[i], p.shape.height(X, Y), 0.0)
        gy, gx = np.gradient(h, s)
        scale = 9.0
        nx, ny, nz = -gx * scale, -gy * scale, np.ones_like(h)
        ln = np.sqrt(nx * nx + ny * ny + nz * nz)
        I = (nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2]) / ln
        if p.flat:
            I = np.full_like(I, 0.62)
        col = np.zeros((N, N, 3), np.uint8)
        levels = [(0.985, 'hi'), (0.86, 'lt'), (0.50, 'base'), (0.22, 's1'), (-9, 's2')]
        assigned = np.zeros((N, N), bool)
        for thr, key in levels:
            mm = (I > thr) & ~assigned
            col[mm] = ramp[key]
            assigned |= mm
        img[..., :3][m] = col[m]
        img[..., 3][m] = 255

    # soften isolated shading pixels (no lone specks)
    rgb = img[..., :3].copy()
    for y in range(1, N - 1):
        for x in range(1, N - 1):
            if owner[y, x] < 0:
                continue
            c = tuple(rgb[y, x])
            nb = [(y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)]
            same = [tuple(rgb[a, b]) == c for a, b in nb if owner[a, b] == owner[y, x]]
            if same and not any(same):
                cols = [tuple(rgb[a, b]) for a, b in nb if owner[a, b] == owner[y, x]]
                best = max(set(cols), key=cols.count)
                if cols.count(best) >= 3:
                    img[y, x, :3] = best

    # internal lines between overlapping parts
    for y in range(N):
        for x in range(N):
            o = owner[y, x]
            if o < 0:
                continue
            p = sp.parts[o]
            if not p.line:
                continue
            for a, b in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= a < N and 0 <= b < N:
                    q = owner[a, b]
                    if q >= 0 and sp.parts[q].z < p.z:
                        if p.line == 'ink':
                            img[y, x, :3] = fl[5]
                        else:
                            img[y, x, :3] = _mat_ramp(sp.parts[q].mat, flavor)['s2'] if p.line == 'soft' else fl[4]
                        break

    # silhouette outline
    U = owner >= 0
    out = np.zeros_like(U)
    out[1:, :] |= U[:-1, :]
    out[:-1, :] |= U[1:, :]
    out[:, 1:] |= U[:, :-1]
    out[:, :-1] |= U[:, 1:]
    out &= ~U
    img[..., :3][out] = fl[5]
    img[..., 3][out] = 255

    # face
    face_color = {'k': C['ink'], 'w': C['white'], 'b': fl[6], 'p': fl[6] if ROM_MODE else C['blush_dk']}
    tw = sp.tweak.get(N, {})

    def put(pattern, cx, cy, mirror_x=False):
        if not pattern:
            return
        h = len(pattern)
        w = len(pattern[0])
        x0 = int(round(cx / s + pad - w / 2))
        y0 = int(round(cy / s + pad - h / 2))
        if mirror_x:
            x0 = N - x0 - w
            pattern = [r[::-1] for r in pattern]
        for yy, row in enumerate(pattern):
            for xx, ch in enumerate(row):
                if ch == '.':
                    continue
                px, py = x0 + xx, y0 + yy
                if 0 <= px < N and 0 <= py < N:
                    img[py, px, :3] = face_color[ch]
                    img[py, px, 3] = 255

    ex, ey = sp.eyes
    ex += tw.get('ex', 0) * s
    ey += tw.get('ey', 0) * s
    ey = 60 + (ey - 60) * sy
    ex = 32 + (ex - 32) * sx
    if sp.blush:
        bx, by = sp.blush
        bx += tw.get('bx', 0) * s
        by += tw.get('by', 0) * s
        by = 60 + (by - 60) * sy
        bx = 32 + (bx - 32) * sx
        put(BLUSH[N], bx, by)
        put(BLUSH[N], bx, by, True)
    if expr == 'squish':
        put(EYE_SQUISH_L[N], ex, ey)
        put(EYE_SQUISH_L[N], ex, ey, True)
    elif expr == 'closed':
        put(EYE_HAPPY[N], ex, ey)
        put(EYE_HAPPY[N], ex, ey, True)
    elif expr == 'sleep':
        put(EYE_SLEEP[N], ex, ey)
        put(EYE_SLEEP[N], ex, ey, True)
    else:
        e = EYE[N]
        put(e, ex, ey)
        # mirrored eye keeps the highlight on the left (light from top-left)
        h = len(e)
        w = len(e[0])
        x0 = N - int(round(ex / s + pad - w / 2)) - w
        y0 = int(round(ey / s + pad - h / 2))
        for yy, row in enumerate(e):
            for xx, ch in enumerate(row):
                if ch != '.':
                    img[y0 + yy, x0 + xx, :3] = face_color[ch]
                    img[y0 + yy, x0 + xx, 3] = 255
    if sp.nose is not None:
        ny_ = 60 + (sp.nose + tw.get('ny', 0) * s - 60) * sy
        put(NOSE[N], 32, ny_)
    if sp.mouth:
        kind, my = sp.mouth
        if expr in ('happy_open', 'squish') and kind in ('u', 'w'):
            kind = 'open' if expr == 'happy_open' else kind
        my += tw.get('my', 0) * s
        my = 60 + (my - 60) * sy
        put(MOUTH[kind][N], 32, my)
    for fn in sp.extras:
        fn(img, N, s, flavor, put)

    # shine highlight
    if sp.shine:
        hx, hy, rx, ry, rot = sp.shine
        hx = 32 + (hx - 32) * sx
        hy = 60 + (hy - 60) * sy
        e = Ellipse(hx, hy, rx, ry, rot)
        m = e.inside(X * 0 + np.meshgrid(idx, idx)[0], np.meshgrid(idx, idx)[1]) & (owner >= 0)
        if N == 16:
            m = np.zeros_like(m)
            px, py = int(hx / s + pad), int(hy / s + pad)
            if owner[py, px] >= 0:
                m[py, px] = True
        img[..., :3][m] = fl[0]

    if flavor == 'sparkle':
        glint = {64: ['..w..', '..w..', 'wwWww', '..w..', '..w..'],
                 32: ['.w.', 'wWw', '.w.'], 16: ['W']}[N]
        for gx, gy in ((45, 33), (40, 53)) if N > 16 else ((45, 36),):
            h = len(glint)
            x0 = int(round(gx / s + pad - h / 2))
            y0 = int(round(gy / s + pad - h / 2))
            for yy, row in enumerate(glint):
                for xx, ch in enumerate(row):
                    if ch == '.':
                        continue
                    if owner[y0 + yy, x0 + xx] >= 0 and img[y0 + yy, x0 + xx, 3]:
                        img[y0 + yy, x0 + xx, :3] = C['white'] if ch == 'W' else fl[0]
    return img


# --------------------------------------------------------------- species
def _whiskers(img, N, s, flavor, put):
    if N == 64:
        line = FL[flavor][5]
        for (x, y) in ((6, 43), (6, 47)):
            for i in range(4):
                yy = y - (i // 2 if y == 43 else -(i // 2))
                img[yy, x + i, :3] = line
                img[yy, 63 - x - i, :3] = line
                img[yy, x + i, 3] = img[yy, 63 - x - i, 3] = 255


SPECIES = {}


def _add(sp):
    SPECIES[sp.key] = sp


BODY = Mochi(32, 42, 26, 19)

_add(Species('bunny', 'Bunny', [
    Part(Ellipse(22, 17, 6.5, 14.5, rot=-12), z=0),
    Part(Ellipse(22, 18, 2.8, 10, rot=-12), z=0.5, mat='pink', line=None, clip=0),
    Part(mirror(Ellipse(22, 17, 6.5, 14.5, rot=-12)), z=0),
    Part(mirror(Ellipse(22, 18, 2.8, 10, rot=-12)), z=0.5, mat='pink', line=None, clip=2),
    Part(BODY, z=1),
], eyes=(21, 41), mouth=('w', 47), blush=(14, 47), shine=(17, 32, 4, 2.2, -35)))

_add(Species('kitty', 'Kitty', [
    Part(Poly([(9, 32), (14, 11), (29, 25)], 2.5), z=0),
    Part(Poly([(14, 28), (16, 17), (24, 25)], 1.0), z=0.5, mat='pink', line=None, clip=0),
    Part(mirror(Poly([(9, 32), (14, 11), (29, 25)], 2.5)), z=0),
    Part(mirror(Poly([(14, 28), (16, 17), (24, 25)], 1.0)), z=0.5, mat='pink', line=None, clip=2),
    Part(BODY, z=1),
], eyes=(21, 41), mouth=('w', 47), blush=(14, 47), shine=(18, 31, 4, 2.2, -35),
    extras=[_whiskers]))

_add(Species('bear', 'Bear', [
    Part(Ellipse(14, 26, 8.5), z=0),
    Part(Ellipse(14, 26, 4.2), z=0.5, mat='pink', line=None, clip=0),
    Part(mirror(Ellipse(14, 26, 8.5)), z=0),
    Part(mirror(Ellipse(14, 26, 4.2)), z=0.5, mat='pink', line=None, clip=2),
    Part(BODY, z=1),
    Part(Ellipse(32, 48.5, 8.5, 6.5), z=2, mat='cream', line='soft'),
], eyes=(20, 40), mouth=('u', 50.5), nose=46, blush=(12, 47), shine=(18, 31, 4, 2.2, -35)))

_add(Species('chick', 'Chick', [
    Part(Ellipse(29, 17, 2.8, 7, rot=-25), z=0),
    Part(Ellipse(35, 18, 2.6, 6, rot=28), z=0),
    Part(Mochi(32, 40, 25, 21), z=1),
    Part(Ellipse(9, 51, 4.2, 7.5, rot=62), z=2, line='soft'),
    Part(mirror(Ellipse(9, 51, 4.2, 7.5, rot=62)), z=2, line='soft'),
    Part(Poly([(28, 44), (36, 44), (32, 49)], 1.6, R=3), z=3, mat='orange', line=None),
], eyes=(21, 39), mouth=None, blush=(14, 46), shine=(18, 29, 4, 2.2, -35)))

_add(Species('whale', 'Whale', [
    Part(Ellipse(49, 33, 4.5, 9, rot=35), z=0),
    Part(Ellipse(49, 21, 3.4, 7, rot=-50), z=0),
    Part(Ellipse(58, 23, 3.4, 7, rot=20), z=0),
    Part(Mochi(29, 43, 26, 17, nt=2.1, nb=3.0), z=1),
    Part(Ellipse(28, 56, 20, 8), z=2, mat='bodylt', line=None, clip=3),
    Part(Ellipse(22, 16, 2.2, 3), z=0, mat='sky', line=None),
    Part(Ellipse(29, 12, 2.2, 3), z=0, mat='sky', line=None),
    Part(Ellipse(36, 16, 2.2, 3), z=0, mat='sky', line=None),
], eyes=(20, 40), mouth=('u', 46), blush=(13, 46), shine=(16, 32, 4, 2.2, -35)))

_add(Species('octo', 'Octo', [
    Part(Ellipse(12, 52, 5.5, 7, rot=20), z=0),
    Part(Ellipse(22, 54, 5.5, 7), z=0),
    Part(Ellipse(32, 55, 5.5, 7), z=0),
    Part(Ellipse(42, 54, 5.5, 7), z=0),
    Part(Ellipse(52, 52, 5.5, 7, rot=-20), z=0),
    Part(Ellipse(32, 33, 23, 20), z=1),
    Part(Ellipse(22, 22, 3.2), z=2, mat='bodylt', line=None, clip=5),
    Part(Ellipse(41, 19, 2.6), z=2, mat='bodylt', line=None, clip=5),
    Part(Ellipse(46, 28, 2.0), z=2, mat='bodylt', line=None, clip=5),
], eyes=(23, 36), mouth=('o', 43), blush=(15, 42), shine=(16, 26, 3.5, 2, -40)))

_add(Species('seal', 'Seal', [
    Part(Mochi(32, 41, 25, 20), z=1),
    Part(Ellipse(10, 54, 7.5, 4, rot=25), z=2, line='soft'),
    Part(mirror(Ellipse(10, 54, 7.5, 4, rot=25)), z=2, line='soft'),
    Part(Ellipse(28.2, 48, 4.6, 3.8), z=2, mat='cream', line='soft'),
    Part(mirror(Ellipse(28.2, 48, 4.6, 3.8)), z=2, mat='cream', line='soft'),
], eyes=(20, 40), mouth=None, nose=45, blush=(12, 46), shine=(18, 30, 4, 2.2, -35)))

_add(Species('crab', 'Crab', [
    Part(Minus(Ellipse(11, 22, 8.5), Poly([(11, 22), (5, 10), (15, 10)], 0.5)), z=0),
    Part(Minus(mirror(Ellipse(11, 22, 8.5)), mirror(Poly([(11, 22), (5, 10), (15, 10)], 0.5))), z=0),
    Part(Ellipse(14, 34, 3, 6, rot=-20), z=0),
    Part(mirror(Ellipse(14, 34, 3, 6, rot=-20)), z=0),
    Part(Ellipse(6, 52, 4, 3), z=0),
    Part(mirror(Ellipse(6, 52, 4, 3)), z=0),
    Part(Mochi(32, 45, 25, 15, nt=2.0, nb=2.8), z=1),
], eyes=(22, 43), mouth=('w', 50), blush=(14, 49), shine=(18, 36, 4, 2, -30)))

_add(Species('frog', 'Frog', [
    Part(Ellipse(19, 26, 9.5), z=0, line=None),
    Part(mirror(Ellipse(19, 26, 9.5)), z=0, line=None),
    Part(Mochi(32, 43, 27, 18), z=1, line=None),
], eyes=(19, 26), mouth=('smile', 43), blush=(12, 45), shine=(13, 21, 2.5, 1.6, -35)))

_add(Species('fox', 'Fox', [
    Part(Ellipse(52, 45, 7.5, 12.5, rot=35), z=-1),
    Part(Ellipse(57, 37, 4.5, 4.5), z=-0.5, mat='cream', line=None, clip=0),
    Part(Poly([(8, 34), (11, 7), (29, 24)], 2.0), z=0),
    Part(Poly([(13, 29), (14, 14), (23, 24)], 1.0), z=0.5, mat='cream', line=None, clip=2),
    Part(mirror(Poly([(8, 34), (11, 7), (29, 24)], 2.0)), z=0),
    Part(mirror(Poly([(13, 29), (14, 14), (23, 24)], 1.0)), z=0.5, mat='cream', line=None, clip=4),
    Part(BODY, z=1),
    Part(Ellipse(20, 52, 12, 9), z=2, mat='cream', line=None, clip=6),
    Part(mirror(Ellipse(20, 52, 12, 9)), z=2, mat='cream', line=None, clip=6),
], eyes=(21, 41), mouth=('u', 50), nose=46.5, blush=(13, 46), shine=(18, 31, 4, 2.2, -35)))

_add(Species('dino', 'Dino', [
    Part(Poly([(20, 28), (22, 17), (29, 24)], 2.6), z=0, mat='pink'),
    Part(Poly([(28, 23), (32, 12), (36, 23)], 2.6), z=0, mat='pink'),
    Part(Poly([(35, 24), (42, 17), (44, 28)], 2.6), z=0, mat='pink'),
    Part(Poly([(46, 47), (59, 52), (47, 58)], 2.0), z=0),
    Part(Mochi(31, 42, 25, 19), z=1),
    Part(Ellipse(31, 55, 12, 8), z=2, mat='cream', line=None, clip=4),
], eyes=(20, 39), mouth=('open', 46), blush=(12, 45), shine=(17, 30, 4, 2.2, -35)))

_add(Species('shroom', 'Shroom', [
    Part(Mochi(32, 49, 15, 12, nt=2.4, nb=3.0), z=0, mat='cream'),
    Part(Mochi(32, 30, 29, 19, nt=2.1, nb=9.0), z=1),
    Part(Ellipse(19, 23, 4.5), z=2, mat='cream', line=None, clip=1),
    Part(Ellipse(37, 17, 5), z=2, mat='cream', line=None, clip=1),
    Part(Ellipse(50, 29, 3.2), z=2, mat='cream', line=None, clip=1),
    Part(Ellipse(29, 32, 2.6), z=2, mat='cream', line=None, clip=1),
], eyes=(26.5, 48), mouth=('u', 53), blush=(21, 52), shine=None))

_add(Species('cloud', 'Cloud', [
    Part(Silhouette(Mochi(32, 40, 30, 21, nt=2.0, nb=3.0, p=2.2),
                    Ellipse(15, 42, 10.5), Ellipse(26, 32, 12), Ellipse(39, 31, 11.5),
                    Ellipse(50, 40, 10), Mochi(32, 48, 28, 11, nt=2.4, nb=3.2)), z=1),
], eyes=(24, 44), mouth=('u', 49), blush=(16, 49), shine=(22, 25, 3.5, 2, -30)))

_add(Species('star', 'Star', [
    Part(Star(32, 35, 29, rf=0.52, round_r=3.5, R=9), z=1),
], eyes=(26, 36), mouth=('u', 42), blush=(20, 42), shine=(26, 20, 2.5, 1.6, -30)))

_add(Species('planet', 'Planet', [
    Part(Minus(Ellipse(32, 38, 30.5, 9.5, rot=-14), Ellipse(32, 38, 21, 3.6, rot=-14)), z=0,
         mat='gold', line=None),
    Part(Ellipse(32, 36, 20), z=1),
    Part(Clip(Minus(Ellipse(32, 38, 30.5, 9.5, rot=-14), Ellipse(32, 38, 21, 3.6, rot=-14)),
              HalfPlane(0.24, 0.97, 0.24 * 32 + 0.97 * 38)), z=2, mat='gold', line='ink'),
    Part(Ellipse(42, 25, 3.2), z=1.5, mat='bodylt', line=None, clip=1),
    Part(Ellipse(36, 20, 1.8), z=1.5, mat='bodylt', line=None, clip=1),
], eyes=(24, 34), mouth=('u', 39.5), blush=(18, 39), shine=(22, 24, 3, 1.8, -35)))

_add(Species('uni', 'Uni', [
    Part(Poly([(12, 30), (15, 15), (25, 25)], 2.0), z=0),
    Part(mirror(Poly([(12, 30), (15, 15), (25, 25)], 2.0)), z=0),
    Part(Poly([(29, 22), (32, 4), (35, 22)], 1.5, R=3), z=0.2, mat='gold2'),
    Part(BODY, z=1),
    Part(Union(Ellipse(22, 26, 6.5, 5.5), Ellipse(31, 24, 5.5, 5)), z=2, mat='pink2', line='ink', clip=3),
    Part(Ellipse(40, 25, 5.5, 5), z=2.1, mat='lav2', line='ink', clip=3),
], eyes=(21, 42), mouth=('u', 48), blush=(14, 48), shine=(15, 35, 3, 1.8, -35)))

# In play order: each area opens after 10 friends are found in the one
# before it (owner decision, step 6). Friend ids follow this order.
AREAS = [
    ('meadow', 'Blossom Meadow', 'box', ['bunny', 'kitty', 'bear', 'chick']),
    ('woods', 'Berry Woods', 'acorn', ['frog', 'fox', 'dino', 'shroom']),
    ('shore', 'Seashell Shore', 'shell', ['whale', 'octo', 'seal', 'crab']),
    ('clouds', 'Cloud Hill', 'capsule', ['cloud', 'star', 'planet', 'uni']),
]
