# Compare the model's wall rectangles with the black wall mask of the official plan.
# python walldiff.py <apts.json> <apt> <level> <plan> x0 y0 x1 y1 k out.png
#   red   = black on the plan, no wall in the model (a missing wall or a slit)
#   blue  = wall in the model, not black on the plan (a door or opening walled over)
#   grey  = both agree
#   cyan  = glass lines, green = room outlines, orange = door openings / leaves in the model
import sys, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from planimg import load

apts_path, apt, level, plan = sys.argv[1:5]
x0, y0, x1, y1, k = map(int, sys.argv[5:10])
out = sys.argv[10]
A = json.load(open(apts_path))[apt]
lv = [l for l in A['levels'] if l['id'] == level][0]

im = np.asarray(load(plan)).astype(int)
H, W, _ = im.shape
black = im.max(axis=2) < 70
model = np.zeros_like(black)
for w in lv['walls']:
    a, b, c, d = w[:4]
    model[int(round(b)):int(round(d)), int(round(a)):int(round(c))] = True
for dr in lv.get('doors', []):
    pass

reg = (slice(y0, y1), slice(x0, x1))
base = Image.fromarray(np.uint8(255 - (255 - im[reg]) * 0.45)).convert('RGBA')
rgba = np.zeros((y1 - y0, x1 - x0, 4), np.uint8)
bb, mm = black[reg], model[reg]
rgba[bb & mm] = (70, 70, 70, 230)
rgba[bb & ~mm] = (235, 20, 40, 235)
rgba[~bb & mm] = (20, 90, 255, 200)
base.alpha_composite(Image.fromarray(rgba, 'RGBA'))
big = base.resize(((x1 - x0) * k, (y1 - y0) * k), Image.NEAREST).convert('RGB')
d = ImageDraw.Draw(big)
try:
    f = ImageFont.truetype('arial.ttf', 13)
except Exception:
    f = ImageFont.load_default()
T = lambda p: ((p[0] - x0) * k, (p[1] - y0) * k)
for r in lv['rooms']:
    pts = [T(p) for p in r['poly']]
    d.line(pts + [pts[0]], fill=(0, 160, 60, 255), width=1)
    cx = sum(p[0] for p in r['poly']) / len(r['poly'])
    cy = sum(p[1] for p in r['poly']) / len(r['poly'])
    d.text(T((cx - 10, cy)), r['id'], fill=(0, 120, 40, 255), font=f)
for g in lv.get('glass', []):
    d.line([T(g['a']), T(g['b'])], fill=(0, 200, 230, 255), width=3)
for dr in lv.get('doors', []):
    a, b = dr['a'], dr['b']
    d.line([T(a), T(b)], fill=(255, 140, 0, 255), width=4)
# grid
for x in range((x0 // 10 + 1) * 10, x1, 10):
    X = (x - x0) * k
    if x % 50 == 0:
        d.line([(X, 0), (X, big.height)], fill=(0, 120, 255), width=1)
        d.text((X + 2, 2), str(x), fill=(0, 60, 200), font=f)
    else:
        d.line([(X, 0), (X, 8)], fill=(0, 120, 255), width=1)
        d.line([(X, big.height - 8), (X, big.height)], fill=(0, 120, 255), width=1)
for y in range((y0 // 10 + 1) * 10, y1, 10):
    Y = (y - y0) * k
    if y % 50 == 0:
        d.line([(0, Y), (big.width, Y)], fill=(255, 0, 120), width=1)
        d.text((2, Y + 2), str(y), fill=(200, 0, 90), font=f)
    else:
        d.line([(0, Y), (8, Y)], fill=(255, 0, 120), width=1)
        d.line([(big.width - 8, Y), (big.width, Y)], fill=(255, 0, 120), width=1)
big.convert('RGB').save(out)
print(out, big.size)
