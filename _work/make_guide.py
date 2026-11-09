"""
Deterministic camera-path guide: a pure push-in on the official imagery from the master
framing to a home's end framing. Used (a) as motion reference for the video model and
(b) as ground truth for validation. usage: python make_guide.py loft4|bung3 [seconds] [fps]
"""
import os, sys, subprocess, tempfile
from nestgeo import Sources, MASTER, GEO, tn_box_to_o, framing_of, path, F

slug = sys.argv[1]
secs = float(sys.argv[2]) if len(sys.argv) > 2 else 6
fps = int(sys.argv[3]) if len(sys.argv) > 3 else 24
src = Sources()
start = framing_of(MASTER)
end = framing_of(tn_box_to_o(GEO[slug]['end']))
n = int(round(secs * fps))
d = tempfile.mkdtemp()
for i in range(n):
    t = i / (n - 1)
    cx, cy, w = path(t, start, end)
    src.view(cx, cy, w, out=(1280, 720)).save(os.path.join(d, f'g{i:04d}.png'))
out = F(f'{slug}_guide.mp4')
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', str(fps), '-i', os.path.join(d, 'g%04d.png'),
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', out], check=True)
print('guide', out, n, 'frames', 'start', [round(v, 1) for v in start], 'end', [round(v, 1) for v in end])
