"""
A real camera move over the official render: the image is split into layers (sky, the buildings
along the far bank, the tower's two faces, the river) and each layer is placed on a plane in 3D
seen by the render's own camera. A virtual camera then travels (moves forward, rises, arcs) and
every frame reprojects the official pixels through those planes. Nothing is invented: every pixel
comes from the official image, only the viewpoint changes, so the facades keep their exact design
while their perspective, the slab lines and the parallax against the sky and the river change as
in a real drone shot.

Calibration of the official camera (ORIG = the 2560 x 1920 version of the render):
  level camera (verticals vertical), horizon at y 1250, principal point x 1280, f = 8000 px;
  the NE face's slab lines meet at x 3356 on the horizon (roof edge and lower slabs), the SE face
  is the orthogonal one (its lines are almost horizontal); the corner between them is at x 1415.
Units: at the tower's distance (Z = 8000) one unit is one ORIG pixel (about 0.15 m).
"""
import math
import os

import cv2
import numpy as np

import camera as C

F0, PPX, YH = 8000.0, 1280.0, 1250.0
X_CORNER = 1415.0                               # where the near face turns into the receding face (slab ends, measured)
Z_TOWER = 8000.0
VP2 = 3356.0
_d2 = np.array([VP2 - PPX, F0])
_d2 = _d2 / np.linalg.norm(_d2)                 # NE face horizontal direction (x, z)
D2 = np.array([_d2[0], 0.0, _d2[1]])
D1 = np.array([-_d2[1], 0.0, _d2[0]])           # SE face direction (orthogonal), pointing left
CORNER = np.array([(X_CORNER - PPX) * Z_TOWER / F0, 0.0, Z_TOWER])
WATER_Y = -55.0                                 # river surface (camera about 8 m above the water)
WATERLINE = 1312.0                              # ORIG y where the river starts below the far bank
TOWER_X = (1248.0, 1497.0)                      # tower span in ORIG x
HALO = (40.0, 100.0)                            # glow zone around buildings that moves with them (ORIG px)
EXT_PAD = (2560, 640)                           # sky plate extension beyond the official frame (ORIG px)


def plane(normal, point):
    n = np.asarray(normal, float)
    n = n / np.linalg.norm(n)
    return n, float(n @ np.asarray(point, float))


# planes: (unit normal n, offset d) with n . P = d
P_SE = plane(np.cross(D1, [0, 1, 0]), CORNER)     # contains D1 and the vertical
P_NE = plane(np.cross(D2, [0, 1, 0]), CORNER)
P_BANK = plane([0, 0, 1], [0, 0, Z_TOWER])        # buildings along the far bank, facing the camera
P_RIVER = plane([0, 1, 0], [0, WATER_Y, 0])


def orig_project(P):
    """3D point(s) (N, 3) -> ORIG pixel coordinates (N, 2)"""
    P = np.atleast_2d(P)
    return np.stack([PPX + F0 * P[:, 0] / P[:, 2], YH - F0 * P[:, 1] / P[:, 2]], axis=1)


def orig_ray(u, v):
    return np.array([(u - PPX) / F0, -(v - YH) / F0, 1.0])


def on_plane(pl, u, v):
    """back project an ORIG pixel onto a plane"""
    n, d = pl
    r = orig_ray(u, v)
    return r * (d / (n @ r))


class Cam:
    """virtual camera: position (x, y, z), yaw (radians, + turns right), focal and principal point in output px"""

    def __init__(self, pos, yaw, f, pp, out_w=C.OUT_W, out_h=C.OUT_H):
        self.pos = np.asarray(pos, float)
        self.yaw = yaw
        self.f = f
        self.pp = pp
        self.w, self.h = out_w, out_h
        c, s = math.cos(yaw), math.sin(yaw)
        self.R = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])   # camera -> world

    def ray(self, u, v):
        d = np.stack([(u - self.pp[0]) / self.f, -(v - self.pp[1]) / self.f, np.ones_like(u)], axis=-1)
        return d @ self.R.T

    def project(self, P):
        Pc = (np.atleast_2d(P) - self.pos) @ self.R
        return np.stack([self.pp[0] + self.f * Pc[:, 0] / Pc[:, 2], self.pp[1] - self.f * Pc[:, 1] / Pc[:, 2]], axis=1)

    def scaled(self, k):
        return Cam(self.pos, self.yaw, self.f * k, (self.pp[0] * k, self.pp[1] * k), int(round(self.w * k)), int(round(self.h * k)))


