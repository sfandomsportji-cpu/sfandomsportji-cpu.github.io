#!/usr/bin/env python3
"""Create transparent KIA/Samsung logos; retain original source files unchanged."""
from collections import deque
from pathlib import Path
from PIL import Image

BASE = Path(__file__).resolve().parents[2] / "assets" / "teams" / "kbo"

def prepare(name):
    original = Image.open(BASE / (name + ".png")).convert("RGBA")
    w, h = original.size
    pixels = original.load()
    outside = bytearray(w * h)
    queue = deque()

    def visit(x, y):
        k = y * w + x
        if outside[k]:
            return
        r, g, b, a = pixels[x, y]
        if a == 0 or (r >= 240 and g >= 240 and b >= 240):
            outside[k] = 1
            queue.append(k)

    for x in range(w):
        visit(x, 0)
        visit(x, h - 1)
    for y in range(h):
        visit(0, y)
        visit(w - 1, y)

    while queue:
        n = queue.popleft()
        x, y = n % w, n // w
        if x:
            visit(x - 1, y)
        if x + 1 < w:
            visit(x + 1, y)
        if y:
            visit(x, y - 1)
        if y + 1 < h:
            visit(x, y + 1)

    for n, removed in enumerate(outside):
        if removed:
            x, y = n % w, n // w
            r, g, b, a = pixels[x, y]
            pixels[x, y] = (r, g, b, 0)

    bbox = original.getchannel("A").getbbox()
    if not bbox:
        raise ValueError("Empty crest: " + name)
    artwork = original.crop(bbox)
    pad = max(3, round(max(artwork.size) * 0.03))
    result = Image.new("RGBA", (artwork.width + pad * 2, artwork.height + pad * 2), (0, 0, 0, 0))
    result.alpha_composite(artwork, (pad, pad))
    destination = BASE / "clean" / (name + ".png")
    destination.parent.mkdir(parents=True, exist_ok=True)
    result.save(destination, "PNG", optimize=True)
    print(name, "crest", result.size, "outside background removed", sum(outside))

if __name__ == "__main__":
    for club in ("KIA", "samsung"):
        prepare(club)
