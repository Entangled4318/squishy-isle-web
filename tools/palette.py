"""Squishy Isle master palette. All values are snapped to GBA 15-bit color."""
from gba import rgb15

C = {}


def _add(**kw):
    for k, v in kw.items():
        C[k] = rgb15(v)


# Shared ink (eyes, text) and whites.
_add(ink='#4a3a5c', ink2='#6b5a80', white='#fffdfa', cream='#fff6e8',
     blush='#ffa3bc', blush_dk='#f07fa2', shadow='#6a5a88')

# Meadow grass.
_add(g_hi='#e2f7c8', g_lt='#cdeeb3', g_base='#b8e6a2', g_dk='#9dd693',
     g_dk2='#84c489', g_ink='#63a17c')

# Flowers.
_add(f_pink='#ffb8cc', f_pink_dk='#f28db0', f_yel='#ffe890', f_yel_dk='#f5c563',
     f_blue='#bcdcff', f_blue_dk='#8fb8f0', f_lav='#dcc8f8', f_lav_dk='#b49ae6',
     f_white='#fffaf4', f_stem='#7fbf7c')

# Sandy path.
_add(p_hi='#fff6e2', p_lt='#fcebcc', p_base='#f5ddb4', p_dk='#e8c79a',
     p_dk2='#d8b085', pebble='#e6d5c8')

# Water.
_add(w_hi='#f2fbff', w_lt='#d2f0fb', w_base='#aee0f4', w_dk='#8ccbec',
     w_dk2='#72b6e2', w_ink='#5a92c4')

# Green tree canopy.
_add(t_hi='#d8f4b4', t_lt='#b9e69c', t_base='#99d28a', t_dk='#7cbc7e',
     t_dk2='#64a676', t_ink='#4d8468')

# Blossom tree canopy.
_add(b_hi='#fff2f6', b_lt='#ffd9e6', b_base='#ffc0d5', b_dk='#f5a2c0',
     b_dk2='#dd86ac', b_ink='#ab618e')

# Trunks and wood.
_add(tr_lt='#ddb095', tr_base='#c49276', tr_dk='#a0725f', tr_ink='#704c52',
     wd_hi='#f6dcc0', wd_lt='#e9c3a0', wd_base='#d6a882', wd_dk='#b98a6c',
     wd_dk2='#9a6f5c', wd_ink='#6e4d55')

# Cottage.
_add(rf_hi='#ffd0d8', rf_lt='#ffb4c2', rf_base='#f898ae', rf_dk='#e07c98',
     rf_ink='#a95a7c', wl_lt='#fffaf0', wl_base='#fbeedb', wl_dk='#ecd6bb',
     wl_ink='#b08f86', dr_lt='#c8f0dc', dr_base='#a6e0c6', dr_dk='#84c8ac',
     win_lt='#e8f6ff', win_base='#c4e4fa', win_dk='#9ccbef')

# Berry Woods: mossy floor (a little deeper and cooler than the meadow),
# soft earth trail, autumn canopy, berries.
_add(mg_hi='#d6efc2', mg_lt='#bce2ab', mg_base='#a0d29a', mg_dk='#86c093', mg_dk2='#6eab89', mg_ink='#568f78')
_add(dt_hi='#fbeedf', dt_lt='#f2ddc6', dt_base='#e6c9aa', dt_dk='#d4b091', dt_dk2='#bd967b')
_add(au_hi='#fff1d8', au_lt='#ffdcaa', au_base='#fcc388', au_dk='#f1a56e', au_dk2='#da8a5e', au_ink='#a8664e')
_add(berry='#ff86a2', berry_dk='#d85f82', bberry='#93a9ef')

# Beach.
_add(s_hi='#fff8ea', s_lt='#fff0d6', s_base='#fce4bf', s_dk='#f1cfa3',
     s_dk2='#e2b98c', s_ink='#c79a78', sea_hi='#f0fcff', sea_lt='#c6f0f6',
     sea_base='#9ee2ee', sea_dk='#7ccde4', sea_dk2='#68b9da', foam='#ffffff')

