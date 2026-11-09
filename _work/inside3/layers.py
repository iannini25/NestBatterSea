"""
Two depth layers from a home's end image (the last frame of its flight, seen from outside):
  F = everything in front of the room (facade, window frames, balcony, plants), the image's own pixels
  R = the room behind, the image's own pixels wherever the room is visible, and the clean plate
      (the same photo with the foreground removed, registered and colour matched) only behind F.
usage: python layers.py <home> <end image> <clean plate> <x0 y0 x1 y1 room box in end image px>
"""
import sys, os, cv2, numpy as np
home, kp, cp = sys.argv[1:4]
bx = [int(v) for v in sys.argv[4:8]]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out'); os.makedirs(OUT, exist_ok=True)
K = cv2.imread(kp).astype(np.float32); Cl = cv2.imread(cp).astype(np.float32)
h, w = K.shape[:2]
Cl = cv2.resize(Cl, (w, h), interpolation=cv2.INTER_CUBIC)
def grad(im):
    g = cv2.GaussianBlur(cv2.cvtColor(im.astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 2)
    m = np.hypot(cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1)); return m / (m.max() + 1e-6)
# register the clean plate on the end image (outside the room box the two should agree)
msk = np.full((h, w), 255, np.uint8); msk[bx[1]:bx[3], bx[0]:bx[2]] = 0
warp = np.eye(3, dtype=np.float32); crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6)
for s in (0.125, 0.25, 0.5):
    A = cv2.resize(grad(K), None, fx=s, fy=s); B = cv2.resize(grad(Cl), None, fx=s, fy=s)
    M = cv2.resize(msk, None, fx=s, fy=s, interpolation=cv2.INTER_NEAREST)
    S = np.diag([s, s, 1]).astype(np.float32)
    ww = (S @ warp @ np.linalg.inv(S)).astype(np.float32)
    try:
        cc, ww = cv2.findTransformECC(A, B, ww, cv2.MOTION_HOMOGRAPHY, crit, M, 5)
    except cv2.error as e:
        print('ecc', s, e); continue
    warp = (np.linalg.inv(S) @ ww @ S).astype(np.float32); print('ecc', s, round(cc, 4))
Clr = cv2.warpPerspective(Cl, warp, (w, h), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
# colour match the clean plate to the end image (low frequency gain, from the room pixels both show)
lab = lambda im: cv2.cvtColor(np.clip(im, 0, 255).astype(np.uint8), cv2.COLOR_BGR2LAB).astype(np.float32)
LK, LC = lab(K), lab(Clr)
d = np.sqrt(((LK - LC) ** 2).sum(2))
inbox = np.zeros((h, w), bool); inbox[bx[1]:bx[3], bx[0]:bx[2]] = True
# foreground = where the end image differs from the clean plate inside the room box (window frames,
# plants, balustrade...); smoothed, cleaned, with soft edges
dd = cv2.GaussianBlur(d, (0, 0), 1.5)
fg = ((dd > float(os.environ.get('THR', 16))) | ~inbox).astype(np.uint8)
fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
# drop tiny islands of "room" inside the foreground and tiny foreground specks inside the room
n, lbl, st, _ = cv2.connectedComponentsWithStats(1 - fg, 8)
for i in range(1, n):
    if st[i, cv2.CC_STAT_AREA] < 400: fg[lbl == i] = 1
n, lbl, st, _ = cv2.connectedComponentsWithStats(fg, 8)
for i in range(1, n):
    if st[i, cv2.CC_STAT_AREA] < 150: fg[lbl == i] = 0
fga = cv2.GaussianBlur(cv2.dilate(fg, np.ones((3, 3), np.uint8)).astype(np.float32), (0, 0), 1.2)
vis = 1 - fga                                   # room visible in the end image
# room layer: own pixels where visible, the clean plate behind the foreground, brightness matched
num = cv2.GaussianBlur(K * vis[..., None], (0, 0), 25); den = cv2.GaussianBlur(Clr * vis[..., None], (0, 0), 25)
wv = cv2.GaussianBlur(vis, (0, 0), 25)[..., None]
gain = np.where(wv > 0.05, (num + 1) / (den + 1), 1.0); gain = np.clip(gain, 0.75, 1.33)
R = Clr * (gain * np.clip(wv * 4, 0, 1) + (1 - np.clip(wv * 4, 0, 1)))
R = R * (1 - vis[..., None]) + K * vis[..., None]
cv2.imwrite(os.path.join(OUT, f'{home}-R.png'), np.clip(R, 0, 255).astype(np.uint8))
Fa = np.dstack([K, fga * 255]).astype(np.uint8)
cv2.imwrite(os.path.join(OUT, f'{home}-F.png'), Fa)
np.save(os.path.join(OUT, f'{home}-clean-H.npy'), warp)
# previews
S = os.environ.get('PREV')
if S:
    v = K.copy(); v[fg.astype(bool) & inbox] = v[fg.astype(bool) & inbox] * 0.4 + np.array([255, 0, 255]) * 0.6
    cv2.imwrite(os.path.join(S, f'{home}-matte.jpg'), cv2.resize(v, (1344, int(1344 * h / w))).astype(np.uint8))
    cv2.imwrite(os.path.join(S, f'{home}-R.jpg'), cv2.resize(np.clip(R, 0, 255), (1344, int(1344 * h / w))).astype(np.uint8))
print('done', home)
