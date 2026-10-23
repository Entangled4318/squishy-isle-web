"""Checks the meadow collision grid with the game's own feet test (viewer.c
blocked(): a 11x6 px feet box), and that every container spot of every area
can be reached. Usage: check_map.py OUTDIR"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
import areas  # noqa: E402

OUT = sys.argv[1]
FEET_W, FEET_H = 5, 5
fails = []


def check(cond, msg):
    print(('PASS ' if cond else 'FAIL ') + msg)
    if not cond:
        fails.append(msg)


a = areas.meadow()
C = areas.CELL


def solid(x, y):
    if x < 0 or y < 0 or x >= a.w or y >= a.h:
        return True
    return a.solid[y // C, x // C]


def blocked(x, y):
    return solid(x - FEET_W, y - FEET_H) or solid(x + FEET_W, y - FEET_H) or solid(x - FEET_W, y) or solid(x + FEET_W, y)


check(C == 4, f'collision cells are 4 px ({C})')
# pen's bottom-left post: Pip can walk north to south past it on the left
px0, py1 = 56, 182
lanes = [x for x in range(8, px0) if all(not blocked(x, y) for y in range(py1 - 40, py1 + 16))]
check(len(lanes) > 0, f'a free north-south lane left of the pen ({lanes[:1]}..{lanes[-1:]})')
# the stream shore is straight and walkable from the north edge to the south edge
shore = [x for x in range(400, a.w) if all(not blocked(x, y) for y in range(FEET_H + 1, a.h - 8))]
check(len(shore) > 0, f'Pip can walk the whole shore north to south (lane x {shore[:1]}..{shore[-1:]})')
# rocks are walk-through
for big, x, y in ((True, 312, 150), (False, 196, 204), (True, 418, 300), (False, 60, 60)):
    r = areas.world.rock(big)
    cx, base = x + r.shape[1] // 2, y + r.shape[0] - 1
    check(not blocked(cx, base) and not blocked(cx, base - 3), f'rock at {x},{y} is walk-through')
# free-standing bushes: Pip can stand right beside the art (feet box within 3 px of
# its edge); the bushes at 180,104 and 150,244 touch the pen fence and a tree
for kind, x, y in (('blossom', 300, 116), ('green', 330, 140)):
    w = areas.bush(kind).shape[1]
    base = y + 15
    left_ok = not blocked(x - FEET_W - 3, base)
    right_ok = not blocked(x + w + FEET_W + 2, base)
    check(left_ok and right_ok, f'bush at {x},{y}: Pip fits right beside it on both sides')



def reachable_spots(area):
    """Every container spot in every area: Pip, walking from the area's start
    (all gates open), can stand where the game counts a touch (viewer.c
    box_hit with TOUCH 6, as the harness seek uses), and each spot's box
    footprint lies on walkable ground, not in the sky or the sea."""
    from collections import deque
    W, H = area.w, area.h

    def sol(x, y):
        return x < 0 or y < 0 or x >= W or y >= H or area.solid[y // C, x // C]

    def walk(x, y, box=None):
        if sol(x - FEET_W, y - FEET_H) or sol(x + FEET_W, y - FEET_H) or sol(x - FEET_W, y) or sol(x + FEET_W, y):
            return False
        if box and x + FEET_W >= box[0] - 7 and x - FEET_W <= box[0] + 7 and y >= box[1] - 6 and y - FEET_H <= box[1]:
            return False
        return True

    seen = np.zeros((H, W), bool)
    sx, sy = area.spawn
    q = deque([(sx, sy)])
    seen[sy, sx] = True
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < W and 0 <= ny < H and not seen[ny, nx] and walk(nx, ny):
                seen[ny, nx] = True
                q.append((nx, ny))
    bad = []
    for (dx0, dy0, dw, dh, _) in area.doors:        # the door zone (viewer.c: up to 12 px below the door)
        if not any(seen[y, x] for y in range(dy0, min(H, dy0 + dh + 12)) for x in range(dx0, dx0 + dw)):
            bad.append(('door', dx0, dy0))
    # an exit needs room: Pip moves 1.25 px a frame, so a band of only one
    # or two reachable feet columns can be stepped over (step 7: the woods and
    # shore west exits were 6 px wide, one column past the edge Pip stops at)
    for (ex, ey, ew, eh, to, ax, ay) in area.exits:
        cols = {x for y in range(ey, min(H, ey + eh)) for x in range(ex, min(W, ex + ew)) if seen[y, x]}
        if len(cols) < 4:
            bad.append(('exit', ex, ey, len(cols)))
    for (bx, by) in area.spots:
        on_ground = all(not sol(x, y) for x in (bx - 6, bx, bx + 6) for y in (by - 5, by))
        touch = any(seen[y, x] and walk(x, y, (bx, by))
                    for y in range(max(0, by - 14), min(H, by + 10)) for x in range(max(0, bx - 16), min(W, bx + 17))
                    if x + FEET_W + 4 >= bx - 7 and x - FEET_W - 4 <= bx + 7 and y + 4 >= by - 6 and y - FEET_H - 4 <= by)
        if not (on_ground and touch):
            bad.append((bx, by))
    return bad


def arrivals_ok(maps):
    """Each exit's arrival point is walkable in the area it leads to and not
    inside one of its exits (no ping-pong)."""
    bad = []
    for ar in maps:
        for (ex, ey, ew, eh, to, ax, ay) in ar.exits:
            dest = maps[to]
            if not reachable_from(dest, (ax, ay)):
                bad.append((ar.name, 'to', dest.name, ax, ay))
            if any(x <= ax < x + w and y <= ay < y + h for (x, y, w, h, *_rest) in dest.exits):
                bad.append((ar.name, 'lands in an exit of', dest.name, ax, ay))
    return bad


def reachable_from(area, pt):
    W, H = area.w, area.h

    def sol(x, y):
        return x < 0 or y < 0 or x >= W or y >= H or area.solid[y // C, x // C]
    x, y = pt
    return not (sol(x - FEET_W, y - FEET_H) or sol(x + FEET_W, y - FEET_H) or sol(x - FEET_W, y) or sol(x + FEET_W, y))


maps = []
for build in (areas.meadow, areas.woods, areas.shore, areas.clouds):
    ar = build()
    maps.append(ar)
    bad = reachable_spots(ar)
    check(not bad, f'{ar.name}: Pip can reach all {len(ar.spots)} container spots (none off the ground), '
                   f'{len(ar.doors)} house door and {len(ar.exits)} exit(s) with room to walk in {bad or ""}')
bad = arrivals_ok(maps)
check(not bad, f'every exit lands on walkable ground in the next area, outside its exits {bad or ""}')


# step 8.4: Momo's heart meter (viewer.c draw_meter) for every spot where Pip
# wakes a sleeping Momo (feet within 34 px of Momo's middle, walkable): the
# bubble clears every signpost and stays on screen. (It can reach the
# counter pill when Pip stands below Momo: the pill hides while it shows.)
MW, MH, TAIL, BOB = 57, 28, 4, 2


def walkable(area, x, y):
    def sol(x, y):
        return x < 0 or y < 0 or x >= area.w or y >= area.h or area.solid[y // C, x // C]
    return not (sol(x - FEET_W, y - FEET_H) or sol(x + FEET_W, y - FEET_H) or sol(x - FEET_W, y) or sol(x + FEET_W, y))


# step 8.5: Cloud Hill's bridges are wide enough to turn onto (the sky beside
# them is solid), and its collision has no one-cell notches in an edge
cl = maps[3]


def lane(area, x0, y0):                     # width of the run of walkable feet x through (x0, y0)
    if not walkable(area, x0, y0):
        return 0
    lo = hi = x0
    while walkable(area, lo - 1, y0):
        lo -= 1
    while walkable(area, hi + 1, y0):
        hi += 1
    return hi - lo + 1


for name, x0, ys, old in (('Momo\'s bridge', 394, range(108, 149, 2), 18), ('the garden bridge', 92, range(246, 273, 2), 14)):
    w = min(lane(cl, x0, y) for y in ys)
    check(w >= 30, f'Cloud Hill: {name} has a walkable lane of at least 30 px ({w}; v1.3: {old})')
free = ~cl.solid
nb = np.zeros(free.shape, int)
nb[1:] += free[:-1]; nb[:-1] += free[1:]; nb[:, 1:] += free[:, :-1]; nb[:, :-1] += free[:, 1:]
notches = int((cl.solid & (nb >= 3)).sum())
check(notches == 0, f'Cloud Hill: no solid cell with 3 walkable neighbours (a notch Pip sticks on): {notches}')

def hit(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


for ar in maps:
    for gxy in ar.gates:
        gx, gy = gxy[0] + gxy[2] // 2, gxy[1] + gxy[3]
        signs, offscreen, spots = set(), 0, 0
        for py in range(gy - 8 - 34, gy - 8 + 35):
            for px in range(gx - 34, gx + 35):
                if (px - gx) ** 2 + (py - gy + 8) ** 2 >= 34 * 34 or not walkable(ar, px, py):
                    continue
                spots += 1
                cx = min(max(px - 120, 0), ar.w - 240)
                cy = min(max(py - 12 - 80, 0), ar.h - 160)
                sx = min(max(gx - MW // 2 - cx, 2), 240 - 2 - MW)
                sy = gy - 32 - 4 - MH - cy
                screen = (sx, sy - BOB, sx + MW, sy + MH + TAIL + BOB)
                box = (screen[0] + cx, screen[1] + cy, screen[2] + cx, screen[3] + cy)
                signs |= {sg for sg in ar.signs if hit(box, sg)}
                offscreen += screen[1] < 0 or screen[3] > 160
        check(spots and not signs and not offscreen,
              f'{ar.name}: Momo at {gx},{gy}: the heart meter clears every sign ({sorted(signs) or "none hidden"}) '
              f'and stays on screen ({spots} spots Pip wakes Momo from; off screen {offscreen})')

img = areas.collision_preview(a)
Image.fromarray(img[..., :3]).resize((a.w * 2, a.h * 2), Image.NEAREST).save(os.path.join(OUT, 'map_collision.png'))
if fails:
    sys.exit(1)
print('all map checks passed')
