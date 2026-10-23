"""Exports the web game's generated art into OUTDIR (default public/gen).

Milestone 1: the app icons, made from the real squishy art (a Strawberry
Bunny drawn at 64 px by squishies.render, scaled up with sharp pixels on a
pastel tile). Milestone 2 adds the map, sprite and font atlases.

Usage: python3 tools/export_web.py public/gen
"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import squishies  # noqa: E402

BG_TOP = (207, 233, 255)     # sky, as on the tap test
BG_BOTTOM = (253, 227, 239)


def tile(size, art_scale):
    """A size x size icon: a soft sky to pink background, the bunny centred."""
    t = np.linspace(0, 1, size)[:, None, None]
    bg = (np.array(BG_TOP) * (1 - t) + np.array(BG_BOTTOM) * t).astype(np.uint8)
    img = Image.fromarray(np.repeat(bg, size, axis=1), 'RGB').convert('RGBA')
    art = squishies.render(squishies.SPECIES['bunny'], 'strawberry', 64)
    sprite = Image.fromarray(art, 'RGBA')
    sprite = sprite.resize((64 * art_scale, 64 * art_scale), Image.NEAREST)
    x = (size - sprite.width) // 2
    y = (size - sprite.height) // 2 + size // 40
    img.alpha_composite(sprite, (x, y))
    return img.convert('RGB')


def main(out):
    os.makedirs(out, exist_ok=True)
    icons = {
        'apple-touch-icon.png': (180, 2),
        'icon-192.png': (192, 2),
        'icon-512.png': (512, 6),
        'icon-maskable-512.png': (512, 5),   # inside the 80% safe circle
    }
    for name, (size, k) in icons.items():
        tile(size, k).save(os.path.join(out, name), optimize=True)
        print(f'wrote {name} {size}x{size}')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'public/gen')
