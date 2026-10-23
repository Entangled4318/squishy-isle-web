"""Exports the web game's art into OUTDIR (default public/gen).

The art functions are the GBA game's (same pixels), but the output is RGBA
PNG instead of 15-bit tiles:
  atlas-N.png       sprites packed into 1024 x 1024 pages
  screens/*.png     whole screens (shelf pages, close-up, open, title, rooms, letter)
  maps/*.png        each area's ground, overlay and glint mask
  art.json          index: sprite rects, screens, maps with their data, font,
                    names, layout constants
  music.json        the songs (music.py), for milestone 3
  icon PNGs         the app icons

Usage: python3 tools/export_web.py public/gen
"""
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import areas  # noqa: E402
import gifts  # noqa: E402
import mockups  # noqa: E402
import npc  # noqa: E402
import props  # noqa: E402
import rooms  # noqa: E402
import squishies  # noqa: E402
import squishy_export  # noqa: E402
from font import G as FONT  # noqa: E402
from gba import blit, new, rgb15  # noqa: E402
from palette import C, FLAVOR_NAME, FLAVOR_ORDER  # noqa: E402
from pip import frames as pip_frames  # noqa: E402
from squishies import AREAS, SPECIES  # noqa: E402

# The GBA exporter's builders and layout numbers, reused as they are.
from export_game import (  # noqa: E402
    COUNT_PILL_W, METER_DX, METER_DY, METER_H, METER_HX, METER_HY, METER_W, PILL_W,
    closeup_background, letter_parts, open_background, title_parts)

ATLAS = 1024
PAD = 1
AREA_BUILDERS = [areas.meadow, areas.woods, areas.shore, areas.clouds]
CONTAINER_COLORS = {
    'box': ('pink', 'lav', 'mint', 'yellow', 'sky'),
    'acorn': ('cream', 'pink', 'mint', 'lav', 'gold'),
    'shell': ('pink', 'peach', 'mint', 'lav', 'yellow'),
    'capsule': tuple(props.CAPSULE_COLORS),
}


def rgba(img):
    return np.ascontiguousarray(img[..., :4]).astype(np.uint8)


