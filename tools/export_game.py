"""Export all game art to C. Usage: python3 export_game.py OUTDIR

Writes OUTDIR/game_assets.c/.h and preview PNGs of every BG screen.
"""
import os
import sys

import numpy as np

from gba import new, blit, rgb15, save_scaled, W, H
from palette import C, FLAVOR_ORDER, FLAVOR_NAME
from gbaconv import bg, obj, bgr555, CWriter
from squishies import AREAS, SPECIES
import squishy_export
import mockups
import props
import areas
import world
import npc
import rooms
import gifts
from pip import frames as pip_frames

OUT = sys.argv[1] if len(sys.argv) > 1 else 'build'
PILL_W = 104          # name pill on the shelf (top right)
COUNT_PILL_W = 52     # found counter pill (top right of the world)
METER_W, METER_H = 57, 28     # Momo's heart meter bubble (8.4): 2 rows of 5 hearts (9 px), 10 and 11 px apart
METER_HX, METER_HY, METER_DX, METER_DY = 4, 4, 10, 11


def palette_and_lookup(images):
    cs = set()
    for im in images:
        cs |= {tuple(int(v) for v in p) for p in im[..., :3][im[..., 3] > 0]}
    cs = sorted(cs)
    if len(cs) > 15:
        raise ValueError(f'{len(cs)} colors')
    lookup = {c: i + 1 for i, c in enumerate(cs)}
    pal = [0] * 16
    for c, i in lookup.items():
        pal[i] = bgr555(c)
    return lookup, pal


def pad_to(img, w, h):
    out = new(w, h)
    blit(out, img, 0, 0)
    return out


def map_rows(m, w_tiles, h_tiles, stride=32):
    rows = []
    for r in range(h_tiles):
        rows += m[r * w_tiles:(r + 1) * w_tiles] + [0] * (stride - w_tiles)
    return rows


def export_multi_bg(cw, prefix, images, max_pals=15):
    """Several full-screen images sharing one tile set and palette set."""
    stack = np.concatenate(images, axis=0)
    b = bg(stack, pal_bank=0, max_pals=max_pals)
    th = H // 8
    cw.u32_bytes(f'{prefix}_tiles', b['tiles'])
    cw.u16(f'{prefix}_pal', [c for p in b['palettes'] for c in p])
    for i in range(len(images)):
        part = b['map'][i * th * 30:(i + 1) * th * 30]
        cw.u16(f'{prefix}_map{i}', map_rows(part, 30, th))
    cw.define(f'{prefix.upper()}_PALS', len(b['palettes']))
    for i, im in enumerate(images):
        save_scaled(im, os.path.join(OUT, f'preview_{prefix}{i}.png'), 2)
    print(f'{prefix}: {b["ntiles"]} tiles, {len(b["palettes"])} palettes')
    return b


def closeup_background():
    img = mockups.sunburst(rgb15('#fff6d8'), rgb15('#ffeab8'), rgb15('#fffbee'), cy=74, glow_r=48)
    blit(img, mockups.stage(), 68, 110)
    p = props.pill(128, 15, C['ui_bg'], C['ui_pk'], C['ui_ink'], C['white'])
    blit(img, p, 56, 141)
    return img


def open_background():
    img = mockups.sunburst(rgb15('#f3edff'), rgb15('#e7ddfb'), rgb15('#fbf8ff'), cy=74, glow_r=48)
    blit(img, mockups.stage(), 68, 110)
    return img


