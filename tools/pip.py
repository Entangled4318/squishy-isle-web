"""Pip, the player: a small kid in a bunny hoodie. Hand-placed pixels.

Frames are 16x32 OBJ cells. Rows are written as left halves for the
symmetric front and back views and mirrored, so both sides always match.
"""
from gba import from_ascii, flip_h, rgb15

PIP = {
    'k': rgb15('#4a3a5c'),   # ink outline
    'w': rgb15('#fffdfa'),   # white
    'a': rgb15('#fff0f4'),   # hood light
    'b': rgb15('#ffd0de'),   # hood base
    'c': rgb15('#f5aac2'),   # hood shade
    'd': rgb15('#e8849f'),   # inner ear / deep shade
    's': rgb15('#ffe6d4'),   # skin
    't': rgb15('#f6c8ab'),   # skin shade
    'h': rgb15('#a8745e'),   # hair / shoes
    'p': rgb15('#ff9db6'),   # blush
    'l': rgb15('#cbb8f4'),   # pants
    'm': rgb15('#a894e0'),   # pants shade
    'g': rgb15('#bff0dc'),   # backpack
    'n': rgb15('#86d2b6'),   # backpack shade
}


def _sym(halves):
    return [h + h[::-1] for h in halves]


def _pad(rows, total=32):
    rows = list(rows)
    while len(rows) < total:
        rows.append('.' * 16)
    return rows


# ---- facing down (front) ----------------------------------------------
_HEAD_DOWN = _sym([
    '........',
    '...kk...',
    '..kabk..',
    '..kadk..',
    '..kadk..',
    '..kbdk..',
    '..kbdkkk',
    '.kbbbaaa',
    'kbbbaaaa',
    'kbbahhhh',
    'kbchhhhh',
    'kbahhsss',
    'kbasskks',
    'kbasskks',
    'kbasppss',
    '.kacssss',
    '..kkcccc',
])
# eye shines on the top-left of both eyes, and a tiny smile
_HEAD_DOWN[12] = _HEAD_DOWN[12][:5] + 'w' + _HEAD_DOWN[12][6:9] + 'w' + _HEAD_DOWN[12][10:]
_HEAD_DOWN[14] = _HEAD_DOWN[14][:7] + 'dd' + _HEAD_DOWN[14][9:]

_BODY_DOWN_STAND = [
    '..kbbbbbbbbbbk..',
    '.kbkabbddbbckck.',
    '.kbkabbbbbbckck.',
    '.kskbbbbbbbcksk.',
    '..kkcccccccckk..',
    '...kllllllmmk...',
    '...kllmkkllmk...',
    '...khhk..khhk...',
    '....kk....kk....',
]
_BODY_DOWN_STEP1 = [
    '..kbbbbbbbbbbk..',
    '.kbkabbddbbckck.',
    '.kbkabbbbbbckck.',
    '.kskbbbbbbbcksk.',
    '..kkcccccccckk..',
    '...kllllllmmk...',
    '...kllmkkllmk...',
    '...khhk.kllmk...',
    '....kk..khhk....',
    '.........kk.....',
]
_BODY_DOWN_STEP2 = [
    '..kbbbbbbbbbbk..',
    '.kbkabbddbbckck.',
    '.kbkabbbbbbckck.',
    '.kskbbbbbbbcksk.',
    '..kkcccccccckk..',
    '...kllllllmmk...',
    '...kllmkkllmk...',
    '...kllmk.khhk...',
    '....khhk..kk....',
    '.....kk.........',
]

