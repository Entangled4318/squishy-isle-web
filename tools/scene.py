"""Tiny GBA-style scene: BG layers + OBJ list, with hardware limit checks."""
import numpy as np

from gba import new, blit, blit_blend, colors_of, pack_tile_palettes, W, H


def unique_tiles(layer):
    """Count unique 8x8 tiles, treating H/V flips as the same tile."""
    seen = set()
    h, w = layer.shape[:2]
    for ty in range(0, h, 8):
        for tx in range(0, w, 8):
            t = layer[ty:ty + 8, tx:tx + 8]
            if not t[..., 3].any():
                continue
            key = min(t.tobytes(), t[:, ::-1].tobytes(), t[::-1].tobytes(), t[::-1, ::-1].tobytes())
            seen.add(key)
    return len(seen)


class Scene:
    def __init__(self, name):
        self.name = name
        self.bgs = {}          # name -> (priority, rgba 240x160 or larger)
        self.objs = []         # (sort_key, img, x, y, mode)
        self.backdrop = (0, 0, 0)

    def bg(self, name, prio, img):
        self.bgs[name] = (prio, img)

    def obj(self, img, x, y, key=None, blend=None):
        """blend=(eva, evb) makes a semi-transparent OBJ (e.g. shadows)."""
        k = y + img.shape[0] if key is None else key
        self.objs.append((k, img, int(x), int(y), blend))

    def render(self, check=True):
        out = new(W, H)
        out[..., :3] = self.backdrop
        out[..., 3] = 255
        # BGs back to front (higher prio number = further back)
        layers = sorted(self.bgs.items(), key=lambda kv: -kv[1][0])
        report = []
        objs = sorted(self.objs, key=lambda o: o[0])
        # objects are drawn between BGs by priority; our scenes put OBJ above
        # every BG except the ones flagged 'over' (priority 0 layers)
        for name, (prio, img) in layers:
            if prio == 0:
                continue
            blit(out, img[:H, :W], 0, 0)
        for k, img, x, y, bl in objs:
            if bl:
                blit_blend(out, img, x, y, *bl)
            else:
                blit(out, img, x, y)
        for name, (prio, img) in layers:
            if prio == 0:
                blit(out, img[:H, :W], 0, 0)
        if check:
            for name, (prio, img) in layers:
                pals = pack_tile_palettes(img[:H, :W])
                report.append(f'BG {name}: {unique_tiles(img[:H, :W])} tiles, {len(pals)} palettes')
            ncols = [len(colors_of(o[1])) for o in self.objs]
            if ncols and max(ncols) > 15:
                raise ValueError(f'{self.name}: OBJ with {max(ncols)} colors')
            # pack every sprite's colour set into the 16 OBJ palettes
            sets = sorted({frozenset(colors_of(o[1])) for o in self.objs}, key=len, reverse=True)
            pals = []
            for cs in sets:
                if any(cs <= p for p in pals):
                    continue
                fit = [p for p in pals if len(p | cs) <= 15]
                if fit:
                    p = min(fit, key=lambda p: len(p | cs))
                    pals.remove(p)
                    pals.append(p | cs)
                else:
                    pals.append(set(cs))
            if len(pals) > 16:
                raise ValueError(f'{self.name}: needs {len(pals)} OBJ palettes')
            bg_pals = sum(len(pack_tile_palettes(img[:H, :W])) for _, (prio, img) in layers)
            if bg_pals > 16:
                raise ValueError(f'{self.name}: needs {bg_pals} BG palettes')
            if len(layers) > 4:
                raise ValueError(f'{self.name}: {len(layers)} BG layers')
            report.append(f'OBJ: {len(self.objs)} sprites, {len(pals)}/16 palettes; BG palettes {bg_pals}/16')
            # scanline sprite pixel budget (approx. 954 cycles ~ 119 16px sprites);
            # we only warn on very dense lines
        return out, report
