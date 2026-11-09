"""Step inside from a Kling start/end clip: retimed to 60 fps so the camera's global motion follows one
smooth bell (Kling starts almost still and brakes unevenly), starting exactly on the flight's last frame
and ending exactly on the final image (each blended in over the first / last few frames, where the
camera barely moves).
usage: python ai/kling_inside.py <clip.mp4> <start.png> <final.png> <out.mkv> [--seconds 3.4]"""
import argparse, math, sys, os, json
import numpy as np, cv2
from scipy.special import betainc
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assemble as AS
ap = argparse.ArgumentParser()
ap.add_argument('clip'); ap.add_argument('start'); ap.add_argument('final'); ap.add_argument('out')
ap.add_argument('--seconds', type=float, default=3.4)
ap.add_argument('--a', type=float, default=1.8); ap.add_argument('--b', type=float, default=1.8)
ap.add_argument('--ends', type=int, default=10, help='output frames over which each end settles on its exact image')
a = ap.parse_args()
Fr = AS.read_frames(a.clip)
S = cv2.imread(a.start)
E = AS.load_image(a.final)
print('frames', len(Fr), 'first vs start %.2f' % np.abs(Fr[0].astype(float) - S).mean(), 'last vs final %.2f' % np.abs(Fr[-1].astype(float) - E).mean())
def sim(x, y):
    M = AS.similarity(cv2.resize(x, (960, 540)), cv2.resize(y, (960, 540)))
    if M is None:
        return 0.0, 0.0, 0.0
    return math.log(math.hypot(M[0, 0], M[1, 0])), M[0, 2] * 2, M[1, 2] * 2
_d = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
_s = [cv2.cvtColor(cv2.resize(f, (480, 270), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY) for f in Fr]
# median image motion per native step (the room, not a foreground that sweeps past), px of the 1920 frame
v = np.array([float(np.median(np.hypot(*np.moveaxis(_d.calc(_s[i], _s[i + 1], None), 2, 0)))) * 4 for i in range(len(Fr) - 1)]) + 1e-3
ap2 = float(os.environ.get('AP2', 0.7))                                   # compressed: a passing foreground must not freeze the camera
P = np.r_[0.0, np.cumsum(v ** ap2)]
print('motion per native step', np.round(v, 1).tolist())
N = int(round(a.seconds * AS.FPS))
x = np.arange(N + 1) / N
src = np.interp(P[-1] * betainc(a.a + 1, a.b + 1, x), P, np.arange(len(P)))
src[0], src[-1] = 0.0, float(len(Fr) - 1)
ff = AS.writer(a.out)
for j in range(N + 1):
    img = AS.interp(Fr, float(src[j]))
    if j < a.ends:
        w = AS.smooth(j / a.ends)
        img = cv2.addWeighted(S, 1 - w, img, w, 0)
    if j > N - a.ends:
        w = AS.smooth((j - (N - a.ends)) / a.ends)
        img = cv2.addWeighted(img, 1 - w, E, w, 0)
    ff.stdin.write(img.tobytes())
ff.stdin.close(); ff.wait()
json.dump({'src': src.tolist(), 'motion': v.tolist()}, open(a.out.replace('.mkv', '-timing.json'), 'w'))
print('written', a.out, N + 1, 'frames')
