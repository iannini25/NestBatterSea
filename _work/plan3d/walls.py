# Decompose the black wall mask of a plan region into axis-aligned rectangles.
import sys, json
import numpy as np
from PIL import Image, ImageDraw
from planimg import load

def largest_rect(mask):
    h, w = mask.shape
    heights = np.zeros(w, dtype=int)
    best = (0, None)
    for y in range(h):
        heights = np.where(mask[y], heights + 1, 0)
        stack = []
        for x in range(w + 1):
            cur = heights[x] if x < w else 0
            start = x
            while stack and stack[-1][1] >= cur:
                sx, sh = stack.pop()
                area = sh * (x - sx)
                if area > best[0]:
                    best = (area, (sx, y - sh + 1, x, y + 1))
                start = sx
            stack.append((start, cur))
    return best

def decompose(mask, min_side=3, min_area=40):
    m = mask.copy()
    rects = []
    while True:
        area, r = largest_rect(m)
        if not r or area < min_area:
            break
        x0, y0, x1, y1 = r
        if min(x1 - x0, y1 - y0) < min_side:
            # too thin: drop these pixels from consideration
            m[y0:y1, x0:x1] = False
            continue
        rects.append([int(x0), int(y0), int(x1), int(y1)])
        m[y0:y1, x0:x1] = False
    return rects

if __name__ == '__main__':
    name, x0, y0, x1, y1 = sys.argv[1], *map(int, sys.argv[2:6])
    a = np.asarray(load(name)).astype(int)
    reg = a[y0:y1, x0:x1]
    dark = (reg.max(axis=2) < 70)
    rects = decompose(dark)
    rects = [[r[0] + x0, r[1] + y0, r[2] + x0, r[3] + y0] for r in rects]
    json.dump(rects, open(sys.argv[6], 'w'))
    # overlay for checking
    img = load(name).crop((x0, y0, x1, y1)).resize(((x1 - x0) * 2, (y1 - y0) * 2), Image.NEAREST).convert('RGBA')
    ov = Image.new('RGBA', img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for i, r in enumerate(rects):
        rr = [(r[0] - x0) * 2, (r[1] - y0) * 2, (r[2] - x0) * 2 - 1, (r[3] - y0) * 2 - 1]
        d.rectangle(rr, outline=(255, 0, 80, 255), fill=(255, 0, 80, 70))
    img.alpha_composite(ov)
    img.convert('RGB').save(sys.argv[7], quality=90)
    print(len(rects), 'rects')
