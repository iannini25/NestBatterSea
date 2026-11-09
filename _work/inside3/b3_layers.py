"""Bungalow 3: layers of the end image (2688 x 1520) with an explicit matte.
F (front) = everything except the living room seen through the open slide door, above the planter.
R (room)  = the end image's own pixels where the room is visible; behind the planter, the door posts
            and outside the opening, the clean plate (registered on the room locally, colour matched)."""
import os, cv2, numpy as np
H0 = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(H0, 'out')
K = cv2.imread(os.path.join(H0, '..', 'ai', 'gen', 'bung3-end-gpt3.png')).astype(np.float32)
Cl = cv2.imread(os.path.join(H0, '..', 'ai', 'gen', 'bung3-clean.png')).astype(np.float32)
h, w = K.shape[:2]
Hg = np.load(os.path.join(OUT, 'bung3-clean-H.npy'))
Clr = cv2.warpPerspective(Cl, Hg, (w, h), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
X0, X1, Y0 = 980, 1594, 506                      # the opening (inner edges of the door posts, soffit line)
# local registration of the clean plate on the room (wall, artwork, lamp, door) above the sofa
def g(im):
    gg = cv2.GaussianBlur(cv2.cvtColor(im.astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 1.5)
    m = np.hypot(cv2.Sobel(gg, cv2.CV_32F, 1, 0), cv2.Sobel(gg, cv2.CV_32F, 0, 1)); return m / (m.max() + 1e-6)
roi = (slice(Y0 + 20, 1060), slice(X0 + 20, X1 - 20))
wl = np.eye(2, 3, dtype=np.float32)
cc, wl = cv2.findTransformECC(g(K[roi]), g(Clr[roi]), wl, cv2.MOTION_AFFINE, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 300, 1e-7), None, 5)
print('local ecc', round(cc, 4), wl.round(4).tolist())
T = np.array([[1, 0, -roi[1].start], [0, 1, -roi[0].start], [0, 0, 1]], np.float32)
A3 = np.vstack([wl, [0, 0, 1]]).astype(np.float32)
M = np.linalg.inv(T) @ A3 @ T                 # end image px -> registered clean px (inverse map)
Cll = cv2.warpPerspective(Clr, M, (w, h), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
# planter silhouette: below y 940, what differs from the clean plate (or is green / dark) and is
# connected to the planter box; then solid from each column's top down
hsv = cv2.cvtColor(K.astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float32)
Bc, Gc, Rc = K[..., 0], K[..., 1], K[..., 2]
green = (hsv[..., 0] >= 27) & (hsv[..., 0] <= 95) & (hsv[..., 1] > 50)
dark = hsv[..., 2] < 70
lab = lambda im: cv2.cvtColor(np.clip(im, 0, 255).astype(np.uint8), cv2.COLOR_BGR2LAB).astype(np.float32)
dif = cv2.GaussianBlur(np.sqrt(((lab(K) - lab(Cll)) ** 2).sum(2)), (0, 0), 1.2)
yy, xx = np.mgrid[0:h, 0:w]
XR = 1785                                        # right end of the slid open glass door stack
zone = (yy > 940) & (xx >= X0 - 30) & (xx < XR + 30)
cand = (green | dark) & zone
cand = cv2.morphologyEx(cand.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
n, lbl, st, _ = cv2.connectedComponentsWithStats(cand, 8)
keep = np.zeros(n, bool)
for i in range(1, n):
    if st[i, cv2.CC_STAT_TOP] + st[i, cv2.CC_STAT_HEIGHT] >= 1125:
        keep[i] = True
fol = keep[lbl] & (cand > 0)
fol = cv2.dilate(fol.astype(np.uint8), np.ones((7, 7), np.uint8))
# thin stems and leaves above the mass: differ from the clean plate, near the foliage, dark or vivid
near = cv2.dilate(fol, np.ones((61, 61), np.uint8)).astype(bool)
extra = (dif > 22) & near & ((hsv[..., 2] < 130) | (hsv[..., 1] > 140)) & zone
extra = cv2.dilate(extra.astype(np.uint8), np.ones((5, 5), np.uint8))

fg = np.zeros((h, w), np.uint8)
for x in range(X0 - 30, min(w, XR + 30)):
    col = np.nonzero(fol[:, x])[0]
    top = col[0] if len(col) else 1130
    fg[min(top, 1130):, x] = 1
fg = np.maximum(fg, extra)
room = np.zeros((h, w), np.uint8); room[Y0:, X0:XR] = 1
fg = (fg | (1 - room)).astype(np.uint8)
# the door stack on the right: only its dark frames stay in front, its glass is open
frames = ((hsv[..., 2] < 95) & (xx >= X1 - 6) & (yy >= Y0) & (yy < 1130)).astype(np.uint8)
frames = cv2.morphologyEx(frames, cv2.MORPH_OPEN, np.ones((25, 1), np.uint8))      # vertical members only
fg = np.maximum(fg, cv2.dilate(frames, np.ones((1, 3), np.uint8)))
fg[908:916, X0:XR] = 1                          # the balustrade's glass top rail is in front of the room
fga = cv2.GaussianBlur(fg.astype(np.float32), (0, 0), 1.0)
vis = 1 - fga
# colour match the clean plate to the room (low frequency gain from the visible room)
num = cv2.GaussianBlur(K * vis[..., None], (0, 0), 30); den = cv2.GaussianBlur(Cll * vis[..., None], (0, 0), 30)
wv = cv2.GaussianBlur(vis, (0, 0), 30)[..., None]
gain = np.clip(np.where(wv > 0.03, (num + 1) / (den + 1), 1.0), 0.8, 1.25)
kk = np.clip(wv * 6, 0, 1)
Cm = Cll * (gain * kk + (1 - kk))
# room layer: own pixels where visible, blended into the clean plate over a few px under the foliage edge
vis_soft = cv2.GaussianBlur(cv2.erode((vis > 0.5).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(np.float32), (0, 0), 2.5)
R = Cm * (1 - vis_soft[..., None]) + K * vis_soft[..., None]
cv2.imwrite(os.path.join(OUT, 'bung3-R.png'), np.clip(R, 0, 255).astype(np.uint8))
cv2.imwrite(os.path.join(OUT, 'bung3-F.png'), np.dstack([K, fga * 255]).astype(np.uint8))
S = os.environ.get('PREV')
if S:
    v = K.copy(); v[fg.astype(bool) & room.astype(bool)] = v[fg.astype(bool) & room.astype(bool)] * 0.4 + np.array([255, 0, 255]) * 0.6
    cv2.imwrite(os.path.join(S, 'bung3-matte.jpg'), cv2.resize(v[400:1300, 800:1900], None, fx=0.9, fy=0.9).astype(np.uint8))
    cv2.imwrite(os.path.join(S, 'bung3-R.jpg'), cv2.resize(np.clip(R, 0, 255)[400:1300, 800:1900], None, fx=0.9, fy=0.9).astype(np.uint8))
