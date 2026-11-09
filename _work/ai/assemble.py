"""
Assemble the hybrid clips into lossless 60 fps masters.

flight:  part A (exact camera move over the official image, 60 fps, from render_part_a.py) followed by
         part B (the AI final approach, 24 fps, from the hand-off frame to the window keyframe).
         Part B is retimed by its measured zoom so that its speed continues part A's at the seam and
         eases out at the window; frames between the AI frames come from optical flow. The last
         frames settle exactly on the keyframe image.
inside:  the AI Step inside clip retimed to a set duration; it starts exactly on the keyframe and
         settles exactly on the room photo.

usage:
  python assemble.py flight <home> --partA a.mkv --partB b.mp4 --key key.png --cams cams.json --seam 0.45 --tb 2.5
  python assemble.py inside <home> --clip c.mp4 --key key.png --photo photo.jpg --dur 3.0
"""
import argparse
import json
import math
import os
import subprocess

import cv2
import numpy as np

W, H, FPS = 1920, 1080, 60
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')


def read_frames(path):
    c = cv2.VideoCapture(path)
    fr = []
    while True:
        ok, f = c.read()
        if not ok:
            break
        if f.shape[1] != W or f.shape[0] != H:
            f = cv2.resize(f, (W, H), interpolation=cv2.INTER_CUBIC if f.shape[1] < W else cv2.INTER_AREA)
        fr.append(f)
    return fr


def load_image(path):
    img = cv2.imread(path)
    h, w = img.shape[:2]
    # crop to 16:9 around the centre, then resize
    if w / h > W / H + 1e-3:
        nw = int(round(h * W / H)); x0 = (w - nw) // 2; img = img[:, x0:x0 + nw]
    elif w / h < W / H - 1e-3:
        nh = int(round(w * H / W)); y0 = (h - nh) // 2; img = img[y0:y0 + nh]
    return cv2.resize(img, (W, H), interpolation=cv2.INTER_AREA if img.shape[1] > W else cv2.INTER_CUBIC)


_dis = None


def flow(a, b):
    global _dis
    if _dis is None:
        _dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    ga, gb = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY), cv2.cvtColor(b, cv2.COLOR_BGR2GRAY)
    return _dis.calc(ga, gb, None)


_fcache = {}


