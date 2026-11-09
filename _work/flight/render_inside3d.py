"""
Step inside, continuing the 3D flight (render_flight3d.py). It starts on the flight's last frame
(the window open onto the room) and the same camera keeps moving in: forward towards the glass and
sideways towards the room's centre of view, so the facade grows past the lens and defocuses while
the room photograph settles exactly full frame. Nothing is generated: the exterior is the official
render seen by the camera, the room is the unaltered photograph.

usage: python render_inside3d.py <home> [--seconds 2.6] [--fps 60] [--blur 7] [--preview]
"""
import argparse
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
import render_flight3d as F  # noqa: E402

T_ZOOM = 0.62            # the camera's move runs over [0, T_ZOOM] of the clip
ZOOM_K = 5.0             # the facade at the window grows this much (the camera ends 1/5 of the way out)
REFL_OFF = (0.0, 0.30)   # the remaining reflections clear over this span
EXT_FADE = (0.52, 0.70)  # what is left of the facade (blurred mullions) fades over this span
PHOTO_END = 0.92         # the photo settles full frame by this time
DEFOCUS = 9.0            # facade blur (px at 1080p) at the end of the move


def smooth(x):
    x = min(1.0, max(0.0, x))
    return x * x * x * (x * (6 * x - 15) + 10)


class Inside:
    def __init__(self, home, out_w=C.OUT_W, out_h=C.OUT_H):
        self.home = home
        self.path = F.Path(home, out_w, out_h)
        self.room = F.Room(self.path)
        self.end = self.path.cam_at(1.0)
        e = self.end
        spec = I.HOMES[home]
        self.aim = X.on_plane(self.path.plane, *F.old_px_to_orig(home, *spec['aim']))
        self.aim_c = (self.aim - e.pos) @ e.R                 # camera coords: x right, y up, z forward
        self.aim_scr = e.project(self.aim)[0]
        self.w, self.h = out_w, out_h

    def cam_at(self, t):
        e = self.end
        z = min(1.0, max(0.0, t / T_ZOOM)) ** 1.35
        if z <= 0:
            return e
        k = ZOOM_K ** z
        frac = (1 - 1 / k) / (1 - 1 / ZOOM_K)
        ax, ay, az = self.aim_c
        fwd = az * (1 - 1 / k)
        zr = az - fwd                                         # the aim's remaining depth
        ut = self.aim_scr[0] + (self.w / 2 - self.aim_scr[0]) * frac
        vt = self.aim_scr[1] + (self.h / 2 - self.aim_scr[1]) * frac
        lx = ax - (ut - e.pp[0]) * zr / e.f                   # sideways so the aim lands on (ut, vt)
        ly = ay - (e.pp[1] - vt) * zr / e.f
        pos = e.pos + e.R @ np.array([lx, ly, fwd])
        return X.Cam(pos, e.yaw, e.f, e.pp, self.w, self.h), z

    def photo_quad(self, t):
        q = smooth(t / PHOTO_END)
        s0 = self.room.scale
        s = s0 * (1 / s0) ** q
        cx = self.room.centre[0] * (1 - q) + self.w / 2 * q
        cy = self.room.centre[1] * (1 - q) + self.h / 2 * q
        hw, hh = s * self.w / 2, s * self.h / 2
        return np.array([(cx - hw, cy - hh), (cx + hw, cy - hh), (cx + hw, cy + hh), (cx - hw, cy + hh)])

    def compose(self, t):
        if t <= 0:
            cam, z = self.end, 0.0
        else:
            r = self.cam_at(t)
            cam, z = (r if isinstance(r, tuple) else (r, 0.0))
        quad = self.room.rect if t <= 0 else self.photo_quad(t)
        refl = I.REFLECTION * (1 - smooth((t - REFL_OFF[0]) / (REFL_OFF[1] - REFL_OFF[0])))
        ext_vis = 1 - smooth((t - EXT_FADE[0]) / (EXT_FADE[1] - EXT_FADE[0]))
        if ext_vis <= 0:
            return F.warp_photo_quad(I.HOMES[self.home]['photo'], quad, self.w, self.h)
        ext = X.render(cam)
        d = DEFOCUS * z ** 1.5 * self.w / C.OUT_W
        if d > 0.3:
            ext = cv2.GaussianBlur(ext, (0, 0), d)
        out, photo, _ = F.through_glass(self.home, ext, cam, self.path.plane, quad, 1.0, refl)
        if ext_vis < 1:
            out = out * ext_vis + photo * (1 - ext_vis)
        return out


_S = {}


def render_frame(args):
    i, times, home = args
    if home not in _S:
        _S[home] = Inside(home)
    s = _S[home]
    acc = None
    for t in times:
        f = s.compose(t)
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
    n = int(round(a.seconds * a.fps)) + 1

    if a.preview:
        s = Inside(a.home, 480, 270)
        idx = list(range(0, n, 5)) + [n - 1]
        tiles = [C.to_u8(s.compose(i / (n - 1))) for i in idx]
        F.save(os.path.join(a.out, f'{a.home}-inside3d-preview.jpg'), F.sheet(tiles, 480, 270, 6), 85)
        print('preview', len(tiles))
        return

    def times(i):
        if i == 0 or i == n - 1 or a.blur <= 1:
            return [i / (n - 1)]
        span = a.shutter / (n - 1)
        return [min(1.0, max(0.0, i / (n - 1) + span * ((k + 0.5) / a.blur - 0.5))) for k in range(a.blur)]

    master = os.path.join(a.out, f'{a.home}-inside-master.mkv')
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{C.OUT_W}x{C.OUT_H}',
                           '-r', str(a.fps), '-i', '-',
                           '-vf', 'scale=out_color_matrix=bt709:out_range=tv:flags=accurate_rnd+full_chroma_int,format=yuv420p',
                           '-c:v', 'ffv1', '-level', '3', '-slices', '16',
                           '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-color_range', 'tv',
                           master], stdin=subprocess.PIPE)
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
    print('master', master, n, 'frames')


if __name__ == '__main__':
    main()
