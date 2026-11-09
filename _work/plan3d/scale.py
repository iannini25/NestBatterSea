# Measure the scale bar of the official plans (0..5 m) to get pixels per metre.
from PIL import Image
import numpy as np, sys
im = np.asarray(Image.open('../../_refs/plantas-oficiais/fp-33.png').convert('RGBA').convert('RGB')).astype(int)
H, W, _ = im.shape
# scan rows near the bottom right for the scale bar (black and white blocks with a black outline)
for y in range(1380, 1400):
    row = im[y, 1300:1600]
    dark = (row.sum(axis=1) < 200)
    xs = np.where(dark)[0]
    if len(xs) > 50:
        print(y, xs.min() + 1300, xs.max() + 1300, len(xs))
