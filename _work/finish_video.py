"""
Finish a generated clip for the site.
  - global per-channel gain so its first frame matches the still it hands over from
  - web encodes: 1920x1080 and 1280x720, forward and reversed (the way back retraces the
    exact same frames), H.264, faststart, short GOP for instant start
  - first and last frames as JPEG, decoded from the finished encode, so the stills the site
    shows before/after the clip are pixel-identical to the clip's own ends

usage: python finish_video.py <in.mp4> <name> <match_still.jpg> [--outdir ../assets]
"""
import os, sys, subprocess, tempfile
import numpy as np
from PIL import Image

src, name, still = sys.argv[1], sys.argv[2], sys.argv[3]
outdir = sys.argv[sys.argv.index('--outdir') + 1] if '--outdir' in sys.argv else os.path.join('..', 'assets')
vdir, sdir = os.path.join(outdir, 'video'), os.path.join(outdir, 'stills')
os.makedirs(vdir, exist_ok=True); os.makedirs(sdir, exist_ok=True)
tmp = tempfile.mkdtemp()

def grab(video, which, path):
    if which == 'first':
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', video, '-frames:v', '1', '-q:v', '1', path], check=True)
    else:
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-sseof', '-0.2', '-i', video, '-update', '1', '-q:v', '1', path], check=True)

# 1. gain from the first frame vs the still it must match
grab(src, 'first', os.path.join(tmp, 'f.png'))
f = np.asarray(Image.open(os.path.join(tmp, 'f.png')).convert('RGB'), np.float64)
m = np.asarray(Image.open(still).convert('RGB').resize((f.shape[1], f.shape[0]), Image.LANCZOS), np.float64)
gain = (m.reshape(-1, 3).mean(0) + 1) / (f.reshape(-1, 3).mean(0) + 1)
gain = np.clip(gain, 0.9, 1.12)
mix = f"colorchannelmixer=rr={gain[0]:.4f}:gg={gain[1]:.4f}:bb={gain[2]:.4f}"
print('gain', gain.round(4))

common = ['-c:v', 'libx264', '-preset', 'slow', '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-movflags', '+faststart',
          '-g', '12', '-bf', '2', '-an']
jobs = [
    (f'{name}.mp4', f'{mix},scale=1920:1080:flags=lanczos', '24'),
    (f'{name}-720.mp4', f'{mix},scale=1280:720:flags=lanczos', '26'),
    (f'{name}-rev.mp4', f'{mix},reverse,scale=1920:1080:flags=lanczos', '24'),
    (f'{name}-rev-720.mp4', f'{mix},reverse,scale=1280:720:flags=lanczos', '26'),
]
for out, vf, crf in jobs:
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-vf', vf, '-crf', crf] + common + [os.path.join(vdir, out)], check=True)
    print(out, round(os.path.getsize(os.path.join(vdir, out)) / 1e6, 2), 'MB')

grab(os.path.join(vdir, f'{name}.mp4'), 'first', os.path.join(sdir, f'{name}-first.jpg'))
grab(os.path.join(vdir, f'{name}.mp4'), 'last', os.path.join(sdir, f'{name}-last.jpg'))
a = np.asarray(Image.open(os.path.join(sdir, f'{name}-first.jpg')).convert('RGB'), np.float64)
print('first frame vs still: mean abs diff', round(float(np.abs(a - m).mean()), 2))
