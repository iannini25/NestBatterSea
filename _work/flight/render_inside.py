"""
Render Step inside. It starts exactly where the flight ends (the official render, the home's
glass open onto the room at its real scale) and keeps moving in: the last reflections clear, the
facade grows past the lens and defocuses, and the room keeps approaching until the move settles
exactly on the living room photograph, the first photo of the tour. Nothing is generated: the
exterior is the official render and the interior is the published photograph, unchanged.

usage: python render_inside.py <home> [--seconds 2.6] [--fps 60] [--blur 7] [--preview]
needs out/<home>-track.json (render_flight.py) and out/<home>-glass-2x.npy (glass_masks.py)
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
import interior as I  # noqa: E402

T_ZOOM = 0.62            # the facade zoom runs over [0, T_ZOOM] of the clip
ZOOM_K = 5.0             # how far the facade zooms in past the arrival framing
REFL_OFF = (0.0, 0.30)   # the remaining reflections clear over this span
EXT_FADE = (0.52, 0.70)  # what is left of the facade (blurred mullions) fades over this span
PHOTO_END = 0.92         # the photo settles at scale 1 by this time
DEFOCUS = 9.0            # facade blur (px at 1080p) at the end of its zoom


def smooth(x):
    x = min(1.0, max(0.0, x))
    return x * x * x * (x * (6 * x - 15) + 10)


def compose(t, start, home, out_w=C.OUT_W, out_h=C.OUT_H):
    spec = I.HOMES[home]
    aim = I.aim_orig(home, start)
    cx0, cy0, w0 = start
    z = min(1.0, max(0.0, t / T_ZOOM)) ** 1.35
    w = w0 / (ZOOM_K ** z)
    f = min(1.0, (1 - w / w0) / (1 - 1 / ZOOM_K))
    cam = (cx0 + (aim[0] - cx0) * f, cy0 + (aim[1] - cy0) * f, w)
    q = smooth(t / PHOTO_END)
    s = spec['s0'] * (1 / spec['s0']) ** q
    a_scr = I.screen_of(aim, cam, out_w, out_h)
    centre = (a_scr[0] * (1 - q) + out_w / 2 * q, a_scr[1] * (1 - q) + out_h / 2 * q)
    shear = spec['shear'] * (1 - q)
    refl = I.REFLECTION * (1 - smooth((t - REFL_OFF[0]) / (REFL_OFF[1] - REFL_OFF[0])))
    ext_vis = 1 - smooth((t - EXT_FADE[0]) / (EXT_FADE[1] - EXT_FADE[0]))
    if ext_vis <= 0:
        return I.warp_photo(spec['photo'], s, centre, shear, out_w, out_h)
    ext = C.render(*cam, out_w, out_h)
    d = DEFOCUS * z ** 1.5 * out_w / C.OUT_W
    if d > 0.3:
        ext = cv2.GaussianBlur(ext, (0, 0), d)
    out, photo = I.through_glass(ext, home, cam, start, 1.0, refl, s, centre, shear, out_w, out_h)
    if ext_vis < 1:
        out = out * ext_vis + photo * (1 - ext_vis)
    return out


def render_frame(args):
    i, times, start, home = args
    acc = None
    for t in times:
        f = compose(t, start, home)
        acc = f if acc is None else acc + f
    return i, C.to_u8(acc / len(times))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('home')
    ap.add_argument('--seconds', type=float, default=2.6)
    ap.add_argument('--fps', type=int, default=60)
    ap.add_argument('--blur', type=int, default=7)
    ap.add_argument('--shutter', type=float, default=0.5)
    ap.add_argument('--preview', action='store_true')
    ap.add_argument('--out', default=os.path.join(C.HERE, 'out'))
    ap.add_argument('--workers', type=int, default=10)
    a = ap.parse_args()
    track = json.load(open(os.path.join(a.out, f'{a.home}-track.json')))
    start = tuple(track['end'])
    n = int(round(a.seconds * a.fps)) + 1

    def times(i):
        if i == 0 or i == n - 1 or a.blur <= 1:
            return [i / (n - 1)]
        span = a.shutter / (n - 1)
        return [min(1.0, max(0.0, i / (n - 1) + span * ((k + 0.5) / a.blur - 0.5))) for k in range(a.blur)]

    if a.preview:
        idx = list(range(0, n, 5)) + [n - 1]
        tiles = [C.to_u8(compose(i / (n - 1), start, a.home, 384, 216)) for i in idx]
        cols = 8
        rows = (len(tiles) + cols - 1) // cols
        sheet = np.zeros((rows * 216, cols * 384, 3), np.uint8)
        for k, tl in enumerate(tiles):
            sheet[(k // cols) * 216:(k // cols + 1) * 216, (k % cols) * 384:(k % cols + 1) * 384] = tl
        cv2.imwrite(os.path.join(a.out, f'{a.home}-inside-preview.jpg'), cv2.cvtColor(sheet, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 85])
        print('preview', len(tiles))
        return

    master = os.path.join(a.out, f'{a.home}-inside-master.mkv')
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{C.OUT_W}x{C.OUT_H}',
                           '-r', str(a.fps), '-i', '-',
                           '-vf', 'scale=out_color_matrix=bt709:out_range=tv:flags=accurate_rnd+full_chroma_int,format=yuv420p',
                           '-c:v', 'ffv1', '-level', '3', '-slices', '16',
                           '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-color_range', 'tv',
                           master], stdin=subprocess.PIPE)
    jobs = [(i, times(i), start, a.home) for i in range(n)]
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
