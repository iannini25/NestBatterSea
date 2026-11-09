# The wheelchair accessible (Part M4(3)) layout for the Accessible homes card.
# Source: the official "Heliport House Wheelchair 7c" slide (_refs/plantas-oficiais/wheelchair.png,
# the same 2000 x 1447 file published on nestbattersea.co.uk/disabled-accessible-homes).
# The slide is a transparent PNG: it is composited over the paper colour used by the affordable plans
# (never colour keyed), cropped to the flat itself, and the two dashed leader lines that tie it to
# the key plan are painted out. Nothing on the plan is redrawn or added.
import os, sys
import numpy as np
from PIL import Image, ImageFilter
import cv2

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = os.path.join(ROOT, '_refs', 'plantas-oficiais', 'wheelchair.png')
OUT = os.environ.get('WC_OUT') or os.path.join(ROOT, 'assets', 'site', 'plans')
DBG = sys.argv[1] if len(sys.argv) > 1 else None
PAPER = (243, 238, 232)                    # the backdrop of the aff-* plans
BOX = (598, 606, 1786, 1400)               # the flat, its balconies and turning circles; no key plan, no title box
UP = 2                                     # supersample the line work before the export sizes


def main():
    rgba = Image.open(SRC).convert('RGBA')
    # paint out the legend box (its facts are in the caption) and the key plan before cropping
    a = np.asarray(rgba).copy()
    a[600:760, 1738:1800, 3] = 0
    a[:792, :772, 3] = 0                   # the corner of the key plan
    rgba = Image.fromarray(a, 'RGBA')
    bg = Image.new('RGBA', rgba.size, PAPER + (255,))
    bg.alpha_composite(rgba)
    im = np.asarray(bg.convert('RGB')).astype(np.float32)
    H, W = im.shape[:2]
    # opaque white on the slide (door openings, a panel beside the living room) becomes paper like the rest
    wht = np.clip((im.min(-1, keepdims=True) - 238) / 12, 0, 1)
    im = im * (1 - wht) + np.array(PAPER, np.float32) * wht
    lum = im.mean(-1)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    # the angled outer wall of the main bedroom must survive where a leader line runs across it
    wall = np.abs(xx - (612.5 + 0.4675 * (yy - 836))) / np.hypot(1, 0.4675) <= 3.2
    out = im.copy()
    # leader lines (fitted on the clean parts of the slide): y = m x + b. A pixel on the line that is
    # darker than the paper or fill on both sides of it takes the mean of those two sides.
    for m, b, x0, x1 in ((1.3672, 84.68, 590, 800), (0.14221, 374.22, 1600, 1712)):
        n = np.array([m, -1.0]) / np.hypot(m, 1)                 # unit normal
        d = (m * xx - yy + b) / np.hypot(m, 1)
        sel = (np.abs(d) <= 1.8) & (xx >= x0) & (xx <= x1) & ~wall
        ys, xs = np.nonzero(sel)
        k = 3.6
        def at(dx, dy):
            return im[np.clip(np.rint(ys + dy).astype(int), 0, H - 1), np.clip(np.rint(xs + dx).astype(int), 0, W - 1)]
        dd = d[ys, xs]
        # step to just beyond each side of the line
        pa = at(n[0] * (-dd - k), n[1] * (-dd - k))
        pb = at(n[0] * (-dd + k), n[1] * (-dd + k))
        side = (pa + pb) / 2
        dark = lum[ys, xs] < np.minimum(pa.mean(-1), pb.mean(-1)) - 14
        out[ys[dark], xs[dark]] = side[dark]
    im = np.clip(out, 0, 255).astype(np.uint8)
    crop = Image.fromarray(im).crop(BOX)
    if DBG:
        crop.save(os.path.join(DBG, 'wc_crop.png'))
    big = crop.resize((crop.width * UP, crop.height * UP), Image.LANCZOS)
    big = big.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))
    print('crop', crop.size, 'ratio %.3f' % (crop.width / crop.height))
    for w in (720, 1440, 2160):
        h = round(w * crop.height / crop.width)
        r = big.resize((w, h), Image.LANCZOS)
        base = os.path.join(OUT, f'wheelchair-{w}')
        r.save(base + '.jpg', quality=90, optimize=True, progressive=True, subsampling=0)
        r.save(base + '.webp', quality=90, method=6)
        r.save(base + '.avif', quality=78)
        print(w, h, [os.path.getsize(base + e) // 1024 for e in ('.avif', '.webp', '.jpg')], 'KB')


main()
