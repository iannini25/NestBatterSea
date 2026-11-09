"""
Step inside, rendered by a real camera over two fixed depth layers built from the home's end image
(layers.py / b3_layers.py): F (facade, frames, balcony, plants) and R (the room). The camera moves
straight towards the room; nothing in the scene changes, only the viewpoint: near things (the planter,
the door frames) grow and slide out of view faster than the room (true parallax), and the shot ends on
the room filling the frame. Frame 0 is the end image itself (the flight's last frame).

usage: python render_inside.py bung3 --zF 16.5 --zR 23 --final 845 575 960 [--seconds 3.6]
"""
import argparse, json, math, os, subprocess
import cv2
import numpy as np

H0 = os.path.dirname(os.path.abspath(__file__))
OUT_W, OUT_H = 1920, 1080


def smoother(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * x * (x * (6 * x - 15) + 10)


class Scene:
    def __init__(self, a):
        self.a = a
        F = cv2.imread(os.path.join(H0, 'out', f'{a.home}-F.png'), cv2.IMREAD_UNCHANGED).astype(np.float32)
        R = cv2.imread(os.path.join(H0, 'out', f'{a.home}-R.png')).astype(np.float32)
        cy = a.crop_y                                                    # the flight's 16:9 crop of the end image
        if cy:
            F, R = F[cy:-cy], R[cy:-cy]
        self.H, self.W = R.shape[:2]
        al = F[..., 3:4] / 255.0
        Fp = np.concatenate([F[..., :3] * al, al * 255.0], 2)          # premultiplied
        k = OUT_W / R.shape[1]
        self.F, self.Fd = [Fp, cv2.resize(Fp, (OUT_W, OUT_H), interpolation=cv2.INTER_AREA)], [1.0, k]
        if a.f2:                                                         # a level at twice the density, so the near layer stays crisp when magnified
            F2 = cv2.resize(Fp, (self.W * 2, self.H * 2), interpolation=cv2.INTER_LANCZOS4)
            F2[..., :3] = F2[..., :3] + a.f2 * (F2[..., :3] - cv2.GaussianBlur(F2[..., :3], (0, 0), 1.8))
            F2 = np.clip(F2, 0, 255); F2[..., :3] = np.minimum(F2[..., :3], F2[..., 3:4])
            self.F, self.Fd = [F2] + self.F, [2.0] + self.Fd
        while min(self.F[-1].shape[:2]) > 64:
            self.F.append(cv2.pyrDown(self.F[-1])); self.Fd.append(self.Fd[-1] / 2)
        # room: level 0 at twice the end image's density (the upscaled room where it exists), level 1 is
        # the end image's own room layer, then halvings
        r2p = os.path.join(H0, 'out', f'{a.home}-R2.png')
        R2 = cv2.imread(r2p).astype(np.float32) if a.r2 else cv2.resize(R, (self.W * 2, self.H * 2), interpolation=cv2.INTER_LANCZOS4)
        if not a.r2:
            R2 = np.clip(R2 + 0.45 * (R2 - cv2.GaussianBlur(R2, (0, 0), 1.6)), 0, 255)
        if a.hi:
            hi = cv2.imread(a.hi).astype(np.float32)
            x0, y0, x1, y1 = a.hi_box
            y0, y1 = y0 - a.crop_y, y1 - a.crop_y
            tgt = cv2.resize(hi, ((x1 - x0) * 2, (y1 - y0) * 2), interpolation=cv2.INTER_AREA)
            # keep the low frequencies of the end image's room (exact colours), the detail of the upscale
            low_hi = cv2.GaussianBlur(tgt, (0, 0), 3)
            low_r = cv2.GaussianBlur(R2[y0 * 2:y1 * 2, x0 * 2:x1 * 2], (0, 0), 3)
            tgt = tgt - low_hi + low_r
            m = np.ones(tgt.shape[:2], np.float32)
            e = 24
            m[:e, :] *= np.linspace(0, 1, e)[:, None]; m[-e:, :] *= np.linspace(1, 0, e)[:, None]
            m[:, :e] *= np.linspace(0, 1, e)[None, :]; m[:, -e:] *= np.linspace(1, 0, e)[None, :]
            for ry0, ry1 in (a.hi_skip or []):                          # rows the upscale must not bring back
                r0, r1 = (ry0 - a.crop_y - y0) * 2, (ry1 - a.crop_y - y0) * 2
                m[max(0, r0 - 6):r1 + 6, :] = 0
                m = cv2.GaussianBlur(m, (0, 0), 2)
            if a.hi_ref:
                # detail only where the room layer is still what was upscaled (behind the planter it changed)
                ref = cv2.imread(a.hi_ref).astype(np.float32)
                ref = ref[max(0, -0):, :]
                cur = R[y0:y1, x0:x1]
                ref = cv2.resize(ref, (cur.shape[1], cur.shape[0]), interpolation=cv2.INTER_AREA)
                agree = (np.abs(cv2.GaussianBlur(ref, (0, 0), 1.5) - cv2.GaussianBlur(cur, (0, 0), 1.5)).max(2) < 7).astype(np.float32)
                agree = cv2.GaussianBlur(cv2.erode(agree, np.ones((5, 5), np.uint8)), (0, 0), 2)
                m = m * cv2.resize(agree, (m.shape[1], m.shape[0]), interpolation=cv2.INTER_LINEAR)
            sl = R2[y0 * 2:y1 * 2, x0 * 2:x1 * 2]
            R2[y0 * 2:y1 * 2, x0 * 2:x1 * 2] = sl * (1 - m[..., None]) + tgt * m[..., None]
        self.R, self.Rd = [R2, R, cv2.resize(R, (OUT_W, OUT_H), interpolation=cv2.INTER_AREA)], [2.0, 1.0, k]
        while min(self.R[-1].shape[:2]) > 64:
            self.R.append(cv2.pyrDown(self.R[-1])); self.Rd.append(self.Rd[-1] / 2)
        self.c = np.array([self.W / 2.0, self.H / 2.0])
        self.f0 = self.W / 2.0 / math.tan(math.radians(a.hfov) / 2)
        self.k = OUT_W / self.W                                          # output px per end image px at t = 0
        fx, fy, fw = a.final
        fy -= a.crop_y
        self.cR = np.array([fx + fw / 2.0, fy + fw * 9 / 32.0])
        self.aR_end = fw / self.W
        self.tz_end = a.zR * (1 - self.aR_end)
        if a.cross:
            # the camera passes the front layer through the point a.cross (start view px, a clear pane);
            # a lens shift (verticals stay vertical) keeps the final view on the chosen part of the room
            Fc = np.array(a.cross, float)
            self.txy_end = (Fc - self.c) * self.tz_end / self.f0
            self.d_end = (self.cR - self.c - (self.f0 / a.zR) * self.txy_end) / self.aR_end
        else:
            self.txy_end = (self.cR - self.c) * a.zR / self.f0
            self.d_end = np.zeros(2)
        if self.tz_end >= a.zF:
            print('note: the camera passes the front layer at', round(a.zF, 2))

    def pose(self, tau):
        u = smoother(tau)
        aR = math.exp(u * math.log(self.aR_end))                         # room scale eases in and out
        tz = self.a.zR * (1 - aR)
        g = tz / self.tz_end
        return tz, self.txy_end * g, self.d_end * smoother(tau)

    def _layer(self, levels, dens, z, tz, txy, border, d=np.zeros(2)):
        """the layer at depth z seen from the camera at (txy, tz): an affine of the start view, sampled
        from the pyramid level(s) whose density brackets the one needed (levels: density = level px per
        end image px, decreasing)"""
        a = (z - tz) / z
        b = self.c * (1 - a) + (self.f0 / z) * txy + d * a
        s = a / self.k                                                   # end image px per output px
        need = 1.0 / s                                                   # level px per end image px wanted

        def at(L):
            sc = dens[L]
            M = np.array([[s * sc, 0, (b[0] + 0.5 * s) * sc - 0.5], [0, s * sc, (b[1] + 0.5 * s) * sc - 0.5]], np.float64)
            return cv2.warpAffine(levels[L], M, (OUT_W, OUT_H), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=border)
        if need >= dens[0]:
            return at(0)
        for L in range(len(dens) - 1):
            if dens[L] >= need >= dens[L + 1]:
                fr = math.log(dens[L] / need) / math.log(dens[L] / dens[L + 1])
                if fr < 1e-3:
                    return at(L)
                if fr > 1 - 1e-3:
                    return at(L + 1)
                return at(L) * (1 - fr) + at(L + 1) * fr
        return at(len(dens) - 1)

    def render(self, tau):
        tz, txy, d = self.pose(tau)
        out = self._layer(self.R, self.Rd, self.a.zR, tz, txy, cv2.BORDER_REPLICATE, d)
        if tz < self.a.zF - 0.05:
            Fl = self._layer(self.F, self.Fd, self.a.zF, tz, txy, cv2.BORDER_CONSTANT, d)
            out = out * (1 - Fl[..., 3:4] / 255.0) + Fl[..., :3]
        return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('home')
    ap.add_argument('--zF', type=float, required=True)
    ap.add_argument('--zR', type=float, required=True)
    ap.add_argument('--final', type=float, nargs=3, required=True, help='x y width of the final view on the end image')
    ap.add_argument('--hfov', type=float, default=55.0)
    ap.add_argument('--hi'); ap.add_argument('--hi-box', type=int, nargs=4)
    ap.add_argument('--hi-skip', type=int, nargs=2, action='append')
    ap.add_argument('--crop-y', type=int, default=0, help='rows cropped top and bottom (the flight crops the end image to 16:9)')
    ap.add_argument('--hi-ref', help='the base resolution crop that was upscaled (detail only where the room still matches it)')
    ap.add_argument('--r2', action='store_true', help='use out/<home>-R2.png (twice the density) as the room level 0')
    ap.add_argument('--cross', type=float, nargs=2, help='where the camera passes the front layer (start view px)')
    ap.add_argument('--f2', type=float, default=0.0, help='unsharp amount of a 2x density level of the front layer (0 = no such level)')
    ap.add_argument('--seconds', type=float, default=3.6)
    ap.add_argument('--fps', type=int, default=60)
    ap.add_argument('--blur', type=int, default=7)
    ap.add_argument('--shutter', type=float, default=0.5)
    ap.add_argument('--sheet', action='store_true')
    a = ap.parse_args()
    sc = Scene(a)
    n = int(round(a.seconds * a.fps)) + 1
    os.makedirs(os.path.join(H0, 'out'), exist_ok=True)
    if a.sheet:
        S = os.environ['PREV']
        idx = list(np.linspace(0, n - 1, 12).astype(int))
        tiles = [cv2.resize(np.clip(sc.render(i / (n - 1)), 0, 255).astype(np.uint8), (480, 270), interpolation=cv2.INTER_AREA) for i in idx]
        tiles = [cv2.putText(t, str(i), (6, 22), 0, 0.7, (0, 255, 255), 2) for t, i in zip(tiles, idx)]
        cv2.imwrite(os.path.join(S, f'{a.home}-inside-sheet.jpg'), np.vstack([np.hstack(tiles[r * 4:(r + 1) * 4]) for r in range(3)]))
        cv2.imwrite(os.path.join(S, f'{a.home}-inside-last.jpg'), np.clip(sc.render(1.0), 0, 255).astype(np.uint8))
        return
    path = os.path.join(H0, 'out', f'{a.home}-inside-master.mkv')
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{OUT_W}x{OUT_H}', '-r', str(a.fps), '-i', '-',
                           '-c:v', 'ffv1', '-level', '3', '-pix_fmt', 'yuv444p', path], stdin=subprocess.PIPE)
    dt = 1.0 / (n - 1)
    last = None
    for i in range(n):
        tau = i * dt
        if i in (0, n - 1) or a.blur <= 1:
            ts = [tau]
        else:
            ts = [min(1, max(0, tau + a.shutter * dt * ((k + 0.5) / a.blur - 0.5))) for k in range(a.blur)]
        acc = sum(sc.render(t) for t in ts) / len(ts)
        last = np.clip(acc + 0.5, 0, 255).astype(np.uint8)
        ff.stdin.write(last.tobytes())
    ff.stdin.close(); ff.wait()
    cv2.imwrite(os.path.join(H0, 'out', f'{a.home}-inside-last.png'), last)
    json.dump({'frames': n, 'fps': a.fps}, open(os.path.join(H0, 'out', f'{a.home}-inside.json'), 'w'))
    print('inside', path, n, 'frames')


if __name__ == '__main__':
    main()
