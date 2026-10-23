"""Convert pipeline art (RGBA numpy images) into GBA data and C source.

- bg():  a full picture -> 4bpp tiles (deduplicated, with flips), a screen
         map and packed 16-color palettes.
- obj(): a sprite image + fixed palette -> 4bpp tiles in 1D mapping order.
- CWriter collects arrays and writes one .c and one .h file.
"""
import numpy as np


def bgr555(c):
    r, g, b = int(c[0]), int(c[1]), int(c[2])
    return (r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10)


def tile4(idx):
    """8x8 array of palette indices -> 32 bytes of 4bpp data."""
    out = bytearray()
    for row in idx:
        for x in range(0, 8, 2):
            out.append((int(row[x]) & 15) | ((int(row[x + 1]) & 15) << 4))
    return bytes(out)


def _colors(t):
    m = t[..., 3] > 0
    return frozenset(tuple(int(v) for v in p) for p in t[..., :3][m])


def _greedy(sets, per_pal):
    pals = []
    for s in sets:
        if any(s <= p for p in pals):
            continue
        best, best_cost = None, None
        for p in pals:
            u = len(p | s)
            if u <= per_pal:
                cost = (u - len(p), -len(p & s))
                if best is None or cost < best_cost:
                    best, best_cost = p, cost
        if best is not None:
            pals.remove(best)
            pals.append(best | s)
        else:
            pals.append(set(s))
    return pals


def _eliminate(sets, pals, per_pal):
    """Try to empty whole palettes by moving their tile sets elsewhere."""
    improved = True
    while improved and len(pals) > 1:
        improved = False
        # sets that fit only in a given palette decide what it must hold
        for victim in sorted(range(len(pals)), key=lambda i: len(pals[i])):
            others = [set(p) for j, p in enumerate(pals) if j != victim]
            owned = [s for s in sets if s <= pals[victim] and not any(s <= o for o in others)]
            ok = True
            for s in sorted(owned, key=len, reverse=True):
                fit = [o for o in others if len(o | s) <= per_pal]
                if not fit:
                    ok = False
                    break
                o = min(fit, key=lambda o: len(o | s) - len(o))
                o |= s
            if ok:
                pals = others
                improved = True
                break
    return pals


def pack_palettes(sets, per_pal=15, max_pals=16, tries=60):
    """Pack tile color sets into palettes of per_pal colors: greedy passes
    over several orders, then palette elimination; keeps the best."""
    import random
    uniq = [s for s in set(sets) if s]
    rnd = random.Random(1)
    best = None
    for t in range(tries):
        if t == 0:
            order = sorted(uniq, key=lambda s: (-len(s), sorted(s)))
        else:
            order = sorted(uniq, key=lambda s: (-len(s) + rnd.random() * 3))
        pals = _eliminate(uniq, _greedy(order, per_pal), per_pal)
        if best is None or len(pals) < len(best):
            best = pals
        if len(best) <= max_pals and t >= 3:
            break
    if len(best) > max_pals:
        raise ValueError(f'needs {len(best)} palettes > {max_pals}')
    return [sorted(p) for p in best]