def h_plane(cam, pl):
    """homography output px -> ORIG px for a plane, from four output points; plus a validity half plane"""
    n, d = pl
    us = np.array([0.0, cam.w, cam.w, 0.0, cam.w / 2])
    vs = np.array([0.0, 0.0, cam.h, cam.h, cam.h / 2])
    dirs = cam.ray(us, vs)
    den = dirs @ n
    t = (d - n @ cam.pos) / np.where(np.abs(den) < 1e-9, 1e-9, den)
    P = cam.pos + dirs * t[:, None]
    src = np.stack([us, vs], 1)[:4].astype(np.float32)
    dst = orig_project(P)[:4].astype(np.float32)
    H = cv2.getPerspectiveTransform(src, dst)
    # n . ray(u, v) is affine in (u, v): valid where it has the sign of (d - n . pos)
    a = (n @ cam.R[:, 0]) / cam.f
    b = -(n @ cam.R[:, 1]) / cam.f
    c = n @ cam.R[:, 2] - a * cam.pp[0] - b * cam.pp[1]
    sign = 1.0 if (d - n @ cam.pos) > 0 else -1.0
    return H, (a * sign, b * sign, c * sign)


def h_sky(cam):
    us = np.array([0.0, cam.w, cam.w, 0.0])
    vs = np.array([0.0, 0.0, cam.h, cam.h])
    dirs = cam.ray(us, vs)
    dst = np.stack([PPX + F0 * dirs[:, 0] / dirs[:, 2], YH - F0 * dirs[:, 1] / dirs[:, 2]], 1).astype(np.float32)
    return cv2.getPerspectiveTransform(np.stack([us, vs], 1).astype(np.float32), dst)


# ---------------------------------------------------------------- layers and plates (ORIG space)
_L = {}


