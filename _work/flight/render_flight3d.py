"""
The flight as a real camera move (see proxy.py): from the site's tower view the camera travels
across the river, climbs to the home's level and turns towards it, ending level and straight on
the window. Over the last second the window opens onto the room (interior.py): the glass panes
show the living room photograph, placed on a plane behind the glass so it keeps a slight parallax
with the facade. Writes a lossless 60 fps master and the window track for the site;
render_inside3d.py continues from the last frame.

usage: python render_flight3d.py <home> [--seconds 4] [--blur 7] [--preview] [--end]
"""
import argparse
import json
import math
import os
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import camera as C  # noqa: E402
import interior as I  # noqa: E402
import proxy as X  # noqa: E402

HOMES = {
    # face: the facade the home is on; box: window box in master px (js/data.js)
    # turn: how far the camera turns from the official direction towards facing the facade square
    #   on (1 = square on). The NE face is seen almost edge on in the official image, so Bungalow 3
    #   only turns a little (more would stretch the facade beyond what the official pixels hold).
    # dist: distance from the window at arrival (units: one ORIG px at the tower)
    # orbit: extra sideways arc mid flight (degrees), zero at both ends
    'loft4': {'face': 'SE', 'box': (1244.3, 534.4, 1293.7, 578.7), 'turn': 1.0, 'dist': 420.0, 'orbit': 0.0},
    'bung3': {'face': 'NE', 'box': (1352.0, 806.0, 1406.0, 837.0), 'turn': 0.1, 'dist': 900.0, 'orbit': 0.0},
}
REVEAL = (0.72, 0.98)        # the window opens over this span of the flight
OLD_END_W = 130.0            # the old arrival framing (ORIG px wide): the arrival keeps its scale
ROOM_DEPTH = 60.0            # the room photo's plane behind the glass (units, about 5 m)
HORIZON_MARGIN = math.radians(0.3)   # once the camera rises, the frame stays this far above the horizon
RISE_SOFT = 30.0             # softness of the moment the camera starts to rise (units)


def bezier_ease(x1, y1, x2, y2):
    def bx(t):
        return 3 * x1 * t * (1 - t) ** 2 + 3 * x2 * t * t * (1 - t) + t ** 3

    def by(t):
        return 3 * y1 * t * (1 - t) ** 2 + 3 * y2 * t * t * (1 - t) + t ** 3

    def f(x):
        if x <= 0:
            return 0.0
        if x >= 1:
            return 1.0
        lo, hi = 0.0, 1.0
        for _ in range(50):
            mid = (lo + hi) / 2
            if bx(mid) < x:
                lo = mid
            else:
                hi = mid
        return by((lo + hi) / 2)
    return f


EASE = bezier_ease(0.45, 0.0, 0.22, 1.0)       # distance, turn, focal
EASE_Y = bezier_ease(0.30, 0.0, 0.30, 1.0)     # climb


def smooth(x):
    x = min(1.0, max(0.0, x))
    return x * x * x * (x * (6 * x - 15) + 10)


def face_plane(face):
    return X.P_SE if face == 'SE' else X.P_NE


def softplus(x, k):
    return k * math.log1p(math.exp(x / k)) if x < 30 * k else x