def save_png(img, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.fromarray(rgba(img), 'RGBA').save(path, optimize=True)


class Sheet:
    """Collects named sprites and packs them into atlas pages (shelf packing,
    tallest first, 1 px transparent gap so nothing bleeds)."""

    def __init__(self):
        self.items = {}

    def add(self, name, img):
        if name in self.items:
            raise ValueError(f'sprite {name} added twice')
        img = rgba(img)
        if img.shape[0] == 0 or img.shape[1] == 0:
            raise ValueError(f'sprite {name} is empty')
        self.items[name] = img

    def pack(self, out):
        order = sorted(self.items, key=lambda n: (-self.items[n].shape[0], -self.items[n].shape[1], n))
        pages, rects = [], {}
        page = None
        x = y = row_h = 0
        for name in order:
            img = self.items[name]
            h, w = img.shape[:2]
            if w + PAD > ATLAS or h + PAD > ATLAS:
                raise ValueError(f'sprite {name} ({w}x{h}) is larger than an atlas page')
            if page is None or x + w + PAD > ATLAS:
                x, y, row_h = 0, y + row_h, 0
            if page is None or y + h + PAD > ATLAS:
                page = np.zeros((ATLAS, ATLAS, 4), np.uint8)
                pages.append(page)
                x = y = row_h = 0
            page[y:y + h, x:x + w] = img
            rects[name] = [len(pages) - 1, x, y, w, h]
            x += w + PAD
            row_h = max(row_h, h + PAD)
        files = []
        for i, p in enumerate(pages):
            used = int(np.nonzero(p[..., 3].any(axis=1))[0][-1]) + 1
            f = f'atlas-{i}.png'
            save_png(p[:used], os.path.join(out, f))
            files.append(f)
        return files, rects


def flavor_render(sp, flavor, size, frame):
    """A squishy frame in one flavor, in the ROM's look (two-shade accents),
    with the GBA exporter's squash narrowing (squishy_export.role_render)."""
    expr, (sx, sy) = squishy_export.FRAMES[frame]
    squishies.ROM_MODE = True
    try:
        im = squishies.render(SPECIES[sp], flavor, size, expr=expr, squash=(sx, sy))
        while not squishy_export._fits(im, size) and sx > 0.9:
            sx -= 0.01
            im = squishies.render(SPECIES[sp], flavor, size, expr=expr, squash=(sx, sy))
        return im
    finally:
        squishies.ROM_MODE = False


def silhouette(sp, size, row):
    """A friend not found yet: the shelf row's tint, the outline in its rim color."""
    role = squishy_export.role_render(sp, size, 'idle')
    fill, rim = mockups.SHELF_SIL[row]
    out = new(size, size)
    m = role[..., 3] > 0
    out[m, :3] = rgb15(fill)
    out[m, 3] = 255
    outline = m & np.all(role[..., :3] == np.array(squishy_export.ROLE[5]), axis=-1)
    out[outline, :3] = rgb15(rim)
    return out


def pad_to(img, w, h):
    out = new(w, h)
    blit(out, img, 0, 0)
    return out


def squishy_sprites(sheet):
    for ai, area in enumerate(AREAS):
        for row, sp in enumerate(area[3]):
            for size, frames in squishy_export.SIZE_FRAMES.items():
                for fr in frames:
                    for fl in FLAVOR_ORDER:
                        sheet.add(f'sq/{sp}/{fl}/{size}/{fr}', flavor_render(sp, fl, size, fr))
                sheet.add(f'sq/{sp}/sil/{size}', silhouette(sp, size, row))
            for fl in FLAVOR_ORDER:
                sheet.add(f'gift/{sp}/{fl}', gifts.preview_rgba(sp, fl))


def container_sprites(sheet):
    kinds64 = {'box': props.box64, 'acorn': props.acorn64, 'shell': props.shell64, 'capsule': props.capsule64}
    for key, _, kind, _ in AREAS:
        for ci, color in enumerate(CONTAINER_COLORS[kind]):
            for part in ('body', 'open', 'lid'):
                sheet.add(f'cont64/{key}/{ci}/{part}', kinds64[kind](color, part))
            if kind == 'box':
                small = props.box16(color)
            elif kind == 'acorn':
                small = props.acorn16(color)
            elif kind == 'shell':
                small = props.shell(color, 16)
            else:
                lt, base, dk = props.CAPSULE_COLORS[color]
                small = props.capsule16(base, dk, lt)
            sheet.add(f'cont16/{key}/{ci}', pad_to(small, 16, 16))


def ui_sprites(sheet):
    sheet.add('abig/0', props.a_button_big(False))
    sheet.add('abig/1', props.a_button_big(True))
    x2 = lambda im: np.repeat(np.repeat(im, 2, axis=0), 2, axis=1)  # noqa: E731
    sheet.add('openui/heart_on', x2(props.HEART))
    sheet.add('openui/heart_off', x2(mockups.hearts_progress(0, 1)))
    sheet.add('openui/arc', mockups.motion_arcs('left'))
    sheet.add('openui/puff', mockups.puff())
    for i in range(12):
        sheet.add(f'confetti/{i}', props.confetti_piece(i))
    sheet.add('star16', props.SPARK_HUGE)
    sheet.add('frame', mockups.selection_frame())
    for name, sp in (('tiny', props.SPARK_TINY), ('small', props.SPARK_SMALL), ('big', props.SPARK_BIG)):
        sheet.add(f'spark/{name}', sp)
    sheet.add('heart8', props.HEART)
    sheet.add('heart_big', props.HEART_BIG)
    for k in props.SNACK_ORDER:
        sheet.add(f'snack/{k}', props.snack16(k))
    sheet.add('envelope16', props.envelope16())
    sheet.add('flag/up', props.mail_flag(True))
    sheet.add('flag/down', props.mail_flag(False))
    for i, tw in enumerate(props.MAP_TWINKLES):
        sheet.add(f'twinkle/{i}', tw)
    sheet.add('envelope64/0', props.envelope64(False))
    sheet.add('envelope64/1', props.envelope64(True))
    sheet.add('shadow64', props.shadow(64, 8, rgb15('#c9789a')))
    sheet.add('shadow12', props.shadow(12, 4, rgb15('#6a5a88')))
    sheet.add('abubble', props.a_button())
    for d in ('right', 'up', 'upright'):
        sheet.add(f'arrow/{d}', props.guide_arrow(d))
    for key, _, kind, _ in AREAS:
        sheet.add(f'icon12/{key}', props.icon12(kind))
        pill = new(64, 16)
        blit(pill, props.pill(COUNT_PILL_W, 15, C['ui_bg'], C['ui_pk'], C['ui_ink'], C['white']), 0, 1)
        blit(pill, props.icon12(kind), 4, 2)
        sheet.add(f'count_pill/{key}', pill[:, :COUNT_PILL_W + 1])
    meter_sprites(sheet)


def meter_sprites(sheet):
    """Momo's heart meter (GBA step 8.4): the bubble with 10 empty hearts, a
    tail toward Momo, and the filled heart drawn over each found friend."""
    meter = new(64, 32)
    blit(meter, props.pill(METER_W, METER_H, C['ui_bg'], C['ui_pk'], C['ui_ink'], C['white'], r=5), 0, 0)
    heart_k = rgb15('#c25a82')
    empty = props.HEART_BIG.copy()
    for yy in range(empty.shape[0]):
        for xx in range(empty.shape[1]):
            if empty[yy, xx, 3]:
                empty[yy, xx, :3] = rgb15('#d98fb0') if tuple(empty[yy, xx, :3]) == heart_k else C['ui_bg']
    for n in range(10):
        blit(meter, empty, METER_HX + (n % 5) * METER_DX, METER_HY + (n // 5) * METER_DY)
    sheet.add('meter/body', meter[:METER_H + 1, :METER_W + 1])
    tail = new(7, 4)
    for k, row in enumerate(('kbbbbbk', '.kbbbk.', '..kbk..', '...k...')):
        for xx, ch in enumerate(row):
            if ch != '.':
                tail[k, xx, :3] = C['ui_ink'] if ch == 'k' else C['ui_bg']
                tail[k, xx, 3] = 255
    sheet.add('meter/tail', tail)


def character_sprites(sheet):
    pf = pip_frames()
    for k in ('down0', 'down1', 'down2', 'up0', 'up1', 'up2', 'right0', 'right1'):
        sheet.add(f'pip/{k}', pf[k])
    mf = npc.frames()
    sheet.add('momo/sleep', mf['sleep'])
    sheet.add('momo/awake', mf['awake'])
    for i, z in enumerate(npc.zz()):
        sheet.add(f'momo/z{i}', z)
    sheet.add('momo/blanket', npc.blanket())


def logo_sprites(sheet):
    bg_img, letters = title_parts()
    table = []
    for i, (img, x, y) in enumerate(letters):
        sheet.add(f'logo/{i}', img)
        table.append({'sprite': f'logo/{i}', 'x': int(x), 'y': int(y)})
    return bg_img, table


def area_data(a, index, out):
    """One area's images and data. Field names follow the GBA AreaMap."""
    save_png(a.ground, os.path.join(out, f'maps/{a.name}-ground.png'))
    save_png(a.overlay, os.path.join(out, f'maps/{a.name}-overlay.png'))
    glint = C[a.shimmer]
    m = (a.ground[..., 3] > 0) & np.all(a.ground[..., :3] == np.array(glint), axis=-1)
    mask = new(a.w, a.h)
    mask[m] = (255, 255, 255, 255)
    save_png(mask, os.path.join(out, f'maps/{a.name}-glint.png'))
    lo, hi = C[a.shimmer], C[a.shimmer.replace('_lt', '_hi')]
    mid = tuple((x + y) // 2 for x, y in zip(lo, hi))
    solid = a.solid.astype(np.uint8)
    return {
        'index': index,
        'name': a.name,
        'w': a.w,
        'h': a.h,
        'ground': f'maps/{a.name}-ground.png',
        'overlay': f'maps/{a.name}-overlay.png',
        'glint': f'maps/{a.name}-glint.png',
        'glintCycle': ['#%02x%02x%02x' % tuple(c) for c in (lo, mid, hi, mid)],
        'cell': areas.CELL,
        'cols': int(solid.shape[1]),
        'rows': int(solid.shape[0]),
        'solid': ''.join('1' if v else '0' for v in solid.flatten()),
        'spawn': list(a.spawn),
        'spots': [list(p) for p in a.spots],
        'firstSpot': a.first_spot,
        'pen': list(a.pen) if a.pen else None,
        'sign': list(a.sign) if a.sign else None,
        'signs': [list(map(int, s)) for s in a.signs],
        'doors': [list(d[:4]) for d in a.doors],
        'exits': [list(e) for e in a.exits],
        'gates': [list(g) for g in a.gates],
        'mailbox': list(a.mailbox) if a.mailbox else None,
        'basket': list(a.basket) if a.basket else None,
        'momo': list(a.momo) if a.momo else None,
    }


# Glyphs the GBA never printed, for grown-up pages on the web.
EXTRA_GLYPHS = {
    '(': ['..#', '.#.', '#..', '#..', '#..', '.#.', '..#'],
    ')': ['#..', '.#.', '..#', '..#', '..#', '.#.', '#..'],
    '_': ['.....', '.....', '.....', '.....', '.....', '.....', '#####'],
}


def font_data():
    glyphs = dict(FONT)
    for ch, rows in EXTRA_GLYPHS.items():
        glyphs.setdefault(ch, rows)
    return {'height': 7, 'descent': 2, 'spacing': 1, 'glyphs': glyphs}


def icons(out):
    """App icons: a Strawberry Bunny at 64 px, scaled up sharp on a sky-to-pink tile."""
    top, bottom = (207, 233, 255), (253, 227, 239)
    art = Image.fromarray(rgba(squishies.render(SPECIES['bunny'], 'strawberry', 64)), 'RGBA')
    for name, size, k in (('apple-touch-icon.png', 180, 2), ('icon-192.png', 192, 2),
                          ('icon-512.png', 512, 6), ('icon-maskable-512.png', 512, 5)):
        t = np.linspace(0, 1, size)[:, None, None]
        bg = (np.array(top) * (1 - t) + np.array(bottom) * t).astype(np.uint8)
        img = Image.fromarray(np.repeat(bg, size, axis=1), 'RGB').convert('RGBA')
        sprite = art.resize((64 * k, 64 * k), Image.NEAREST)
        img.alpha_composite(sprite, ((size - sprite.width) // 2, (size - sprite.height) // 2 + size // 40))
        img.convert('RGB').save(os.path.join(out, name), optimize=True)


def music(out):
    import music as m
    m.export(out)
    for f in ('music_data.c', 'music_data.h'):
        p = os.path.join(out, f)
        if os.path.exists(p):
            os.remove(p)
    os.replace(os.path.join(out, 'music_songs.json'), os.path.join(out, 'music.json'))


def main(out):
    os.makedirs(out, exist_ok=True)
    icons(out)
    sheet = Sheet()
    squishy_sprites(sheet)
    container_sprites(sheet)
    ui_sprites(sheet)
    character_sprites(sheet)
    title_bg, logo = logo_sprites(sheet)

    screens = {
        'title': title_bg,
        'closeup': closeup_background(),
        'open': open_background(),
    }
    back, card = letter_parts()
    screens['letter_back'] = back
    screens['letter_card'] = card
    for i in range(4):
        screens[f'shelf{i}'] = mockups.shelf_background(i, pill_w=PILL_W)
        screens[f'room{i}'] = rooms.room_background(AREAS[i][0])
    for name, img in screens.items():
        save_png(img, os.path.join(out, f'screens/{name}.png'))

    maps = [area_data(b(), i, out) for i, b in enumerate(AREA_BUILDERS)]
    for i, m in enumerate(maps):
        if m['name'] != AREAS[i][0]:
            raise ValueError(f'area maps must follow the play order: {m["name"]} at {i}')

    files, rects = sheet.pack(out)
    index = {
        'atlases': files,
        'sprites': rects,
        'screens': {k: f'screens/{k}.png' for k in screens},
        'maps': maps,
        'logo': logo,
        'font': font_data(),
        'names': {
            'areas': [{'key': a[0], 'name': a[1], 'container': a[2], 'species': a[3]} for a in AREAS],
            'species': {k: SPECIES[k].name for a in AREAS for k in a[3]},
            'flavors': FLAVOR_ORDER,
            'flavorNames': [FLAVOR_NAME[f] for f in FLAVOR_ORDER],
            'snacks': list(props.SNACK_ORDER),
            'containerColors': {a[0]: list(CONTAINER_COLORS[a[2]]) for a in AREAS},
        },
        'layout': {
            'shelf': dict(mockups.SHELF, pillW=PILL_W),
            'room': rooms.ROOM,
            'meter': {'w': METER_W, 'h': METER_H, 'hx': METER_HX, 'hy': METER_HY, 'dx': METER_DX, 'dy': METER_DY},
            'countPillW': COUNT_PILL_W,
            'pipFeetRow': max(int(np.nonzero(f[..., 3].any(axis=1))[0][-1]) for f in pip_frames().values()),
            'squishyFrames': {str(k): list(v) for k, v in squishy_export.SIZE_FRAMES.items()},
        },
    }
    with open(os.path.join(out, 'art.json'), 'w') as f:
        json.dump(index, f, separators=(',', ':'))
    music(out)
    total = sum(os.path.getsize(os.path.join(dp, fn)) for dp, _, fns in os.walk(out) for fn in fns)
    print(f'{len(rects)} sprites on {len(files)} atlas pages, {len(screens)} screens, '
          f'{len(maps)} maps; {total // 1024} KB in {out}')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'public/gen')
