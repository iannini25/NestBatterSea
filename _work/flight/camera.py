"""
Exact camera moves over the official Nest Battersea render.

Nothing is generated: every frame is the official image itself, seen by a virtual camera
that pans and zooms. Two official sources are used, registered to each other (ECC 0.9989):
  W  = the original night river render, 4204 x 3153 (nestbattersea.co.uk 2153_031_72_00-1-1.jpg)
  TU = the official close render of the tower (tower-night.png, 680 x 1840, twice the density
       of the 2560 px version), upscaled 3.18x (frames/tower_up.png), used where it covers.
All camera maths is in ORIG coordinates: the 2560 x 1920 version of the render, continuous
(pixel i covers [i, i+1)). The site's facade image is the ORIG box [160, 140, 2560, 1490]
at 2560 x 1440 (master px), so ORIG = 160 + m / (16 / 15), 140 + m / (16 / 15).
"""
import math
import os

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.dirname(HERE)
ROOT = os.path.dirname(WORK)

OUT_W, OUT_H = 1920, 1080
K_W = 4204 / 2560.0                      # W px per ORIG px
T_SCALE = (0.50000316, 0.5000003)        # ORIG px per T px (ECC)
T_OFF = (1179.9943, 329.9968)            # ORIG position of T's origin (ECC)
TU_S = (2160 / 680.0, 5843 / 1840.0)     # TU px per T px
MASTER_BOX = (160.0, 140.0, 2560.0, 1490.0)
M2O = 2400.0 / 2560.0                    # ORIG px per master px


def master_to_orig(x, y):
    return MASTER_BOX[0] + x * M2O, MASTER_BOX[1] + y * M2O


def orig_to_master(x, y):
    return (x - MASTER_BOX[0]) / M2O, (y - MASTER_BOX[1]) / M2O


def pyramid(img, levels=7):
    out = [img]
    for _ in range(levels):
        h, w = out[-1].shape[:2]
        if min(h, w) < 64:
            break
        out.append(cv2.resize(out[-1], ((w + 1) // 2, (h + 1) // 2), interpolation=cv2.INTER_AREA))
    return out


class Source:
    """an image pyramid plus the continuous affine ORIG -> source pixels (x = ax*X + bx)"""

    def __init__(self, img, ax, bx, ay, by, name):
        self.levels = pyramid(img)
        self.ax, self.bx, self.ay, self.by = ax, bx, ay, by
        self.name = name
        self.h0, self.w0 = img.shape[:2]

    def sample(self, cx, cy, w, out_w=OUT_W, out_h=OUT_H, magnify=cv2.INTER_CUBIC):
        """render the camera (centre cx, cy, width w in ORIG px) from this source, float32 RGB"""
        px = w / out_w                                   # ORIG px per output px
        foot = px * self.ax                              # source px per output px
        lf = math.log2(foot) if foot > 0 else 0.0
        if lf <= 0:
            return self._warp(0, cx, cy, px, out_w, out_h, magnify)
        l0 = int(math.floor(lf))
        fr = lf - l0
        l0 = min(l0, len(self.levels) - 1)
        a = self._warp(l0, cx, cy, px, out_w, out_h, cv2.INTER_LINEAR)
        if fr < 1e-3 or l0 + 1 >= len(self.levels):
            return a
        b = self._warp(l0 + 1, cx, cy, px, out_w, out_h, cv2.INTER_LINEAR)
        return a * (1 - fr) + b * fr

    def _warp(self, L, cx, cy, px, out_w, out_h, interp):
        img = self.levels[L]
        h, w = img.shape[:2]
        rx, ry = w / self.w0, h / self.h0               # level px per base px
        # output index u -> ORIG X = cx + (u + 0.5 - out_w / 2) * px
        # -> source continuous xs = ax * X + bx -> level index = xs * rx - 0.5
        sx = px * self.ax * rx
        sy = px * self.ay * ry
        ox = (self.ax * (cx + (0.5 - out_w / 2) * px) + self.bx) * rx - 0.5
        oy = (self.ay * (cy + (0.5 - out_h / 2) * px) + self.by) * ry - 0.5
        M = np.array([[sx, 0, ox], [0, sy, oy]], np.float64)
        r = cv2.warpAffine(img, M, (out_w, out_h), flags=interp | cv2.WARP_INVERSE_MAP,
                           borderMode=cv2.BORDER_REPLICATE)
        return r.astype(np.float32)


_cache = {}


def sources():
    if 'W' in _cache:
        return _cache['W'], _cache['TU'], _cache['mask']
    W = cv2.cvtColor(cv2.imread(os.path.join(WORK, 'official', '2153_031_72_00-1-1.jpg')), cv2.COLOR_BGR2RGB)
    TU = cv2.cvtColor(cv2.imread(os.path.join(WORK, 'frames', 'tower_up.png')), cv2.COLOR_BGR2RGB)
    sw = Source(W, K_W, 0.0, K_W, 0.0, 'W')
    # ORIG X -> T x = (X - off) / scale -> TU = T * s
    ax = TU_S[0] / T_SCALE[0]
    ay = TU_S[1] / T_SCALE[1]
    st = Source(TU, ax, -T_OFF[0] * ax, ay, -T_OFF[1] * ay, 'TU')
    # coverage of TU with a soft edge (40 TU px), sampled like an image
    h, w = TU.shape[:2]
    m = np.zeros((h, w), np.float32)
    e = 40
    m[e:h - e, e:w - e] = 1.0
    m = cv2.GaussianBlur(m, (0, 0), e / 2)
    mask = Source(m, ax, -T_OFF[0] * ax, ay, -T_OFF[1] * ay, 'mask')
    _cache.update(W=sw, TU=st, mask=mask)
    return sw, st, mask


def render(cx, cy, w, out_w=OUT_W, out_h=OUT_H):
    """one frame: W everywhere, the close tower render wherever it covers (same render, finer)"""
    sw, st, sm = sources()
    a = sw.sample(cx, cy, w, out_w, out_h)
    b = st.sample(cx, cy, w, out_w, out_h)
    m = sm.sample(cx, cy, w, out_w, out_h, cv2.INTER_LINEAR)[..., None]
    return a * (1 - m) + b * m


def to_u8(img):
    return np.clip(img + 0.5, 0, 255).astype(np.uint8)