class Path:
    """The camera: it flies from the official viewpoint to the window, turning towards it, and
    climbs as soon as it can: it keeps the official height while the river and the far bank are in
    the frame, then rises along the line that keeps the frame's lower edge just above the horizon.
    So everything in the frame is always something the official image shows (the tower, the bank
    seen from its own height, the sky), never ground behind the bank that no image holds. The
    camera never tilts: verticals stay vertical and the window ends level and square in the frame."""

    def __init__(self, home, out_w=C.OUT_W, out_h=C.OUT_H, turn=None):
        h = HOMES[home]
        self.home = home
        self.w, self.h = out_w, out_h
        x0, y0 = C.master_to_orig(h['box'][0], h['box'][1])
        x1, y1 = C.master_to_orig(h['box'][2], h['box'][3])
        pl = face_plane(h['face'])
        self.plane = pl
        self.bay = X.on_plane(pl, (x0 + x1) / 2, (y0 + y1) / 2)
        self.corners3d = np.array([X.on_plane(pl, x, y) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))])
        n = pl[0] if pl[0][2] < 0 else -pl[0]          # outward normal (towards the river)
        self.start = X.start_cam(out_w, out_h)
        bx, by_, bz = self.bay
        self.D0 = math.hypot(bx, bz)
        self.az0 = math.atan2(bx, bz)
        square = math.atan2(-n[0], -n[2])              # looking along -n: square on to the facade
        k = h['turn'] if turn is None else turn
        self.az1 = self.az0 + (square - self.az0) * k
        self.D1 = h['dist']
        self.orbit = math.radians(h['orbit'])
        sx, sy = self.start.project(self.bay)[0]
        self.x0s, self.y0s = float(sx), float(sy)      # the window's place in the start frame
        self.f0 = self.start.f
        # at arrival one ORIG px at the window is out_w / OLD_END_W px, as in the old arrival framing
        self.f1 = out_w / OLD_END_W * X.F0 * self.D1 / bz
        self.rise0 = softplus(self._line(0.0, 0.0, self.D0, self.bay[2], self.f0), RISE_SOFT)

    def _line(self, e, ey, D, dz, f):
        y_t = self.y0s + (self.h / 2 - self.y0s) * ey
        return self.bay[1] - dz * ((self.h - y_t) / f + math.tan(HORIZON_MARGIN))

    def cam_at(self, t):
        if t <= 0:
            return self.start
        e, ey = EASE(t), EASE_Y(t)
        bx, by_, bz = self.bay
        D = self.D0 * (self.D1 / self.D0) ** e
        az = self.az0 + (self.az1 - self.az0) * e + self.orbit * math.sin(math.pi * e)
        yaw = az - self.az0 * (1 - e)                   # the window drifts to the frame centre
        f = self.f0 * (self.f1 / self.f0) ** e
        dz = D * math.cos(az - yaw)                     # the window's depth along the view axis
        yc = softplus(self._line(e, ey, D, dz, f), RISE_SOFT) - self.rise0 * (1 - e)
        pos = (bx - D * math.sin(az), yc, bz - D * math.cos(az))
        x_t = self.x0s + (self.w / 2 - self.x0s) * e
        y_t = self.y0s + (self.h / 2 - self.y0s) * ey
        ppx = x_t - f * math.tan(az - yaw)
        ppy = y_t + f * (by_ - yc) / dz
        return X.Cam(pos, yaw, f, (ppx, ppy), self.w, self.h)


# ------------------------------------------------------------ the window opening onto the room
def old_end(home):
    """the old arrival framing (centre, width in ORIG px) the glass masks were drawn on"""
    b = HOMES[home]['box']
    x0, y0 = C.master_to_orig(b[0], b[1])
    x1, y1 = C.master_to_orig(b[2], b[3])
    return (x0 + x1) / 2, (y0 + y1) / 2, OLD_END_W


def old_px_to_orig(home, u, v):
    cx, cy, w = old_end(home)
    return cx + (u + 0.5 - C.OUT_W / 2) / C.OUT_W * w, cy + (v + 0.5 - C.OUT_H / 2) / C.OUT_W * w


class Room:
    """the living room photo on a plane facing the arrival camera, ROOM_DEPTH behind the glass.
    At arrival it is the unaltered photo at the scale it had before (s0 of the frame), centred on
    the aim point; on the way it moves with the parallax of a plane that far behind the glass."""

    def __init__(self, path):
        end = path.cam_at(1.0)
        spec = I.HOMES[path.home]
        A = X.on_plane(path.plane, *old_px_to_orig(path.home, *spec['aim']))
        ua, va = end.project(A)[0]
        s = spec['s0']
        self.centre, self.scale = (float(ua), float(va)), s
        hw, hh = s * end.w / 2, s * end.h / 2
        rect = np.array([(ua - hw, va - hh), (ua + hw, va - hh), (ua + hw, va + hh), (ua - hw, va + hh)])
        zA = float((A - end.pos) @ end.R[:, 2])
        rays = end.ray(rect[:, 0], rect[:, 1])          # forward component 1
        self.P = end.pos + rays * (zA + ROOM_DEPTH)
        self.rect = rect

    def quad(self, cam):
        return cam.project(self.P)


