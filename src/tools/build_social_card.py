#!/usr/bin/env python3
"""Build the local, crawler-friendly 1200x630 SFANDOM link-preview PNG.

Requires Pillow 11.3.0 in GitHub Actions; no network requests or external photos.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'assets' / 'share' / 'sfandom-social-20261010.png'
MARK = ROOT / 'assets' / 'brand' / 'sfandom-mark-512.png'
W, H = 1200, 630


def font(size: int, bold: bool = False):
    filename = 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'
    for p in (Path('/usr/share/fonts/truetype/dejavu') / filename,
              Path('/usr/share/fonts/truetype/liberation') / ('LiberationSans-Bold.ttf' if bold else 'LiberationSans-Regular.ttf')):
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.truetype(filename, size)


def main():
    im = Image.new('RGB', (W, H), '#090C17')
    pixels = im.load()
    for y in range(H):
        for x in range(W):
            g = max(0.0, 1 - ((x - 1020)**2 / 870000 + (y - 80)**2 / 480000))
            r = max(0.0, 1 - ((x - 250)**2 / 430000 + (y - 620)**2 / 500000))
            pixels[x, y] = (int(9 + 13*g + 5*r), int(12 + 11*g), int(23 + 28*g + 6*r))
    draw = ImageDraw.Draw(im, 'RGBA')
    draw.polygon([(900, 0), (1200, 0), (1200, 630), (1100, 630)], fill=(200, 16, 46, 22))
    draw.polygon([(1030, 0), (1200, 0), (1200, 450)], fill=(200, 16, 46, 19))
    draw.rectangle((0, 0, 14, H), fill=(215, 27, 54, 255))
    draw.rounded_rectangle((67, 123, 375, 445), radius=32, fill=(255, 255, 255, 17), outline=(255, 255, 255, 28), width=2)
    if MARK.exists():
        mark = Image.open(MARK).convert('RGBA').resize((282, 282), Image.Resampling.LANCZOS)
        im.paste(mark, (81, 143), mark)
    else:
        draw.rounded_rectangle((90, 144, 355, 412), radius=30, fill=(1, 3, 21, 255))
        draw.text((142, 215), 'SF', font=font(98, True), fill=(250, 250, 252, 255))
    draw.text((414, 178), 'SFANDOM', font=font(99, True), fill=(249, 250, 253, 255))
    draw.text((421, 310), '& KAIRO', font=font(57, True), fill=(245, 65, 85, 255))
    draw.line((422, 405, 1103, 405), fill=(245, 245, 245, 60), width=2)
    draw.text((423, 426), 'SPORTS  |  ANALYSIS  |  COMMUNITY', font=font(23, True), fill=(213, 222, 238, 255))
    draw.text((423, 479), 'PLAY FIRST. ANALYSIS NEXT.', font=font(22), fill=(167, 180, 199, 255))
    draw.text((71, 558), 'sfandom.com', font=font(22, True), fill=(224, 228, 237, 255))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    im.save(OUTPUT, 'PNG', optimize=True)
    print(f'Built {OUTPUT} ({W}x{H}, {OUTPUT.stat().st_size} bytes)')


if __name__ == '__main__':
    main()
