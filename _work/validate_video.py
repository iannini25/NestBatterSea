"""
Fidelity check for a fly-in video ("the camera only moves").

A faithful push-in shows, in every frame, a zoomed window of the same official image.
For each sampled frame we track the framing (cx, cy, w) in ORIG coordinates that best
explains it (scale sweep + FFT normalised cross-correlation of gradient maps, searched
around the previous frame's framing) and report the structural match score. Invented or
dropped slabs, bays or windows lower the score; a camera that wanders off the target
shows up as a framing far from the target at the end.

usage: python validate_video.py <video.mp4> <slug> [--every 3] [--out report.json]
"""
import json, subprocess, sys, os, tempfile
import numpy as np
from PIL import Image
from nestgeo import Sources, MASTER, GEO, tn_box_to_o, framing_of, path

OW, OH = 224, 126          # frame matching resolution
PAD = 2.2                  # search canvas = PAD x frame size

def grad(a):
    gx = np.zeros_like(a); gy = np.zeros_like(a)
    gx[:, 1:-1] = a[:, 2:] - a[:, :-2]
    gy[1:-1, :] = a[2:, :] - a[:-2, :]
    return np.hypot(gx, gy)

def match_template(img, tpl):
    """Normalised cross-correlation of tpl over img (valid positions), via FFT + integral images."""
    H, W = img.shape; h, w = tpl.shape
    t = tpl - tpl.mean(); tn = np.sqrt((t * t).sum()) + 1e-6
    fsz = (H + h, W + w)
    F = np.fft.rfft2(img, fsz); T = np.fft.rfft2(t[::-1, ::-1], fsz)
    num = np.fft.irfft2(F * T, fsz)[h - 1:H, w - 1:W]
    S = np.pad(img, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    S2 = np.pad(img * img, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    def box(A):
        return A[h:, w:] - A[:-h, w:] - A[h:, :-w] + A[:-h, :-w]
    s, s2 = box(S), box(S2)
    var = s2 - s * s / (h * w)
    den = np.sqrt(np.maximum(var, 1e-6)) * tn
    return num / den

def frames_of(video, every):
    d = tempfile.mkdtemp()
    subprocess.run(['ffmpeg', '-v', 'error', '-i', video, '-vf', f"framestep={every},scale={OW}:{OH}:flags=area",
                    '-fps_mode', 'passthrough', os.path.join(d, 'f%04d.png')], check=True)
    n = int(subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0', '-show_entries',
                            'stream=nb_read_frames', '-of', 'csv=p=0', video], capture_output=True, text=True).stdout.strip())
    fs = sorted(os.listdir(d))
    return n, [np.asarray(Image.open(os.path.join(d, f)).convert('L'), np.float32) for f in fs]

def track(src, E, prev, scales):
    """best (score, (cx, cy, w)) for frame gradient E around prev framing"""
    best = (-2, prev)
    cw, ch = int(OW * PAD), int(OH * PAD)
    for s in scales:
        w = prev[2] * s
        cvs = np.asarray(src.view(prev[0], prev[1], w * PAD, out=(cw, ch)), np.float32)
        G = grad(cvs)
        R = match_template(G, E)
        iy, ix = np.unravel_index(np.argmax(R), R.shape)
        sc = float(R[iy, ix])
        if sc > best[0]:
            # offset of the frame window inside the canvas -> new centre
            px = (ix + OW / 2) / cw; py = (iy + OH / 2) / ch
            cx = prev[0] + (px - 0.5) * w * PAD
            cy = prev[1] + (py - 0.5) * w * PAD * 9 / 16
            best = (sc, (cx, cy, w))
    return best

def main():
    video, slug = sys.argv[1], sys.argv[2]
    every = int(sys.argv[sys.argv.index('--every') + 1]) if '--every' in sys.argv else 3
    out = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else None
    src = Sources(gray=True)
    start = framing_of(MASTER); end = framing_of(tn_box_to_o(GEO[slug]['end']))
    def arg_framing(flag):
        if flag in sys.argv:
            v = sys.argv[sys.argv.index(flag) + 1]
            if v.startswith('tn:'):
                return framing_of(tn_box_to_o([float(x) for x in v[3:].split(',')]))
            return tuple(float(x) for x in v.split(','))
        return None
    start = arg_framing('--start') or start
    end = arg_framing('--end') or end
    total, frs = frames_of(video, every)
    # make sure the true last frame is part of the samples (tracking backwards starts there)
    d = tempfile.mkdtemp()
    subprocess.run(['ffmpeg', '-v', 'error', '-sseof', '-0.2', '-i', video, '-update', '1', '-vf', f'scale={OW}:{OH}:flags=area',
                    os.path.join(d, 'last.png')], check=True)
    last_fr = np.asarray(Image.open(os.path.join(d, 'last.png')).convert('L'), np.float32)
    idx = [i * every for i in range(len(frs))]
    if idx[-1] != total - 1:
        frs.append(last_fr); idx.append(total - 1)
    grads = [grad(fr) for fr in frs]

    P = (end[0], end[1]); w0, w1 = start[2], end[2]
    def on_guide(w):
        k = (w - w1) / (w0 - w1)
        return (P[0] + (start[0] - P[0]) * k, P[1] + (start[1] - P[1]) * k, w)
    def run(order, first):
        res = {}
        prev = first
        for i in order:
            E = grads[i]
            best = (-2, prev)
            # hypotheses: continue from the previous frame, or sit on the ideal straight path at that zoom
            for h in (prev, on_guide(prev[2])):
                sc, f = track(src, E, h, np.exp(np.linspace(np.log(0.62), np.log(1.6), 15)))
                sc2, f2 = track(src, E, f, np.exp(np.linspace(-0.04, 0.04, 9)))
                if sc2 >= sc: sc, f = sc2, f2
                if sc > best[0]: best = (sc, f)
            res[i] = best
            prev = best[1]
        return res
    fwd = run(range(len(frs)), start)
    bwd = run(range(len(frs) - 1, -1, -1), end)   # backwards from the known end framing
    rows = []
    for i in range(len(frs)):
        sc, f = max(fwd[i], bwd[i], key=lambda r: r[0])
        cx, cy, w = f
        fi = idx[i]
        g = path(fi / max(total - 1, 1), start, end)
        rows.append({'frame': fi, 'score': round(sc, 3), 'zoom': round(start[2] / w, 2), 'cx': round(cx, 1), 'cy': round(cy, 1),
                     'w': round(w, 1), 'guide_zoom': round(start[2] / g[2], 2)})
        print(f"{fi:4d}  score {sc:5.2f}  zoom x{start[2]/w:6.2f} (guide x{start[2]/g[2]:6.2f})  centre ({cx:7.1f},{cy:7.1f})", flush=True)
    scores = [r['score'] for r in rows]
    zooms = [r['zoom'] for r in rows]
    mono = all(b >= a * 0.97 for a, b in zip(zooms, zooms[1:]))
    last = rows[-1]
    end_err = float(np.hypot(last['cx'] - end[0], last['cy'] - end[1]) / end[2])
    summary = {'video': os.path.basename(video), 'frames': total, 'min': min(scores), 'mean': round(float(np.mean(scores)), 3),
               'p10': round(float(np.percentile(scores, 10)), 3), 'monotonic_zoom': mono,
               'final_zoom': last['zoom'], 'target_zoom': round(start[2] / end[2], 2),
               'final_centre_error_frac': round(end_err, 3), 'rows': rows}
    print(json.dumps({k: v for k, v in summary.items() if k != 'rows'}))
    if out: json.dump(summary, open(out, 'w'), indent=1)

if __name__ == '__main__':
    main()
