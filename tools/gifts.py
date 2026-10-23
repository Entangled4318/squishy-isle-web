"""Gifts the friends send with their letters (step 6.9): one keepsake per
species, 16x16, drawn in palette slots of the friends' own palettes
(squishy_export: 1-5 flavor ramp hi..deep, 6 outline, 7 blush, 8 ink,
9 white), so each gift shows in its friend's flavor colors with no new
palette."""
import numpy as np

from gbaconv import tile4

SLOT = {'.': 0, 'h': 1, 'l': 2, 'b': 3, 's': 4, 'd': 5, 'k': 6, 'p': 7, 'i': 8, 'w': 9}

GIFTS = {
    'bunny': [          # tulip in a little pot
        '....k.k.k.......',
        '...kbkbkbk......',
        '...kblblbk......',
        '...kbhbbsk......',
        '....kbbsk.......',
        '.....kkk........',
        '......k..kk.....',
        '..kk..k.kppk....',
        '.kppk.kkppk.....',
        '..kkppkpkk......',
        '....kkkk........',
        '...kddddk.......',
        '...kdwssk.......',
        '....ksssk.......',
        '....kkkk........',
    ],
    'kitty': [          # ball of yarn with a loose end
        '.....kkkkk......',
        '...kkblbbbkk....',
        '..kbhlbsbbbsk...',
        '..kblbsbbbssk...',
        '.kbbbsbbbsbssk..',
        '.kbbsbbbsbbssk..',
        '.kbsbbbsbbsssk..',
        '.kbbbbsbbssssk..',
        '..ksbsbbssssk...',
        '..ksssbssssdk...',
        '...kkssssddkk...',
        '.....kkkkkk.kk..',
        '..............kk',
    ],
    'bear': [           # honey pot with a heart label and a lid
        '.....kkkkk......',
        '....kwhhhhk.....',
        '...kkkkkkkkk....',
        '...klllllllk....',
        '..kblbbbbbbbk...',
        '..kblbkkbkkbk...',
        '..kbbkppkppkk...'.replace('kk...', 'sk...'),
        '..kbbkpppppsk...',
        '..kbbbkpppksk...',
        '..kbbbbkpkbsk...',
        '..kbbbbbkbbsk...',
        '...kbbbbbbsk....',
        '...kssssssdk....',
        '....kkkkkkk.....',
    ],
    'chick': [          # little bell on a bow
        '....kk...kk.....',
        '...kppk.kppk....',
        '....kkpkpkk.....',
        '......kpk.......',
        '.....kkkkk......',
        '....khlbbbk.....',
        '...khlbbbbsk....',
        '...klbbbbbsk....',
        '..klbbbbbbssk...',
        '..kbbbbbbbssk...',
        '.kkkkkkkkkkkkk..',
        '.kddddddddddd k'[:14] + 'k.',
        '.kkkkkkikkkkkk..',
        '......kiik......',
        '.......kk.......',
    ],
    'frog': [           # little crown
        '..k....k....k...',
        '.kwk..kwk..kwk..',
        '.kbk..kbk..kbk..',
        '.kbbk.kbk.kbbk..',
        '.kbhbkbbbkbbbk..',
        '.kbbbbbpbbbbsk..',
        '.kbbbbpppbbbsk..',
        '.kbbbbbpbbbssk..',
        '.kssssssssssdk..',
        '.kwbwbwbwbwbwk..',
        '.kkkkkkkkkkkkk..',
    ],
    'fox': [            # autumn leaf on a twig
        '.......kk.......',
        '......kbbk......',
        '.....kbhbbk.....',
        '..kk.kbhbbk.kk..',
        '.kbbkbbhbbbkbbk.',
        '.kbbbbbhbbbbbsk.',
        '..kbbbbhbbbbsk..',
        '.kbbbbbhbbbbssk.',
        '.kbbbbbhbbbsssk.',
        '..kkbbbhbbsskk..',
        '....kkshsskk....',
        '......kdk.......',
        '......kdk.......',
        '.......k........',
    ],
    'dino': [           # spotted egg
        '......kkkk......',
        '.....khlbbk.....',
        '....khlbbbbk....',
        '....klbssbbk....',
        '...kbbssbbbsk...',
        '...kbbbbbbssk...',
        '..kbbbbbssbssk..',
        '..kbssbbssbssk..',
        '..kbssbbbbbssk..',
        '..kbbbbbbbsssk..',
        '...kbbbssssdk...',
        '...kssssssddk...',
        '....kkddddkk....',
        '......kkkk......',
    ],
    'shroom': [         # tiny mushroom lamp
        '.....kkkkkk.....',
        '...kkbwbbwbkk...',
        '..kbhbbbbbbbsk..',
        '.kbwbbbwbbbwbsk.',
        '.kbbbbbbbbbbbsk.',
        '.kkkkkkkkkkkkkk.',
        '.....kwhhhk.....',
        '.....kwhhhk.....',
        '.....kwhhhk.....',
        '....kkkkkkkk....',
        '...kddddddddk...',
        '...kkkkkkkkkk...',
    ],
    'whale': [          # toy sailboat
        '.......k........',
        '.......kk.......',
        '.......kwk......',
        '.......kwwk.....',
        '.......kwwwk....',
        '.......kwwwwk...',
        '.......kwwwwwk..',
        '.......kkkkkkkk.',
        '.......k........',
        'kkkkkkkkkkkkkkkk',
        'kbhbbbbbbbbbbbsk',
        '.kbbpbbbbbpbbsk.',
        '..kbbbbbbbbbsk..',
        '...kssssssssk...',
        '....kkkkkkkk....',
    ],
    'octo': [           # heart locket with a little ring
        '.......kk.......',
        '......k..k......',
        '......k..k......',
        '..kkk..kk.kkk...',
        '.kbhbk.kk.kbbbk.'[:15],
        'kbhbbbkkkkbbbbsk'[:15],
        'kbhbbbbbbbbbbsk.',
        'kbbbbbbwbbbbssk.',
        '.kbbbbbbbbbssk..',
        '..kbbbbbbbssk...',
        '...kbbbbbssk....',
        '....kbbbssk.....',
        '.....kbssk......',
        '......kkk.......',
    ],
    'seal': [           # beach ball
        '.....kkkkkk.....',
        '...kkwwbbbbkk...',
        '..kwwwwbbbbbbk..',
        '.kwhwwwbbbbbbsk.',
        '.kwwwwwbbbbbssk.',
        'kpppppwwwwwbbssk',
        'kppppppwwwwwwssk',
        'kpppppwwwwwwwwsk',
        'kppppbbbbbwwwwsk',
        '.kpbbbbbbbbwwsk.',
        '.kbbbbbbbbbbssk.',
        '..kbbbbbbbbssk..',
        '...kkssssddkk...',
        '.....kkkkkk.....',
    ],
    'crab': [           # sand bucket
        '....kkkkkkkk....',
        '...k........k...',
        '..k..........k..',
        '..kkkkkkkkkkkk..',
        '..kwhhhhhhhhlk..',
        '..kbbbbbbbbbsk..',
        '..kbhbpbbpbbsk..',
        '...kbbbbbbbsk...',
        '...kbbpbbpbsk...',
        '...kbbbbbbbsk...',
        '...kbbbbbbssk...',
        '....ksssssdk....',
        '....kkkkkkkk....',
    ],
    'cloud': [          # umbrella
        '.......kk.......',
        '.....kkbbkk.....',
        '...kkbhbbbbkk...',
        '..kbhbbbbbbbbk..',
        '.kbhbbbbbbbbbsk.',
        '.kbbbbbbbbbbbsk.',
        'kbbbbbbbbbbbbssk',
        'kkkdkkkdkkkdkkkk',
        '.......kk.......',
        '.......kk.......',
        '.......kk.......',
        '.......kk.......',
        '....kk.kk.......',
        '....kkkk........',
    ],
    'star': [           # star wand
        '.....kk.........',
        '....kbbk........',
        'kkkkbhbbkkkk....',
        'kbbbbhbbbbbk....',
        '.kbbbbbbbbk.....',
        '..kbbbbbbk......',
        '..kbbkkbbk......',
        '.kbbk.kkbbk.....',
        '.kkk..kpkkk.....',
        '.......kpk......',
        '........kpk.....',
        '.........kpk....',
        '..........kpk...',
        '...........kk...',
    ],
    'planet': [         # toy rocket
        '.......kk.......',
        '......kbbk......',
        '.....kbhbbk.....',
        '.....kbhbbk.....',
        '.....kbwwbk.....',
        '.....kwiiwk.....',
        '.....kbwwbk.....',
        '.....kbbbsk.....',
        '....kkbbbskk....',
        '...kpkbbbskpk...',
        '..kppkbbbskppk..',
        '..kkkkkkkkkkkk..',
        '......kppk......',
        '.......kk.......',
    ],
    'uni': [            # sparkly gem
        '...kkkkkkkkk....',
        '..khhwlhhlbbk...',
        '.khwhlllhlbbsk..',
        'kkkkkkkkkkkkkkk.',
        'klhhlbbbbbbbssk.',
        '.klhlbbbbbbbsk..',
        '..klhbbbbbbsk...',
        '...klbbbbbssk...',
        '....klbbbssk....',
        '.....klbssk.....',
        '......kbsk......',
        '.......kk.......',
    ],
}


