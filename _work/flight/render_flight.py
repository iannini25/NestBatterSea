"""
Render a flight: the camera travels over the official render from the site's tower view to one
home, ending centred on its window. Output: a lossless 60 fps master (FFV1, yuv420p, BT.709
limited, tagged) plus the per frame camera and window box for the site's outline.

usage: python render_flight.py <home> [--seconds 4] [--fps 60] [--blur 7] [--arc 0.05] [--preview]
"""
import argparse
import json
import math
import os
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import camera as C  # noqa: E402
import interior as I  # noqa: E402

REVEAL = (0.70, 0.98)   # the window opens (the room shows through the glass) as the camera lands

HOMES = {
    # window box in master px (js/data.js) and the end framing width in ORIG px
    'loft4': {'box_m': (1244.3, 534.4, 1293.7, 578.7), 'end_w': 130.0},
    'bung3': {'box_m': (1352.0, 806.0, 1406.0, 837.0), 'end_w': 130.0},
}
START = (1360.0, 815.0, 2400.0)          # the site's tower view, ORIG centre and width


def box_orig(box_m):
    x0, y0 = C.master_to_orig(box_m[0], box_m[1])
    x1, y1 = C.master_to_orig(box_m[2], box_m[3])
    return x0, y0, x1, y1


def zoom_path(p0, p1, rho=math.sqrt(2)):
    """van Wijk and Nuij smooth pan and zoom (as in d3.interpolateZoom); returns f(t) -> (x, y, w)"""
    ux0, uy0, w0 = p0
    ux1, uy1, w1 = p1
    dx, dy = ux1 - ux0, uy1 - uy0
    d2 = dx * dx + dy * dy
    rho2, rho4 = rho * rho, rho ** 4
    if d2 < 1e-12:
        S = math.log(w1 / w0) / rho
        return lambda t: (ux0 + t * dx, uy0 + t * dy, w0 * math.exp(rho * t * S))
    d1 = math.sqrt(d2)
    b0 = (w1 * w1 - w0 * w0 + rho4 * d2) / (2 * w0 * rho2 * d1)
    b1 = (w1 * w1 - w0 * w0 - rho4 * d2) / (2 * w1 * rho2 * d1)
    r0 = math.log(math.sqrt(b0 * b0 + 1) - b0)
    r1 = math.log(math.sqrt(b1 * b1 + 1) - b1)
    S = (r1 - r0) / rho

    def f(t):
        s = t * S
        u = w0 / (rho2 * d1) * (math.cosh(r0) * math.tanh(rho * s + r0) - math.sinh(r0))
        return (ux0 + u * dx, uy0 + u * dy, w0 * math.cosh(r0) / math.cosh(rho * s + r0))
    return f


def bezier_ease(x1, y1, x2, y2):
    """CSS cubic-bezier easing"""
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


def camera_at(t, path, ease, arc, end):
    """camera (cx, cy, w) at normalized time t in [0, 1]"""
    e = ease(t)
    x, y, w = path(e)
    if arc:
        # a gentle sideways curve, zero at both ends, proportional to the current view width
        x += arc * math.sin(math.pi * e) * w
    if t >= 1:
        return end
    return x, y, w


def smooth(x):
    x = min(1.0, max(0.0, x))
    return x * x * x * (x * (6 * x - 15) + 10)


def frame_at(t, path, ease, path_args, out_w=C.OUT_W, out_h=C.OUT_H):
    end = tuple(path_args['p'][1])
    cam = camera_at(t, path, ease, path_args['arc'], end)
    f = C.render(*cam, out_w, out_h)
    home = path_args.get('home')
    clear = smooth((t - REVEAL[0]) / (REVEAL[1] - REVEAL[0]))
    if home and clear > 0:
        spec = I.HOMES[home]
        s = spec['s0'] * (end[2] / cam[2]) ** 0.15
        centre = I.screen_of(I.aim_orig(home, end), cam, out_w, out_h)
        f, _ = I.through_glass(f, home, cam, end, clear, I.REFLECTION, s, centre, spec['shear'], out_w, out_h)
    return f


