"""Write a valid GBA cartridge header into a ROM file.

Usage: python3 gbafix.py ROM [--title TITLE] [--code CODE] [--maker MK]

Sets the Nintendo logo, title, game code, maker code, fixed byte and the
header complement check, and pads the ROM to a 256-byte multiple. The real
BIOS refuses to boot a ROM whose logo or complement is wrong, so emulators
that run a BIOS file (for example mGBA with gba_bios.bin) need this.
"""
import argparse
import sys

# 156-byte compressed logo bitmap. Verified: its CRC-16 (poly 0xA001,
# init 0xFFFF) is 0xCF56, the fixed logo checksum stored in every DS header.
LOGO = bytes.fromhex(
    '24FFAE51699AA2213D84820A84E409AD11248B98C0817F21A352BE199309CE20'
    '10464A4AF82731EC58C7E83382E3CEBF85F4DF94CE4B09C194568AC01372A7FC'
    '9F844D73A3CA9A615897A327FC039876231DC7610304AE56BF38840040A70EFD'
    'FF52FE036F9530F197FBC08560D68025A963BE03014E38E2F9A234FFBB3E0344'
    '780090CB88113A9465C07C6387F03CAFD625E48B380AAC7221D4F807')
LOGO_CRC = 0xCF56


def crc16(data):
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def complement(hdr):
    return (-(sum(hdr[0xA0:0xBD]) + 0x19)) & 0xFF


def fix(rom, title, code, maker):
    assert len(LOGO) == 156 and crc16(LOGO) == LOGO_CRC, 'logo data corrupt'
    rom = bytearray(rom)
    if len(rom) < 0xC0:
        raise ValueError('ROM smaller than a header')
    rom[0x04:0xA0] = LOGO
    rom[0xA0:0xAC] = title.upper().encode('ascii')[:12].ljust(12, b'\0')
    rom[0xAC:0xB0] = code.upper().encode('ascii')[:4].ljust(4, b'0')
    rom[0xB0:0xB2] = maker.upper().encode('ascii')[:2].ljust(2, b'0')
    rom[0xB2] = 0x96
    rom[0xB3] = 0x00
    rom[0xB4] = 0x00
    rom[0xB5:0xBC] = bytes(7)
    rom[0xBC] = 0x00
    rom[0xBD] = complement(rom)
    rom[0xBE:0xC0] = bytes(2)
    pad = (-len(rom)) % 256
    rom += b'\xff' * pad
    return bytes(rom)


def check(rom):
    """Return a list of problems (empty when the header is valid)."""
    errs = []
    if rom[0x04:0xA0] != LOGO:
        errs.append('logo mismatch')
    if rom[0xB2] != 0x96:
        errs.append('fixed byte 0xB2 is not 0x96')
    if rom[0xBD] != complement(rom):
        errs.append('complement check wrong')
    if rom[3] != 0xEA:
        errs.append('entry point is not an ARM branch')
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('rom')
    ap.add_argument('--title', default='SQUISHY ISLE')
    ap.add_argument('--code', default='SQIS')
    ap.add_argument('--maker', default='00')
    a = ap.parse_args()
    data = open(a.rom, 'rb').read()
    out = fix(data, a.title, a.code, a.maker)
    errs = check(out)
    if errs:
        sys.exit('gbafix: ' + ', '.join(errs))
    open(a.rom, 'wb').write(out)
    print(f'gbafix: {a.rom} ok, {len(out)} bytes, title {a.title!r}, code {a.code}')


if __name__ == '__main__':
    main()
