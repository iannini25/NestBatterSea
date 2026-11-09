import sys
from PIL import Image, ImageDraw, ImageFont
from planimg import load
name, x0, y0, x1, y1, k, out = sys.argv[1], *map(int, sys.argv[2:7]), sys.argv[7]
im = load(name).crop((x0, y0, x1, y1)).resize(((x1 - x0) * k, (y1 - y0) * k), Image.LANCZOS).convert('RGBA')
ov = Image.new('RGBA', im.size, (0, 0, 0, 0))
d = ImageDraw.Draw(ov)
try:
    f = ImageFont.truetype('arial.ttf', 14)
except Exception:
    f = ImageFont.load_default()
for x in range((x0 // 10 + 1) * 10, x1, 10):
    c = (0, 120, 255, 150) if x % 50 == 0 else (0, 160, 255, 45)
    d.line([((x - x0) * k, 0), ((x - x0) * k, im.height)], fill=c, width=1)
    if x % 50 == 0:
        d.text(((x - x0) * k + 2, 2), str(x), fill=(0, 60, 200, 255), font=f)
for y in range((y0 // 10 + 1) * 10, y1, 10):
    c = (255, 0, 120, 150) if y % 50 == 0 else (255, 0, 120, 45)
    d.line([(0, (y - y0) * k), (im.width, (y - y0) * k)], fill=c, width=1)
    if y % 50 == 0:
        d.text((2, (y - y0) * k + 2), str(y), fill=(200, 0, 90, 255), font=f)
im.alpha_composite(ov)
im.convert('RGB').save(out, quality=92)
print(im.size)
