"""
Rebuild the Bungalow 3 flight master with ONE smooth speed curve from the tower view to the window.

The old master (assemble.py flight) eased part A down to 0.45 x at the seam and retimed part B by its
measured zoom only; part B's own motion is mostly an orbit that starts slowly, so the camera went
slow, fast, slow, fast, stop. Here the whole path is measured as one: per step image motion (dense
DIS flow, forward/backward consistent, on textured pixels, in px of the 1920 frame) over part A's
60 fps frames and part B's native AI frames, summed into a cumulative "progress" along the path.
The output frames are then placed on that path so that progress follows a single ease in / ease out
bell (speed ~ x^a (1-x)^b, one peak, no plateau).

  part A (s <= 90):  re-rendered exactly at the fractional camera time (render_part_a / previz camera),
                     motion blur over half the new frame step; frame 0 is part A's own frame 0.
  part B (s >  90):  the AI frames at fractional native index, bidirectional flow interpolation
                     (assemble.interp). The low frequency grade step at the hand-off is carried and
                     faded as before; the last frames settle exactly on the keyframe as before.

usage (from _work):  python ai/retime_b3.py [--frames 284] [--a 1.5] [--b 1.8] [--dry]
writes ai/out/bung3-flight-master.mkv, ai/out/bung3-flight-timing.json, ai/out/bung3-flight-track.json
"""
import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.special import betainc

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(WORK, 'flight'))
import assemble as AS  # noqa: E402

PART_A = os.path.join(WORK, 'flight', 'out', 'hybrid', 'bung3-partA.mkv')
PART_A_TRACK = os.path.join(WORK, 'flight', 'out', 'hybrid', 'bung3-partA-track.json')
PART_B = os.path.join(HERE, 'gen', 'bung3-partB-kling3.mp4')
KEY = os.path.join(HERE, 'gen', 'bung3-end-gpt3.png')
OUT = os.path.join(HERE, 'out')
SEAM_T = 0.30                     # part A covers previz time [0, 0.30]
END_BOX = [0.0, 0.32, 0.67, 0.72]  # the window box on the keyframe (as in the published track)
W, H, FPS = AS.W, AS.H, AS.FPS
WORKERS = 4                       # each previz worker holds the layer pyramids (~1.5 GB)

# ---------------------------------------------------------------- motion measure
SW, SH = 480, 270
_dis = None


def small(f):
    return cv2.cvtColor(cv2.resize(f, (SW, SH), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)


def step_motion(a, b):
    """mean image motion a -> b in px of the 1920 frame, over textured pixels whose forward and
    backward flows agree (flat sky makes the flow wander)"""
    global _dis
    if _dis is None:
        _dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    yy, xx = np.mgrid[0:SH, 0:SW].astype(np.float32)
    f = _dis.calc(a, b, None)
    bk = _dis.calc(b, a, None)
    bw = cv2.remap(bk, xx + f[..., 0], yy + f[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(1e3, 1e3))
    err = np.hypot(f[..., 0] + bw[..., 0], f[..., 1] + bw[..., 1])
    gx, gy = cv2.Sobel(a, cv2.CV_32F, 1, 0), cv2.Sobel(a, cv2.CV_32F, 0, 1)
    g = cv2.GaussianBlur(np.hypot(gx, gy), (0, 0), 2)
    m = np.hypot(f[..., 0], f[..., 1])
    ok = (err < 0.5 + 0.05 * m) & (g > 12)
    if ok.mean() < 0.05:
        ok = g > 12
    return float(m[ok].mean()) * W / SW


def motion_curve(smalls):
    return np.array([step_motion(smalls[i], smalls[i + 1]) for i in range(len(smalls) - 1)])


def video_smalls(path):
    c = cv2.VideoCapture(path)
    out = []
    while True:
        ok, f = c.read()
        if not ok:
            break
        out.append(small(f))
    return out


# ---------------------------------------------------------------- part A renders
def render_a(jobs, tmp):
    """render part A frames [(k, [previz times])] in parallel; returned through the same ffv1 yuv444p
    round trip as part A itself so their grade matches part A's frame 0 exactly"""
    import render_part_a as RPA
    path = os.path.join(tmp, 'a.mkv')
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                           '-c:v', 'ffv1', '-level', '3', '-pix_fmt', 'yuv444p', path], stdin=subprocess.PIPE)
    pending, nxt = {}, 0
    with ProcessPoolExecutor(WORKERS) as ex:
        for i, fr in ex.map(RPA.render_frame, [(k, ts, 'bung3') for k, ts in enumerate(jobs)], chunksize=1):
            pending[i] = fr
            while nxt in pending:
                ff.stdin.write(pending.pop(nxt).tobytes())
                nxt += 1
    ff.stdin.close()
    ff.wait()
    return AS.read_frames(path)