def glass(home, cam, plane):
    """the home's glass and open panes (drawn on the old arrival frame) seen by cam"""
    g2, o2 = I.masks(home)
    Hf, _ = X.h_plane(cam, plane)                       # output continuous -> ORIG continuous
    cx, cy, w = old_end(home)
    k = C.OUT_W / w
    A = np.array([[2 * k, 0, 2 * (C.OUT_W / 2 - cx * k) - 0.5], [0, 2 * k, 2 * (C.OUT_H / 2 - cy * k) - 0.5], [0, 0, 1.0]])
    T = np.array([[1, 0, 0.5], [0, 1, 0.5], [0, 0, 1.0]])
    M = A @ Hf @ T
    fl = cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP
    gm = cv2.warpPerspective(g2, M, (cam.w, cam.h), flags=fl, borderMode=cv2.BORDER_CONSTANT)
    om = cv2.warpPerspective(o2, M, (cam.w, cam.h), flags=fl, borderMode=cv2.BORDER_CONSTANT)
    return gm, om


def warp_photo_quad(name, quad, out_w, out_h):
    """the photo (1920 x 1080, untouched inside, softly extended outside) onto a screen quad"""
    ext, pad = I.photo_ext(name)
    src = np.array([[pad, pad], [pad + C.OUT_W, pad], [pad + C.OUT_W, pad + C.OUT_H], [pad, pad + C.OUT_H]], np.float32)
    Hm = cv2.getPerspectiveTransform(np.asarray(quad, np.float32), src)   # output continuous -> ext continuous
    T = np.array([[1, 0, 0.5], [0, 1, 0.5], [0, 0, 1.0]])
    S = np.array([[1, 0, -0.5], [0, 1, -0.5], [0, 0, 1.0]])
    return cv2.warpPerspective(ext, S @ Hm @ T, (out_w, out_h), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP,
                               borderMode=cv2.BORDER_REPLICATE)


def lamp_screen(home, cam, plane):
    lamp = I.HOMES[home].get('lamp')
    if lamp is None:
        return None
    p = cam.project(np.array([X.on_plane(plane, *old_px_to_orig(home, lamp[0], lamp[1])),
                              X.on_plane(plane, *old_px_to_orig(home, lamp[0] + lamp[2], lamp[1]))]))
    return p[0], math.hypot(*(p[1] - p[0]))


def through_glass(home, ext, cam, plane, quad, clear, reflection):
    """the room photo (on quad) seen through the home's glass; clear 0..1 opens the glass,
    reflection 0..1 keeps that much of the original glass on the closed panes"""
    gm, om = glass(home, cam, plane)
    photo = warp_photo_quad(I.HOMES[home]['photo'], quad, cam.w, cam.h)
    a = gm * clear * (1 - reflection * (1 - om / np.maximum(gm, 1e-3)))
    a = np.clip(a, 0, 1)[..., None]
    out = ext * (1 - a) + photo * a
    ls = lamp_screen(home, cam, plane)
    if ls is not None:
        # the garden lamp keeps its glow over the room
        (lx, ly), r = ls
        yy, xx = np.mgrid[0:cam.h, 0:cam.w].astype(np.float32)
        fl = np.exp(-(((xx + 0.5 - lx) ** 2 + (yy + 0.5 - ly) ** 2) / (0.6 * r) ** 2))[..., None]
        lum = ext.mean(axis=2, keepdims=True)
        core = np.clip((lum - 215) / 30, 0, 1)
        glow = np.maximum(0, ext - 185) * 1.2
        add = core * (ext - out) + (1 - core) * glow
        out = out + fl * np.maximum(0, add) * clear
    return out, photo, gm


def frame_at(path, room, t, window=True):
    cam = path.cam_at(t)
    img = X.render(cam)
    clear = smooth((t - REVEAL[0]) / (REVEAL[1] - REVEAL[0]))
    if window and clear > 0:
        img, _, _ = through_glass(path.home, img, cam, path.plane, room.quad(cam), clear, I.REFLECTION)
    return img


# ------------------------------------------------------------ the window track for the site
def master_homography(path, cam):
    """3x3 H: master px (X, Y, 1) on the home's facade -> normalized frame (u, v) of this camera"""
    pts_m = np.array([[1100.0, 400.0], [1500.0, 400.0], [1500.0, 950.0], [1100.0, 950.0]])
    P = np.array([X.on_plane(path.plane, *C.master_to_orig(x, y)) for x, y in pts_m])
    uv = cam.project(P) / np.array([cam.w, cam.h])
    H = cv2.getPerspectiveTransform(pts_m.astype(np.float32), uv.astype(np.float32))
    return (H / H[2, 2]).ravel()


_W = {}


