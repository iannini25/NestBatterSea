"""Robust global motion of a clip: dense DIS flow from anchor frames (every 4), iteratively reweighted affine
fit -> cumulative zoom / shift per frame (px of the 1920 frame); per step derivative saved as (z, tx, ty)."""
import sys, numpy as np, cv2, assemble as AS
def affine(g0, g1, dis, ys, xs, X):
    fl = dis.calc(g0, g1, None); u = fl[ys, xs, 0].ravel(); v = fl[ys, xs, 1].ravel()
    w = np.ones(u.size)
    for _ in range(5):
        a = np.linalg.lstsq(X * w[:, None], u * w, rcond=None)[0]; b = np.linalg.lstsq(X * w[:, None], v * w, rcond=None)[0]
        w = 1 / np.maximum(np.hypot(X @ a - u, X @ b - v), 1.0)
    return np.array([(a[0] + b[1]) / 2, a[2] * 2, b[2] * 2])
def cum(path, step=4):
    F = AS.read_frames(path)
    g = [cv2.cvtColor(cv2.resize(f, (960, 540), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY) for f in F]
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    ys, xs = np.mgrid[0:540:6, 0:960:6]; X = np.c_[xs.ravel() - 480, ys.ravel() - 270, np.ones(xs.size)]
    n = len(g); C = np.zeros((n, 3)); anc = 0
    for k in range(1, n):
        C[k] = C[anc] + affine(g[anc], g[k], dis, ys, xs, X)
        if k - anc == step: anc = k
    return C
if __name__ == '__main__':
    src, out = sys.argv[1:3]
    C = cum(src); np.save(out, np.diff(C, axis=0)); print(out, C.shape, 'total zoom %.3f' % C[-1, 0])