# ---------------------------------------------------------------- the window box
def box_track(src, LB):
    trk = np.array(json.load(open(PART_A_TRACK))['frames'])          # (91, 4, 2)
    bb = np.stack([trk[:, :, 0].min(1), trk[:, :, 1].min(1), trk[:, :, 0].max(1), trk[:, :, 1].max(1)], 1)
    s0, e = bb[-1], np.array(END_BOX)
    ws, we, hs, he = s0[2] - s0[0], e[2] - e[0], s0[3] - s0[1], e[3] - e[1]
    nA = len(bb) - 1
    out = []
    for s in src:
        if s <= nA:
            b = [float(np.interp(s, np.arange(len(bb)), bb[:, c])) for c in range(4)]
        else:     # part B: the box follows the AI clip's measured zoom (as in the published track)
            k = float(np.interp(s - nA, np.arange(len(LB)), LB)) / LB[-1]
            w = math.exp(math.log(ws) + (math.log(we) - math.log(ws)) * k)
            h = math.exp(math.log(hs) + (math.log(he) - math.log(hs)) * k)
            g, gh = (w - we) / (ws - we), (h - he) / (hs - he)
            cx = (e[0] + e[2]) / 2 + ((s0[0] + s0[2]) / 2 - (e[0] + e[2]) / 2) * g
            cy = (e[1] + e[3]) / 2 + ((s0[1] + s0[3]) / 2 - (e[1] + e[3]) / 2) * gh
            b = [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]
        out.append([round(x, 5) + 0.0 for x in b])
    out[-1] = [round(x, 5) + 0.0 for x in END_BOX]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--frames', type=int, default=271, help='output frames (60 fps); 271 puts the last frame on an encoder keyframe (GOP 30)')
    ap.add_argument('--a', type=float, default=1.5, help='ease in exponent (speed ~ x^a (1-x)^b)')
    ap.add_argument('--b', type=float, default=1.8, help='ease out exponent')
    ap.add_argument('--smooth-a', type=float, default=3.0, help='gaussian sigma (source steps) on the part A measured motion')
    ap.add_argument('--smooth-b', type=float, default=2.0, help='gaussian sigma (native steps) on the part B measured motion')
    ap.add_argument('--blur', type=int, default=7, help='part A motion blur samples per source frame step')
    ap.add_argument('--shutter', type=float, default=0.5)
    ap.add_argument('--settle', type=float, default=0.4)
    ap.add_argument('--xfade', type=float, default=0.3)
    ap.add_argument('--dry', action='store_true', help='timing only')
    ap.add_argument('--metric', default='flow', choices=['flow', 'global'])
    a = ap.parse_args()

    # 1. measure the path
    sA = video_smalls(PART_A)
    sB = video_smalls(PART_B)
    nA, nB = len(sA) - 1, len(sB) - 1
    vA, vB = motion_curve(sA), motion_curve(sB)
    if a.metric == 'global':
        # the global camera motion of each step (similarity fit: zoom moves the corners, plus the shift),
        # unsmoothed: the AI clip's own frames do not advance evenly, so equal progress per output frame
        # must follow its real steps (a smoothed measure lets that unevenness through as a stutter)
        def gmag(g):
            return np.sqrt((g[:, 0] * 1101.0) ** 2 + g[:, 1] ** 2 + g[:, 2] ** 2)
        vA, vB = gmag(np.load(os.path.join(OUT, 'b3-global-A.npy'))), gmag(np.load(os.path.join(OUT, 'b3-global-B.npy')))
    v = np.r_[vA, vB]
    # smoothed within each part (never across the hand-off: part A ends fast, part B starts slow)
    sm = lambda x, s: gaussian_filter1d(x, s, mode='nearest') if s > 0 else x
    vs = np.r_[sm(vA, a.smooth_a), sm(vB, a.smooth_b)]
    P = np.r_[0.0, np.cumsum(vs)]                       # progress at source position s = 0 .. nA + nB
    print('measured motion: part A %.0f px over %d frames, part B %.0f px over %d native frames' % (vA.sum(), nA, vB.sum(), nB))

    # 2. one bell: target progress at each output frame
    N = a.frames - 1
    x = np.arange(N + 1) / N
    Pt = P[-1] * betainc(a.a + 1, a.b + 1, x)
    src = np.interp(Pt, P, np.arange(len(P)))
    src[0], src[-1] = 0.0, float(nA + nB)
    sp = np.diff(Pt)
    print('output %d frames (%.2f s); planned speed peak %.1f px/frame at %.2f s; seam at output frame %d' % (
        N + 1, (N + 1) / FPS, sp.max(), (sp.argmax() + 0.5) / FPS, int(np.searchsorted(src, nA))))

    B = AS.read_frames(PART_B)
    LB = AS.zoom_profile_stride(B)                       # part B's measured zoom, for the window box
    track = box_track(src, LB)
    del B
    timing = {'frames': N + 1, 'partA_frames': nA + 1, 'partB_native_frames': nB + 1, 'a': a.a, 'b': a.b,
              'src': src.tolist(), 'progress': P.tolist(), 'target': Pt.tolist(), 'motion': v.tolist(), 'LB': LB.tolist(),
              'note': 'src <= %d: part A frame index (previz t = src * %.6f); src > %d: part B native index src - %d' % (nA, SEAM_T / nA, nA, nA)}
    if a.dry:
        json.dump(timing, open(os.path.join(OUT, 'bung3-flight-timing-dry.json'), 'w'))
        return

    # 3. part A frames, rendered at their exact camera times
    dtA = SEAM_T / nA
    jA = [j for j in range(N + 1) if src[j] <= nA]
    jobs = []
    for j in jA:
        t = src[j] * dtA
        if j == 0:
            jobs.append([0.0])
            continue
        stepA = (src[min(N, j + 1)] - src[j - 1]) / 2           # source frames per output frame here
        nb = int(max(3, min(21, round(a.blur * max(stepA, 0.2)))))
        span = a.shutter * stepA * dtA
        jobs.append([max(0.0, min(SEAM_T, t + span * ((k + 0.5) / nb - 0.5))) for k in range(nb)])
    cache, cjobs = os.path.join(OUT, 'bung3-partA-retimed.mkv'), os.path.join(OUT, 'bung3-partA-retimed.json')
    if os.path.exists(cache) and os.path.exists(cjobs) and json.load(open(cjobs)) == jobs:
        print('part A frames from the render cache', cache)
        RA = AS.read_frames(cache)
    else:
        with tempfile.TemporaryDirectory(dir=OUT) as tmp:
            print('rendering %d part A frames' % len(jobs), flush=True)
            RA = render_a(jobs, tmp)
            os.replace(os.path.join(tmp, 'a.mkv'), cache)
        json.dump(jobs, open(cjobs, 'w'))
    B = AS.read_frames(PART_B)
    A0 = AS.read_frames(PART_A)
    a0, aEnd = A0[0], A0[-1]
    del A0
    print('render check: frame 0 vs part A frame 0 MAD %.3f' % float(np.abs(RA[0].astype(np.float32) - a0.astype(np.float32)).mean()))
    RA[0] = a0                                               # exactly the site's start frame

    # 4. write the master
    key = AS.load_image(KEY)
    dlp = cv2.GaussianBlur(aEnd.astype(np.float32) - B[0].astype(np.float32), (0, 0), 25)
    Mend = AS.similarity(B[-1], key)
    print('part B end vs keyframe: scale %.4f shift (%.1f, %.1f)' % (math.hypot(Mend[0, 0], Mend[1, 0]), Mend[0, 2], Mend[1, 2]))
    settle, xfade = int(round(a.settle * FPS)), int(round(a.xfade * FPS))
    out = os.path.join(OUT, 'bung3-flight-master.mkv')
    ff = AS.writer(out)
    jB0 = None
    for j in range(N + 1):
        if src[j] <= nA:
            img = RA[jA.index(j)]
        else:
            if jB0 is None:
                jB0 = j
            img = AS.interp(B, float(src[j] - nA))
            q = j - jB0 + 1                                     # output frames since the hand-off
            if q < xfade:
                w = 1 - AS.smooth(q / xfade)
                img = np.clip(img.astype(np.float32) + dlp * w, 0, 255).astype(np.uint8)
        if j >= N + 1 - settle:
            w = AS.smooth((j - (N + 1 - settle)) / max(1, settle - 1))
            img = AS.settle_on(img, key, Mend, w)
        ff.stdin.write(img.tobytes())
    ff.stdin.close()
    ff.wait()
    json.dump(timing, open(os.path.join(OUT, 'bung3-flight-timing.json'), 'w'))
    json.dump({'fps': FPS, 'frames': track}, open(os.path.join(OUT, 'bung3-flight-track.json'), 'w'))
    print('flight master', out, N + 1, 'frames', '%.2f s' % ((N + 1) / FPS))


if __name__ == '__main__':
    main()
