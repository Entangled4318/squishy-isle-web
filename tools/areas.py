"""Full-size area maps for the ROM.

Each area returns two layers and a collision grid:
  ground  - terrain, decor and the lower part of every object (under Pip)
  overlay - the upper part of tall objects (tree tops, roofs), over Pip
  solid   - 4x4 px cells Pip cannot enter (fine enough to walk close by)
The split height equals Pip's height, and tall objects block that same
height above their base, so Pip is covered by a tree top only when he is
really behind it.
"""
import math

import numpy as np

from gba import new, blit, rgb15
from palette import C
import world
from world import (render_terrain, MEADOW_KINDS, shape_labels, Capsule, Oval, SmoothUnion, SDF,
                   tree, cottage, bush, tree_shadow)
import props

PIP_H = 26          # sprite height that must be covered correctly
CELL = 4


class Area:
    def __init__(self, name, w, h):
        self.name, self.w, self.h = name, w, h
        self.ground = None
        self.overlay = new(w, h)
        self.solid = np.zeros((h // CELL, w // CELL), bool)
        self.spawn = (w // 2, h // 2)
        self.spots = []          # container spots (x, y of the sprite's bottom centre)
        self.first_spot = 0      # spot of the very first container of a game (in view of the spawn)
        self.pen = None          # (x0, y0, x1, y1) where found friends roam (their feet)
        self.sign = None         # (x, y) of the pen sign's base centre
        self.doors = []          # (x, y, w, h, target)
        self.signs = []          # signposts' ink boxes (x0, y0, x1, y1), see place(sign=True)
        self.exits = []          # (x, y, w, h, to_area, arrive_x, arrive_y): feet in the box walk to that area
        self.shimmer = 'w_lt'    # palette color that glints (cycled at run time)
        self.gates = []          # (x, y, w, h, to_area): solid while that area is shut; Momo the
                                 # sleepy panda (32x32, feet at x + w/2, y + h) lies there
        self.mailbox = None      # (x, y): base centre of the mailbox (A reads the newest friend's letter)
        self.basket = None       # (x, y): base centre of the picnic basket (A: snack time)
        self.momo = None         # (x, y): Momo's feet on its bed here, once every way is open (Cloud Hill)

    def block(self, x0, y0, x1, y1):
        """Mark pixel rect [x0,x1) x [y0,y1) solid (rounded to cells)."""
        c0, r0 = max(0, int(x0) // CELL), max(0, int(y0) // CELL)
        c1, r1 = min(self.w // CELL, -(-int(x1) // CELL)), min(self.h // CELL, -(-int(y1) // CELL))
        self.solid[r0:r1, c0:c1] = True

    def place(self, img, x, y, block_w=None, block_inset=0, tall=None, sign=False):
        """Put an object with its top-left at (x, y). Pixels higher than
        PIP_H above the base go to the overlay. block_w: width of the solid
        footprint (centred), block height = min(PIP_H, object height).
        sign: a signpost; its ink box goes in self.signs (check_map.py keeps
        them clear of Momo's heart meter)."""
        h, w = img.shape[:2]
        if sign:
            cols, rws = img[..., 3].any(axis=0).nonzero()[0], img[..., 3].any(axis=1).nonzero()[0]
            self.signs.append((x + cols[0], y + rws[0], x + cols[-1] + 1, y + rws[-1] + 1))
        rows = np.nonzero(img[..., 3].any(axis=1))[0]
        if not len(rows):
            return
        base = y + rows[-1] + 1
        split = base - PIP_H
        for yy in range(h):
            Y = y + yy
            if Y < 0 or Y >= self.h:
                continue
            target = self.overlay if Y < split else self.ground
            row = img[yy:yy + 1]
            blit(target, row, x, Y)
        if block_w:
            top = base - min(PIP_H if tall is None else tall, rows[-1] - rows[0] + 1)
            cx = x + w / 2
            self.block(cx - block_w / 2, top + block_inset, cx + block_w / 2, base)

    def decor(self, img, x, y):
        blit(self.ground, img, x, y)


class Stream(SDF):
    def __init__(self, x):
        self.x = x

    def d(self, X, Y):
        return self.x - X + 0 * Y                     # straight shore: Pip can walk its whole length


def bridge(h=28):
    """Wooden bridge across the stream (planks run horizontally)."""
    w = 44
    img = new(w, h)
    for y in range(h):
        for x in range(w):
            if y in (0, h - 1):
                c = C['wd_ink']
            elif y in (1, h - 2):
                c = C['wd_dk2']
            elif x % 6 == 5:
                c = C['wd_dk']
            else:
                c = C['wd_lt'] if (x // 6) % 2 == 0 else C['wd_base']
            img[y, x, :3] = c
            img[y, x, 3] = 255
    # rails
    for x in range(w):
        for y in (3, h - 4):
            img[y, x, :3] = C['wd_dk2'] if x % 6 else C['wd_ink']
    return img


def meadow():
    W_, H_ = 480, 320
    a = Area('meadow', W_, H_)
    path = SmoothUnion(10,
                       Capsule(232, 90, 232, 196, 15),
                       Capsule(232, 200, 470, 200, 15),
                       Capsule(232, 200, 84, 200, 13),
                       Capsule(84, 200, 84, 300, 13))
    pond = Oval(362, 96, 50, 32, n=2.3)
    lab = shape_labels(W_, H_, 'g', [('p', path), ('w', pond), ('w', Stream(460))])
    ground, lab = render_terrain(None, MEADOW_KINDS, lab=lab)
    a.ground = ground
    # water is solid; the bridge opens the stream again
    water = lab == 'w'
    for r in range(H_ // CELL):
        for c in range(W_ // CELL):
            if water[r * CELL:(r + 1) * CELL, c * CELL:(c + 1) * CELL].mean() > 0.3:
                a.solid[r, c] = True

    # ---- ground decor
    for name, x, y in (
            ('patch_pink', 150, 120), ('patch_yellow', 40, 130), ('patch_mix', 300, 160),
            ('patch_pink', 180, 270), ('patch_yellow', 330, 280), ('patch_mix', 20, 250),
            ('patch_pink', 410, 250), ('patch_yellow', 270, 130), ('tuft', 120, 150),
            ('tuft', 380, 170), ('tuft_small', 200, 240), ('tuft', 60, 90), ('clover', 150, 230),
            ('clover', 400, 140), ('tuft_small', 300, 90), ('tuft', 250, 270), ('patch_mix', 110, 290),
            ('tuft_small', 30, 190), ('clover', 360, 240), ('tuft', 180, 150), ('patch_pink', 370, 300)):
        a.decor(world.decor(name), x, y)
    for (x, y, f) in ((336, 80, False), (372, 102, True), (386, 78, False), (344, 108, False)):
        a.decor(world.lily_pad(f), x, y)
    a.decor(world.picnic_blanket(), 292, 232)
    a.decor(world.door_mat(), 226, 99)

    # ---- trees (big first so small ones overlap nicely); shadows go under
    trees = [
        ('green', True, -14, -34), ('green', False, 34, -12), ('green', False, 70, -20),
        ('blossom', True, 108, -40), ('blossom', False, 156, -16),
        ('green', True, 276, -38), ('green', False, 324, -14), ('blossom', False, 358, -24),
        ('blossom', True, 392, -36), ('green', False, 410, 6),
        ('green', True, -20, 26), ('blossom', False, -10, 84), ('green', True, -22, 130),
        ('blossom', False, 10, 286), ('green', True, 150, 284), ('blossom', False, 196, 292),
        ('blossom', True, 236, 290), ('blossom', False, 366, 290), ('green', True, 404, 280),
        ('blossom', False, 30, 226), ('blossom', False, 118, 236), ('green', False, 404, 120),
    ]
    for kind, big, x, y in trees:
        t = tree(kind, big)
        a.decor(tree_shadow(t.shape[1]), x, y + t.shape[0] - 6)
    for kind, big, x, y in sorted(trees, key=lambda t: t[3] + tree(t[0], t[1]).shape[0]):
        t = tree(kind, big)
        a.place(t, x, y, block_w=t.shape[1] - 8)

    # ---- cottage, garden, props
    a.place(cottage(), 200, 34, block_w=48)
    a.doors.append((224, 90, 16, 10, 'home'))
    a.place(world.decor('tulips'), 122, 70)
    a.place(world.decor('tulips'), 138, 72)
    a.place(world.decor('tulips'), 154, 70)
    a.place(world.mailbox(flag=False), 268, 74, block_w=8, tall=6)   # the flag is a sprite
    a.mailbox = (276, 96)
    a.place(world.signpost(world.mini_acorn()), 398, 164, block_w=8, tall=6, sign=True)   # the bridge leads to the woods;
    # 16 px west of 414 (8.4): Momo's heart meter bubble covered it (one tile west still hid 3 px)
    a.place(world.basket(), 322, 230, block_w=10, tall=6)
    a.basket = (329, 243)
    for kind, x, y in (('green', 180, 104), ('blossom', 300, 116), ('blossom', 150, 244),
                       ('green', 330, 140)):
        a.place(bush(kind), x, y, block_w=10, tall=6)
    for big, x, y in ((True, 312, 150), (False, 196, 204), (True, 418, 300), (False, 60, 60)):
        r = world.rock(big)
        a.place(r, x, y)                             # walk-through (owner request)
    for x, y in ((64, 136), (388, 150), (262, 300)):
        a.decor(world.mushrooms(), x, y)
    for x, y in ((200, 102), (250, 104), (262, 212), (196, 214), (110, 212), (330, 186)):
        a.place(world.decor('tulips'), x, y)         # walk-through: they looked too small to block

    # ---- friend pen left of the cottage: fence all round, sign by the corner
    px0, py0, px1, py1 = 56, 98, 176, 182           # outer fence box: room for all 20 friends
    top = world.fence(7)
    a.place(top, px0, py0 - 6, block_w=top.shape[1], tall=6)
    a.place(top, px0, py1 - top.shape[0], block_w=top.shape[1], tall=6)
    side = world.fence_side(py1 - py0 - 6)
    a.place(side, px0 - 3, py0, block_w=7, tall=side.shape[0])
    a.place(side, px1 - 4, py0, block_w=7, tall=side.shape[0])
    a.pen = (px0 + 8, py0 + 20, px1 - 8, py1 - 14)     # feet area; keeps heads off the rails
    sign_img = world.signpost(world.mini_heart())
    a.place(sign_img, px1 + 2, py1 - 22, block_w=8, tall=6, sign=True)
    a.sign = (px1 + 2 + sign_img.shape[1] // 2, py1 + 1)
    for name, x, y in (('patch_mix', 60, 200), ('patch_yellow', 350, 196), ('patch_pink', 124, 170),
                       ('tuft', 220, 250), ('patch_mix', 420, 226), ('tuft', 100, 132)):
        a.decor(world.decor(name), x, y)
    a.place(world.reeds(), 318, 74)
    a.place(world.reeds(), 402, 104)
    br = bridge()
    a.decor(br, 436, 186)
    a.solid[186 // CELL:(186 + 28) // CELL, 432 // CELL:] = False
    a.solid[186 // CELL, 460 // CELL:] = True          # rails, over the water only: the shore stays walkable
    a.solid[(186 + 27) // CELL, 460 // CELL:] = True
    a.block(472, 0, 480, 320)                          # map edge beyond the stream
    a.exits.append((462, 186, 10, 28, 1, 20, 200))      # east end of the bridge: to the woods
    a.gates.append((442, 186, 28, 28, 1))               # Momo sleeps across the bridge until the woods open

    a.spawn = (232, 124)
    a.spots = [(60, 206), (150, 212), (286, 180), (210, 150), (140, 88), (330, 210), (400, 220),
               (270, 260), (100, 260), (380, 166)]
    a.first_spot = 3                                   # (210, 150), just below the cottage
    return a


def woods():
    """Berry Woods: a mossy clearing ringed by green and autumn trees. The
    trail comes in from the meadow bridge (west) to the clearing, a path
    runs north through it to a big old tree and turns east to the shore
    (every path straight: owner request).
    Friend pen (the meadow's size) in the south-east with its sign."""
    W_, H_ = 480, 320
    a = Area('woods', W_, H_)
    trail = SmoothUnion(12,
                        Capsule(0, 200, 240, 200, 14),           # straight paths only (owner): in from the meadow,
                        Capsule(240, 200, 240, 70, 13),          # north through the clearing to the big old tree,
                        Capsule(240, 120, 480, 120, 14))         # and out east to the shore
    clearing = Oval(238, 172, 34, 22, n=2.2)
    lab = shape_labels(W_, H_, 'g', [('p', trail), ('p', clearing)])
    ground, lab = render_terrain(None, world.WOODS_KINDS, lab=lab)
    a.ground = ground

    # ---- forest floor: ferns, leaves, tufts, mushrooms
    for x, y in ((40, 150), (120, 240), (190, 120), (300, 70), (410, 60), (70, 280), (230, 270),
                 (330, 180), (440, 170), (140, 150), (380, 300)):
        a.decor(world.fern(), x, y)
    for i, (x, y) in enumerate(((60, 230), (170, 150), (260, 220), (320, 110), (420, 90), (110, 290),
                                (200, 60), (290, 250), (450, 250), (30, 110), (360, 200))):
        a.decor(world.leaves(i), x, y)
    for name, x, y in (('tuft', 90, 170), ('tuft_small', 280, 150), ('clover', 160, 270), ('tuft', 400, 150),
                       ('tuft_small', 50, 250), ('clover', 330, 90), ('tuft', 250, 110), ('tuft_small', 440, 290)):
        a.decor(world.decor(name, 'woods'), x, y)
    for x, y in ((104, 128), (268, 228), (430, 200), (180, 290)):
        a.decor(world.mushrooms(), x, y)
    for i, (x, y) in enumerate(((20, 170), (90, 90), (130, 60), (210, 100), (270, 130), (300, 170), (380, 150),
                                (410, 230), (340, 300), (250, 300), (160, 240), (90, 230), (20, 300), (120, 130),
                                (190, 180), (280, 80), (350, 40), (430, 130), (60, 60), (230, 240))):
        a.decor(world.leaves(i + 11), x, y)           # a carpet of fallen leaves: autumn woods, not meadow
    for x, y in ((230, 40), (360, 110), (20, 60), (170, 300), (270, 310)):
        a.decor(world.fern(), x, y)

    # ---- trees: a thick ring at the edges, a few inside. Positions snap to
    # the 8 px grid so copies of a tree share their tiles (the 1024 limit).
    ring = []
    for i, x in enumerate(range(-16, 480, 28)):                      # two rows along the top
        ring.append(('green' if i % 3 else 'autumn', i % 2 == 0, x, -40 + (i % 2) * 10))
    for i, x in enumerate(range(-4, 480, 30)):                       # and one along the bottom
        ring.append(('autumn' if i % 3 == 1 else 'green', i % 2 == 1, x, 294 - (i % 2) * 8))
    for y in (26, 70, 116, 236):                                     # west edge (the trail at 200 stays open)
        ring.append(('green' if y % 3 else 'autumn', y in (26, 236), -22, y))
    for y in (18, 58, 150, 196, 240):                                # east edge (the trail at 120 stays open)
        ring.append(('autumn' if y in (58, 196) else 'green', y in (18, 196), 440, y))
    inside = [('green', False, 120, 80), ('autumn', False, 340, 56), ('green', False, 56, 100),
              ('autumn', False, 150, 216), ('green', True, 60, 40), ('autumn', False, 400, 72),
              ('green', True, 64, 208), ('autumn', False, 200, 226),
              ('autumn', False, 30, 140), ('green', False, 96, 40), ('autumn', True, 150, 30),
              ('green', False, 290, 36), ('green', False, 110, 136)]
    trees = [(k, b, x // 8 * 8, y // 8 * 8) for k, b, x, y in ring + inside]
    for kind, big, x, y in trees:
        t = tree(kind, big)
        a.decor(tree_shadow(t.shape[1], C['mg_dk']), x, y + t.shape[0] - 6)
    for kind, big, x, y in sorted(trees, key=lambda t: t[3] + tree(t[0], t[1]).shape[0]):
        t = tree(kind, big)
        a.place(t, x, y, block_w=t.shape[1] - 8)

    # ---- the mushroom house at the north end of the path (its door opens the room with the woods gifts)
    a.place(world.mushroom_house(), 211, 12, block_w=40, tall=18)
    a.doors.append((232, 60, 16, 10, 'home'))

    # ---- props: berry bushes, stumps, fallen logs
    for kind, x, y in (('red', 88, 116), ('blue', 176, 100), ('red', 262, 214), ('blue', 70, 166),
                       ('red', 402, 90), ('blue', 36, 252), ('red', 136, 250)):   # blue 70,166 was on the trail (8.1)
        a.place(world.berry_bush(kind), x, y, block_w=10, tall=6)
    for x, y in ((282, 84), (380, 90)):
        a.place(world.stump(), x, y, block_w=12, tall=6)
    a.place(world.log(30), 150, 128, block_w=26, tall=6)
    a.place(world.log(24), 18, 92, block_w=20, tall=6)

    # ---- friend pen, south-east (same size as the meadow's), sign by its top-left corner
    px0, py0, px1, py1 = 300, 200, 420, 284
    top = world.fence(7)
    a.place(top, px0, py0 - 6, block_w=top.shape[1], tall=6)
    a.place(top, px0, py1 - top.shape[0], block_w=top.shape[1], tall=6)
    side = world.fence_side(py1 - py0 - 6)
    a.place(side, px0 - 3, py0, block_w=7, tall=side.shape[0])
    a.place(side, px1 - 4, py0, block_w=7, tall=side.shape[0])
    a.pen = (px0 + 8, py0 + 20, px1 - 8, py1 - 14)
    sign_img = world.signpost(world.mini_heart())
    a.place(sign_img, px0 - 26, py0 - 4, block_w=8, tall=6, sign=True)
    a.sign = (px0 - 26 + sign_img.shape[1] // 2, py0 + 19)

    a.block(0, 0, 4, 186)                              # map edges beside the trail ends
    a.block(0, 214, 4, 320)
    a.block(476, 0, 480, 106)
    a.block(476, 134, 480, 320)
    a.exits.append((0, 186, 12, 28, 0, 450, 200))      # west: back over the bridge (12 px: Pip's feet stop at x 5)
    a.exits.append((468, 106, 12, 28, 2, 20, 200))     # east: to the shore
    a.gates.append((450, 106, 28, 28, 2))              # Momo sleeps here until the shore opens
    a.spawn = (24, 200)
    a.spots = [(96, 168), (326, 100), (150, 170), (200, 150), (292, 150), (230, 110), (352, 170),
               (410, 150), (190, 276), (250, 250), (180, 200), (40, 190)]
    a.first_spot = 0                                   # in view of the arrival from the meadow
    return a


class Sea(SDF):
    """Open sea along the north edge, a gently wavy shoreline."""

    def d(self, X, Y):
        return Y - (62 + 5 * np.sin(X / 23.0) + 3 * np.sin(X / 9.0 + 1.3))


def shore():
    """Seashell Shore: sand under a wavy sea (north). The boardwalk comes in
    from the woods (west); the way on to Cloud Hill leaves east, where Momo
    sleeps until the shore has 10 friends. Umbrella, towel, sandcastle,
    palms, a tide pool; pen (the meadow's size) in the south-east."""
    W_, H_ = 480, 320
    a = Area('shore', W_, H_)
    lab = shape_labels(W_, H_, 's', [('e', Sea()), ('w', Oval(96, 272, 30, 13, n=2.2))])
    a.ground = world.shore_ground(lab)
    water = (lab == 'e') | (lab == 'w')
    for r in range(H_ // CELL):
        for c in range(W_ // CELL):
            if water[r * CELL:(r + 1) * CELL, c * CELL:(c + 1) * CELL].mean() > 0.3:
                a.solid[r, c] = True
    a.shimmer = 'sea_lt'

    # ---- sand decor: starfish, tiny shells, footprints, the boardwalk
    for x, y in ((190, 92), (40, 140), (120, 230), (360, 100), (250, 290), (440, 250), (30, 300)):
        a.decor(world.starfish(), x, y)
    for i, (x, y) in enumerate(((70, 92), (150, 88), (14, 170), (228, 124), (300, 150), (410, 120), (180, 300),
                                (330, 296), (460, 200), (60, 214))):
        a.decor(world.tiny_shell(i % 2), x, y)
    world.footprints(a.ground, [(130, 120), (135, 126), (129, 134), (134, 141), (128, 148), (133, 155), (127, 162)])
    a.decor(world.boardwalk(92), 0, 193)
    a.decor(world.towel(), 248, 128)
    for (w_, x, y) in ((36, 201, 136), (26, 2, 148), (26, 402, 126), (26, 166, 298), (26, 434, 282)):
        a.decor(world.tree_shadow(w_, C['s_dk']), x, y)
    for x, y in ((40, 22), (330, 34)):
        a.decor(world.sailboat(), x, y)

    # ---- objects; the beach hut up the beach (its door opens the room with the shore gifts)
    a.place(world.beach_hut(), 294, 72, block_w=46, tall=18)
    a.doors.append((314, 118, 16, 10, 'home'))
    P_, T_ = world.PALM_PAD, world.PALM_TOP            # the palm image grew in 8.1 (its fronds were cut)
    a.place(world.palm(), -6 - P_, 100 - T_, block_w=10, tall=6)
    a.place(world.palm(flip=True), 396 - P_, 78 - T_, block_w=10, tall=6)
    a.place(world.palm(), 160 - P_, 250 - T_, block_w=10, tall=6)
    a.place(world.palm(flip=True), 428 - P_, 232 - T_, block_w=10, tall=6)   # 8 px west: its leaves clear the east fence
    a.place(world.umbrella(), 196, 92, block_w=6, tall=6)
    a.place(world.sandcastle(), 110, 146, block_w=30, tall=10)
    a.place(world.bucket(), 148, 170)
    a.place(world.beach_ball(), 176, 190)
    for big, x, y in ((True, 58, 262), (False, 128, 270), (False, 40, 280)):
        a.place(world.rock(big), x, y, block_w=8 if big else 0, tall=4)

    # ---- friend pen (the meadow's size), sign by its top-left corner
    px0, py0, px1, py1 = 290, 184, 410, 268
    top = world.fence(7)
    a.place(top, px0, py0 - 6, block_w=top.shape[1], tall=6)
    a.place(top, px0, py1 - top.shape[0], block_w=top.shape[1], tall=6)
    side = world.fence_side(py1 - py0 - 6)
    a.place(side, px0 - 3, py0, block_w=7, tall=side.shape[0])
    a.place(side, px1 - 4, py0, block_w=7, tall=side.shape[0])
    a.pen = (px0 + 8, py0 + 20, px1 - 8, py1 - 14)
    sign_img = world.signpost(world.mini_heart())
    a.place(sign_img, px0 - 26, py0 - 4, block_w=8, tall=6, sign=True)
    a.sign = (px0 - 26 + sign_img.shape[1] // 2, py0 + 19)

    a.block(0, 0, 4, 190)                              # map edges beside the ways in and out
    a.block(0, 210, 4, 320)
    a.block(476, 0, 480, 136)
    a.block(476, 164, 480, 320)
    a.block(0, 316, 480, 320)
    a.exits.append((0, 186, 12, 28, 1, 456, 120))      # west: the boardwalk back to the woods (12 px, as above)
    a.decor(world.cloud_puff(72, 16, 2), 420, 142)       # a straight cloud walkway east to Cloud Hill
    # low fences along the east and west edges: the boardwalk and the cloud
    # walkway (where Momo sleeps until 10 shore friends) are the only ways off
    for x, runs in ((472, ((72, 132), (168, 316))), (1, ((72, 186), (214, 316)))):
        for y0, y1 in runs:
            side = world.fence_side(y1 - y0)
            a.place(side, x, y0, block_w=7, tall=side.shape[0])
    a.exits.append((468, 136, 12, 28, 3, 24, 204))     # east: on to Cloud Hill
    a.gates.append((450, 136, 28, 28, 3))              # Momo sleeps here until Cloud Hill opens
    a.spawn = (24, 200)
    a.spots = [(70, 176), (120, 110), (220, 176), (262, 150), (380, 150), (60, 120), (250, 240),
               (160, 214), (200, 300), (300, 300), (420, 296), (100, 240)]
    a.first_spot = 0                                   # in view of the arrival on the boardwalk
    return a


class CloudMask(SDF):
    """Signed distance of a union of shapes, for the cloud islands."""

    def __init__(self, *s):
        self.s = s

    def d(self, X, Y):
        d = self.s[0].d(X, Y)
        for t in self.s[1:]:
            d = np.minimum(d, t.d(X, Y))
        return d


def clouds():
    """Cloud Hill: puffy cloud islands in a lavender to pink sky. Cloud
    steps come up from the shore (west); the big island has the capsule
    machine under a rainbow, candy trees and the friend pen (the meadow's
    size). Puff bridges lead to a small garden island (south-west) and to
    Momo's bed (north-east), where Momo sleeps happily once every way is open."""
    from world import CloudBlob
    W_, H_ = 480, 320
    a = Area('clouds', W_, H_)
    sky = world.sky_map(W_, H_, [(0, rgb15('#c4c0f2')), (48, rgb15('#cfc8f6')), (104, rgb15('#dbd0f8')),
                                 (168, rgb15('#e8d6f6')), (232, rgb15('#f4dcf2')), (288, rgb15('#fde2ee'))])
    # far sky: rainbow behind the big island, moon, stars, soft clouds
    blit(sky, world.rainbow(208, 100, 5), 132, 6)
    blit(sky, world.glint_moon(), 44, 18)
    for i, (w_, h_, x, y) in enumerate(((52, 20, 6, 60), (44, 16, 404, 128), (40, 16, 196, 292), (56, 20, 352, 280),
                                        (36, 14, 20, 150))):
        blit(sky, mockups_cloud(w_, h_, i + 7), x, y)
    for (x, y) in ((110, 30), (360, 20), (18, 108), (300, 8), (452, 110), (150, 300), (440, 230), (8, 250),
                   (250, 100)):
        sky[y, x, :3] = C['st_lt']
    main = CloudBlob(244, 194, 172, 88, bump=9, seed=2)
    garden = CloudBlob(76, 282, 50, 24, bump=7, seed=5)                # small island, south-west
    bed = CloudBlob(416, 86, 52, 32, bump=7, seed=4)                   # Momo's island, north-east
    puffs = (puff_bridge(-14, 204, 92, 204, 13, 6, 3) +                # straight cloud path from the shore
             puff_bridge(92, 246, 92, 272, 18, 2, 11) +            # straight bridges (owner): down to the garden,
             puff_bridge(394, 150, 394, 104, 20, 3, 13))           # up to Momo's island. Puffs 18 and 20 (were 12, 14):
    # the sky beside a bridge is solid, so the walkable lane is ~24 px narrower than the cloud;
    # at 14 and 18 px Pip had to line up exactly to turn onto them (Brick test, 8.5). Now 30 and 34 px.
    lab = shape_labels(W_, H_, 'x', [('c', CloudMask(main, garden, bed, *puffs))])
    a.ground = world.cloud_ground(lab, sky)
    walk = lab == 'c'
    cover = np.zeros((H_ // CELL, W_ // CELL))
    for r in range(H_ // CELL):
        for c in range(W_ // CELL):
            cover[r, c] = walk[r * CELL:(r + 1) * CELL, c * CELL:(c + 1) * CELL].mean()
            if cover[r, c] < 0.7:
                a.solid[r, c] = True
    # Close one-cell notches (8.5, Brick test): the 70% rule left single solid
    # cells in the inside corners where an island meets a bridge, and Pip,
    # walking diagonally toward Momo, stuck on them. A solid cell turns
    # walkable when 3 of its 4 neighbours are walkable (a notch in an edge,
    # however little cloud it holds), or when it is at least 30% cloud with
    # walkable cells on opposite sides (a gap a cell wide).
    for _ in range(2):
        free = ~a.solid
        nb = np.zeros_like(free, dtype=int)
        nb[1:] += free[:-1]; nb[:-1] += free[1:]; nb[:, 1:] += free[:, :-1]; nb[:, :-1] += free[:, 1:]
        ns = np.zeros_like(free); ns[1:-1] = free[:-2] & free[2:]
        ew = np.zeros_like(free); ew[:, 1:-1] = free[:, :-2] & free[:, 2:]
        a.solid &= ~((nb >= 3) | ((cover >= 0.3) & (ns | ew)))
    a.shimmer = 'st_lt'

    # ---- stars on the clouds (they twinkle), lollipops, tree shadows
    for i, (x, y) in enumerate(((130, 170), (206, 262), (300, 140), (400, 236), (84, 214), (206, 176), (164, 132),
                                (400, 160), (60, 292), (440, 110), (330, 118), (146, 262), (30, 196), (250, 116))):
        a.decor(world.star_glint(i % 3 == 0), x, y)
    for kind, x, y in (('pink', 190, 148), ('blue', 150, 190), ('mint', 110, 290), ('pink', 380, 96),
                       ('mint', 408, 206), ('blue', 238, 214), ('pink', 396, 132)):
        a.decor(world.lollipop(kind), x, y)
    # ('blue', 304, 96) was at 330,100 until 8.5: its trunk stood 3 px under the island edge, a dead-end pocket
    # on the way to Momo's bridge (Brick test)
    trees = [('blue', 164, 96), ('blue', 304, 96), ('blue', 112, 196), ('pink', 176, 232),
             ('blue', 36, 250), ('pink', 104, 250), ('blue', 256, 240)]
    trees = [(k, x // 8 * 8, y // 8 * 8) for k, x, y in trees]
    for kind, x, y in trees:
        a.decor(world.tree_shadow(26, C['cl_dk']), x + 3, y + 38)

    # ---- the cloud cottage (its door opens the room with the Cloud Hill gifts)
    a.place(world.cloud_cottage(), 92, 100, block_w=42, tall=16)
    a.doors.append((113, 148, 16, 10, 'home'))

    # ---- the capsule machine under the rainbow, candy trees
    g = world.gacha()
    a.place(g, 216, 84, block_w=34, tall=10)
    for kind, x, y in sorted(trees, key=lambda t: t[2]):
        t = world.candy_tree(kind)
        a.place(t, x, y, block_w=8, tall=6)

    # ---- Momo's bed on the north-east island
    bed_img = world.cloud_bed()
    bx, by = 390, 76
    a.place(bed_img, bx, by)
    a.block(bx + 2, by + 4, bx + 46, by + 22)
    a.momo = (bx + 26, by + 18)

    # ---- friend pen (the meadow's size), east of the machine; sign by its top-left corner
    px0, py0, px1, py1 = 282, 168, 402, 252
    top = world.fence(7)
    a.place(top, px0, py0 - 6, block_w=top.shape[1], tall=6)
    a.place(top, px0, py1 - top.shape[0], block_w=top.shape[1], tall=6)
    side = world.fence_side(py1 - py0 - 6)
    a.place(side, px0 - 3, py0, block_w=7, tall=side.shape[0])
    a.place(side, px1 - 4, py0, block_w=7, tall=side.shape[0])
    a.pen = (px0 + 8, py0 + 20, px1 - 8, py1 - 14)
    sign_img = world.signpost(world.mini_heart())
    a.place(sign_img, px0 - 26, py0 - 4, block_w=8, tall=6, sign=True)
    a.sign = (px0 - 26 + sign_img.shape[1] // 2, py0 + 19)

    a.block(0, 0, 4, 190)                              # map edge beside the way down
    a.block(0, 218, 4, 320)
    a.exits.append((0, 190, 12, 28, 2, 452, 150))     # west: down the cloud steps to the shore (12 px: see woods)
    a.spawn = (24, 204)
    a.spots = [(96, 190), (170, 160), (216, 200), (150, 226), (300, 130), (376, 150), (64, 296),
               (100, 274), (446, 100), (232, 262), (344, 262), (196, 118)]
    a.first_spot = 0                                   # in view of the arrival
    return a


def puff_bridge(x0, y0, x1, y1, r, n, seed):
    """A walkable chain of overlapping cloud puffs from (x0,y0) to (x1,y1)."""
    from world import CloudBlob
    out = []
    for i in range(n + 1):
        t = i / n
        out.append(CloudBlob(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, r + 3, r, bump=4.5, seed=seed + i))
    return out


def mockups_cloud(w, h, seed):
    import mockups
    return mockups.cloud(w, h, seed)


def collision_preview(a):
    img = a.ground.copy()
    ov = a.overlay[..., 3] > 0
    img[ov] = a.overlay[ov]
    for r in range(a.solid.shape[0]):
        for c in range(a.solid.shape[1]):
            if a.solid[r, c]:
                sub = img[r * CELL:(r + 1) * CELL, c * CELL:(c + 1) * CELL, :3].astype(int)
                sub[:] = (sub * 0.5 + np.array([255, 60, 90]) * 0.5).astype(int)
                img[r * CELL:(r + 1) * CELL, c * CELL:(c + 1) * CELL, :3] = sub
    for (x, y) in a.spots:
        img[y - 2:y + 2, x - 2:x + 2, :3] = (40, 40, 255)
    return img