def layers():
    if _L:
        return _L
    O = cv2.cvtColor(cv2.imread(os.path.join(C.WORK, 'official', '2153_031_72_00-1-1.jpg')), cv2.COLOR_BGR2RGB)
    O = cv2.resize(O, (2560, 1920), interpolation=cv2.INTER_AREA)
    H, Wd = O.shape[:2]
    lab = cv2.cvtColor(O, cv2.COLOR_RGB2LAB).astype(np.float32)
    # a smooth model of the night sky (quadratic in x, cubic in y), fitted on pixels that are surely sky
    yy0, xx0 = np.mgrid[0:H, 0:Wd]
    sure = (yy0 < 330) | (((xx0 < 50) | (xx0 > Wd - 50)) & (yy0 < 1100))
    sure &= (yy0 % 4 == 0) & (xx0 % 4 == 0)
    xs_, ys_ = xx0[sure] / Wd, yy0[sure] / H
    def basis(x, y):
        return np.stack([np.ones_like(x), x, x * x, y, y * y, y ** 3, x * y, x * x * y, x * y * y], -1)
    Bm = basis(xs_, ys_)
    model = np.zeros_like(lab)
    Ball = basis(xx0.ravel() / Wd, yy0.ravel() / H)
    for ch in range(3):
        coef = np.linalg.lstsq(Bm, lab[..., ch][sure], rcond=None)[0]
        model[..., ch] = (Ball @ coef).reshape(H, Wd)
    dist = np.sqrt(((lab - model) ** 2).sum(axis=2))
    g = cv2.GaussianBlur(lab[..., 0], (0, 0), 1.2)
    grad = np.hypot(cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1))
    grad = cv2.blur(grad, (5, 5))
    solid = ((dist > 14) | (grad > 22)).astype(np.uint8)
    solid = cv2.morphologyEx(solid, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    solid = cv2.morphologyEx(solid, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    skyline = np.full(Wd, H, np.int32)
    run = cv2.erode(solid, np.ones((9, 1), np.uint8))
    for x in range(Wd):
        ys = np.nonzero(run[:, x])[0]
        if len(ys):
            skyline[x] = max(0, ys[0] - 1)
    yy, xx = np.mgrid[0:H, 0:Wd]
    # the buildings are opaque only on their own pixels: the sky right next to them (the anti aliased
    # edge, any glow) goes into the additive glow layer below, so it adapts to the sky that ends up
    # behind them when the camera climbs (an opaque rim of the old sky would show as a pale halo)
    below = yy >= skyline[None, :]
    river = yy >= WATERLINE
    tower = below & ~river & (xx >= TOWER_X[0]) & (xx <= TOWER_X[1]) & (yy < 1176)
    bank = below & ~river & ~tower
    sky = ~below & ~river
    f32 = lambda m: cv2.GaussianBlur(m.astype(np.float32), (0, 0), 0.8)
    # the glow the render puts around lit buildings (and the street lamps' haze) belongs to them:
    # near every building the sky is split into a clean sky (the plate) plus the glow, an additive
    # layer that travels with its building. Up to HALO[0] px from a building the plate is the clean
    # model, fading back to the real sky by HALO[1] px; plate + glow is exactly the official sky.
    solid_all = below & ~river
    dist = cv2.distanceTransform((~solid_all).astype(np.uint8), cv2.DIST_L2, 5)
    w = (np.clip((HALO[1] - dist) / (HALO[1] - HALO[0]), 0, 1) * sky).astype(np.float32)
    d_t = cv2.distanceTransform((~tower).astype(np.uint8), cv2.DIST_L2, 5)
    d_b = cv2.distanceTransform((~bank).astype(np.uint8), cv2.DIST_L2, 5)
    to_tower = d_t <= d_b
    if TOWER_MATTE:
        # the open air between the balconies on the tower's sides is sky in the official image: it must
        # not travel with the tower (it reads as a pale band around it once the sky behind changes);
        # those pixels and the 1 px anti aliased rim next to them go to the sky
        Ofl = O.astype(np.float32)
        ref = np.zeros((H, 3), np.float32)
        cols = np.r_[int(TOWER_X[0]) - 70:int(TOWER_X[0]) - 3, int(TOWER_X[1]) + 3:int(TOWER_X[1]) + 70]
        for y in range(H):
            px = Ofl[y, cols][sky[y, cols]]
            ref[y] = np.median(px, 0) if len(px) else (ref[y - 1] if y else 0)
        gg = cv2.GaussianBlur(cv2.cvtColor(O, cv2.COLOR_RGB2GRAY).astype(np.float32), (0, 0), 1)
        gr = np.hypot(cv2.Sobel(gg, cv2.CV_32F, 1, 0), cv2.Sobel(gg, cv2.CV_32F, 0, 1))
        skylike = (np.abs(Ofl - ref[:, None, :]).max(2) < 14) & (gr < 40) & tower
        air = (skylike | sky).astype(np.uint8)
        tower = tower & ~skylike & ~cv2.dilate(air, np.ones((3, 3), np.uint8)).astype(bool)
        # near the silhouette (glass balustrades, anti aliasing, bloom) a soft key: a pixel is as opaque
        # as it is far from the sky colour of its row
        d_air = cv2.distanceTransform((1 - cv2.dilate(air, np.ones((3, 3), np.uint8))).astype(np.uint8), cv2.DIST_L2, 3)
        dc = np.abs(Ofl - ref[:, None, :]).max(2)
        key_a = np.clip((dc - 10.0) / 70.0, 0, 1)
        band = np.clip((d_air - 3.0) / 9.0, 0, 1)            # 0 at the rim, 1 twelve px inside
        bluish = (Ofl[..., 2] - Ofl[..., 0]) > 30
        tower_a = tower.astype(np.float32) * np.maximum(key_a, band) * ~((d_air < 3.5) & bluish)
    else:
        tower_a = tower.astype(np.float32)
    se = f32(tower_a * (xx < X_CORNER))
    ne = f32(tower_a * (xx >= X_CORNER))
    bank_m = f32(bank)
    sky_real = sky & (dist > HALO[1])
    # clean sky: a smooth model of the sky fitted on the sky away from the buildings, carrying the
    # broad residual of the nearby real sky so it matches it (behind the buildings, seen when the
    # camera rises past them, and under their glow)
    Of = O.astype(np.float32)
    ys_all = np.nonzero(sky_real.any(axis=1))[0]
    y_low = int(ys_all.max()) if len(ys_all) else H - 1
    sel = sky_real & (yy0 % 2 == 0) & (xx0 % 2 == 0)
    Bs = basis(xx0[sel] / Wd, yy0[sel] / H)
    coefs = [np.linalg.lstsq(Bs, Of[..., ch][sel], rcond=None)[0] for ch in range(3)]

    def sky_model(xo, yo):
        Bq = basis(np.clip(xo, 0, Wd - 1).ravel() / Wd, np.clip(yo, 0, y_low).ravel() / H)
        return np.stack([(Bq @ c).reshape(xo.shape) for c in coefs], -1).astype(np.float32)

    smooth_sky = sky_model(xx0.astype(np.float32), yy0.astype(np.float32))
    s32 = sky_real.astype(np.float32)
    num = cv2.GaussianBlur((Of - smooth_sky) * s32[..., None], (0, 0), 60)
    den = cv2.GaussianBlur(s32, (0, 0), 60)[..., None]
    fill = smooth_sky + num / np.maximum(den, 1e-4) * np.clip(den * 4, 0, 1)
    w3 = w[..., None]
    skyp = np.where(sky[..., None], Of * (1 - w3) + fill * w3, fill)
    glow = (Of - fill) * w3
    glows = {}
    for key, m in (('g_se', to_tower & (xx < X_CORNER)), ('g_ne', to_tower & (xx >= X_CORNER)), ('g_bank', ~to_tower)):
        gk = glow * m[..., None]
        ys_, xs_ = np.nonzero(np.abs(gk).max(axis=2) > 0.25)
        if len(ys_) == 0:
            continue
        y0_, y1_, x0_, x1_ = ys_.min(), ys_.max() + 1, xs_.min(), xs_.max() + 1
        glows[key] = (np.round(gk[y0_:y1_, x0_:x1_]).astype(np.int16), (int(x0_), int(y0_)))
    if TOWER_MATTE:
        # around the tower the official sky itself stays in the sky plate (fixed at infinity), with no
        # glow travelling on the tower's planes; behind the tower the plate is the sky interpolated
        # row by row between its two sides, so whatever the tower uncovers matches the sky around it
        ta, tb = int(TOWER_X[0]), int(TOWER_X[1])
        span = np.arange(ta - 8, tb + 9)
        for y in range(H):
            lm_ = sky[y, ta - 16:ta - 6]
            rm_ = sky[y, tb + 6:tb + 16]
            lv = Of[y, ta - 16:ta - 6][lm_].mean(0) if lm_.sum() >= 3 else None
            rv = Of[y, tb + 6:tb + 16][rm_].mean(0) if rm_.sum() >= 3 else None
            if lv is None and rv is None:
                continue
            lv = rv if lv is None else lv
            rv = lv if rv is None else rv
            k = ((span - (ta - 11)) / float((tb + 11) - (ta - 11))).clip(0, 1)[:, None]
            row = lv[None, :] * (1 - k) + rv[None, :] * k
            real = sky[y, span]
            skyp[y, span] = np.where(real[:, None], Of[y, span], row)
        near_t = to_tower & sky & (np.abs(xx - (ta + tb) / 2) < (tb - ta) / 2 + HALO[1] + 4)
        skyp[near_t] = Of[near_t]
        glows.pop('g_se', None)
        glows.pop('g_ne', None)
    # beyond the official frame (the camera turns and climbs): the same model held at the frame's
    # edge, a plain gradient, at quarter resolution; blended in over the last 48 px of the frame
    q = 4
    eh, ew = (H + 2 * EXT_PAD[1]) // q, (Wd + 2 * EXT_PAD[0]) // q
    yq, xq = np.mgrid[0:eh, 0:ew].astype(np.float32)
    xo, yo = (xq + 0.5) * q - 0.5 - EXT_PAD[0], (yq + 0.5) * q - 0.5 - EXT_PAD[1]
    ext = sky_model(xo, yo)
    inner = (xo >= 0) & (xo <= Wd - 1) & (yo >= 0) & (yo <= H - 1)
    small = cv2.resize(skyp, (Wd // q, H // q), interpolation=cv2.INTER_AREA)
    xi = np.clip(((xo + 0.5) / q - 0.5).round().astype(int), 0, Wd // q - 1)
    yi = np.clip(((yo + 0.5) / q - 0.5).round().astype(int), 0, H // q - 1)
    edge = small[yi, xi]
    dist = np.maximum(np.maximum(-xo, xo - (Wd - 1)), np.maximum(-yo, yo - (H - 1))).clip(0)
    keep = np.exp(-dist / 300.0)[..., None]
    ext = np.where(inner[..., None], edge, ext + (edge - sky_model(np.clip(xo, 0, Wd - 1), np.clip(yo, 0, H - 1))) * keep)
    yy1, xx1 = np.mgrid[0:H, 0:Wd].astype(np.float32)
    d_in = np.minimum(np.minimum(xx1, Wd - 1 - xx1), np.minimum(yy1, H - 1 - yy1))
    sky_in = np.clip(d_in / 48.0, 0, 1)
    _L.update(O=O, sky=np.clip(skyp + 0.5, 0, 255).astype(np.uint8), sky_ext=ext.astype(np.float32), sky_in=sky_in, m_sky=f32(sky), m_bank=bank_m, m_se=se, m_ne=ne, glows=glows,
              m_river=f32(river), skyline=skyline)
    return _L


def pyramid_level(H, cam, levels_n):
    """scale (ORIG px per output px) at the centre of the frame through homography H"""
    u, v = cam.w / 2, cam.h / 2
    p = H @ np.array([u, v, 1.0])
    q = H @ np.array([u + 1, v, 1.0])
    s = math.hypot(q[0] / q[2] - p[0] / p[2], q[1] / q[2] - p[1] / p[2])
    return s


def warp(src, H, cam, interp=cv2.INTER_LINEAR, border=cv2.BORDER_REPLICATE):
    return cv2.warpPerspective(src, H, (cam.w, cam.h), flags=interp | cv2.WARP_INVERSE_MAP, borderMode=border)


def warp_source(source, H_orig, cam):
    """sample a camera.Source (affine ORIG -> source px, with a pyramid) through an output -> ORIG homography"""
    A = np.array([[source.ax, 0, source.bx], [0, source.ay, source.by], [0, 0, 1.0]])
    Hs = A @ H_orig
    s = pyramid_level(H_orig, cam, len(source.levels)) * source.ax
    lf = math.log2(s) if s > 0 else 0.0
    if lf <= 0:
        return warp(source.levels[0], _to_index(Hs, source, 0), cam, cv2.INTER_CUBIC).astype(np.float32)
    l0 = min(int(lf), len(source.levels) - 1)
    fr = lf - l0
    a = warp(source.levels[l0], _to_index(Hs, source, l0), cam).astype(np.float32)
    if fr < 1e-3 or l0 + 1 >= len(source.levels):
        return a
    b = warp(source.levels[l0 + 1], _to_index(Hs, source, l0 + 1), cam).astype(np.float32)
    return a * (1 - fr) + b * fr


def _to_index(Hs, source, L):
    """continuous source coords -> level L pixel index, composed with output pixel centres"""
    img = source.levels[L]
    rx, ry = img.shape[1] / source.w0, img.shape[0] / source.h0
    S = np.array([[rx, 0, -0.5], [0, ry, -0.5], [0, 0, 1.0]])
    T = np.array([[1, 0, 0.5], [0, 1, 0.5], [0, 0, 1.0]])         # output index -> output centre
    return S @ Hs @ T


def half_plane(cam, abc):
    a, b, c = abc
    yy, xx = np.mgrid[0:cam.h, 0:cam.w].astype(np.float32)
    return np.clip((a * (xx + 0.5) + b * (yy + 0.5) + c) * 4000.0, 0, 1)


# opt in (the full deterministic flights): the glow around the buildings is an atmospheric bloom of
# the far view; carried on the building planes it grows into a pale band around the tower as the
# camera closes in, so it fades out with the magnification of the tower (GLOW_FADE = (s0, s1):
# full glow while the tower is shown at s0 ORIG px per output px or more, none at s1 or less)
GLOW_FADE = None
TOWER_MATTE = False     # opt in, before the first layers() call
# opt in: a sharp inlay on a facade plane (the window's end image registered on the official facade):
# dict(plane=P_SE, levels=[float RGB pyramid], mask=[pyramid], K=ORIG -> inlay px (3x3), alpha=0..1)
INLAY = None


def _sample_pyr(levels, Hk, cam):
    """sample an image pyramid through output -> level-0 px homography Hk (trilinear by scale)"""
    u, v = cam.w / 2, cam.h / 2
    p = Hk @ np.array([u, v, 1.0]); q = Hk @ np.array([u + 1, v, 1.0]); r = Hk @ np.array([u, v + 1, 1.0])
    s = max(math.hypot(q[0] / q[2] - p[0] / p[2], q[1] / q[2] - p[1] / p[2]),
            math.hypot(r[0] / r[2] - p[0] / p[2], r[1] / r[2] - p[1] / p[2]))
    lf = math.log2(s) if s > 1e-9 else 0.0
    T = np.array([[1, 0, 0.5], [0, 1, 0.5], [0, 0, 1.0]])

    def at(L):
        k = 0.5 ** L
        S = np.array([[k, 0, 0.5 * k - 0.5], [0, k, 0.5 * k - 0.5], [0, 0, 1.0]])
        img = levels[L]
        return cv2.warpPerspective(img, S @ Hk @ T, (cam.w, cam.h), flags=(cv2.INTER_CUBIC if L == 0 and lf <= 0 else cv2.INTER_LINEAR) | cv2.WARP_INVERSE_MAP,
                                   borderMode=cv2.BORDER_CONSTANT).astype(np.float32)
    if lf <= 0:
        return at(0)
    l0 = min(int(lf), len(levels) - 1)
    fr = lf - l0
    a = at(l0)
    if fr < 1e-3 or l0 + 1 >= len(levels):
        return a
    return a * (1 - fr) + at(l0 + 1) * fr


def _room_h(cam, room):
    """output px -> room image px, through the room's plane (parallel to the facade, behind it), seen
    by the reference end camera the room image was registered on (ref) and its registration A"""
    n, d = room['plane']
    us = np.array([0.0, cam.w, cam.w, 0.0]); vs = np.array([0.0, 0.0, cam.h, cam.h])
    dirs = cam.ray(us, vs)
    den = dirs @ n
    if np.any(np.abs(den) < 1e-9):
        return None
    t = (d - n @ cam.pos) / den
    if np.any(t <= 0):
        return None
    P = cam.pos + dirs * t[:, None]
    q = room['ref'].project(P)
    q = np.c_[q, np.ones(4)] @ room['A'].T
    q = q[:, :2] / q[:, 2:3]
    return cv2.getPerspectiveTransform(np.stack([us, vs], 1).astype(np.float32), q.astype(np.float32))


def render(cam):
    """one frame of the virtual camera, float RGB"""
    L = layers()
    sw, st, sm = C.sources()
    Hs = h_sky(cam)
    # the sky: the official sky (and its clean fill behind the buildings) inside the official frame,
    # the smooth model of it beyond (where the camera turns or climbs past the frame)
    out = warp(L['sky'], _orig_index(Hs), cam).astype(np.float32)
    S = np.array([[0.25, 0, EXT_PAD[0] / 4.0 - 0.5], [0, 0.25, EXT_PAD[1] / 4.0 - 0.5], [0, 0, 1.0]])
    T = np.array([[1, 0, 0.5], [0, 1, 0.5], [0, 0, 1.0]])
    ext = warp(L['sky_ext'], S @ Hs @ T, cam)
    a = warp(L['sky_in'], _orig_index(Hs), cam, border=cv2.BORDER_CONSTANT)[..., None]
    out = out * a + ext * (1 - a)
    # the buildings' glow, travelling with them
    for key, pl in (('g_bank', P_BANK), ('g_ne', P_NE), ('g_se', P_SE)):
        if key not in L['glows']:
            continue
        g, (gx, gy) = L['glows'][key]
        Hg, vg = h_plane(cam, pl)
        gain = 1.0
        if GLOW_FADE is not None:
            sc = pyramid_level(Hg, cam, 1)
            gain = float(np.clip((sc - GLOW_FADE[1]) / (GLOW_FADE[0] - GLOW_FADE[1]), 0, 1))
            gain = gain * gain * (3 - 2 * gain)
            if gain <= 0:
                continue
        Tc = np.array([[1, 0, -gx], [0, 1, -gy], [0, 0, 1.0]])
        gw = cv2.warpPerspective(g, Tc @ _orig_index(Hg), (cam.w, cam.h), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                                 borderMode=cv2.BORDER_CONSTANT).astype(np.float32)
        out += gw * (gain * half_plane(cam, vg))[..., None]
    # the buildings along the far bank
    Hb, vb = h_plane(cam, P_BANK)
    mb = warp(L['m_bank'], _orig_index(Hb), cam, border=cv2.BORDER_CONSTANT)[..., None] * half_plane(cam, vb)[..., None]
    img = warp_source(sw, Hb, cam)
    out = out * (1 - mb) + img * mb
    # the tower: NE face, then SE face; the close tower render wherever it covers
    for pl, key in ((P_NE, 'm_ne'), (P_SE, 'm_se')):
        Hf, vf = h_plane(cam, pl)
        m = warp(L[key], _orig_index(Hf), cam, border=cv2.BORDER_CONSTANT) * half_plane(cam, vf)
        a = warp_source(sw, Hf, cam)
        b = warp_source(st, Hf, cam)
        cov = warp_source(sm, Hf, cam)
        if cov.ndim == 3:
            cov = cov[..., 0]
        face = a * (1 - cov[..., None]) + b * cov[..., None]
        if INLAY is not None and INLAY['plane'] is pl and INLAY.get('alpha', 1.0) > 0:
            Hk = INLAY['K'] @ Hf
            ki = _sample_pyr(INLAY['levels'], Hk, cam)
            km = _sample_pyr(INLAY['mask'], Hk, cam)
            km = (km[..., 0] if km.ndim == 3 else km) * INLAY.get('alpha', 1.0)
            if ki.shape[2] == 4:
                # premultiplied: the facade, frames and balcony in front; the room on its own plane behind
                fa = np.clip(ki[..., 3:4] / 255.0, 0, 1)
                room = INLAY.get('room')
                if room is not None:
                    Hr = _room_h(cam, room)
                    rr = _sample_pyr(room['levels'], Hr, cam) if Hr is not None else 0.0
                    ki = ki[..., :3] + rr * (1 - fa)
                else:
                    ki = ki[..., :3] + face * (1 - fa)
            face = face * (1 - km[..., None]) + ki * km[..., None]
        m = m[..., None]
        out = out * (1 - m) + face * m
    # the river, below the horizon
    Hr, vr = h_plane(cam, P_RIVER)
    mr = warp(L['m_river'], _orig_index(Hr), cam, border=cv2.BORDER_CONSTANT)[..., None] * half_plane(cam, vr)[..., None]
    img = warp_source(sw, Hr, cam)
    out = out * (1 - mr) + img * mr
    return out


def _orig_index(H):
    """for images stored at ORIG resolution: output index -> ORIG index"""
    S = np.array([[1, 0, -0.5], [0, 1, -0.5], [0, 0, 1.0]])
    T = np.array([[1, 0, 0.5], [0, 1, 0.5], [0, 0, 1.0]])
    return S @ H @ T


def start_cam(out_w=C.OUT_W, out_h=C.OUT_H):
    """the site's tower view: the original camera, framed on ORIG [160, 140, 2560, 1490]"""
    k = out_w / 2400.0
    return Cam((0, 0, 0), 0.0, F0 * k, ((PPX - 160) * k, (YH - 140) * k), out_w, out_h)
