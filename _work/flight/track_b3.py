"""Bungalow 3 window outline, frame by frame on the published master. Exact camera up to the hand off; then
homography tracking forward from there and backward from the last frame (outline on the storey's glazing),
blended, verticals kept vertical, lightly smoothed. Run with PREVIZ_WARP=0.4,1,1,1,0.30"""
import json, sys, numpy as np, cv2
from scipy.ndimage import gaussian_filter1d
sys.path.insert(0, '../ai'); import assemble as AS
import render_previz as RP, proxy as X, camera as C
S = sys.argv[1]; W, H = 1920, 1080
t = json.load(open('../ai/out/bung3-flight-timing.json')); src = np.array(t['src']); nA = t['partA_frames'] - 1
p = RP.Previz('bung3', W, H); dt = 0.30 / nA
M2O = np.array([[C.M2O, 0, C.MASTER_BOX[0]], [0, C.M2O, C.MASTER_BOX[1]], [0, 0, 1]])
poly = np.array([[1352, 806], [1406, 818], [1406, 837], [1352, 825]], float)
F = AS.read_frames('../ai/out/bung3-flight-master.mkv'); n = len(F); G = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in F]
def pquad(Hm):
    q = Hm @ np.c_[poly, np.ones(4)].T; return (q[:2] / q[2]).T
Q = [None] * n
for j in range(n):
    if src[j] <= nA:
        Q[j] = pquad(np.linalg.inv(X.h_plane(p.cam_at(src[j] * dt), p.plane)[0]) @ M2O)
j0 = max(j for j in range(n) if Q[j] is not None)
lk = dict(winSize=(25, 25), maxLevel=4, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 40, 0.01))
def step(a, b, q):
    x0, y0 = q.min(0); x1, y1 = q.max(0); h_ = max(y1 - y0, 30); w_ = max(x1 - x0, 60)
    m = np.zeros_like(G[a])
    xa, ya = int(max(0, x0 - .25 * w_)), int(max(0, y0 - .7 * h_)); xb, yb = int(min(W, x1 + .25 * w_)), int(min(H, y1 + .7 * h_))
    if xb - xa < 80 or yb - ya < 60: xa, ya, xb, yb = 0, 0, W, H
    m[ya:yb, xa:xb] = 255
    pts = cv2.goodFeaturesToTrack(G[a], 1500, 0.003, 5, mask=m)
    nx, st, _ = cv2.calcOpticalFlowPyrLK(G[a], G[b], pts, None, **lk); bk, st2, _ = cv2.calcOpticalFlowPyrLK(G[b], G[a], nx, None, **lk)
    ok = (st.ravel() == 1) & (st2.ravel() == 1) & (np.linalg.norm((bk - pts).reshape(-1, 2), axis=1) < 0.5)
    A, inl = cv2.findHomography(pts[ok], nx[ok], cv2.RANSAC, 1.0, maxIters=4000)
    return cv2.perspectiveTransform(q[None].astype(np.float64), A)[0]
Qf = list(Q)
for j in range(j0 + 1, n): Qf[j] = step(j - 1, j, Qf[j - 1])
endq = np.array([[8, 348], [1282, 348], [1282, 808], [8, 808]], float)
Qb = [None] * n; Qb[-1] = endq
for j in range(n - 2, j0 - 1, -1): Qb[j] = step(j + 1, j, Qb[j + 1])
print('disagreement at seam', np.abs(Qb[j0] - Q[j0]).max().round(1), 'at end', np.abs(Qf[-1] - endq).max().round(1))
np.save('out/hybrid/b3-Qb.npy', np.array(Qb[j0:])); np.save('out/hybrid/b3-Qexact.npy', np.array(Q[:j0 + 1]))
ths=[]
for j in [j0, j0+12, j0+28, j0+45, j0+62, j0+80, j0+100, j0+120, j0+140]:
    im=F[j].copy(); cv2.polylines(im,[Qb[j].astype(np.int32)],True,(0,255,0),4); cv2.polylines(im,[Qf[j].astype(np.int32)],True,(0,0,255),3)
    ths.append(cv2.putText(cv2.resize(im,(640,360),interpolation=cv2.INTER_AREA),str(j),(6,22),0,.7,(0,255,255),2))
cv2.imwrite(S+r'3qb.jpg',np.vstack([np.hstack(ths[r*3:(r+1)*3]) for r in range(3)]),[cv2.IMWRITE_JPEG_QUALITY,88])
A_ = np.array([q for q in Q[:j0 + 1]])
B_ = []
for j in range(j0 + 1, n):
    x = (j - j0) / (n - 1 - j0); w = x * x * (3 - 2 * x); B_.append(Qf[j] * (1 - w) + Qb[j] * w)
B_ = np.array(B_)
# level camera: verticals stay vertical; the correction to do so fades in after the hand off
fade = np.clip(np.arange(1, len(B_) + 1) / 30.0, 0, 1)[:, None]
for a, b in ((0, 3), (1, 2)):
    m = (B_[:, a, 0] + B_[:, b, 0]) / 2
    B_[:, a, 0] = B_[:, a, 0] * (1 - fade[:, 0]) + m * fade[:, 0]; B_[:, b, 0] = B_[:, b, 0] * (1 - fade[:, 0]) + m * fade[:, 0]
all_ = np.r_[A_, B_]
smooth = gaussian_filter1d(all_, 2.5, axis=0, mode='nearest'); wt = np.clip((np.arange(n) - j0) / 8.0, 0, 1)[:, None, None]
tail = np.clip((n - 1 - np.arange(n)) / 8.0, 0, 1)[:, None, None]
out = all_ * (1 - wt * tail) + smooth * wt * tail
np.save('out/hybrid/bung3-quads.npy', out)
hs, boxes = [], []
for q in out:
    qn = q / [W, H]; Hn = cv2.getPerspectiveTransform(poly.astype(np.float32), qn.astype(np.float32))
    hs.append([round(float(v), 9) for v in Hn.ravel()])
    boxes.append([round(float(qn[:, 0].min()), 5), round(float(qn[:, 1].min()), 5), round(float(qn[:, 0].max()), 5), round(float(qn[:, 1].max()), 5)])
json.dump({'h': hs, 'frames': boxes}, open('out/hybrid/bung3-htrack.json', 'w'))
idx = [j0, j0 + 12, j0 + 28, j0 + 45, j0 + 62, j0 + 80, j0 + 100, j0 + 120, j0 + 140, j0 + 155, n - 12, n - 1]
th = []
for j in idx:
    im = F[j].copy(); cv2.polylines(im, [out[j].astype(np.int32)], True, (0, 0, 255), 4)
    th.append(cv2.putText(cv2.resize(im, (640, 360), interpolation=cv2.INTER_AREA), str(j), (6, 22), 0, .7, (0, 255, 255), 2))
cv2.imwrite(S + r'\b3t3.jpg', np.vstack([np.hstack(th[r * 3:(r + 1) * 3]) for r in range(4)]), [cv2.IMWRITE_JPEG_QUALITY, 88])
