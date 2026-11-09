"""
Previz of the window flights: the exact camera path, rendered from the official image split into
3D planar layers (proxy.py). Far away it is sharp and exact; close up it is soft (the official
pixels are magnified), so it is a GUIDE for the AI render, not a final clip.

The camera starts exactly on the site's tower view, travels across the river, rises and turns,
and ends level at the window's mid height, square on to the facade, a few metres from the glass,
with a moderately wide lens: the window fills the frame and, through it, the room's floor and
ceiling would both be visible.

usage: python render_previz.py <home> [--seconds 5] [--fps 24] [--out out] [--sheet]
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
import proxy as X  # noqa: E402

HOMES = {
    # face: facade of the home; box: window box (master px); turn: 1 = end square on to the face
    # end_dist: distance from the window plane at arrival (units; the bay is about 46 units wide)
    # end_hfov: horizontal field of view at arrival (degrees)
    # side: +1 the camera swings to the right of the window on the way, -1 to the left (orbit side)
    'loft4': {'face': 'SE', 'box': (1244.3, 534.4, 1293.7, 578.7), 'turn': 1.0, 'end_dist': 96.0, 'end_hfov': 55.0},
    'bung3': {'face': 'NE', 'box': (1352.0, 806.0, 1406.0, 837.0), 'turn': 1.0, 'end_dist': 110.0, 'end_hfov': 55.0},
}


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
        for _ in range(60):
            mid = (lo + hi) / 2
            if bx(mid) < x:
                lo = mid
            else:
                hi = mid
        return by((lo + hi) / 2)
    return f


E_DIST = bezier_ease(0.40, 0.0, 0.20, 1.0)     # travel (distance, log)
E_TURN = bezier_ease(0.50, 0.0, 0.30, 1.0)     # orbit towards square on
E_RISE = bezier_ease(0.35, 0.0, 0.25, 1.0)     # climb to the window's mid height
E_LENS = bezier_ease(0.55, 0.0, 0.25, 1.0)     # lens widening, mostly late


class Previz:
    def __init__(self, home, out_w=C.OUT_W, out_h=C.OUT_H, turn=None, end_dist=None, end_hfov=None):
        h = HOMES[home]
        self.home, self.w, self.h = home, out_w, out_h
        x0, y0 = C.master_to_orig(h['box'][0], h['box'][1])
        x1, y1 = C.master_to_orig(h['box'][2], h['box'][3])
        self.plane = X.P_SE if h['face'] == 'SE' else X.P_NE
        self.bay = X.on_plane(self.plane, (x0 + x1) / 2, (y0 + y1) / 2)
        self.corners3d = np.array([X.on_plane(self.plane, x, y) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))])
        n = self.plane[0] if self.plane[0][2] < 0 else -self.plane[0]
        self.start = X.start_cam(out_w, out_h)
        bx, by_, bz = self.bay
        self.D0 = math.hypot(bx, bz)
        self.az0 = math.atan2(bx, bz)
        square = math.atan2(-n[0], -n[2])
        k = h['turn'] if turn is None else turn
        self.az1 = self.az0 + (square - self.az0) * k
        # the window's facade is not perpendicular to the end view unless turn = 1: the end distance
        # is measured along the view axis to the window centre
        self.D1 = h['end_dist'] if end_dist is None else end_dist
        hfov = math.radians(h['end_hfov'] if end_hfov is None else end_hfov)
        self.f1 = out_w / 2 / math.tan(hfov / 2)
        self.f0 = self.start.f
        sx, sy = self.start.project(self.bay)[0]
        self.x0s, self.y0s = float(sx), float(sy)

    def cam_at(self, t):
        if t <= 0:
            return self.start
        e, et, er, el = E_DIST(t), E_TURN(t), E_RISE(t), E_LENS(t)
        w = os.environ.get('PREVIZ_WARP')
        if w and self.home == os.environ.get('PREVIZ_WARP_HOME', 'bung3'):
            # per component time warp on [0, seam] (same pose at 0 and at the seam, rate k at the seam):
            # h(u) = u + (k - 1) u^2 (u - 1), so the deterministic part's motion at the hand off can match
            # the next clip's (approach / turn / rise / lens independently)
            kd, kt, kr, kl, seam = (float(v) for v in w.split(','))
            if t < seam:
                h = lambda k: seam * ((t / seam) + (k - 1) * (t / seam) ** 2 * ((t / seam) - 1))
                e, et, er, el = E_DIST(h(kd)), E_TURN(h(kt)), E_RISE(h(kr)), E_LENS(h(kl))
        return self._cam(e, et, er, el)

    def _cam(self, e, et, er, el):
        bx, by_, bz = self.bay
        D = self.D0 * (self.D1 / self.D0) ** e
        az = self.az0 + (self.az1 - self.az0) * et
        yc = by_ * er
        pos = np.array([bx - D * math.sin(az), yc, bz - D * math.cos(az)])
        yaw = az - self.az0 * (1 - et)                  # the window drifts to the frame centre
        f = self.f0 * (self.f1 / self.f0) ** el
        dz = D * math.cos(az - yaw)
        # the window's place on screen: from its place in the tower view to the frame centre
        x_t = self.x0s + (self.w / 2 - self.x0s) * et
        y_t = self.y0s + (self.h / 2 - self.y0s) * er
        ppx = x_t - f * math.tan(az - yaw)
        ppy = y_t + f * (by_ - yc) / dz
        return X.Cam(pos, yaw, f, (ppx, ppy), self.w, self.h)


_P = {}


def render_frame(args):
    i, t, home, kw = args
    if home not in _P:
        _P[home] = Previz(home, **kw)
    return i, C.to_u8(X.render(_P[home].cam_at(t)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('home')
    ap.add_argument('--seconds', type=float, default=5.0)
    ap.add_argument('--fps', type=int, default=24)
    ap.add_argument('--size', default='1920x1080')
    ap.add_argument('--turn', type=float, default=None)
    ap.add_argument('--end-dist', type=float, default=None)
    ap.add_argument('--end-hfov', type=float, default=None)
    ap.add_argument('--sheet', action='store_true', help='contact sheet only')
    ap.add_argument('--tag', default='')
    ap.add_argument('--workers', type=int, default=12)
    ap.add_argument('--out', default=os.path.join(C.HERE, 'out', 'previz'))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    w, h = map(int, a.size.split('x'))
    kw = dict(out_w=w, out_h=h, turn=a.turn, end_dist=a.end_dist, end_hfov=a.end_hfov)
    n = int(round(a.seconds * a.fps)) + 1
    p = Previz(a.home, **kw)
    if a.sheet:
        idx = list(range(0, n, max(1, n // 23))) + [n - 1]
        sp = Previz(a.home, **dict(kw, out_w=480, out_h=270))
        tiles = [C.to_u8(X.render(sp.cam_at(i / (n - 1)))) for i in idx]
        cols = 6
        rows = (len(tiles) + cols - 1) // cols
        sheet = np.zeros((rows * 270, cols * 480, 3), np.uint8)
        for k, tl in enumerate(tiles):
            sheet[(k // cols) * 270:(k // cols + 1) * 270, (k % cols) * 480:(k % cols + 1) * 480] = tl
        cv2.imwrite(os.path.join(a.out, f'{a.home}{a.tag}-sheet.jpg'), cv2.cvtColor(sheet, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 85])
        end = C.to_u8(X.render(p.cam_at(1.0)))
        cv2.imwrite(os.path.join(a.out, f'{a.home}{a.tag}-end.png'), cv2.cvtColor(end, cv2.COLOR_RGB2BGR))
        print('sheet', len(tiles), 'end f', round(p.f1, 1), 'D1', p.D1, 'az1', round(math.degrees(p.az1), 2))
        return
    # the camera per frame (for the site's window track and for checks)
    cams = []
    for i in range(n):
        c = p.cam_at(i / (n - 1))
        q = c.project(p.corners3d) / np.array([c.w, c.h])
        cams.append({'pos': [round(float(v), 3) for v in c.pos], 'yaw': round(float(c.yaw), 6), 'f': round(float(c.f), 3),
                     'pp': [round(float(v), 3) for v in c.pp], 'window': [[round(float(x), 5), round(float(y), 5)] for x, y in q]})
    json.dump({'home': a.home, 'fps': a.fps, 'size': [w, h], 'frames': cams}, open(os.path.join(a.out, f'{a.home}{a.tag}-cams.json'), 'w'))
    path = os.path.join(a.out, f'{a.home}{a.tag}-previz.mp4')
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{w}x{h}', '-r', str(a.fps), '-i', '-',
                           '-c:v', 'libx264', '-preset', 'slow', '-crf', '14', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', path],
                          stdin=subprocess.PIPE)
    jobs = [(i, i / (n - 1), a.home, kw) for i in range(n)]
    pending, nxt = {}, 0
    with ProcessPoolExecutor(a.workers) as ex:
        for i, fr in ex.map(render_frame, jobs, chunksize=2):
            pending[i] = fr
            while nxt in pending:
                ff.stdin.write(pending.pop(nxt).tobytes())
                nxt += 1
    ff.stdin.close()
    ff.wait()
    print('previz', path, n, 'frames')


if __name__ == '__main__':
    main()
