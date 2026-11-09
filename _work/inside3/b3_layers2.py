"""Bungalow 3 layers v2: exact compositing. B = clean plate aligned to the end image by dense flow.
alpha = solid planter + soft leaves (difference to B, gated by leaf colours), F = (K - (1 - a) B) / a,
R = B in the planter zone, K elsewhere. Frame 0 recomposes to K exactly; nothing of the room is left in F
and no leaf is left in R."""
import os, cv2, numpy as np
H0 = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(H0, 'out')
K = cv2.imread(os.path.join(H0, '..', 'ai', 'gen', 'bung3-end-gpt3.png')).astype(np.float32)
Cl = cv2.imread(os.path.join(H0, '..', 'ai', 'gen', 'bung3-clean.png'))
h, w = K.shape[:2]
Hg = np.load(os.path.join(OUT, 'bung3-clean-H.npy'))
B = cv2.warpPerspective(Cl, Hg, (w, h), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT).astype(np.float32)
cx0, cy0 = 900, 440
cw = cv2.imread(os.path.join(OUT, 'b3-cleanwarp.png')).astype(np.float32)
B[cy0:cy0 + cw.shape[0], cx0:cx0 + cw.shape[1]] = cw
# low frequency gain of B to K on the room (where both show the room)
X0, XR, Y0 = 980, 1785, 506
room = np.zeros((h, w), np.float32); room[Y0:920, X0:XR] = 1
num = cv2.GaussianBlur(K * room[..., None], (0, 0), 30); den = cv2.GaussianBlur(B * room[..., None], (0, 0), 30)
wv = cv2.GaussianBlur(room, (0, 0), 30)[..., None]
gain = np.clip(np.where(wv > 0.02, (num + 1) / (den + 1), 1.0), 0.85, 1.18)
B = B * gain
lab = lambda im: cv2.cvtColor(np.clip(im, 0, 255).astype(np.uint8), cv2.COLOR_BGR2LAB).astype(np.float32)
d = cv2.GaussianBlur(np.sqrt(((lab(K) - lab(B)) ** 2).sum(2)), (0, 0), 0.7)
hsv = cv2.cvtColor(np.clip(K, 0, 255).astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float32)
Hh, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
yy, xx = np.mgrid[0:h, 0:w]
# leaf colours: green/olive, dark stems, white/pale flowers (low saturation, bright) ; never the orange cushion
green_ = ((Hh >= 22) & (Hh <= 95) & (S > 45)) | (V < 75)
gnear = cv2.dilate(green_.astype(np.uint8), np.ones((13, 13), np.uint8)).astype(bool)
leaf = green_ | ((S < 60) & (V > 170) & gnear & (yy >= 990))      # pale flowers only among leaves, low in the planter
orange = (Hh < 20) & (S > 120)
leaf &= ~orange
zone = (xx >= X0 - 30) & (xx < XR + 30) & (yy >= 925)
# solid: the planter box and the dense foliage (as before, eroded so its edge goes to the soft matte)
dense = ((((Hh >= 22) & (Hh <= 95) & (S > 50)) | (V < 70)) & zone).astype(np.uint8)
dense = cv2.morphologyEx(dense, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
n, lbl, st, _ = cv2.connectedComponentsWithStats(dense, 8)
keep = np.zeros(n, bool)
for i in range(1, n):
    if st[i, cv2.CC_STAT_TOP] + st[i, cv2.CC_STAT_HEIGHT] >= 1125 and st[i, cv2.CC_STAT_AREA] > 2000:
        keep[i] = True
mass = keep[lbl] & (dense > 0)
solid = np.zeros((h, w), np.uint8)
for x in range(X0 - 30, XR + 30):
    col = np.nonzero(mass[:, x])[0]
    top = col[0] if len(col) else 1130
    solid[min(top, 1130) + 10:, x] = 1                # 10 px below the mass top: the top edge is soft
solid[1130:, X0 - 30:XR + 30] = 1
solid = cv2.erode(solid, np.ones((5, 5), np.uint8))
# soft leaves: how much the pixel departs from the room behind it, only for leaf coloured pixels near the planter
near = cv2.dilate(mass.astype(np.uint8), np.ones((121, 121), np.uint8)).astype(bool) & zone
soft = np.clip((d - 9.0) / 22.0, 0, 1) * (leaf & near)
soft = cv2.morphologyEx(soft, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
a = np.maximum(solid.astype(np.float32), soft)
# everything outside the opening is in front (facade, frames, the storeys above and below)
outside = np.ones((h, w), np.float32); outside[Y0:, X0:XR] = 0
frames = ((V < 95) & (xx >= 1594 - 6) & (yy >= Y0) & (yy < 1130)).astype(np.uint8)
frames = cv2.morphologyEx(frames, cv2.MORPH_OPEN, np.ones((25, 1), np.uint8))
rail = np.zeros((h, w), np.float32)
rail[908:915, X0:1594] = np.clip((d[908:915, X0:1594] - 8.0) / 20.0, 0, 1)      # the glass rail itself, exact (no sofa strip)
a = np.maximum.reduce([a, outside, cv2.dilate(frames, np.ones((1, 3), np.uint8)).astype(np.float32), rail])
a = np.clip(cv2.GaussianBlur(a, (0, 0), 0.6), 0, 1)
# room layer: B in the planter zone (no leaf anywhere), K above it
# the room: its own pixels above the foliage (per column, 45 px above the highest leaf), the clean plate
# below, with a soft vertical blend; no leaf can remain painted on the room
anyleaf = ((a > 0.03) | (green_ & near)) & (xx >= X0 - 30) & (xx < XR + 30) & (yy >= 900)
anyleaf = cv2.morphologyEx(anyleaf.astype(np.uint8), cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
topc = np.full(w, h, np.float32)
for x in range(X0 - 30, XR + 30):
    c_ = np.nonzero(anyleaf[925:, x])[0]
    topc[x] = 925 + c_[0] if len(c_) else 1135
from scipy.ndimage import minimum_filter1d
topc[X0 - 30:XR + 30] = minimum_filter1d(topc[X0 - 30:XR + 30], 61)
topc[X0 - 30:XR + 30] = cv2.GaussianBlur(topc[X0 - 30:XR + 30][None, :], (0, 0), sigmaX=20, sigmaY=0.01)[0] - 40
topc[1580:] = np.maximum(topc[1580:], 1005)        # behind the open door stack the console and vase stand above the leaves
zr = np.clip((yy - topc[None, :]) / 30.0, 0, 1).astype(np.float32)
zr[:, :X0 - 30] = 0; zr[:, XR + 30:] = 0
zr[905:918, X0:1594] = np.maximum(zr[905:918, X0:1594], 1.0)          # behind the glass rail
zr = cv2.GaussianBlur(zr, (0, 0), 2)[..., None]
R = K * (1 - zr) + B * zr
# foreground colour so that a*F + (1-a)*R == K exactly at frame 0
a3 = a[..., None]
F = np.where(a3 > 0.02, (K - (1 - a3) * R) / np.maximum(a3, 0.02), K)
F = np.clip(F, 0, 255)
cv2.imwrite(os.path.join(OUT, 'bung3-R.png'), np.clip(R + 0.5, 0, 255).astype(np.uint8))
cv2.imwrite(os.path.join(OUT, 'bung3-F.png'), np.dstack([np.clip(F + 0.5, 0, 255), a * 255 + 0.5]).astype(np.uint8))
comp = a3 * F + (1 - a3) * R
print('recompose MAD', float(np.abs(comp - K).mean()))
S_ = os.environ.get('PREV')
if S_:
    crop = (slice(860, 1200), slice(950, 1820))
    vis = (np.array([255, 0, 255]) * (1 - a3) + F * a3)[crop]
    cv2.imwrite(os.path.join(S_, 'b3v2-F.jpg'), vis.astype(np.uint8))
    cv2.imwrite(os.path.join(S_, 'b3v2-R.jpg'), np.clip(R[crop], 0, 255).astype(np.uint8))