def render_frame(args):
    i, times, path_args = args
    path = zoom_path(*path_args['p'])
    ease = bezier_ease(*path_args['ease'])
    acc = None
    for t in times:
        f = frame_at(t, path, ease, path_args)
        acc = f if acc is None else acc + f
    return i, C.to_u8(acc / len(times))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('home')
    ap.add_argument('--seconds', type=float, default=4.0)
    ap.add_argument('--fps', type=int, default=60)
    ap.add_argument('--blur', type=int, default=7, help='sub frames per frame (motion blur)')
    ap.add_argument('--shutter', type=float, default=0.5, help='fraction of the frame interval')
    ap.add_argument('--arc', type=float, default=0.05)
    ap.add_argument('--ease', default='0.55,0,0.18,1')
    ap.add_argument('--preview', action='store_true', help='half size, every 6th frame, contact sheet only')
    ap.add_argument('--out', default=os.path.join(C.HERE, 'out'))
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--no-window', action='store_true', help='keep the glass as in the official render (for the glass masks)')
    a = ap.parse_args()
    h = HOMES[a.home]
    bx = box_orig(h['box_m'])
    end = ((bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2, h['end_w'])
    pa = {'p': (START, end), 'ease': tuple(float(v) for v in a.ease.split(',')), 'arc': a.arc,
          'home': None if a.no_window else a.home}
    n = int(round(a.seconds * a.fps)) + 1
    os.makedirs(a.out, exist_ok=True)

    def times(i):
        if i == 0 or i == n - 1 or a.blur <= 1:
            return [i / (n - 1)]
        span = a.shutter / (n - 1)
        return [min(1.0, max(0.0, i / (n - 1) + span * ((k + 0.5) / a.blur - 0.5))) for k in range(a.blur)]

    # track: camera and window box per frame (centre time)
    path = zoom_path(*pa['p'])
    ease = bezier_ease(*pa['ease'])
    cams, boxes = [], []
    for i in range(n):
        cx, cy, w = camera_at(i / (n - 1), path, ease, pa['arc'], end)
        hh = w * 9 / 16
        cams.append([round(v, 3) for v in ((cx - C.MASTER_BOX[0]) / C.M2O, (cy - C.MASTER_BOX[1]) / C.M2O, w / C.M2O)])
        boxes.append([round((bx[0] - cx) / w + 0.5, 5), round((bx[1] - cy) / hh + 0.5, 5),
                      round((bx[2] - cx) / w + 0.5, 5), round((bx[3] - cy) / hh + 0.5, 5)])
    json.dump({'fps': a.fps, 'frames': boxes, 'cam': cams, 'end': end}, open(os.path.join(a.out, f'{a.home}-track.json'), 'w'))

    if a.preview:
        import cv2
        idx = list(range(0, n, 6)) + [n - 1]
        tiles = []
        for i in idx:
            tiles.append(C.to_u8(frame_at(i / (n - 1), path, ease, pa, 384, 216)))
        cols = 7
        rows = (len(tiles) + cols - 1) // cols
        sheet = np.zeros((rows * 216, cols * 384, 3), np.uint8)
        for k, t in enumerate(tiles):
            sheet[(k // cols) * 216:(k // cols + 1) * 216, (k % cols) * 384:(k % cols + 1) * 384] = t
        cv2.imwrite(os.path.join(a.out, f'{a.home}-preview.jpg'), cv2.cvtColor(sheet, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 85])
        print('preview', len(tiles), 'frames')
        return

    master = os.path.join(a.out, f'{a.home}-flight-master.mkv')
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{C.OUT_W}x{C.OUT_H}',
                           '-r', str(a.fps), '-i', '-',
                           '-vf', 'scale=out_color_matrix=bt709:out_range=tv:flags=accurate_rnd+full_chroma_int,format=yuv420p',
                           '-c:v', 'ffv1', '-level', '3', '-slices', '16',
                           '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-color_range', 'tv',
                           master], stdin=subprocess.PIPE)
    jobs = [(i, times(i), pa) for i in range(n)]
    pending = {}
    nxt = 0
    with ProcessPoolExecutor(a.workers) as ex:
        for i, fr in ex.map(render_frame, jobs, chunksize=2):
            pending[i] = fr
            while nxt in pending:
                ff.stdin.write(pending.pop(nxt).tobytes())
                nxt += 1
                if nxt % 30 == 0:
                    print(f'{a.home}: {nxt}/{n}', flush=True)
    ff.stdin.close()
    ff.wait()
    print('master', master, n, 'frames')


if __name__ == '__main__':
    main()