def gift_index(species):
    """16x16 array of palette slots, the drawing standing on the bottom row."""
    rows = GIFTS[species]
    w = max(len(r) for r in rows)
    idx = np.zeros((16, 16), np.uint8)
    top = 16 - len(rows)
    left = (16 - w) // 2
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            idx[top + y, left + x] = SLOT[ch if ch in SLOT else '.']
    return idx


def gift_tiles(species):
    idx = gift_index(species)
    return b''.join(tile4(idx[ty:ty + 8, tx:tx + 8]) for ty in (0, 8) for tx in (0, 8))


def preview_rgba(species, flavor):
    """RGBA picture of a gift in a flavor, for previews and checks."""
    from palette import FL, C
    from gba import new
    ramp = FL[flavor]
    cols = [None, ramp[0], ramp[1], ramp[2], ramp[3], ramp[4], ramp[5], ramp[6], C['ink'], C['white']]
    idx = gift_index(species)
    img = new(16, 16)
    for y in range(16):
        for x in range(16):
            if idx[y, x]:
                img[y, x, :3] = cols[idx[y, x]]
                img[y, x, 3] = 255
    return img


if __name__ == '__main__':
    from gba import save_scaled
    from squishies import AREAS
    from palette import FLAVOR_ORDER
    rows = []
    for a in AREAS:
        for sp in a[3]:
            rows.append(np.concatenate([preview_rgba(sp, fl) for fl in FLAVOR_ORDER], axis=1))
    grid = np.concatenate([np.concatenate(rows[i:i + 4], axis=0) for i in range(0, 16, 4)], axis=1)
    bg = grid.copy()
    bg[..., :3] = (250, 240, 232)
    m = grid[..., 3] > 0
    bg[m] = grid[m]
    bg[..., 3] = 255
    save_scaled(bg, 'gifts.png', 5)
