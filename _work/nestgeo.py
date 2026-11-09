"""
Shared geometry for the Nest Battersea flight work.

One coordinate system: ORIG = pixels of the official CGI _refs/cgi-oficial/01-night-river.jpg
(2560 x 1920). The official high-res tower render tower-night.png (680 x 1840, "TN") sits
inside it at scale 0.5, top-left (1181, 329) - measured by normalised cross-correlation
(score 0.83 at scale 0.500).

Sources (all official imagery, upscaled with Higgsfield's structure-preserving upscaler):
  frames/full_up.jpg   whole 01-night-river.jpg, 4K
  frames/tower_up.png  tower-night.png, 4K (3.176 px per TN px)
"""
import json, os
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
F = lambda *p: os.path.join(HERE, 'frames', *p)

def tn2o(x, y):
    return 1181 + x / 2.0, 329 + y / 2.0

def o2tn(X, Y):
    return 2.0 * (X - 1181), 2.0 * (Y - 329)

GEO = json.load(open(F('geometry.json')))
# master framing (16:9) in ORIG coords
MASTER = GEO['master_orig']

def tn_box_to_o(b):
    x0, y0 = tn2o(b[0], b[1]); x1, y1 = tn2o(b[2], b[3])
    return [x0, y0, x1, y1]

class Sources:
    def __init__(self, gray=False):
        mode = 'L' if gray else 'RGB'
        self.full = Image.open(F('full_up.jpg')).convert(mode)
        self.fs = self.full.width / 2560.0
        self.tower = Image.open(F('tower_up.png')).convert(mode)
        self.ts = self.tower.width / 680.0          # px per TN px

    def view(self, cx, cy, w, out=(1920, 1080), prefer_tower_below=760):
        """16:9 window of width w (ORIG px) centred at (cx, cy).
        Close views use the sharper official tower render wherever it covers the window
        and the full CGI around it, so the reference never switches source mid-frame."""
        h = w * out[1] / out[0]
        X0, Y0, X1, Y1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
        x0, y0 = o2tn(X0, Y0); x1, y1 = o2tn(X1, Y1)
        if w < prefer_tower_below and x0 >= 0 and y0 >= 0 and x1 <= 680 and y1 <= 1840:
            box = tuple(v * self.ts for v in (x0, y0, x1, y1))
            return self.tower.resize(out, Image.LANCZOS, box=box)
        box = tuple(v * self.fs for v in (X0, Y0, X1, Y1))
        img = safe_resize(self.full, box, out)
        if w < prefer_tower_below:
            # paste the part covered by the tower render (TN 0..680 x 0..1840)
            ix0, iy0, ix1, iy1 = max(x0, 0), max(y0, 0), min(x1, 680), min(y1, 1840)
            if ix1 - ix0 > 4 and iy1 - iy0 > 4:
                sx, sy = out[0] / (x1 - x0), out[1] / (y1 - y0)
                pw, ph = max(1, round((ix1 - ix0) * sx)), max(1, round((iy1 - iy0) * sy))
                part = self.tower.resize((pw, ph), Image.LANCZOS, box=tuple(v * self.ts for v in (ix0, iy0, ix1, iy1)))
                img.paste(part, (round((ix0 - x0) * sx), round((iy0 - y0) * sy)))
        return img

def safe_resize(im, box, out):
    """resize(box=...) that tolerates boxes partly outside the image (outside = black)."""
    x0, y0, x1, y1 = box
    W, H = im.size
    if x0 >= 0 and y0 >= 0 and x1 <= W and y1 <= H:
        return im.resize(out, Image.LANCZOS, box=box)
    sx, sy = out[0] / (x1 - x0), out[1] / (y1 - y0)
    cx0, cy0, cx1, cy1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
    canvas = Image.new(im.mode, out, 0)
    if cx1 <= cx0 or cy1 <= cy0:
        return canvas
    pw, ph = max(1, round((cx1 - cx0) * sx)), max(1, round((cy1 - cy0) * sy))
    part = im.resize((pw, ph), Image.LANCZOS, box=(cx0, cy0, cx1, cy1))
    canvas.paste(part, (round((cx0 - x0) * sx), round((cy0 - y0) * sy)))
    return canvas

def framing_of(box):
    """[x0,y0,x1,y1] -> (cx, cy, w)"""
    return ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2, box[2] - box[0])

def ease(t):
    # smootherstep: zero velocity and acceleration at both ends
    return t * t * t * (t * (t * 6 - 15) + 10)

def path(t, start, end):
    """Camera framing at t in [0,1]: constant-rate zoom toward the end centre."""
    c0x, c0y, w0 = start
    c1x, c1y, w1 = end
    e = ease(t)
    w = w0 * (w1 / w0) ** e
    k = (w - w1) / (w0 - w1)                 # 1 -> 0
    return (c1x + (c0x - c1x) * k, c1y + (c0y - c1y) * k, w)
