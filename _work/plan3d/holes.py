# Find see through holes in a top down render: pixels inside the home's footprint where
# nothing was drawn (alpha 0 on the transparent canvas).
# python holes.py <apts.json> <apt> <level id> <render.png> x0 y0 x1 y1 k [overlay.png]
import sys, json
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

apts, apt, level, png = sys.argv[1:5]
x0, y0, x1, y1, k = map(float, sys.argv[5:10])
out = sys.argv[10] if len(sys.argv) > 10 else None
A = json.load(open(apts))[apt]
lv = [l for l in A['levels'] if l['id'] == level][0]
im = Image.open(png).convert('RGBA')
W, H = im.size
T = lambda p: ((p[0] - x0) * k, (p[1] - y0) * k)
fp = Image.new('L', (W, H), 0)
d = ImageDraw.Draw(fp)
for r in lv['rooms']:
    if r.get('exterior'):
        continue
    d.polygon([T(p) for p in r['poly']], fill=255)
for w in lv['walls']:
    d.rectangle([T((w[0], w[1])), T((w[2], w[3]))], fill=255)
for s in lv.get('solids', []):
    d.polygon([T(p) for p in s['poly']], fill=255)
for f in lv.get('fills', []):
    d.polygon([T(p) for p in f['poly']], fill=255)
for o in lv.get('doors', []):
    q = o['o']
    d.rectangle([T((q[0], q[1])), T((q[2], q[3]))], fill=255)
# the envelope: rooms and walls with every enclosed gap filled and slits up to 5 px closed,
# so a hole is any spot of it where nothing was drawn
mask = np.asarray(fp) > 0
r = int(round(5 * k))
yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
mask = ndimage.binary_closing(mask, structure=(xx * xx + yy * yy) <= r * r, iterations=1)
mask = ndimage.binary_fill_holes(mask)
# the double height void and the stair well of an upper floor are meant to be open
cut = Image.new('L', (W, H), 0)
cd = ImageDraw.Draw(cut)
if lv.get('void'):
    cd.polygon([T(p) for p in lv['void']], fill=255)
if lv is not A['levels'][0] and A['levels'][0].get('stair'):
    b = A['levels'][0]['stair']['box']
    cd.rectangle([T((b[0], b[1] + 4)), T((b[2], b[3]))], fill=255)
mask &= ~(np.asarray(cut) > 0)
mask = ndimage.binary_erosion(mask, iterations=2)
alpha = np.asarray(im)[:, :, 3]
holes = mask & (alpha < 16)
lab, n = ndimage.label(holes)
found = []
for i, sl in enumerate(ndimage.find_objects(lab)):
    area = int((lab[sl] == i + 1).sum())
    if area < 2:
        continue
    ys, xs = sl
    found.append((area, x0 + xs.start / k, y0 + ys.start / k, x0 + xs.stop / k, y0 + ys.stop / k))
found.sort(reverse=True)
print(f'{apt} {level}: {len(found)} holes')
for a, ax, ay, bx, by in found[:40]:
    print(f'  {a:6d} px  plan [{ax:.1f}, {ay:.1f}, {bx:.1f}, {by:.1f}]')
if out:
    ov = im.copy()
    o = Image.new('RGBA', im.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(o)
    for a, ax, ay, bx, by in found:
        od.rectangle([T((ax - 2, ay - 2)), T((bx + 2, by + 2))], outline=(255, 0, 60, 255), width=2)
    bg = Image.new('RGBA', im.size, (20, 20, 30, 255))
    bg.alpha_composite(ov)
    bg.alpha_composite(o)
    bg.convert('RGB').save(out)