def render_frame(args):
    i, times, home, turn = args
    if home not in _W:
        p = Path(home, turn=turn)
        _W[home] = (p, Room(p))
    p, room = _W[home]
    acc = None
    for t in times:
        f = frame_at(p, room, t)
        acc = f if acc is None else acc + f
    return i, C.to_u8(acc / len(times))


def sheet(tiles, tw, th, cols=8):
    rows = (len(tiles) + cols - 1) // cols
    s = np.zeros((rows * th, cols * tw, 3), np.uint8)
    for k, tl in enumerate(tiles):
        s[(k // cols) * th:(k // cols + 1) * th, (k % cols) * tw:(k % cols + 1) * tw] = tl
    return s


def save(path, img, q=90):
    cv2.imwrite(path, cv2.cvtColor(img, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, q])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('home')
    ap.add_argument('--seconds', type=float, default=4.0)
    ap.add_argument('--fps', type=int, default=60)
    ap.add_argument('--blur', type=int, default=7)
    ap.add_argument('--shutter', type=float, default=0.5)
    ap.add_argument('--preview', action='store_true')
    ap.add_argument('--end', action='store_true', help='only the arrival frame (and its exterior)')
    ap.add_argument('--turn', type=float, default=None)
    ap.add_argument('--tag', default='')
    ap.add_argument('--workers', type=int, default=10)
    ap.add_argument('--out', default=os.path.join(C.HERE, 'out'))
    a = ap.parse_args()
    path = Path(a.home, turn=a.turn)
    room = Room(path)
    n = int(round(a.seconds * a.fps)) + 1
    tag = a.tag

    if a.end:
        img = frame_at(path, room, 1.0)
        save(os.path.join(a.out, f'{a.home}-arrival3d{tag}.jpg'), C.to_u8(img), 92)
        save(os.path.join(a.out, f'{a.home}-arrival3d{tag}-ext.jpg'), C.to_u8(X.render(path.cam_at(1.0))), 92)
        print('end yaw', round(math.degrees(path.az1), 2), 'f1', round(path.f1, 1))
        return

    if a.preview:
        idx = list(range(0, n, 8)) + [n - 1]
        small = Path(a.home, 480, 270, turn=a.turn)
        sroom = Room(small)
        tiles = [C.to_u8(frame_at(small, sroom, i / (n - 1))) for i in idx]
        save(os.path.join(a.out, f'{a.home}-flight3d{tag}-preview.jpg'), sheet(tiles, 480, 270, 6), 85)
        print('preview', len(tiles), 'tiles')
        return

    # the window track for the site: per frame of the forward clip, the facade homography and the box
    hs, boxes = [], []
    for i in range(n):
        cam = path.cam_at(i / (n - 1))
        hs.append([round(float(v), 9) for v in master_homography(path, cam)])
        q = cam.project(path.corners3d) / np.array([cam.w, cam.h])
        boxes.append([round(float(q[:, 0].min()), 5), round(float(q[:, 1].min()), 5),
                      round(float(q[:, 0].max()), 5), round(float(q[:, 1].max()), 5)])
    json.dump({'fps': a.fps, 'frames': boxes, 'h': hs}, open(os.path.join(a.out, f'{a.home}-track3d.json'), 'w'))

    master = os.path.join(a.out, f'{a.home}-flight-master.mkv')
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{C.OUT_W}x{C.OUT_H}',
                           '-r', str(a.fps), '-i', '-',
                           '-vf', 'scale=out_color_matrix=bt709:out_range=tv:flags=accurate_rnd+full_chroma_int,format=yuv420p',
                           '-c:v', 'ffv1', '-level', '3', '-slices', '16',
                           '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-color_range', 'tv',
                           master], stdin=subprocess.PIPE)

    def times(i):
        if i == 0 or i == n - 1 or a.blur <= 1:
            return [i / (n - 1)]
        span = a.shutter / (n - 1)
        return [min(1.0, max(0.0, i / (n - 1) + span * ((k + 0.5) / a.blur - 0.5))) for k in range(a.blur)]

    jobs = [(i, times(i), a.home, a.turn) for i in range(n)]
    pending, nxt = {}, 0
    with ProcessPoolExecutor(a.workers) as ex:
        for i, fr in ex.map(render_frame, jobs, chunksize=2):
            pending[i] = fr
            while nxt in pending:
                ff.stdin.write(pending.pop(nxt).tobytes())
                nxt += 1
    ff.stdin.close()
    ff.wait()
    print('master', master, n, 'frames')


if __name__ == '__main__':
    main()