def bg(img, pal_bank=0, max_pals=16, tile_base=0, flips=True):
    """Convert a picture (h, w multiples of 8) to tiles, map and palettes.
    Transparent pixels become index 0. Returns a dict."""
    h, w = img.shape[:2]
    assert h % 8 == 0 and w % 8 == 0, 'image must be a multiple of 8'
    tiles_rgba = [img[ty:ty + 8, tx:tx + 8] for ty in range(0, h, 8) for tx in range(0, w, 8)]
    sets = [_colors(t) for t in tiles_rgba]
    pals = pack_palettes(sets, max_pals=max_pals)
    lookup = [{c: i + 1 for i, c in enumerate(p)} for p in pals]
    tiles = [bytes(32)]              # tile 0 is always blank
    index = {bytes(32): 0}
    mp = []
    for t, s in zip(tiles_rgba, sets):
        if not s:
            mp.append(tile_base)
            continue
        pi = next(i for i, p in enumerate(pals) if s <= set(p))
        lk = lookup[pi]
        idx = np.zeros((8, 8), np.uint8)
        for y in range(8):
            for x in range(8):
                if t[y, x, 3]:
                    idx[y, x] = lk[tuple(int(v) for v in t[y, x, :3])]
        entry = None
        variants = [(idx, 0)]
        if flips:
            variants += [(idx[:, ::-1], 1 << 10), (idx[::-1], 1 << 11), (idx[::-1, ::-1], 3 << 10)]
        for v, flag in variants:
            key = tile4(v)
            if key in index:
                entry = index[key] | flag
                break
        if entry is None:
            key = tile4(idx)
            index[key] = len(tiles)
            entry = len(tiles)
            tiles.append(key)
        mp.append(((entry & 0x3FF) + tile_base) | (entry & 0xC00) | ((pal_bank + pi) << 12))
    palettes = [[0] + [bgr555(c) for c in p] + [0] * (15 - len(p)) for p in pals]
    return {'tiles': b''.join(tiles), 'map': mp, 'w': w // 8, 'h': h // 8,
            'palettes': palettes, 'ntiles': len(tiles)}


def obj(img, lookup):
    """Sprite tiles in 1D order. lookup: color tuple -> palette index."""
    h, w = img.shape[:2]
    out = bytearray()
    for ty in range(0, h, 8):
        for tx in range(0, w, 8):
            idx = np.zeros((8, 8), np.uint8)
            t = img[ty:ty + 8, tx:tx + 8]
            for y in range(8):
                for x in range(8):
                    if t[y, x, 3]:
                        idx[y, x] = lookup[tuple(int(v) for v in t[y, x, :3])]
            out += tile4(idx)
    return bytes(out)


def palette_of(img, first=1):
    """Build a lookup and a 16-entry BGR555 palette from an image's colors."""
    cs = sorted({tuple(int(v) for v in p) for p in img[..., :3][img[..., 3] > 0]})
    if len(cs) > 16 - first:
        raise ValueError(f'{len(cs)} colors do not fit one palette')
    lookup = {c: i + first for i, c in enumerate(cs)}
    pal = [0] * 16
    for c, i in lookup.items():
        pal[i] = bgr555(c)
    return lookup, pal


class CWriter:
    def __init__(self, name):
        self.name = name
        self.c = [f'/* Generated by tools/ from the art pipeline. Do not edit. */\n#include "{name}.h"\n']
        self.h = [f'/* Generated. Do not edit. */\n#ifndef {name.upper()}_H\n#define {name.upper()}_H\n'
                  '#include <stdint.h>\n']

    def u16(self, ident, values):
        body = ',\n'.join('    ' + ', '.join(f'0x{v:04X}' for v in values[i:i + 12])
                          for i in range(0, len(values), 12))
        self.c.append(f'const uint16_t {ident}[{len(values)}] __attribute__((aligned(4))) = {{\n{body}\n}};\n')
        self.h.append(f'extern const uint16_t {ident}[{len(values)}];\n')

    def u32_bytes(self, ident, data):
        assert len(data) % 4 == 0
        vals = [int.from_bytes(data[i:i + 4], 'little') for i in range(0, len(data), 4)]
        body = ',\n'.join('    ' + ', '.join(f'0x{v:08X}' for v in vals[i:i + 8])
                          for i in range(0, len(vals), 8))
        self.c.append(f'const uint32_t {ident}[{len(vals)}] = {{\n{body}\n}};\n')
        self.h.append(f'extern const uint32_t {ident}[{len(vals)}];\n')

    def define(self, ident, value):
        self.h.append(f'#define {ident} {value}\n')

    def save(self, outdir):
        import os
        os.makedirs(outdir, exist_ok=True)
        self.h.append('#endif\n')
        with open(os.path.join(outdir, self.name + '.c'), 'w') as f:
            f.write('\n'.join(self.c))
        with open(os.path.join(outdir, self.name + '.h'), 'w') as f:
            f.write(''.join(self.h))