# Sky / clouds.
_add(sky_top='#c9c6f5', sky_mid='#dcd6fa', sky_lo='#f2dcf2', sky_pk='#ffe2ec',
     sky_pch='#ffe9dc', cl_hi='#ffffff', cl_base='#f6f2ff', cl_dk='#e2dcf6',
     cl_dk2='#cbc2ec', cl_ink='#a79ad6')
# Cloud Hill stars and moon: their fill glints at run time (st_lt -> st_hi)
_add(st_lt='#fff2b0', st_hi='#fffdfa', st_ink='#e0b050')

# UI.
_add(ui_bg='#fff4f7', ui_pk='#ffd2df', ui_pk2='#ffb6ca', ui_line='#e088a8',
     ui_ink='#8a5a7a', ui_mint='#bff0dc', ui_mint2='#93dcc0',
     ui_yel='#fff0a0', ui_yel2='#ffd86a', ui_lav='#e4d6fb', ui_lav2='#c7b0f2',
     ui_blue='#cfe6ff', ui_blue2='#a8ccf6', btn_a='#ff9fb8', btn_a2='#f07a9c',
     btn_a3='#c85b82')

# Squishy flavors: hi, light, base, shade1, shade2, outline, blush.
FLAVORS = {
    'vanilla': ['#fffefa', '#fff8ea', '#fcedd3', '#f0d8b6', '#e0c09a', '#a37e68', '#ffa3bc'],
    'strawberry': ['#fff5f8', '#ffe2ea', '#ffcbd9', '#f7abc0', '#e68ca8', '#b85c82', '#f47ea2'],
    'matcha': ['#f7fff2', '#e4f8d8', '#caedb9', '#aadb9c', '#8cc587', '#5a9170', '#ffa3bc'],
    'taro': ['#fcf8ff', '#efe4fd', '#ddcdf8', '#c6afee', '#ab93dc', '#7864ae', '#ff9fc4'],
    'sparkle': ['#fffde4', '#fff2ae', '#ffe27e', '#f7c860', '#e6aa48', '#b27a30', '#ff9eb0'],
}
FLAVOR_ORDER = ['vanilla', 'strawberry', 'matcha', 'taro', 'sparkle']
FLAVOR_NAME = {'vanilla': 'Vanilla', 'strawberry': 'Strawberry', 'matcha': 'Matcha',
               'taro': 'Taro', 'sparkle': 'Sparkle'}

FL = {k: [rgb15(h) for h in v] for k, v in FLAVORS.items()}

# Fixed accent ramps (light, base, dark) used on squishies.
ACC = {
    'pink': [rgb15(h) for h in ('#ffe0ea', '#ffb6cb', '#ec8fae')],
    'orange': [rgb15(h) for h in ('#ffe0a8', '#ffc070', '#ec9a4e')],
    'cream': [rgb15(h) for h in ('#fffdf6', '#fff4e0', '#f2dcc0')],
    'brown': [rgb15(h) for h in ('#b08a78', '#8a6660', '#6a4c52')],
    'mint': [rgb15(h) for h in ('#dffaf0', '#b4ecd8', '#8ad4bc')],
    'sky': [rgb15(h) for h in ('#e6f6ff', '#bfe4fb', '#93cbef')],
    'gold': [rgb15(h) for h in ('#fff6c8', '#ffe07a', '#e8b44a')],
    'red': [rgb15(h) for h in ('#ffd0d0', '#ff9a9a', '#e07074')],
    'lav': [rgb15(h) for h in ('#f2eaff', '#d8c6fa', '#b69be8')],
    'panda': [rgb15(h) for h in ('#b4aac8', '#8f84aa', '#72688e')],   # Momo's ears and eye patches
}