# ---- facing up (back) -------------------------------------------------
_HEAD_UP = _sym([
    '........',
    '...kk...',
    '..kabk..',
    '..kack..',
    '..kack..',
    '..kbck..',
    '..kbckkk',
    '.kbbbaaa',
    'kbbbaaaa',
    'kbbbbaab',
    'kbbbbbbb',
    'kbcbbbbb',
    'kbcbbbbb',
    'kbccbbbb',
    'kbccbbbb',
    '.kccbbbb',
    '..kkcccc',
])
_BODY_UP_STAND = [
    '..kbkgggggnkbk..',
    '.kbkgggggggnkck.',
    '.kbkggnnggnnkck.',
    '.kskgggggggnksk.',
    '..kkknnnnnnnkk..',
    '...kllllllmmk...',
    '...kllmkkllmk...',
    '...khhk..khhk...',
    '....kk....kk....',
]
_BODY_UP_STEP1 = [
    '..kbkgggggnkbk..',
    '.kbkgggggggnkck.',
    '.kbkggnnggnnkck.',
    '.kskgggggggnksk.',
    '..kkknnnnnnnkk..',
    '...kllllllmmk...',
    '...kllmkkllmk...',
    '...khhk.kllmk...',
    '....kk..khhk....',
    '.........kk.....',
]

# ---- facing right (side) ----------------------------------------------
_SIDE = [
    '................',
    '.....kk.........',
    '....kabk........',
    '....kadk..kk....',
    '....kadk.kabk...',
    '....kbdk.kadk...',
    '...kkbdkkkbdk...',
    '..kbbbbbbaabk...',
    '.kbbbbbaaaaabk..',
    '.kbbbbbahhhhhk..',
    'kbbbbbhhhhhhhk..',
    'kbcbbbhhsssshk..',
    'kbcbbhssssswkk..',
    'kbccbhsssssksk..',
    'kbccbhsspps dk..'.replace(' ', 's'),
    '.kccbbssssstk...',
    '..kkcccccckk....',
    '..kgkbbbbbbk....',
    '.kggkbbbbbbak...',
    '.kgnkbbbbbbak...',
    '.kgnkbbbbsskk...',
    '..kkkccccckk....',
    '....kllllmk.....',
    '....kllmmmk.....',
    '....khhhhhk.....',
    '.....kkkkk......',
]
_SIDE_STEP = [
    '................',
    '.....kk.........',
    '....kabk........',
    '....kadk..kk....',
    '....kadk.kabk...',
    '....kbdk.kadk...',
    '...kkbdkkkbdk...',
    '..kbbbbbbaabk...',
    '.kbbbbbaaaaabk..',
    '.kbbbbbahhhhhk..',
    'kbbbbbhhhhhhhk..',
    'kbcbbbhhsssshk..',
    'kbcbbhssssswkk..',
    'kbccbhsssssksk..',
    'kbccbhsspps dk..'.replace(' ', 's'),
    '.kccbbssssstk...',
    '..kkcccccckk....',
    '..kgkbbbbbbk....',
    '.kggkbbbbbbak...',
    '.kgnkbbbbbbssk..',
    '.kgnkbbbbbbkk...',
    '..kkkccccckk....',
    '...kllmkllmk....',
    '..khhkkkkhhhk...',
    '...kk....kkk....',
]


def frames():
    down_head = _HEAD_DOWN
    up_head = _HEAD_UP
    f = {}
    f['down0'] = from_ascii(_pad(down_head + _BODY_DOWN_STAND), PIP)
    f['down1'] = from_ascii(_pad(down_head + _BODY_DOWN_STEP1), PIP)
    f['down2'] = from_ascii(_pad(down_head + _BODY_DOWN_STEP2), PIP)
    f['up0'] = from_ascii(_pad(up_head + _BODY_UP_STAND), PIP)
    f['up1'] = from_ascii(_pad(up_head + _BODY_UP_STEP1), PIP)
    f['up2'] = flip_h(f['up1'])
    f['right0'] = from_ascii(_pad(_SIDE), PIP)
    f['right1'] = from_ascii(_pad(_SIDE_STEP), PIP)
    f['left0'] = flip_h(f['right0'])
    f['left1'] = flip_h(f['right1'])
    return f
