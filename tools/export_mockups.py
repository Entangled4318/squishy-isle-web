"""Export the numbered mockup set into mockups/.

Usage (from the repo root): python3 tools/export_mockups.py
Writes 4x screenshots (960x640, the exact integer scale the Trimui Brick's
1024x768 screen shows), a contact sheet, the full squishy collection sheet
and an on-device framing preview.
"""
import os
import subprocess
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, 'mockups')
sys.path.insert(0, HERE)

from gba import save_scaled  # noqa: E402
from mockups import SCENES  # noqa: E402

ORDER = ['title', 'meadow', 'open', 'reveal', 'squish', 'shelf', 'shore', 'clouds']


def main():
    os.makedirs(OUT, exist_ok=True)
    paths = []
    for i, name in enumerate(ORDER, 1):
        img, report = SCENES[name]().render()
        path = os.path.join(OUT, f'{i:02d}_{name}.png')
        save_scaled(img, path, 4)
        paths.append(path)
        print(f'{i:02d}_{name}: ' + '; '.join(report))

    ims = [Image.open(p).resize((480, 320), Image.NEAREST) for p in paths]
    sheet = Image.new('RGB', (480 * 2 + 30, 320 * 4 + 50), (58, 50, 72))
    for i, im in enumerate(ims):
        sheet.paste(im, (10 + (i % 2) * 490, 10 + (i // 2) * 330))
    sheet.save(os.path.join(OUT, 'contact_sheet.png'))

    # 4x integer scale on a 1024x768 panel: 960x640 centred, 32/64 px borders
    dev = Image.new('RGB', (1024, 768), (0, 0, 0))
    dev.paste(Image.open(paths[1]), (32, 64))
    dev.save(os.path.join(OUT, 'on_device_1024x768.png'))

    subprocess.run([sys.executable, os.path.join(HERE, 'sheet_squishies.py'), OUT], check=True)


if __name__ == '__main__':
    main()
