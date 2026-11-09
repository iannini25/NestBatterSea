# High zoom crop of an official plan with a labelled 10 px ruler on the edges and faint 10 px grid.
# python zoom.py <plan> x0 y0 x1 y1 k out.png
import sys
from PIL import Image, ImageDraw, ImageFont
from planimg import load

name = sys.argv[1]
x0, y0, x1, y1, k = map(int, sys.argv[2:7])
out = sys.argv[7]
im = load(name).crop((x0, y0, x1, y1)).resize(((x1 - x0) * k, (y1 - y0) * k), Image.NEAREST)
M = 34
can = Image.new('RGB', (im.width + M, im.height + M), (255, 255, 255))
can.paste(im, (M, M))
d = ImageDraw.Draw(can, 'RGBA')
try:
    f = ImageFont.truetype('arial.ttf', 11)
except Exception:
    f = ImageFont.load_default()
for x in range(((x0 + 4) // 5) * 5, x1 + 1, 5):
    X = M + (x - x0) * k
    major = x % 10 == 0
    d.line([(X, M), (X, can.height)], fill=(0, 110, 255, 70 if major else 28), width=1)
    if major:
        d.text((X - 10, 2 + (x // 10 % 2) * 14), str(x), fill=(0, 60, 200), font=f)
for y in range(((y0 + 4) // 5) * 5, y1 + 1, 5):
    Y = M + (y - y0) * k
    major = y % 10 == 0
    d.line([(M, Y), (can.width, Y)], fill=(255, 0, 110, 70 if major else 28), width=1)
    if major:
        d.text((2, Y - 6), str(y), fill=(200, 0, 90), font=f)
can.save(out)
print(out, can.size)
