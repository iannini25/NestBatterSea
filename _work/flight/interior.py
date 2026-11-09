"""
The room seen through the home's real glass, shared by the flight (the window opens as the camera
lands) and by Step inside (the camera goes in).

Proportions: from the official camera (far away, long lens) a room behind the glass appears at
almost the scale of the facade itself. The LOFT 4 bay is about 4 m wide at 170 px per metre in
the arrival frame and its far wall (the kitchen) is about 7.7 m behind the glass; the photo's 66
degree view spans about 10 m there, i.e. about 1700 px: the photo sits behind the glass at about
0.88 of the frame. Bungalow 3 is similar (0.86).
"""
import os

import cv2
import numpy as np

import camera as C

HOMES = {
    # aim: arrival frame pixel the camera heads for in Step inside (the room's centre of view)
    # s0: photo scale behind the glass at arrival; shear: slope of the glass plane on screen
    # open: panes that stand open (arrival frame px, x0, y0, x1, y1); the others keep a faint reflection
    'loft4': {'aim': (1150.0, 560.0), 'photo': 'loft4-living', 's0': 0.88, 'shear': 0.0,
              'open': [(1073.5, 636.0, 1210.0, 852.0)], 'lamp': (815.0, 772.0, 70.0)},
    'bung3': {'aim': (985.0, 585.0), 'photo': 'bung3-living', 's0': 0.86, 'shear': 0.10,
              'open': [(853.0, 480.0, 996.0, 720.0)]},
}
REFLECTION = 0.18      # how much of the original glass (sheers, reflections) stays on closed panes

_photo, _mask = {}, {}


def photo_ext(name):
    if name not in _photo:
        p = os.path.join(C.ROOT, 'assets', 'interiors', name + '.jpg')
        img = cv2.cvtColor(cv2.imread(p), cv2.COLOR_BGR2RGB)
        if img.shape[1] != C.OUT_W:
            img = cv2.resize(img, (C.OUT_W, C.OUT_H), interpolation=cv2.INTER_AREA)
        pad = 240
        ext = cv2.copyMakeBorder(img, pad, pad, pad, pad, cv2.BORDER_REFLECT_101)
        blur = cv2.GaussianBlur(ext, (0, 0), 36)
        inner = np.zeros(ext.shape[:2], np.float32)
        inner[pad:-pad, pad:-pad] = 1
        m = np.maximum(inner, cv2.GaussianBlur(inner, (0, 0), 14))[..., None]
        ext = ext.astype(np.float32) * m + blur.astype(np.float32) * (1 - m)
        _photo[name] = (ext, pad)
    return _photo[name]


def masks(home):
    """glass and open panes, on the 2x arrival frame"""
    if home not in _mask:
        g = np.load(os.path.join(C.HERE, 'out', f'{home}-glass-2x.npy')).astype(np.float32)
        o = np.zeros_like(g)
        for x0, y0, x1, y1 in HOMES[home]['open']:
            o[int(y0 * 2):int(y1 * 2), int(x0 * 2):int(x1 * 2)] = 1
        o = cv2.GaussianBlur(o, (0, 0), 2.0) * g
        _mask[home] = (g, o)
    return _mask[home]


def warp_photo(name, s, centre, shear, out_w, out_h):
    ext, pad = photo_ext(name)
    k = out_w / C.OUT_W
    sc = s * k
    A = np.array([[sc, 0.0], [shear * sc, sc]])
    Ai = np.linalg.inv(A)
    pc = np.array([C.OUT_W / 2 + pad - 0.5, C.OUT_H / 2 + pad - 0.5])
    off = pc - Ai @ (np.array(centre) - 0.5)
    M = np.hstack([Ai, off[:, None]])
    return cv2.warpAffine(ext, M, (out_w, out_h), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP,
                          borderMode=cv2.BORDER_REPLICATE)


def warp_arrival(img2x, cam, start, out_w, out_h):
    """anything drawn on the 2x arrival frame, seen by the camera cam"""
    cx, cy, w = cam
    cx0, cy0, w0 = start
    k = out_w / C.OUT_W
    r = w / w0 / k
    bx = 2 * ((cx - cx0) / w0 * C.OUT_W + 0.5 * r - out_w * r / 2 + C.OUT_W / 2) - 0.5
    by = 2 * ((cy - cy0) / w0 * C.OUT_W + 0.5 * r - out_h * r / 2 + C.OUT_H / 2) - 0.5
    M = np.array([[2 * r, 0, bx], [0, 2 * r, by]], np.float64)
    return cv2.warpAffine(img2x, M, (out_w, out_h), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=0)


def aim_orig(home, start):
    ax, ay = HOMES[home]['aim']
    return (start[0] + (ax + 0.5 - C.OUT_W / 2) / C.OUT_W * start[2],
            start[1] + (ay + 0.5 - C.OUT_H / 2) / C.OUT_W * start[2])


def screen_of(pt, cam, out_w, out_h):
    cx, cy, w = cam
    return ((pt[0] - cx) / w * out_w + out_w / 2, (pt[1] - cy) / w * out_w + out_h / 2)


def through_glass(ext, home, cam, start, clear, reflection, photo_scale, photo_centre, shear, out_w, out_h):
    """composite the room into the glass of ext; clear 0..1 opens the glass, reflection 0..1 on closed panes"""
    spec = HOMES[home]
    g, o = masks(home)
    gm = warp_arrival(g, cam, start, out_w, out_h)
    om = warp_arrival(o, cam, start, out_w, out_h)
    photo = warp_photo(spec['photo'], photo_scale, photo_centre, shear, out_w, out_h)
    a = gm * clear * (1 - reflection * (1 - om / np.maximum(gm, 1e-3)))
    a = np.clip(a, 0, 1)[..., None]
    out = ext * (1 - a) + photo * a
    lamp = spec.get('lamp')
    if lamp is not None:
        # the garden lamp keeps its glow over the room: lighten with a soft radial falloff
        k = out_w / C.OUT_W
        lx, ly = screen_of(arrival_to_orig(lamp[0], lamp[1], start), cam, out_w, out_h)
        r = lamp[2] * k * start[2] / cam[2]
        yy, xx = np.mgrid[0:out_h, 0:out_w].astype(np.float32)
        f = np.exp(-(((xx - lx) ** 2 + (yy - ly) ** 2) / (0.6 * r) ** 2))[..., None]
        lum = ext.mean(axis=2, keepdims=True)
        core = np.clip((lum - 215) / 30, 0, 1)          # the lamp itself and its rays
        glow = np.maximum(0, ext - 185) * 1.2           # light above the sheer curtains' level
        add = core * (ext - out) + (1 - core) * glow
        out = out + f * np.maximum(0, add) * clear
    return out, photo


def arrival_to_orig(x, y, start):
    return (start[0] + (x + 0.5 - C.OUT_W / 2) / C.OUT_W * start[2],
            start[1] + (y + 0.5 - C.OUT_H / 2) / C.OUT_W * start[2])
