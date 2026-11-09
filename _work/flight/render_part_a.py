"""
Part A of a hybrid flight: the exact camera move over the official image (render_previz.Previz),
from the site's tower view to the hand-off time T_SEAM, at 60 fps with motion blur, plus the
hand-off frame (PNG) that starts the AI final approach.

usage: python render_part_a.py <home> --seam 0.45 [--seconds 5] [--fps 60] [--blur 7]
The previz timeline is --seconds long; part A covers [0, seam] of it at real speed.
"""
import argparse
import json
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

_P = {}


def render_frame(args):
    i, times, home = args
    if home not in _P:
        _P[home] = RP.Previz(home)
    p = _P[home]
    acc = None
    for t in times:
        f = X.render(p.cam_at(t))
        acc = f if acc is None else acc + f
    return i, C.to_u8(acc / len(times))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('home')
    ap.add_argument('--seam', type=float, required=True)
    ap.add_argument('--seconds', type=float, default=5.0)
    ap.add_argument('--fps', type=int, default=60)
    ap.add_argument('--blur', type=int, default=7)
    ap.add_argument('--shutter', type=float, default=0.5)
    ap.add_argument('--workers', type=int, default=12)
    ap.add_argument('--out', default=os.path.join(C.HERE, 'out', 'hybrid'))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    p = RP.Previz(a.home)
    n = int(round(a.seconds * a.seam * a.fps)) + 1          # frames from t = 0 to t = seam
    dt = a.seam / (n - 1)
    seam = C.to_u8(X.render(p.cam_at(a.seam)))
    cv2.imwrite(os.path.join(a.out, f'{a.home}-seam.png'), cv2.cvtColor(seam, cv2.COLOR_RGB2BGR))
    # the window track over part A (normalized quad per frame)
    track = []
    for i in range(n):
        c = p.cam_at(i * dt)
        q = c.project(p.corners3d) / np.array([c.w, c.h])
        track.append([[round(float(x), 5), round(float(y), 5)] for x, y in q])
    json.dump({'fps': a.fps, 'seam': a.seam, 'frames': track}, open(os.path.join(a.out, f'{a.home}-partA-track.json'), 'w'))
    master = os.path.join(a.out, f'{a.home}-partA.mkv')
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{C.OUT_W}x{C.OUT_H}',
                           '-r', str(a.fps), '-i', '-', '-c:v', 'ffv1', '-level', '3', '-pix_fmt', 'yuv444p', master], stdin=subprocess.PIPE)

    def times(i):
        t = i * dt
        if i == 0 or i == n - 1 or a.blur <= 1:
            return [t]
        span = a.shutter * dt
        return [max(0.0, min(a.seam, t + span * ((k + 0.5) / a.blur - 0.5))) for k in range(a.blur)]

    jobs = [(i, times(i), a.home) for i in range(n)]
    pending, nxt = {}, 0
    with ProcessPoolExecutor(a.workers) as ex:
        for i, fr in ex.map(render_frame, jobs, chunksize=2):
            pending[i] = fr
            while nxt in pending:
                ff.stdin.write(pending.pop(nxt).tobytes())
                nxt += 1
    ff.stdin.close()
    ff.wait()
    print('part A', master, n, 'frames; seam frame saved')


if __name__ == '__main__':
    main()
