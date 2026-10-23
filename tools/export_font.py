"""Export the rounded pixel font for the ROM's variable-width text.

Usage: python3 export_font.py OUTDIR  -> OUTDIR/font_data.c/.h
Each glyph: width (1..8) and 9 rows of bit masks (bit 0 = leftmost pixel);
rows 0-6 are the body, rows 7-8 hold descenders.
"""
import sys

from font import G
from gbaconv import CWriter

FIRST, LAST = 32, 126


def main(out):
    widths, rows = [], []
    for code in range(FIRST, LAST + 1):
        g = G.get(chr(code), G['?'])
        w = len(g[0])
        widths.append(w)
        for r in range(9):
            row = g[r] if r < len(g) else '.' * w
            mask = 0
            for x, c in enumerate(row):
                if c == '#':
                    mask |= 1 << x
            rows.append(mask)
    cw = CWriter('font_data')
    cw.c.append(f'const uint8_t font_widths[{len(widths)}] = {{{", ".join(map(str, widths))}}};\n')
    cw.h.append(f'extern const uint8_t font_widths[{len(widths)}];\n')
    body = ',\n'.join('    ' + ', '.join(f'0x{v:02X}' for v in rows[i:i + 9]) for i in range(0, len(rows), 9))
    cw.c.append(f'const uint8_t font_rows[{len(rows)}] = {{\n{body}\n}};\n')
    cw.h.append(f'extern const uint8_t font_rows[{len(rows)}];\n')
    cw.define('FONT_FIRST', FIRST)
    cw.define('FONT_LAST', LAST)
    cw.save(out)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'build')