def interp(frames, tau):
    """frame at fractional index tau by bidirectional flow warping"""
    i0 = int(math.floor(tau))
    i0 = max(0, min(len(frames) - 1, i0))
    f = tau - i0
    if f < 1e-3 or i0 + 1 >= len(frames):
        return frames[i0].copy()
    if f > 1 - 1e-3:
        return frames[i0 + 1].copy()
    a, b = frames[i0], frames[i0 + 1]
    if i0 not in _fcache:
        _fcache.clear()
        _fcache[i0] = (flow(a, b), flow(b, a))
    fab, fba = _fcache[i0]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    # backward warp: the pixel at time f came from a at x - f * fab and from b at x + (1 - f) * fba
    wa = cv2.remap(a, xx - f * fab[..., 0], yy - f * fab[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    wb = cv2.remap(b, xx - (1 - f) * fba[..., 0], yy - (1 - f) * fba[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return cv2.addWeighted(wa, 1 - f, wb, f, 0)


def zoom_profile(frames):
    """cumulative log scale of a push in, from ORB matches between consecutive frames"""
    orb = cv2.ORB_create(3000)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    L = [0.0]
    prev = None
    for f in frames:
        g = cv2.cvtColor(cv2.resize(f, (960, 540)), cv2.COLOR_BGR2GRAY)
        kp, des = orb.detectAndCompute(g, None)
        if prev is not None:
            kp0, des0 = prev
            s = 1.0
            if des is not None and des0 is not None and len(kp) > 20 and len(kp0) > 20:
                m = bf.match(des0, des)
                if len(m) > 20:
                    p0 = np.float32([kp0[x.queryIdx].pt for x in m]); p1 = np.float32([kp[x.trainIdx].pt for x in m])
                    M, inl = cv2.estimateAffinePartial2D(p0, p1, method=cv2.RANSAC, ransacReprojThreshold=2.0)
                    if M is not None:
                        s = math.hypot(M[0, 0], M[1, 0])
            L.append(L[-1] + math.log(max(1e-3, s)))
        prev = (kp, des)
    L = np.array(L)
    return np.maximum.accumulate(L)          # a push in never zooms out; flatten noise


def similarity(a, b):
    """similarity transform (2x3) taking image a onto image b, from ORB matches"""
    orb = cv2.ORB_create(4000)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    ka, da = orb.detectAndCompute(cv2.cvtColor(a, cv2.COLOR_BGR2GRAY), None)
    kb, db = orb.detectAndCompute(cv2.cvtColor(b, cv2.COLOR_BGR2GRAY), None)
    m = bf.match(da, db)
    pa = np.float32([ka[x.queryIdx].pt for x in m]); pb = np.float32([kb[x.trainIdx].pt for x in m])
    M, _ = cv2.estimateAffinePartial2D(pa, pb, method=cv2.RANSAC, ransacReprojThreshold=2.0)
    return M


def partial(M, w):
    """the similarity M applied a fraction w of the way (scale, rotation and shift interpolated)"""
    s = math.hypot(M[0, 0], M[1, 0]); r = math.atan2(M[1, 0], M[0, 0])
    s_w, r_w = s ** w, r * w
    c, sn = s_w * math.cos(r_w), s_w * math.sin(r_w)
    # keep the frame centre's motion proportional
    cx, cy = W / 2, H / 2
    tx = (M[0, 0] * cx + M[0, 1] * cy + M[0, 2]) - cx
    ty = (M[1, 0] * cx + M[1, 1] * cy + M[1, 2]) - cy
    return np.array([[c, -sn, cx + tx * w - (c * cx - sn * cy)], [sn, c, cy + ty * w - (sn * cx + c * cy)]])


def settle_on(img, exact, M, w):
    """slide img into alignment with the exact end image and dissolve into it (w: 0 -> 1)"""
    if M is not None:
        img = cv2.warpAffine(img, partial(M, w), (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return cv2.addWeighted(img, 1 - w, exact, w, 0)


def zoom_profile_stride(frames, stride=4):
    """cumulative log zoom measured over stride frame steps (far less drift than frame to frame)"""
    ks = list(range(0, len(frames), stride))
    if ks[-1] != len(frames) - 1:
        ks.append(len(frames) - 1)
    L = [0.0]
    for a_, b_ in zip(ks[:-1], ks[1:]):
        M = similarity(cv2.resize(frames[a_], (960, 540)), cv2.resize(frames[b_], (960, 540)))
        L.append(L[-1] + (math.log(math.hypot(M[0, 0], M[1, 0])) if M is not None else 0.0))
    L = np.maximum.accumulate(np.array(L))
    return np.interp(np.arange(len(frames)), ks, L)


def hermite(t, p0, p1, m0, m1):
    t2, t3 = t * t, t * t * t
    return (2 * t3 - 3 * t2 + 1) * p0 + (t3 - 2 * t2 + t) * m0 + (-2 * t3 + 3 * t2) * p1 + (t3 - t2) * m1


def writer(path):
    return subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                             '-vf', 'scale=out_color_matrix=bt709:out_range=tv:flags=accurate_rnd+full_chroma_int,format=yuv420p',
                             '-c:v', 'ffv1', '-level', '3', '-slices', '16',
                             '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-color_range', 'tv', path],
                            stdin=subprocess.PIPE)


def smooth(x):
    x = min(1.0, max(0.0, x))
    return x * x * x * (x * (6 * x - 15) + 10)


def flight(a):
    A = read_frames(a.partA)
    B = read_frames(a.partB)
    key = load_image(a.key)
    print('part A', len(A), 'frames; part B', len(B), 'frames')
    print('seam: part A last vs part B first MAD %.2f' % float(np.abs(A[-1].astype(np.float32) - B[0].astype(np.float32)).mean()))
    LB = zoom_profile_stride(B)
    print('part B zoom x%.2f' % math.exp(LB[-1]))
    # part A's zoom rate at the seam (log scale per second), from the previz window widths
    cams = json.load(open(a.cams))
    fr = cams['frames']; pf = cams['fps']
    wv = np.array([max(p[0] for p in f['window']) - min(p[0] for p in f['window']) for f in fr])
    k = a.seam * (len(fr) - 1)
    i0 = int(math.floor(k)); i0 = max(1, min(len(fr) - 2, i0))
    rate = (math.log(wv[i0 + 1]) - math.log(wv[i0 - 1])) / 2 * pf
    if a.measure:                                   # measure part A's image zoom the same way as part B's
        LA = zoom_profile_stride(A[-17:], 4)
        rate = float(np.polyfit(np.arange(len(LA)), LA, 1)[0]) * FPS
        print('part A measured zoom rate at the seam %.2f log/s' % rate)
    rate *= a.aslow                                  # part A is eased down to this speed at the seam
    T = a.tb
    m0 = rate * T
    if m0 > 2.9 * LB[-1]:
        print('warning: part A is faster than part B can ease out; clamping'); m0 = 2.9 * LB[-1]
    n = int(round(T * FPS))
    out = os.path.join(OUT, f'{a.home}-flight-master.mkv')
    ff = writer(out)
    if a.aslow < 1.0:                               # ease part A's speed down into the seam
        K = int(round(0.5 * FPS)); n0 = len(A) - 1 - K
        ts = list(np.arange(0, n0))
        t, k = float(n0), 0
        while t < len(A) - 1 - 1e-6:
            ts.append(t)
            k += 1
            v = 1 - (1 - a.aslow) * smooth(min(1.0, k / K))
            t += v
        for t in ts:
            ff.stdin.write(interp(A, t).tobytes())
        print('part A eased: %d frames -> %d' % (len(A) - 1, len(ts)))
    else:
        for f in A[:-1]:
            ff.stdin.write(f.tobytes())
    settle = int(round(a.settle * FPS))
    xfade = int(round(a.xfade * FPS))
    # the AI clip's first frame differs a little from the exact seam frame (grade, sharpness): carry the
    # low frequency difference into part B and fade it out, so the hand-off has no visible step
    dlp = cv2.GaussianBlur(A[-1].astype(np.float32) - B[0].astype(np.float32), (0, 0), 25)
    Mend = similarity(B[-1], key)
    print('part B end vs keyframe: scale %.4f shift (%.1f, %.1f)' % (math.hypot(Mend[0, 0], Mend[1, 0]), Mend[0, 2], Mend[1, 2]))
    taus = []
    for j in range(n + 1):
        t = j / n
        L = hermite(t, 0.0, LB[-1], m0, 0.0)
        tau = float(np.interp(L, LB, np.arange(len(LB))))
        taus.append(tau)
        if j == 0:
            img = A[-1].copy()                          # the exact seam frame (shared with part A)
        else:
            img = interp(B, tau)
            if j < xfade:
                w = 1 - smooth(j / xfade)
                img = np.clip(img.astype(np.float32) + dlp * w, 0, 255).astype(np.uint8)
        if j >= n + 1 - settle:                         # settle exactly on the keyframe
            w = smooth((j - (n + 1 - settle)) / max(1, settle - 1))
            img = settle_on(img, key, Mend, w)
        ff.stdin.write(img.tobytes())
    ff.stdin.close(); ff.wait()
    json.dump({'partA_frames': len(A), 'partB_out_frames': n + 1, 'taus': taus, 'LB': LB.tolist(), 'rate': rate},
              open(os.path.join(OUT, f'{a.home}-flight-timing.json'), 'w'))
    print('flight master', out, len(A) - 1 + n + 1, 'frames', '%.2f s' % ((len(A) - 1 + n + 1) / FPS))


def inside(a):
    C = read_frames(a.clip)
    key = load_image(a.key)
    photo = load_image(a.photo)
    print('clip', len(C), 'frames; first vs key MAD %.2f, last vs photo MAD %.2f' % (
        float(np.abs(C[0].astype(np.float32) - key.astype(np.float32)).mean()),
        float(np.abs(C[-1].astype(np.float32) - photo.astype(np.float32)).mean())))
    n = int(round(a.dur * FPS))
    out = os.path.join(OUT, f'{a.home}-inside-master.mkv')
    ff = writer(out)
    xin = int(round(0.15 * FPS)); xout = int(round(a.settle * FPS))
    Min = similarity(C[0], key)                       # where the clip's first frame sits on the keyframe
    Mout = similarity(C[-1], photo)
    for M, nm in ((Min, 'start vs key'), (Mout, 'end vs photo')):
        print(nm, 'scale %.4f shift (%.1f, %.1f)' % (math.hypot(M[0, 0], M[1, 0]), M[0, 2], M[1, 2]))
    for j in range(n + 1):
        tau = j / n * (len(C) - 1)
        img = interp(C, tau)
        if j < xin:                                   # leave the exact keyframe: the reverse of a settle
            w = 1 - smooth(j / xin)
            img = settle_on(img, key, Min, w)
        if j >= n + 1 - xout:
            w = smooth((j - (n + 1 - xout)) / max(1, xout - 1))
            img = settle_on(img, photo, Mout, w)
        ff.stdin.write(img.tobytes())
    ff.stdin.close(); ff.wait()
    print('inside master', out, n + 1, 'frames')


def inside2(a):
    """Step inside without any dissolve: the AI clip from the exact keyframe to the room threshold
    (the extended photo), then a pure camera push over the extended photo that lands on the exact
    photograph. Nothing in the room can move: the last part is the photograph itself."""
    C = read_frames(a.clip)
    key = load_image(a.key)
    photo = cv2.imread(a.photo)                                   # 1920 x 1080, untouched
    wide = cv2.imread(a.wide)                                     # extended photo, photo at its centre
    Hw, Ww = wide.shape[:2]
    ox, oy = (Ww - W) // 2, (Hw - H) // 2
    # the original pixels, exactly, inside the extension (feathered only outside the photo)
    m = np.zeros((Hw, Ww), np.uint8); m[oy:oy + H, ox:ox + W] = 1
    d = cv2.distanceTransform(m, cv2.DIST_L2, 5)               # distance inside the photo to its edge
    m3 = np.clip(d / 24.0, 0, 1)[..., None]                    # exact photo in the core, eased into the extension at its edge
    big = wide.copy(); big[oy:oy + H, ox:ox + W] = photo
    wide = (big.astype(np.float32) * m3 + wide.astype(np.float32) * (1 - m3)).astype(np.uint8)
    Z = Ww / W                                                    # the push over the extension

    def push(z):                                                  # z: 1 (whole extension) -> Z (the photo)
        cw, ch = Ww / z, Hw / z
        x0, y0 = Ww / 2 - cw / 2, Hw / 2 - ch / 2
        M = np.array([[cw / W, 0, x0 + 0.5 * cw / W - 0.5], [0, ch / H, y0 + 0.5 * ch / H - 0.5]])
        if abs(z - Z) < 1e-6:
            return photo.copy()
        return cv2.warpAffine(wide, M, (W, H), flags=cv2.INTER_AREA | cv2.WARP_INVERSE_MAP if z < 1.5 else cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP,
                              borderMode=cv2.BORDER_REPLICATE)

    wide0 = cv2.resize(wide, (W, H), interpolation=cv2.INTER_AREA)
    LC = zoom_profile_stride(C, 3)
    Min = similarity(C[0], key)
    Mout = similarity(C[-1], wide0)
    print('clip', len(C), 'frames; zoom x%.2f; start vs key scale %.4f shift (%.1f, %.1f); end vs threshold scale %.4f shift (%.1f, %.1f)' % (
        math.exp(LC[-1]), math.hypot(Min[0, 0], Min[1, 0]), Min[0, 2], Min[1, 2], math.hypot(Mout[0, 0], Mout[1, 0]), Mout[0, 2], Mout[1, 2]))
    d_in = cv2.GaussianBlur(key.astype(np.float32) - C[0].astype(np.float32), (0, 0), 25)
    endC = cv2.warpAffine(C[-1], Mout, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    d_out = wide0.astype(np.float32) - endC.astype(np.float32)   # what remains after alignment
    # timing: the AI clip keeps its own (smooth) motion, played s times faster; the push over the
    # photograph starts at the clip's final speed and eases out once, on the photograph
    s = a.speed
    last = len(C) - 1 - a.tailcut                          # Kling brakes over its very last frames: stop before
    Mend = similarity(C[last], wide0)
    seg = LC[last - 16:last + 1]
    r0 = max(0.05, float(np.polyfit(np.arange(len(seg)), seg, 1)[0]) * 24 * s)   # log zoom per second at the join
    nc = int(round(last / 24 / s * FPS))
    lz = math.log(Z)
    Tp = min(2.0, max(0.7, 2.2 * lz / r0))
    npush = int(round(Tp * FPS))
    print('clip part %.2f s (to native frame %d), push %.2f s, join speed %.2f log/s; last frame vs threshold scale %.4f shift (%.1f, %.1f)' % (
        nc / FPS, last, Tp, r0, math.hypot(Mend[0, 0], Mend[1, 0]), Mend[0, 2], Mend[1, 2]))
    out = os.path.join(OUT, f'{a.home}-inside-master.mkv')
    ff = writer(out)
    xin = int(round(0.3 * FPS)); xal = int(round(0.2 * FPS))
    for j in range(nc + 1):
        tau = j / nc * last
        if j == 0:
            img = key.copy()
        elif j == nc:
            img = wide0.copy()
        else:
            img = interp(C, tau)
            if j < xin:                                   # leave the exact keyframe (geometry and grade only)
                w = 1 - smooth(j / xin)
                img = cv2.warpAffine(img, partial(Min, w), (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
                img = np.clip(img.astype(np.float32) + d_in * w, 0, 255).astype(np.uint8)
            if j > nc - xal:                              # slide into exact registration with the threshold image
                w = (j - (nc - xal)) / xal
                img = cv2.warpAffine(img, partial(Mend, w), (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
                if j > nc - 6:                            # aligned: the threshold image's own detail takes over,
                    q = (j - (nc - 6)) / 6                # shown at the same scheduled zoom so nothing stalls
                    sc = math.exp(-r0 * (nc - j) / FPS)
                    Sm = np.array([[sc, 0, W / 2 * (1 - sc)], [0, sc, H / 2 * (1 - sc)]])
                    tgt = cv2.warpAffine(wide0, Sm, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT)
                    msk = cv2.warpAffine(np.ones((H, W), np.float32), Sm, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
                    msk = cv2.GaussianBlur(cv2.erode(msk, np.ones((9, 9), np.uint8)), (0, 0), 4)[..., None] * q
                    img = (img.astype(np.float32) * (1 - msk) + tgt.astype(np.float32) * msk).astype(np.uint8)
        ff.stdin.write(img.tobytes())
    for k in range(1, npush + 1):
        t = k / npush
        L = hermite(t, 0.0, lz, r0 * Tp, 0.0)
        img = push(math.exp(L)) if k < npush else photo.copy()
        ff.stdin.write(img.tobytes())
    n = nc + npush
    ff.stdin.close(); ff.wait()
    print('inside master', out, n + 1, 'frames, ends exactly on the photograph')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('kind', choices=['flight', 'inside', 'inside2'])
    ap.add_argument('home')
    ap.add_argument('--partA'); ap.add_argument('--partB'); ap.add_argument('--key'); ap.add_argument('--cams')
    ap.add_argument('--seam', type=float, default=0.45)
    ap.add_argument('--tb', type=float, default=2.5, help='part B duration (s)')
    ap.add_argument('--measure', action='store_true', help='flight: seam speed from part A frames')
    ap.add_argument('--aslow', type=float, default=1.0, help='flight: part A speed factor reached at the seam')
    ap.add_argument('--settle', type=float, default=0.2, help='seconds over which the clip settles on its exact end image')
    ap.add_argument('--xfade', type=float, default=0.15)
    ap.add_argument('--clip'); ap.add_argument('--photo'); ap.add_argument('--wide')
    ap.add_argument('--dur', type=float, default=3.0)
    ap.add_argument('--speed', type=float, default=2.0, help='inside2: playback speed of the AI clip')
    ap.add_argument('--tailcut', type=int, default=2, help='inside2: braking native frames dropped at the clip end')
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    {'flight': flight, 'inside': inside, 'inside2': inside2}[a.kind](a)


if __name__ == '__main__':
    main()
