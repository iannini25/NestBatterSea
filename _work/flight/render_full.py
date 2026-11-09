"""
A window flight rendered entirely by the exact virtual camera (no AI video): the official render
split into planar layers (proxy.py) plus, on the home's facade plane, its end image (the straight on
view of the window, registered on the official facade) as a sharp inlay. Every frame is the same
fixed scene seen from a moving camera: nothing in the building or the room changes over the shot.

The inlay is there from the start; only in the first fraction of a second, while the window is a few
pixels wide, it is faded in from the official pixels (the still on the site), which reads as the
lights coming on. Close up the glow around the tower (a bloom of the far view) fades out, so no pale
band grows around the tower.

Timing: the camera path is reparametrized so the perceived speed (screen motion of the facade) is
one smooth bell: slow start, fast middle, slow arrival, no plateau or dip.

usage: python render_full.py loft4 --key ../ai/gen/loft4-end-gpt.png --reg out/hybrid/loft4-key-A.npy
         [--seconds 5] [--fps 60] [--blur 7] [--end-scale 0.92] [--sheet]
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
import render_previz as RP  # noqa: E402

_S = {}


def smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * x * (x * (6 * x - 15) + 10)


class Flight:
    def __init__(self, a, out_w=C.OUT_W, out_h=C.OUT_H):
        self.a = a
        h = RP.HOMES[a.home]
        ref = RP.Previz(a.home, 1920, 1080)                       # the end view the inlay was registered on
        self.p = RP.Previz(a.home, out_w, out_h, end_dist=h['end_dist'] * a.end_scale)
        pl = ref.plane
        H_end, _ = X.h_plane(ref.cam_at(1.0), pl)                 # 1920 px -> ORIG
        A = np.load(a.reg)                                        # 1920 px -> inlay px
        K = A @ np.linalg.inv(H_end)                              # ORIG -> inlay px
        key = cv2.cvtColor(cv2.imread(a.key), cv2.COLOR_BGR2RGB).astype(np.float32)
        room = None
        if a.layers:
            # the end image split in two: F (premultiplied RGBA: facade, frames, balcony) on the facade
            # plane, and the room R on a parallel plane a.room_depth units behind it
            Fa = cv2.imread(a.layers + '-F.png', cv2.IMREAD_UNCHANGED).astype(np.float32)
            al = Fa[..., 3:4] / 255.0
            key = np.concatenate([cv2.cvtColor(Fa[..., :3].astype(np.uint8), cv2.COLOR_BGR2RGB).astype(np.float32) * al, Fa[..., 3:4]], 2)
            Rm = cv2.cvtColor(cv2.imread(a.layers + '-R.png'), cv2.COLOR_BGR2RGB).astype(np.float32)
            rl = [Rm]
            while min(rl[-1].shape[:2]) > 32:
                rl.append(cv2.pyrDown(rl[-1]))
            n_, d_ = pl
            room = dict(levels=rl, plane=(n_, d_ + a.room_depth * (1 if d_ > 0 else -1)), ref=ref.cam_at(1.0), A=A)
        kh, kw = key.shape[:2]
        e = a.feather * kw
        yy, xx = np.mgrid[0:kh, 0:kw].astype(np.float32)
        d = np.minimum(np.minimum(xx, kw - 1 - xx), np.minimum(yy, kh - 1 - yy))
        m = np.clip(d / e, 0, 1)
        m = m * m * (3 - 2 * m)
        lv, lm = [key], [m]
        while min(lv[-1].shape[:2]) > 32:
            lv.append(cv2.pyrDown(lv[-1]))
            lm.append(cv2.pyrDown(lm[-1]))
        X.GLOW_FADE = (a.glow_fade[0], a.glow_fade[1])
        X.TOWER_MATTE = True
        X.INLAY = dict(plane=pl, levels=lv, mask=lm, K=K, alpha=1.0, room=room)
        self.pl = pl
        self.tmap = self._timing()

    def _speed(self, t, dt=1e-3):
        """perceived speed at path time t: mean screen motion of the facade plane (px per unit t)"""
        c0, c1 = self.p.cam_at(max(0.0, t - dt)), self.p.cam_at(min(1.0, t + dt))
        H0, _ = X.h_plane(c0, self.pl)
        H1, _ = X.h_plane(c1, self.pl)
        M = np.linalg.inv(H1) @ H0
        us, vs = np.meshgrid(np.linspace(0.1, 0.9, 7) * c0.w, np.linspace(0.1, 0.9, 5) * c0.h)
        P = np.stack([us.ravel(), vs.ravel(), np.ones(us.size)])
        Q = M @ P
        Q = Q[:2] / Q[2]
        return float(np.mean(np.hypot(Q[0] - P[0], Q[1] - P[1]))) / (min(1.0, t + dt) - max(0.0, t - dt))

    def _timing(self):
        if getattr(self.a, 'flow_timing', None):
            ts, prog = np.load(self.a.flow_timing)               # measured optical flow (flow_timing.py)
            return ts, prog
        ts = np.linspace(0, 1, 801)
        v = np.array([self._speed(t) for t in ts])
        prog = np.concatenate([[0], np.cumsum((v[1:] + v[:-1]) / 2 * np.diff(ts))])
        prog /= prog[-1]
        self.raw_speed = v
        return ts, prog

    def t_of(self, tau):
        """path time for shot time tau in [0, 1]: progress follows a smootherstep (one bell of speed)"""
        ts, prog = self.tmap
        target = smooth(tau) if self.a.ease == 'smoother' else 0.5 - 0.5 * math.cos(math.pi * min(max(tau, 0), 1))
        return float(np.interp(target, prog, ts))

    def alpha(self, tau):
        t0, t1 = self.a.light
        return smooth((tau - t0) / (t1 - t0)) if t1 > t0 else 1.0

    def cam(self, tau):
        return self.p.cam_at(self.t_of(tau))


def _init(a, w, h):
    _S['f'] = Flight(a, w, h)


def render_frame(args):
    i, taus = args
    f = _S['f']
    acc = None
    for tau in taus:
        X.INLAY['alpha'] = f.alpha(tau)
        img = X.render(f.cam(tau))
        acc = img if acc is None else acc + img
    return i, C.to_u8(acc / len(taus))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('home')
    ap.add_argument('--key', required=True)
    ap.add_argument('--reg', required=True)
    ap.add_argument('--seconds', type=float, default=5.0)
    ap.add_argument('--fps', type=int, default=60)
    ap.add_argument('--blur', type=int, default=7)
    ap.add_argument('--shutter', type=float, default=0.5)
    ap.add_argument('--end-scale', type=float, default=0.92)
    ap.add_argument('--feather', type=float, default=0.035)
    ap.add_argument('--layers', help='prefix of <prefix>-F.png / <prefix>-R.png (inside3/out/loft4)')
    ap.add_argument('--room-depth', type=float, default=40.0, help='room plane behind the facade (units, 0.15 m)')
    ap.add_argument('--light', type=float, nargs=2, default=(0.0, 0.12))
    ap.add_argument('--glow-fade', type=float, nargs=2, default=(1.0, 0.45))
    ap.add_argument('--ease', default='smoother', choices=['smoother', 'cosine'])
    ap.add_argument('--flow-timing', help='progress curve from flow_timing.py (perceived speed)')
    ap.add_argument('--workers', type=int, default=10)
    ap.add_argument('--sheet', action='store_true')
    ap.add_argument('--out', default=os.path.join(C.HERE, 'out', 'full'))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    n = int(round(a.seconds * a.fps)) + 1
    if a.sheet:
        f = Flight(a, 480, 270)
        idx = list(range(0, n, max(1, n // 23))) + [n - 1]
        tiles = []
        for i in idx:
            tau = i / (n - 1)
            X.INLAY['alpha'] = f.alpha(tau)
            tl = C.to_u8(f.p.cam_at(f.t_of(tau)) and X.render(f.cam(tau)))
            tiles.append(cv2.putText(tl.copy(), str(i), (6, 22), 0, 0.7, (255, 255, 0), 2))
        cols = 6
        rows = (len(tiles) + cols - 1) // cols
        sheet = np.zeros((rows * 270, cols * 480, 3), np.uint8)
        for k, tl in enumerate(tiles):
            sheet[(k // cols) * 270:(k // cols + 1) * 270, (k % cols) * 480:(k % cols + 1) * 480] = tl
        cv2.imwrite(os.path.join(a.out, f'{a.home}-sheet.jpg'), cv2.cvtColor(sheet, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 85])
        sp = [f._speed(f.t_of(i / 100.0)) * (f.t_of(min(1, i / 100.0 + 0.005)) - f.t_of(max(0, i / 100.0 - 0.005))) / 0.01 for i in range(101)]
        print('speed (px per unit shot time) every 0.1:', [round(sp[i]) for i in range(0, 101, 10)])
        return
    f = Flight(a)
    dt = 1.0 / (n - 1)

    def taus(i):
        tau = i * dt
        if i == 0 or i == n - 1 or a.blur <= 1:
            return [tau]
        span = a.shutter * dt
        return [min(1.0, max(0.0, tau + span * ((k + 0.5) / a.blur - 0.5))) for k in range(a.blur)]

    # the window track (normalized quad per frame) for the site
    track = []
    for i in range(n):
        c = f.cam(i * dt)
        q = c.project(f.p.corners3d) / np.array([c.w, c.h])
        track.append([[round(float(x), 5), round(float(y), 5)] for x, y in q])
    json.dump({'fps': a.fps, 'frames': track}, open(os.path.join(a.out, f'{a.home}-track.json'), 'w'))
    master = os.path.join(a.out, f'{a.home}-flight-master.mkv')
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{C.OUT_W}x{C.OUT_H}',
                           '-r', str(a.fps), '-i', '-', '-c:v', 'ffv1', '-level', '3', '-pix_fmt', 'yuv444p', master], stdin=subprocess.PIPE)
    jobs = [(i, taus(i)) for i in range(n)]
    pending, nxt, last = {}, 0, None
    with ProcessPoolExecutor(a.workers, initializer=_init, initargs=(a, C.OUT_W, C.OUT_H)) as ex:
        for i, fr in ex.map(render_frame, jobs, chunksize=2):
            pending[i] = fr
            while nxt in pending:
                last = pending.pop(nxt)
                ff.stdin.write(last.tobytes())
                if nxt % 30 == 0:
                    print('frame', nxt, flush=True)
                nxt += 1
    ff.stdin.close()
    ff.wait()
    cv2.imwrite(os.path.join(a.out, f'{a.home}-last.png'), cv2.cvtColor(last, cv2.COLOR_RGB2BGR))
    print('flight', master, n, 'frames')


if __name__ == '__main__':
    main()
