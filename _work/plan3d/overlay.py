# Overlay a top down render on the official plan crop at the same scale.
# python overlay.py <plan> x0 y0 x1 y1 k <render.png> <out.jpg> [label]
import sys
from PIL import Image, ImageDraw, ImageFont
from planimg import load

plan = sys.argv[1]
x0, y0, x1, y1, k = map(int, sys.argv[2:7])
ren, out = sys.argv[7], sys.argv[8]
label = sys.argv[9] if len(sys.argv) > 9 else ''
base = load(plan).crop((x0, y0, x1, y1)).resize(((x1 - x0) * k, (y1 - y0) * k), Image.LANCZOS).convert('RGBA')
r = Image.open(ren).convert('RGBA').resize(base.size)
# left: plan, middle: render, right: render at 55 % over the plan
a = r.copy()
a.putalpha(r.getchannel('A').point(lambda v: int(v * 0.55)))
mix = base.copy()
mix.alpha_composite(a)
bg = Image.new('RGBA', base.size, (24, 24, 30, 255))
bg.alpha_composite(r)
W, H = base.size
sheet = Image.new('RGB', (W * 3, H + 30), (255, 255, 255))
for i, im in enumerate((base, bg, mix)):
    sheet.paste(im.convert('RGB'), (i * W, 30))
d = ImageDraw.Draw(sheet)
try:
    f = ImageFont.truetype('arial.ttf', 16)
except Exception:
    f = ImageFont.load_default()
for i, t in enumerate(('official plan', 'model from above', 'model over the plan')):
    d.text((i * W + 8, 6), f'{label}  {t}', fill=(20, 20, 20), font=f)
sheet.save(out, quality=88)
print(out, sheet.size)
