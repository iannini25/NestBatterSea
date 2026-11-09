"""
Join flight segments and retime them onto one smooth camera-speed profile.

Each segment was generated between two exact keyframes, so the joint frame is shared.
Generated segments do not agree on speed at the joint (and the last one may stop dead),
so the joined clip is resampled in time: the camera's log-zoom per source frame comes from
the validator tracks, and output frames follow the same velocity profile as the approved
LOFT 4 flight (gentle start, steady middle, soft landing). Frames between two source frames
are blended, which at these small inter-frame differences reads as continuous motion.

usage: python retime.py <out.mp4> <seconds> <profile_track.json> seg1.mp4:seg1.json:z0:z1 seg2.mp4:...
  z0, z1 = exact zoom (vs the master) of each segment's first and last keyframe
Writes <out.mp4> and <out>.track.json (per output frame: cx, cy, w in ORIG coords).
"""
import json, os, sys, subprocess, tempfile
import numpy as np
from PIL import Image

out, secs, profile_json = sys.argv[1], float(sys.argv[2]), sys.argv[3]
segs = [a.split(':') for a in sys.argv[4:]]
FPS = 24

def read_frames(video):
    d = tempfile.mkdtemp()
    subprocess.run(['ffmpeg', '-v', 'error', '-i', video, os.path.join(d, 'f%04d.png')], check=True)
    return [os.path.join(d, f) for f in sorted(os.listdir(d))]

frames, logz, fr = [], [], []          # fr: (cx, cy, w) per source frame
for k, (video, track, z0, z1) in enumerate(segs):
    fs = read_frames(video)
    rows = json.load(open(track))['rows']
    n = len(fs)
    idx = np.array([r['frame'] for r in rows], float)
    w = np.array([r['w'] for r in rows], float); cx = np.array([r['cx'] for r in rows]); cy = np.array([r['cy'] for r in rows])
    # anchor the measured zoom to the exact keyframe zooms at both ends
    lz = np.log(w[0] / w)                                   # relative log-zoom inside the segment
    lz = lz / lz[-1] * (np.log(float(z1)) - np.log(float(z0))) + np.log(float(z0))
    i_all = np.arange(n)
    lz_all = np.interp(i_all, idx, lz)
    cx_all = np.interp(i_all, idx, cx); cy_all = np.interp(i_all, idx, cy); w_all = np.interp(i_all, idx, w)
    start = 1 if k > 0 else 0                              # the joint frame is shared: keep it once
    frames += fs[start:]; logz += list(lz_all[start:]); fr += list(zip(cx_all[start:], cy_all[start:], w_all[start:]))

logz = np.maximum.accumulate(np.array(logz))               # strictly forward
L = logz[-1]
# reference velocity profile from the approved flight (normalised log-zoom over normalised time)
prow = json.load(open(profile_json))['rows']
pt = np.array([r['frame'] for r in prow], float); pt /= pt[-1]
pz = np.log(np.array([r['zoom'] for r in prow], float)); pz = (pz - pz[0]) / (pz[-1] - pz[0])
pz = np.maximum.accumulate(pz)

N = int(round(secs * FPS)) + 1
src_pos = np.arange(len(frames), dtype=float)
tmp = tempfile.mkdtemp()
track = []
for j in range(N):
    target = np.interp(j / (N - 1), pt, pz) * (L - logz[0]) + logz[0]
    s = float(np.interp(target, logz, src_pos))            # fractional source frame
    a = int(np.floor(s)); b = min(a + 1, len(frames) - 1); t = s - a
    A = Image.open(frames[a]).convert('RGB')
    img = A if t < 1e-3 or a == b else Image.blend(A, Image.open(frames[b]).convert('RGB'), t)
    img.save(os.path.join(tmp, f'o{j:04d}.png'))
    ca, cb = fr[a], fr[b]
    track.append([round(ca[i] + (cb[i] - ca[i]) * t, 2) for i in range(3)])
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', str(FPS), '-i', os.path.join(tmp, 'o%04d.png'),
                '-c:v', 'libx264', '-crf', '14', '-preset', 'slow', '-pix_fmt', 'yuv420p', out], check=True)
json.dump({'fps': FPS, 'frames': track}, open(out.replace('.mp4', '.track.json'), 'w'))
print('wrote', out, N, 'frames from', len(frames), 'source frames; total zoom x', round(float(np.exp(L)), 2))