def letter_parts():
    """Letter scene: a pink polka-dot backdrop, and a cream card (transparent
    around it) with a scalloped pink edge, ruled lines under the text, a
    round frame for the friend's portrait and a heart stamp."""
    ys, xs = np.mgrid[0:H, 0:W]
    back = new(W, H)
    back[..., 3] = 255
    back[..., :3] = rgb15('#fbe4ee')
    back[..., :3][((xs % 16) == 3) & ((ys % 16) == 4)] = rgb15('#f6d0e0')
    back[..., :3][((xs % 16) == 11) & ((ys % 16) == 12)] = rgb15('#f6d0e0')
    card = new(W, H)
    x0, y0, x1, y1 = 12, 8, 228, 152
    paper, rule, band, ink = rgb15('#fffaf0'), rgb15('#f6dccf'), rgb15('#ffd2df'), rgb15('#e088a8')
    inside = (xs >= x0) & (xs < x1) & (ys >= y0) & (ys < y1)
    # scalloped edge: bumps every 8 px around the card
    bump = np.zeros_like(inside)
    for cx in range(x0 + 4, x1, 8):
        for cy in (y0, y1 - 1):
            bump |= (xs - cx) ** 2 + (ys - cy) ** 2 <= 16
    for cy in range(y0 + 4, y1, 8):
        for cx in (x0, x1 - 1):
            bump |= (xs - cx) ** 2 + (ys - cy) ** 2 <= 16
    shape = inside | bump
    card[shape, :3] = band
    card[shape, 3] = 255
    inner = (xs >= x0 + 4) & (xs < x1 - 4) & (ys >= y0 + 4) & (ys < y1 - 4)
    card[inner, :3] = paper
    out = np.zeros_like(shape)
    out[1:] |= shape[:-1]; out[:-1] |= shape[1:]; out[:, 1:] |= shape[:, :-1]; out[:, :-1] |= shape[:, 1:]
    out &= ~shape
    card[out, :3] = ink
    card[out, 3] = 255
    edge = inner & ~((xs >= x0 + 5) & (xs < x1 - 5) & (ys >= y0 + 5) & (ys < y1 - 5))
    card[edge, :3] = rgb15('#f5c4d4')
    for y in (38, 60, 74, 100, 114):                   # ruled lines under the text (see letter.c)
        card[y, 110:214, :3] = rule
    # round frame for the portrait: soft pink disc with a dotted rim
    d2 = (xs - 60) ** 2 + (ys - 80) ** 2
    card[(d2 <= 36 * 36) & inner, :3] = rgb15('#ffeef3')
    ring = (d2 <= 37 * 37) & (d2 > 35 * 35) & (((xs + ys) // 3) % 2 == 0)
    card[ring, :3] = rgb15('#f5b8cc')
    # heart stamp, top right
    sx, sy = 196, 14
    card[sy:sy + 24, sx:sx + 20, :3] = rgb15('#ffffff')
    for x in range(sx, sx + 20, 2):
        card[sy, x, :3] = paper
        card[sy + 23, x, :3] = paper
    for y in range(sy, sy + 24, 2):
        card[y, sx, :3] = paper
        card[y, sx + 19, :3] = paper
    card[sy + 3:sy + 21, sx + 3:sx + 17, :3] = rgb15('#ffe0ea')
    blit(card, props.HEART_BIG, sx + 6, sy + 8)
    # small hearts in the bottom corners
    blit(card, props.HEART, x0 + 8, y1 - 16)
    blit(card, props.HEART, x1 - 15, y1 - 16)
    return back, card


def title_parts():
    """Title screen from the mockup: one flat background (sky, island and the
    cast's shadows) plus the logo letters as separate bouncing sprites."""
    sc = mockups.scene_title()
    bg_img = new(W, H)
    for name in ('sky', 'island'):
        blit(bg_img, sc.bgs[name][1], 0, 0)
    for key, img, x, y, mode in sc.objs:        # shadows only (blended in the mockup)
        if mode is not None and key is not None and key < 200:
            sh = img.copy()
            m = sh[..., 3] > 0
            under = bg_img[y:y + sh.shape[0], x:x + sh.shape[1], :3].astype(int)
            mix = (under * 11 + sh[..., :3].astype(int) * 5) // 16
            region = bg_img[y:y + sh.shape[0], x:x + sh.shape[1]]
            region[m, :3] = (mix[m] // 8 * 8).astype(np.uint8)
    letters = []
    for word_, h, cols, y in (('SQUISHY', 28, ['strawberry', 'sparkle', 'matcha', 'sky', 'taro', 'peach', 'strawberry'], 2),
                              ('ISLE', 22, ['sky', 'taro', 'strawberry', 'matcha'], 45)):
        for img, x, yy in mockups.logo_letters(word_, h, cols, 121 if word_ == 'SQUISHY' else 120, y):
            ys, xs = np.nonzero(img[..., 3])
            crop = img[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
            letters.append((crop, x + xs.min(), yy + ys.min()))
    return bg_img, letters


def main():
    os.makedirs(OUT, exist_ok=True)
    cw = CWriter('game_assets')
    cw.h.append('\ntypedef struct {\n    const char *name;\n    uint8_t area;\n'
                '    const uint32_t *t16, *t32, *t64;\n} SpeciesInfo;\n\n')

    # ---------------- squishies
    species_rows = []
    for ai, area in enumerate(AREAS):
        ex = squishy_export.area_export(area[0])
        cw.u16(f'sq_pal_{area[0]}', [c for fl in FLAVOR_ORDER for c in ex['palettes'][fl]])
        for sp in area[3]:
            for size in (16, 32, 64):
                cw.u32_bytes(f'sq_{sp}_{size}', b''.join(ex['tiles'][sp][size]))
            species_rows.append((sp, ai))
    sil = squishy_export.area_export('meadow')['silhouettes']
    cw.u16('sq_sil_pal', [c for r in range(4) for c in sil[r]])
    cw.c.append('const SpeciesInfo species_info[16] = {\n' + ',\n'.join(
        f'    {{"{SPECIES[sp].name}", {ai}, sq_{sp}_16, sq_{sp}_32, sq_{sp}_64}}' for sp, ai in species_rows)
        + '\n};\n')
    cw.h.append('extern const SpeciesInfo species_info[16];\n')
    cw.c.append('const uint16_t *const sq_area_pals[4] = {' +
                ', '.join(f'sq_pal_{a[0]}' for a in AREAS) + '};\n')
    cw.h.append('extern const uint16_t *const sq_area_pals[4];\n')
    cw.c.append('const char *const flavor_names[5] = {' +
                ', '.join(f'"{FLAVOR_NAME[f]}"' for f in FLAVOR_ORDER) + '};\n')
    cw.h.append('extern const char *const flavor_names[5];\n')
    cw.c.append('const char *const area_names[4] = {' + ', '.join(f'"{a[1]}"' for a in AREAS) + '};\n')
    cw.h.append('extern const char *const area_names[4];\n')
    for k, v in (('SQ_FRAMES16_IDLE', 0), ('SQ_FRAMES16_SQUISH', 1), ('SQ32_IDLE', 0), ('SQ32_OPEN', 1),
                 ('SQ64_IDLE', 0), ('SQ64_BLINK', 1), ('SQ64_OPEN', 2), ('SQ64_SQUISH', 3)):
        cw.define(k, v)

    # ---------------- shelf pages (one per active tab)
    pages = [mockups.shelf_background(i, pill_w=PILL_W) for i in range(4)]
    export_multi_bg(cw, 'shelf', pages)
    for k, v in mockups.SHELF.items():
        cw.define(f'SHELF_{k.upper()}', v)
    cw.define('SHELF_PILL_W', PILL_W)

    # ---------------- close-up screen
    export_multi_bg(cw, 'closeup', [closeup_background()])

    # ---------------- open screen: box in 5 colors (closed body, open body, lid)
    export_multi_bg(cw, 'openbg', [open_background()])
    # each area's container at 64 px in its 5 colors (the map's color order):
    # closed body, open body, lid (64 tiles each), one palette per color
    kinds = {'box': (props.box64, ('pink', 'lav', 'mint', 'yellow', 'sky')),
             'acorn': (props.acorn64, ('cream', 'pink', 'mint', 'lav', 'gold')),
             'shell': (props.shell64, ('pink', 'peach', 'mint', 'lav', 'yellow')),
             'capsule': (props.capsule64, tuple(props.CAPSULE_COLORS))}
    names, sheet = [], []
    for key, _, kind, _ in AREAS:
        fn, colors = kinds[kind]
        for color in colors:
            parts = [fn(color, 'body'), fn(color, 'open'), fn(color, 'lid')]
            lk, pal = palette_and_lookup(parts)
            cw.u32_bytes(f'cont64_{key}_{color}_tiles', b''.join(obj(p, lk) for p in parts))
            cw.u16(f'cont64_{key}_{color}_pal', pal)
            names.append(f'cont64_{key}_{color}')
            sheet.append(fn(color, 'all'))
    cw.h.append('extern const uint32_t *const cont64_tiles[20];   /* area * 5 + color */\n'
                'extern const uint16_t *const cont64_pal[20];\n')
    cw.c.append('const uint32_t *const cont64_tiles[20] = {' + ', '.join(f'{n}_tiles' for n in names) + '};\n')
    cw.c.append('const uint16_t *const cont64_pal[20] = {' + ', '.join(f'{n}_pal' for n in names) + '};\n')
    save_scaled(np.concatenate([np.concatenate(sheet[i:i + 5], axis=1) for i in range(0, 20, 5)], axis=0),
                os.path.join(OUT, 'containers64.png'), 2)
    abig = [pad_to(props.a_button_big(False), 32, 32), pad_to(props.a_button_big(True), 32, 32)]
    lk, pal = palette_and_lookup(abig)
    cw.u32_bytes('abig_tiles', b''.join(obj(a, lk) for a in abig))
    cw.u16('abig_pal', pal)
    heart_off = mockups.hearts_progress(0, 1)
    x2 = lambda im: np.repeat(np.repeat(im, 2, axis=0), 2, axis=1)
    bits = [pad_to(x2(props.HEART), 16, 16), pad_to(x2(heart_off), 16, 16), pad_to(mockups.motion_arcs('left'), 8, 8),
            pad_to(mockups.puff(), 16, 8)]
    lk, pal = palette_and_lookup(bits)
    cw.u32_bytes('openui_tiles', b''.join(obj(b, lk) for b in bits))
    cw.u16('openui_pal', pal)
    cw.define('OPENUI_HEART_ON', 0)
    cw.define('OPENUI_HEART_OFF', 4)
    cw.define('OPENUI_ARC', 8)
    cw.define('OPENUI_PUFF', 9)

    # ---------------- title
    tbg, letters = title_parts()
    export_multi_bg(cw, 'titlebg', [tbg])
    sizes = [(32, 32, 0, 2), (64, 32, 1, 3), (32, 64, 2, 3), (64, 64, 0, 3)]   # w, h, shape, size
    # pack letters into as few palettes as fit (15 colors each)
    pals, pal_of = [], []
    for img, x, y in letters:
        cs = {tuple(int(v) for v in p) for p in img[..., :3][img[..., 3] > 0]}
        for i, pc in enumerate(pals):
            if len(pc | cs) <= 15:
                pals[i] = pc | cs
                pal_of.append(i)
                break
        else:
            pals.append(cs)
            pal_of.append(len(pals) - 1)
    lookups = []
    pal_words = []
    for pc in pals:
        lk = {c: i + 1 for i, c in enumerate(sorted(pc))}
        lookups.append(lk)
        pal = [0] * 16
        for c, i in lk.items():
            pal[i] = bgr555(c)
        pal_words += pal
    tiles, table = b'', []
    for (img, x, y), pi in zip(letters, pal_of):
        h_, w_ = img.shape[:2]
        sw, sh_, shape, size = next(t for t in sizes if t[0] >= w_ and t[1] >= h_)
        table += [len(tiles) // 32, x, y, shape, size, pi, sw, sh_]
        tiles += obj(pad_to(img, sw, sh_), lookups[pi])
    cw.u32_bytes('logo_tiles', tiles)
    cw.u16('logo_pal', pal_words)
    cw.u16('logo_table', table)
    cw.define('LOGO_LETTERS', len(letters))
    cw.define('LOGO_PALS', len(pals))
    print(f'logo: {len(letters)} letters, {len(tiles) // 32} tiles, {len(pals)} palettes')

    # ---------------- reveal: confetti and big star
    conf = [pad_to(props.confetti_piece(i), 8, 8) for i in range(12)]
    lk, pal = palette_and_lookup(conf)
    cw.u32_bytes('confetti_tiles', b''.join(obj(c, lk) for c in conf))
    cw.u16('confetti_pal', pal)
    cw.define('CONFETTI_N', len(conf))
    star = new(16, 16)
    blit(star, props.SPARK_HUGE, 2, 2)
    lk, pal = palette_and_lookup([star])
    cw.u32_bytes('star16_tiles', obj(star, lk))
    cw.u16('star16_pal', pal)

    # ---------------- UI sprites
    frame = pad_to(mockups.selection_frame(), 64, 32)
    lk, pal = palette_and_lookup([frame])
    cw.u32_bytes('ui_frame_tiles', obj(frame, lk))
    cw.u16('ui_frame_pal', pal)

    sparks = [props.SPARK_TINY, props.SPARK_SMALL, props.SPARK_BIG]
    cells = []
    for sp in sparks:
        f = new(8, 8)
        blit(f, sp, (8 - sp.shape[1]) // 2, (8 - sp.shape[0]) // 2)
        cells.append(f)
    heart = new(8, 8)
    blit(heart, props.HEART, 0, 0)
    cells.append(heart)
    # meadow extras in the same palette (the maps use all 16 OBJ palettes):
    # 8 snacks, the envelope over the mailbox, its flag up and down (16x16 each)
    twinkles = []
    for tw in props.MAP_TWINKLES:                  # container twinkles on the map (8.1), centred in 16x16
        f = new(16, 16)
        blit(f, tw, (16 - tw.shape[1]) // 2, (16 - tw.shape[0]) // 2)
        twinkles.append(f)
    extras = [props.snack16(k) for k in props.SNACK_ORDER] + [props.envelope16(), props.mail_flag(True),
                                                              props.mail_flag(False)] + twinkles
    lk, pal = palette_and_lookup(cells + extras)
    cw.u32_bytes('ui_small_tiles', b''.join(obj(c, lk) for c in cells))
    cw.u16('ui_small_pal', pal)
    cw.u32_bytes('ui_extra_tiles', b''.join(obj(c, lk) for c in extras))
    cw.define('SNACK_KINDS', len(props.SNACK_ORDER))
    cw.define('EXTRA_ENVELOPE', len(props.SNACK_ORDER) * 4)
    cw.define('EXTRA_FLAG_UP', len(props.SNACK_ORDER) * 4 + 4)
    cw.define('EXTRA_FLAG_DOWN', len(props.SNACK_ORDER) * 4 + 8)
    cw.define('EXTRA_TWINKLE', len(props.SNACK_ORDER) * 4 + 12)   # 3 frames, 4 tiles each
    cw.c.append('const char *const snack_names[' + str(len(props.SNACK_ORDER)) + '] = {' +
                ', '.join(f'"{k}"' for k in props.SNACK_ORDER) + '};\n')
    cw.h.append(f'extern const char *const snack_names[{len(props.SNACK_ORDER)}];\n')
    save_scaled(np.concatenate(extras, axis=1), os.path.join(OUT, 'meadow_extras.png'), 6)

    # ---------------- house rooms (one per area) and the friends' gifts
    cw.h.append('\ntypedef struct {\n    const uint32_t *tiles; uint32_t tiles_bytes;\n'
                '    const uint16_t *pal; uint16_t pal_bytes;\n    const uint16_t *map;\n} RoomArt;\n')
    arts = []
    for i, a in enumerate(AREAS):
        export_multi_bg(cw, f'room{i}', [rooms.room_background(a[0])])
        arts.append(f'{{room{i}_tiles, sizeof room{i}_tiles, room{i}_pal, sizeof room{i}_pal, room{i}_map0}}')
    cw.c.append('const RoomArt room_art[4] = {\n    ' + ',\n    '.join(arts) + '\n};\n')
    cw.h.append('extern const RoomArt room_art[4];\n')
    for k, v in rooms.ROOM.items():
        cw.define(f'ROOM_{k.upper()}', v)
    # 16x16 per species in play order, drawn in the friends' palette slots
    cw.u32_bytes('gift_tiles', b''.join(gifts.gift_tiles(sp) for a in AREAS for sp in a[3]))

    # ---------------- letter: static background (map0), the card that slides up (map1), envelope
    export_multi_bg(cw, 'letter', list(letter_parts()))
    env = [props.envelope64(False), props.envelope64(True)]
    lk, pal = palette_and_lookup(env)
    cw.u32_bytes('envelope64_tiles', b''.join(obj(e, lk) for e in env))
    cw.u16('envelope64_pal', pal)
    cw.define('UI_TWINKLE0', 0)
    cw.define('UI_HEART', 3)

    shadow = props.shadow(64, 8, rgb15('#c9789a'))[:, :32]     # left half; right half is h-flipped
    cw.u32_bytes('ui_shadow_tiles', obj(shadow, {rgb15('#c9789a'): 1}))
    cw.u16('ui_shadow_pal', [0, bgr555(rgb15('#c9789a'))] + [0] * 14)

    cw.u16('ui_text_pal', [0, bgr555(C['ui_ink']), bgr555(C['white']), bgr555(C['ui_line'])] + [0] * 12)

    # found counter pill, top right, as in the mockups: the area's container
    # icon at the left end, the count ("7/20") printed over it at run time in
    # color 1 (ui_ink). Two 32x16 sprites and one palette per area.
    # Momo's heart meter (step 8.4, owner pick "A"): while Pip stands by a
    # sleeping Momo, a bubble shows 10 hearts, one filled per friend found in
    # the area (10 wake Momo). Same palette as the pill: body 64x32 (the
    # bubble with 10 empty hearts), a tail tile under it toward Momo, and a
    # 16x16 filled heart drawn over each empty one.
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
    tail = new(8, 8)
    for k, row in enumerate(('kbbbbbk', '.kbbbk.', '..kbk..', '...k...')):
        for xx, ch in enumerate(row):
            if ch != '.':
                tail[k, xx, :3] = C['ui_ink'] if ch == 'k' else C['ui_bg']
                tail[k, xx, 3] = 255
    full = new(16, 16)
    blit(full, props.HEART_BIG, 0, 0)
    icons = [props.icon12(a[2]) for a in AREAS]     # one pill per area, in play order
    pills, pals, meters = [], [], []
    for ic in icons:
        img = new(64, 16)
        blit(img, props.pill(COUNT_PILL_W, 15, C['ui_bg'], C['ui_pk'], C['ui_ink'], C['white']), 0, 1)
        blit(img, ic, 4, 2)             # inside the pill, clear of its left end
        lk, _ = palette_and_lookup([img, meter, tail, full])
        cs = [C['ui_ink']] + sorted(c for c in lk if c != C['ui_ink'])
        if len(cs) > 15:
            raise ValueError(f'count pill: {len(cs)} colors')
        lk = {c: i + 1 for i, c in enumerate(cs)}
        pills.append(obj(img[:, :32], lk) + obj(img[:, 32:], lk))   # two 32x16 halves
        pals += [0] + [bgr555(c) for c in cs] + [0] * (15 - len(cs))
        meters.append(obj(meter, lk) + obj(tail, lk) + obj(full, lk))
    cw.u32_bytes('count_pill_tiles', b''.join(pills))
    cw.u16('count_pill_pal', pals)
    cw.u32_bytes('momo_meter_tiles', b''.join(meters))      # per area: 32 body, 1 tail, 4 heart
    for k, v in (('METER_TILES', 37), ('METER_TAIL', 32), ('METER_HEART', 33), ('METER_W', METER_W), ('METER_H', METER_H),
                 ('METER_HX', METER_HX), ('METER_HY', METER_HY), ('METER_DX', METER_DX), ('METER_DY', METER_DY)):
        cw.define(k, v)
    save_scaled(np.concatenate([meter, np.pad(tail, ((0, 24), (0, 0), (0, 0))), np.pad(full, ((0, 16), (0, 0), (0, 0)))], axis=1),
                os.path.join(OUT, 'momo_meter.png'), 6)
    cw.define('COUNT_PILL_W', COUNT_PILL_W)
    cw.define('COUNT_TEXT_X', 18)       # the 32 px text strip starts here inside the pill

    # ---------------- Pip
    pf = pip_frames()
    order = ['down0', 'down1', 'down2', 'up0', 'up1', 'up2', 'right0', 'right1']
    lk, pal = palette_and_lookup([pf[k] for k in order])
    cw.u32_bytes('pip_tiles', b''.join(obj(pf[k], lk) for k in order))
    cw.u16('pip_pal', pal)
    feet = max(int(np.nonzero(pf[k][..., 3].any(axis=1))[0][-1]) for k in order)
    cw.define('PIP_FEET_ROW', feet)
    small_shadow = props.shadow(12, 4, rgb15('#6a5a88'))
    sh = new(16, 8)
    blit(sh, small_shadow, 2, 2)
    cw.u32_bytes('shadow16_tiles', obj(sh, {rgb15('#6a5a88'): 1}))     # its palette is written with the gate log

    # ---------------- meadow sprites: gift boxes, A bubble, guide arrow
    from gbaconv import tile4
    idx = props.box16_index()
    cw.u32_bytes('box16_tiles', b''.join(tile4(idx[ty:ty + 8, tx:tx + 8]) for ty in (0, 8) for tx in (0, 8)))
    box_pals = []
    for color in ('pink', 'lav', 'mint', 'yellow', 'sky'):
        box_pals += [0] + [bgr555(c) for c in props.box16_palette(color)] + [0] * (15 - len(props.BOX16_KEYS))
    cw.u16('box16_pal', box_pals)
    cw.define('BOX_COLORS', 5)

    # containers on the map, per area in play order: 4 tiles and 5 color
    # palettes each (the meadow's box keeps its hand-made index; others
    # share one index image across their 5 color variants)
    cont_tiles, cont_pals = [], []
    for key, _, kind, _ in AREAS[:len(AREA_BUILDERS)]:
        if kind == 'box':
            cont_tiles.append(b''.join(tile4(idx[ty:ty + 8, tx:tx + 8]) for ty in (0, 8) for tx in (0, 8)))
            cont_pals += box_pals
            continue
        variants = {'acorn': lambda: [props.acorn16(c) for c in ('cream', 'pink', 'mint', 'lav', 'gold')],
                    'shell': lambda: [props.shell(c, 16) for c in ('pink', 'peach', 'mint', 'lav', 'yellow')],
                    'capsule': lambda: [props.capsule16(b, d, l) for l, b, d in props.CAPSULE_COLORS.values()]}[kind]()
        index, pals = shared_index(variants)
        cont_tiles.append(b''.join(tile4(index[ty:ty + 8, tx:tx + 8]) for ty in (0, 8) for tx in (0, 8)))
        for pal in pals:
            cont_pals += [0] + [bgr555(c) for c in pal] + [0] * (15 - len(pal))
        save_scaled(np.concatenate(variants, axis=1), os.path.join(OUT, f'{key}_containers.png'), 8)
    cw.u32_bytes('cont16_tiles', b''.join(cont_tiles))
    cw.u16('cont16_pal', cont_pals)

    # Momo the sleepy panda lies across each way that is still shut (32x32
    # asleep, awake, then two 8x8 z's). Its colors go after the small
    # shadow's in the same OBJ palette (the maps use all 16)
    mf = npc.frames()
    parts = [mf['sleep'], mf['awake']] + npc.zz() + [npc.blanket()]
    npc_cols = sorted({tuple(int(v) for v in p) for im in parts for p in im[..., :3][im[..., 3] > 0]})
    if len(npc_cols) > 14:
        raise ValueError(f'Momo: {len(npc_cols)} colors')
    nlk = {c: i + 2 for i, c in enumerate(npc_cols)}
    cw.u32_bytes('npc_tiles', b''.join(obj(im, nlk) for im in parts))
    cw.define('NPC_AWAKE', 16)
    cw.define('NPC_ZZ', 32)
    cw.define('NPC_BLANKET', 34)           # 64x32 (quilt in its rows 17..30): tucks Momo in on its cloud bed
    shadow_npc_pal = [0, bgr555(rgb15('#6a5a88'))] + [bgr555(c) for c in npc_cols]
    cw.u16('shadow16_pal', shadow_npc_pal + [0] * (16 - len(shadow_npc_pal)))
    save_scaled(np.concatenate(parts[:2], axis=1), os.path.join(OUT, 'npc_momo.png'), 6)

    # the A bubble and the guide arrow share one palette (step 8.3: the map
    # needs 3 free OBJ palettes for followers from other areas)
    abtn = pad_to(props.a_button(), 16, 32)
    arrows = [props.guide_arrow(d) for d in ('right', 'up', 'upright')]
    lk, pal = palette_and_lookup([abtn] + arrows)
    cw.u32_bytes('abubble_tiles', obj(abtn, lk))
    cw.u16('abubble_pal', pal)
    cw.u32_bytes('arrow_tiles', b''.join(obj(a, lk) for a in arrows))
    cw.u16('arrow_pal', pal)
    save_scaled(np.concatenate(arrows + [pad_to(props.box16(c), 16, 16) for c in ('pink', 'lav', 'mint', 'yellow', 'sky')], axis=1),
                os.path.join(OUT, 'meadow_sprites.png'), 8)

    # ---------------- areas, in play order (only the ones built so far)
    cw.h.append('\n/* One walkable area: maps, collision, container spots, pen, doors. */\n'
                'typedef struct {\n    uint8_t area;                        /* index in play order (friend ids area*20..) */\n'
                '    const uint32_t *tiles; uint32_t tiles_bytes;\n    const uint16_t *pal; uint16_t pal_bytes;\n'
                '    const uint16_t *ground, *overlay;    /* 64x64 maps, 4 screenblocks each */\n'
                '    const uint8_t *solid; uint8_t cell_shift;\n    uint16_t w, h, spawn_x, spawn_y;\n'
                '    const uint16_t *spots; uint8_t nspots, first_spot;   /* x, y pairs */\n'
                '    uint16_t pen_x0, pen_y0, pen_x1, pen_y1, sign_x, sign_y;\n'
                '    const uint16_t *shimmer; uint8_t nshimmer;\n'
                '    const uint16_t *shimmer_cycle;       /* 4 colors the glint steps through */\n'
                '    const uint16_t *doors; uint8_t ndoors;   /* x, y, w, h: up here opens the house room */\n'
                '    const uint16_t *exits; uint8_t nexits;   /* x, y, w, h, to area, arrive x, arrive y */\n'
                '    const uint16_t *gates; uint8_t ngates;   /* x, y, w, h, to area: Momo lies there while it is shut */\n'
                '    uint16_t momo_x, momo_y;             /* Momo sleeps on its bed here once every way is open (0 = none) */\n'
                '    uint16_t mail_x, mail_y, basket_x, basket_y;   /* base centres of the mailbox and picnic basket (0 = none) */\n'
                '} AreaMap;\n')
    built = [b() for b in AREA_BUILDERS]
    names = [a[0] for a in AREAS]
    rows = []
    for i, area in enumerate(built):
        if area.name != names[i]:
            raise ValueError(f'area maps must follow the play order: {area.name} at {i}, expected {names[i]}')
        rows.append(export_area(cw, area, i))
    cw.c.append(f'const AreaMap area_maps[{len(rows)}] = {{\n' + ',\n'.join(rows) + '\n};\n')
    cw.h.append(f'extern const AreaMap area_maps[{len(rows)}];\n')
    cw.define('AREA_MAPS', len(rows))
    cw.save(OUT)


AREA_BUILDERS = [areas.meadow, areas.woods, areas.shore, areas.clouds]       # every map, in play order


def shared_index(variants):
    """Color variants of one drawing -> (index image, palette per variant).
    Every variant must color the same pixels the same way (a color of the
    first maps to exactly one color of each other), so one tile set serves all."""
    first = variants[0]
    m = first[..., 3] > 0
    cols = sorted({tuple(int(v) for v in p) for p in first[..., :3][m]})
    if len(cols) > 15:
        raise ValueError(f'{len(cols)} colors')
    index = np.zeros(first.shape[:2], np.uint8)
    for i, c in enumerate(cols):
        index[m & np.all(first[..., :3] == c, axis=-1)] = i + 1
    pals = []
    for v in variants:
        if not np.array_equal(v[..., 3] > 0, m):
            raise ValueError('variants differ in shape')
        pal = []
        for i in range(len(cols)):
            got = {tuple(int(x) for x in p) for p in v[..., :3][index == i + 1]}
            if len(got) != 1:
                raise ValueError(f'color {cols[i]} maps to {len(got)} colors in a variant')
            pal.append(got.pop())
        pals.append(pal)
    return index, pals


def export_area(cw, a, index):
    """Writes one area's data and returns its AreaMap initializer."""
    stack = np.concatenate([a.ground, a.overlay], axis=0)
    b = bg(stack, pal_bank=0, max_pals=16)
    if b['ntiles'] > 1024:
        raise ValueError(f'{a.name}: {b["ntiles"]} tiles > 1024')
    tw, th = a.w // 8, a.h // 8

    def sb64(entries):
        # 64x64 map in 4 screenblocks: (0,0) (1,0) (0,1) (1,1)
        out = [0] * 4096
        for ty in range(th):
            for tx in range(tw):
                sbn = (ty // 32) * 2 + (tx // 32)
                out[sbn * 1024 + (ty % 32) * 32 + (tx % 32)] = entries[ty * tw + tx]
        return out

    n = tw * th
    cw.u32_bytes(f'{a.name}_tiles', b['tiles'])
    cw.u16(f'{a.name}_pal', [c for p in b['palettes'] for c in p])
    cw.u16(f'{a.name}_ground', sb64(b['map'][:n]))
    cw.u16(f'{a.name}_overlay', sb64(b['map'][n:]))
    solid = a.solid.astype(np.uint8).flatten().tolist()
    cw.c.append(f'const uint8_t {a.name}_solid[{len(solid)}] = {{' + ','.join(map(str, solid)) + '};\n')
    cw.h.append(f'extern const uint8_t {a.name}_solid[{len(solid)}];\n')
    up = a.name.upper()
    cw.define(f'{up}_CELL_SHIFT', areas.CELL.bit_length() - 1)
    cw.define(f'{up}_W', a.w)
    cw.define(f'{up}_H', a.h)
    cw.define(f'{up}_PALS', len(b['palettes']))
    cw.define(f'{up}_SPAWN_X', a.spawn[0])
    cw.define(f'{up}_SPAWN_Y', a.spawn[1])
    spots = [v for p in a.spots for v in p]
    cw.u16(f'{a.name}_spots', spots)
    cw.define(f'{up}_FIRST_SPOT', a.first_spot)
    if a.pen:
        for k, v in zip(('X0', 'Y0', 'X1', 'Y1'), a.pen):
            cw.define(f'{up}_PEN_{k}', v)
        cw.define(f'{up}_SIGN_X', a.sign[0])
        cw.define(f'{up}_SIGN_Y', a.sign[1])
    cw.define(f'{up}_NSPOTS', len(a.spots))
    # palette slots holding the water shimmer color, for runtime cycling
    target = bgr555(C[a.shimmer])
    slots = [bi * 16 + ci for bi, p in enumerate(b['palettes']) for ci, c in enumerate(p) if ci and c == target]
    cw.u16(f'{a.name}_shimmer', slots or [0])
    cw.define(f'{up}_NSHIMMER', len(slots))
    lo, hi = C[a.shimmer], C[a.shimmer.replace('_lt', '_hi')]
    mid = tuple((x + y) // 2 for x, y in zip(lo, hi))
    cw.u16(f'{a.name}_shimmer_cycle', [bgr555(lo), bgr555(mid), bgr555(hi), bgr555(mid)])
    doors = [v for d in a.doors for v in d[:4]]
    cw.u16(f'{a.name}_doors', doors or [0, 0, 0, 0])
    cw.u16(f'{a.name}_exits', [v for e in a.exits for v in e] or [0] * 7)
    cw.u16(f'{a.name}_gates', [v for g in a.gates for v in g] or [0] * 5)
    cw.define(f'{up}_NDOORS', len(a.doors))
    full = a.ground.copy()
    m = a.overlay[..., 3] > 0
    full[m] = a.overlay[m]
    save_scaled(full, os.path.join(OUT, f'preview_{a.name}.png'), 2)
    print(f'{a.name}: {b["ntiles"]} tiles, {len(b["palettes"])} palettes')
    pen = a.pen or (0, 0, 0, 0)
    sign = a.sign or (0, 0)
    momo = a.momo or (0, 0)
    mail = a.mailbox or (0, 0)
    basket = a.basket or (0, 0)
    n = a.name
    return (f'    {{{index}, {n}_tiles, {len(b["tiles"])}, {n}_pal, {len(b["palettes"]) * 32}, {n}_ground, {n}_overlay,\n'
            f'     {n}_solid, {areas.CELL.bit_length() - 1}, {a.w}, {a.h}, {a.spawn[0]}, {a.spawn[1]},\n'
            f'     {n}_spots, {len(a.spots)}, {a.first_spot}, {pen[0]}, {pen[1]}, {pen[2]}, {pen[3]}, {sign[0]}, {sign[1]},\n'
            f'     {n}_shimmer, {len(slots)}, {n}_shimmer_cycle, {n}_doors, {len(a.doors)}, {n}_exits, {len(a.exits)},\n'
            f'     {n}_gates, {len(a.gates)}, {momo[0]}, {momo[1]}, {mail[0]}, {mail[1]}, {basket[0]}, {basket[1]}}}')


if __name__ == '__main__':
    main()
