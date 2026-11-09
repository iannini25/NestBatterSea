"""Bungalow 3 layers v3. Principle: F holds ONLY what is really in front (facade, jambs, rail, planter, leaves) and
R holds ONLY the room, with no copy of anything in F. R = the end image K wherever K shows the room; everything K
hides (behind the leaves, the rail, the jambs, the header) is the rigid clean plate, gradient-domain blended to K so
no seam exists, plus plain continuations of ceiling, floor and door stack where the plate has none.
Frame 0 recomposes to K: F = (K - (1 - a) R) / a."""
import os, cv2, numpy as np
from scipy.ndimage import minimum_filter1d, median_filter, gaussian_filter1d
from scipy import sparse
from scipy.sparse.linalg import splu

H0 = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(H0, 'out')
K = cv2.imread(os.path.join(H0, '..', 'ai', 'gen', 'bung3-end-gpt3.png')).astype(np.float32)
Cl = cv2.imread(os.path.join(H0, '..', 'ai', 'gen', 'bung3-clean.png'))
h, w = K.shape[:2]
Hg = np.load(os.path.join(OUT, 'bung3-clean-H.npy'))
yy, xx = np.mgrid[0:h, 0:w]
yy = yy.astype(np.float32); xx = xx.astype(np.float32)
PREV = os.environ.get('PREV')

# geometry of the opening, in end image px
XL, XJ, XS, YT = 975, 1757, 1795, 512       # room starts right of XL, the front jamb starts at XJ, its outer edge XS, ceiling below YT
ZX0, ZX1 = XL, XJ                           # planter zone inside the opening
RY0, RY1 = 908, 915                         # glass rail band
YFLOOR = 1186                               # the plate shows floor down to here (then the sill)
RAILC = 911.5

# the balustrade glass below the rail veils the dark door stack (measured on flat surfaces: stack 11 -> 40, vase and sofa
# nearly unchanged). It belongs to the front layer: Ku is the clear view behind it, a uniform tinted pane restores K at frame 0
VEIL_A, VEIL_C = 0.26, np.array([109.0, 150.0, 198.0], np.float32)
wveil = np.clip((xx - 1560) / 40.0, 0, 1) * (yy >= 916) * (xx < XS + 3) * (xx >= ZX0)
agl = (VEIL_A * wveil).astype(np.float32)
Ku = np.clip((K - agl[..., None] * VEIL_C) / (1 - agl[..., None]), 0, 255)

# 1. rigid clean plate (never bent by dense flow), corrected only by a gentle 1D horizontal fit of the sofa zone
Clr = cv2.warpPerspective(Cl, Hg, (w, h), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT).astype(np.float32)
g8 = lambda im: cv2.cvtColor(np.clip(im, 0, 255).astype(np.uint8), cv2.COLOR_BGR2GRAY)
lab = lambda im: cv2.cvtColor(np.clip(im, 0, 255).astype(np.uint8), cv2.COLOR_BGR2LAB).astype(np.float32)
Lk = lab(K)
A_ = Lk[..., 1] - 128.0; B_ = Lk[..., 2] - 128.0; L_ = Lk[..., 0] * 100.0 / 255.0
hsv = cv2.cvtColor(np.clip(K, 0, 255).astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float32)
Hh, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
# leaf colours: anything green, dark olive stems; never the orange cushion or the brown table
leafy_ = (A_ < -3.5) | ((A_ < 3) & (L_ < 28) & (yy > 1000) & (xx < 1590)) | ((Hh >= 20) & (Hh <= 42) & (S > 105) & (yy > 985) & (A_ < 6) & (L_ > 45))
leafy_ &= ~((Hh < 18) & (S > 110))
dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
dis.setPatchSize(24); dis.setPatchStride(6); dis.setVariationalRefinementAlpha(60)
xa, xb, ya, yb = 985, 1590, 920, 1000
fl = dis.calc(g8(K[ya:yb, xa:xb]), g8(Clr[ya:yb, xa:xb]), None)
ok = ~cv2.dilate(leafy_[ya:yb, xa:xb].astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool)
dx = np.zeros(w, np.float32); dy = float(np.median(fl[..., 1][ok]))
for x in range(xa, xb):
    c = ok[:, x - xa]
    dx[x] = np.median(fl[c, x - xa, 0]) if c.sum() > 5 else np.nan
xs = np.arange(w)
good = ~np.isnan(dx) & (xs >= xa) & (xs < xb)
dx = np.interp(xs, xs[good], dx[good]).astype(np.float32)
dx = gaussian_filter1d(median_filter(dx, 31), 14).astype(np.float32)
fade = np.clip((xs - 980) / 30.0, 0, 1) * np.clip((1600 - xs) / 40.0, 0, 1)
dx *= fade
yfade = np.clip((yy - 890) / 30.0, 0, 1)
print('plate fit: dy', round(dy, 2), 'dx range', float(dx.min()), float(dx.max()))
xshift = 10.0 * np.clip((882 - xx) / 28.0, 0, 1)         # the plate's curtain edge sits just outside the final view
G = cv2.remap(Clr, xx + dx[None, :] * yfade + xshift, yy + dy * yfade, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
# the console and door stack foot of the plate, registered to K rigidly on the visible rows of the console
best = (0.0, 2.0, -5.0)                 # measured from the console's top front edge and front corner in K and in the plate
wc_ = (np.clip((xx - 1590) / 18.0, 0, 1) * np.clip((yy - 950) / 14.0, 0, 1) * np.clip((1122 - yy) / 26.0, 0, 1)).astype(np.float32)   # the console only, never the rug
G = cv2.remap(G, (xx - wc_ * best[1]).astype(np.float32), (yy - wc_ * best[2]).astype(np.float32), cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
# the plate has no door stack behind the console: its foot continues down from K's visible rows to the floor line
foot_col = np.median(Ku[972:990, 1595:1632], axis=0)
for y in range(1004, 1030):
    G[y, 1595:1632] = foot_col
# global colour match of the plate to K on the room that both show
room = (xx > XL + 40) & (xx < 1590) & (yy > YT + 8) & (yy < 900)
gain = np.median(K[room], axis=0) / np.maximum(np.median(G[room], axis=0), 1.0)
print('plate gain', gain)
G = G * gain.reshape(1, 1, 3)
# the plate ends in the curtain at the far left only outside the final view (fine) and in the sill below YFLOOR: mirror the floor
for y in range(YFLOOR, h):
    p_ = (y - YFLOOR) % 96                  # reflect within the plank rows just above the sill (no rug)
    G[y] = G[YFLOOR - 2 - (p_ if p_ < 48 else 95 - p_)]
# the right side wall of the plate is not this room: down the jamb, K's own columns continue to the floor line
yc = 965
G[YT:yc, XJ - 8:XS + 3] = Ku[YT:yc, XJ - 8:XS + 3]
for x in range(XJ, XS + 3):
    G[yc:, x] = Ku[yc, x]
# plate reference (R so far) for the matte
Bref = G.copy()

# 2. solid part of the front layer
dLab = np.sqrt(((Lk - lab(Bref)) ** 2).sum(2))
zone = (xx >= ZX0) & (xx < ZX1) & (yy >= 920) & (yy < 1165)
zone &= ~((xx >= 1470) & (xx < 1600) & (yy < 998))          # the room's own potted tree is never front layer
leafy = leafy_ & zone
leafy8 = leafy.astype(np.uint8)
dens = cv2.GaussianBlur(leafy.astype(np.float32), (0, 0), 5)
ysolid = np.full(w, 1136, np.float32)
for x in range(ZX0, ZX1):
    col = dens[920:1136, x]
    ys = np.nonzero(col > 0.6)[0]
    ysolid[x] = 920 + ys[0] if len(ys) else 1130
ysolid[ZX0:ZX1] = gaussian_filter1d(median_filter(ysolid[ZX0:ZX1], 25), 4)
solid = (yy >= ysolid[None, :].astype(np.float32) + 28) & (xx >= ZX0) & (xx < ZX1)
solid[1120:, ZX0 - 6:ZX1] = True            # planter box, slab
# 3. leaves above the solid line: per pixel alpha from K over the plate, colours taken from the leaves themselves
# seeds: leaf colours connected to the mass (hysteresis) so stems survive and stray specks in the room do not
near = cv2.dilate(leafy8, np.ones((9, 9), np.uint8)).astype(bool)
# dark stems/edges that are darker than the room, not the door stack
dark_ = (dLab > 13) & (K.sum(2) < Bref.sum(2) - 30) & (yy > 925) & (A_ < 6)
dark_ &= ~(xx >= 1590)
tbl = np.zeros((h, w), np.uint8)
cv2.fillPoly(tbl, [np.array([[1248, 980], [1349, 976], [1420, 1000], [1441, 1060], [1380, 1062], [1250, 1046]], np.int32)], 1)
cv2.rectangle(tbl, (1160, 985), (1245, 1036), 1, -1)
cush = (xx >= 973) & (xx < 1014) & (yy >= 899) & (yy < 932)
# flowers and pale leaf debris: unlike the plate, close to the leaves and close to the planter
# flowers and pale blossoms: unlike the plate, white rather than cream, among the leaves and low in the planter
pale_ = (dLab > 15) & near & (S < np.where(xx >= 1590, 100, 60)) & (V > 150) & (yy > 1000) & (tbl == 0)
nc_, lc_, sc_, _ = cv2.connectedComponentsWithStats(pale_.astype(np.uint8), 8)
pale_ = (sc_[:, cv2.CC_STAT_AREA] <= 220)[lc_] & pale_
lo = (leafy | dark_ | pale_) & zone & ~((xx >= 1590) & (xx < 1640) & (yy < 1050))
# thin stems: grown through pixels that are clearly darker than the room, a few steps from the leaves
thin = (K.sum(2) < Bref.sum(2) - 14) & (A_ < 10) & zone & (tbl == 0) & (xx < 1590)
frond2 = ((Hh >= 20) & (Hh <= 42) & (S > 80) & (dLab > 10) & (yy > 1000) & (xx >= 1590) & zone) | ((xx >= 1695) & (yy >= 1008) & (dLab > 11) & (S < 100) & (V > 150) & zone)
lo = lo | frond2
stem_y = (xx >= 1590) & (yy >= 995) & (yy < 1062) & (dLab > 12) & (K.sum(2) > Bref.sum(2) + 20) & (Hh >= 18) & (Hh <= 45) & zone
thin = thin | stem_y
lo8 = lo.astype(np.uint8)
for _i in range(24):
    lo8 = cv2.dilate(lo8, np.ones((3, 3), np.uint8)) & (thin | lo).astype(np.uint8)
lo = lo8.astype(bool)
n, lbl, st, _ = cv2.connectedComponentsWithStats(lo.astype(np.uint8), 8)
touch = np.zeros(n, bool)
touch[np.unique(lbl[solid & lo])] = True
area_keep = st[:, cv2.CC_STAT_AREA] >= 4
touch[0] = False
keep = touch | area_keep
keep[0] = False
strict_ = (A_ < -1) | (K.sum(2) < Bref.sum(2) - 40)
leaf_final = keep[lbl] & lo & ~((tbl > 0) & ~strict_)
for i_ in range(1, n):
    if (st[i_, cv2.CC_STAT_AREA] < 70 or (st[i_, cv2.CC_STAT_LEFT] >= 1590 and st[i_, cv2.CC_STAT_AREA] < 420)) and st[i_, cv2.CC_STAT_TOP] + st[i_, cv2.CC_STAT_HEIGHT] < (ysolid[st[i_, cv2.CC_STAT_LEFT]] - 12):
        m_ = lbl == i_
        if float(A_[m_].mean()) > -2.5 or (st[i_, cv2.CC_STAT_LEFT] >= 1590):
            leaf_final[m_] = False
leaf_core = leaf_final.astype(np.uint8)
dist, labels = cv2.distanceTransformWithLabels(1 - leaf_core, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
pts = np.argwhere(leaf_core > 0)
lab_map = np.zeros(pts.shape[0] + 2, np.int32)
lab_map[labels[pts[:, 0], pts[:, 1]]] = np.arange(pts.shape[0])
idx = lab_map[labels]
Fc = K[pts[idx, 0], pts[idx, 1]]
Fc = cv2.blur(Fc, (5, 5))
num = ((K - Bref) * (Fc - Bref)).sum(2); den = ((Fc - Bref) ** 2).sum(2) + 80.0
aest = np.clip(num / den, 0, 1)
band = cv2.dilate(leaf_core, np.ones((5, 5), np.uint8)).astype(bool) & zone & ~((tbl > 0) & ~strict_)
a_leaf = np.where(band, np.clip((aest - 0.18) / 0.62, 0, 1), 0.0).astype(np.float32)
a_leaf[leaf_final & (aest > 0.5)] = 1.0
foot_ = (xx >= 1590) & (xx < 1645) & (yy < 1032) & (A_ > -3.5)
a_leaf[foot_] = 0
a_leaf = np.maximum(a_leaf, solid.astype(np.float32))
a_leaf = cv2.GaussianBlur(a_leaf, (0, 0), 0.5)

# 4. facade: everything outside the opening, the header, the jambs
outside = np.zeros((h, w), np.float32)
outside[:YT, :] = 1
outside[:, :XL] = 1
outside[:, XJ:] = 1
outside = np.clip(cv2.GaussianBlur(outside, (0, 0), 0.6) * 1.0, 0, 1)
# 5. the rail: its rows
ar = np.zeros((h, w), np.float32)
prof = {908: 0.2, 909: 1, 910: 1, 911: 1, 912: 1, 913: 1, 914: 1, 915: 0.2}
for y_, v_ in prof.items():
    ar[y_, ZX0:ZX1] = v_
# the rail as a uniform metal cap: per row the median colour along the opening (K's rail carries sofa colour stripes)
rail_rows = sorted(prof)
rc = {}
for y_ in rail_rows:
    rc[y_] = np.stack([median_filter(K[y_, :, c], size=321, mode='nearest') for c in range(3)], 1)
base_ = rc[912]; bm_ = base_.mean(1, keepdims=True)
for y_ in rail_rows:
    rc[y_] = base_ * (rc[y_].mean(1, keepdims=True) / np.maximum(bm_, 1.0))
rc[908] = rc[909]; rc[915] = rc[914]
for y_ in rail_rows:
    loc_ = np.stack([median_filter(K[y_, :, c], size=25, mode='nearest') for c in range(3)], 1)
    w_rc = np.clip((xx[0] - (XJ - 110)) / 100.0, 0, 1)[:, None]
    rc[y_] = rc[y_] * (1 - w_rc) + loc_ * w_rc
a = np.maximum.reduce([a_leaf, outside, ar])
a_g = np.where((yy >= 916) & (yy < 1136) & (xx >= ZX0) & (xx < ZX1), agl, 0).astype(np.float32)
a = np.maximum(a, a_g)

Y1d0 = 1300
# 6. hole of the room layer: everything hidden by the front layer, plus the table fragments K shows between the leaves
table = tbl
hole = (np.maximum(a_leaf, outside) > 0.01) | (table > 0) | cush | (lo & zone & ~foot_)
hole = cv2.dilate(hole.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
hole[yc:Y1d0, XJ - 1:XS + 3] = True
hole[1004:Y1d0, 1590:XJ] = True           # the console below its visible rows: plate only, no flower or leaf pixels of K
# solve the room's hole in the gradient domain: inside the hole R = G + D, D harmonic with D = K - G on the visible room
X0d, X1d, Y0d, Y1d = 540, 1802, YT, 1300
G2 = G.copy()
hole2 = hole.copy()
sub = (slice(Y0d, Y1d), slice(X0d, X1d))
mask = hole2[sub].copy()
mask[0, :] = mask[-1, :] = False; mask[:, 0] = mask[:, -1] = False
rows, cols = np.nonzero(mask)
nidx = -np.ones(mask.shape, np.int32); nidx[rows, cols] = np.arange(len(rows))
print('hole px', len(rows))
D_b = (Ku - G2)[sub]
D_b[0, :] = 0; D_b[-1, :] = 0; D_b[:, 0] = 0; D_b[:, -1] = 0   # the outer border keeps the plate as is
Dout = np.zeros(D_b.shape, np.float32)
r_, c_, v_ = [], [], []
ii = np.arange(len(rows))
r_.append(ii); c_.append(ii); v_.append(np.full(len(rows), 4.0))
for dy_, dx_ in ((1, 0), (-1, 0), (0, 1), (0, -1)):
    nr, nc = rows + dy_, cols + dx_
    nk = nidx[nr, nc]
    m_ = nk >= 0
    r_.append(ii[m_]); c_.append(nk[m_]); v_.append(np.full(m_.sum(), -1.0))
A = sparse.csc_matrix((np.concatenate(v_), (np.concatenate(r_), np.concatenate(c_))), shape=(len(rows), len(rows)))
lu = splu(A)
for ch in range(3):
    b = np.zeros(len(rows), np.float64)
    for dy_, dx_ in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nr, nc = rows + dy_, cols + dx_
        ext = nidx[nr, nc] < 0
        b[ii[ext]] += D_b[nr[ext], nc[ext], ch]
    x_ = lu.solve(b)
    sign_ = np.sign(x_); mag_ = np.abs(x_)
    x_ = np.where(cols + X0d < 1590, sign_ * np.where(mag_ > 18, 18 + 0.4 * (mag_ - 18), mag_), x_)
    Dout[rows, cols, ch] = x_
R = Ku.copy()
Ro = R[sub]
Rs = G2[sub] + Dout
Ro[mask] = Rs[mask]
R[sub] = Ro
# inside the visible room, close to the planter, K fades into the solved room over 34 px: no leaf shaped seam of texture
dt = cv2.distanceTransform((~hole).astype(np.uint8), cv2.DIST_L2, 5)
w_ = np.clip(1 - dt / 34.0, 0, 1) ** 1.5
w_ = (w_ * (yy > 925) * (xx < 1590) * (xx > XL + 1)).astype(np.float32)[..., None]
Rf = (G2[sub] + cv2.GaussianBlur((Ku[sub] - G2[sub]) * (~mask)[..., None], (0, 0), 9) / np.maximum(cv2.GaussianBlur((~mask).astype(np.float32), (0, 0), 9), 0.15)[..., None])
Rf = np.where(mask[..., None], Rs, Rf)
R[sub] = R[sub] * (1 - w_[sub]) + Rf * w_[sub]
R[YT, :XL + 3] = R[YT + 1, :XL + 3]; R[Y1d - 1] = R[Y1d - 2]
R[1004:1030, 1595:1632] = foot_col                # door stack foot, K's own colours (not offset by the solve)
# 6b. the rail band (rows 908..915): the room just above and below it, interpolated across the 8 rows
for i_, y in enumerate(range(RY0, RY1 + 1)):
    t_ = (i_ + 1.0) / (RY1 - RY0 + 2)
    t_ = t_ * t_ * (3 - 2 * t_)
    top_ = R[2 * RY0 - 1 - y].copy(); bot_ = R[2 * RY1 + 1 - y].copy()
    R[y, ZX0 - 2:XS + 3] = (top_ * (1 - t_) + bot_ * t_)[ZX0 - 2:XS + 3]
# 7. continuations the plate cannot give: outside the Poisson domain
# ceiling above YT: the room's ceiling continues, mirrored (more of the same ceiling with its recessed lights), then held
Ry = R.copy()
band_ = cv2.morphologyEx(Ry[YT:YT + 84], cv2.MORPH_OPEN, np.ones((41, 41), np.uint8))
band_[:, :985] = band_[:, 985:1000].mean(1, keepdims=True)
band_ = cv2.GaussianBlur(band_, (0, 0), 6)
for y in range(0, YT):
    d_ = YT - y
    src = min(d_ + 6, 82) if d_ <= 90 else max(82 - (d_ - 90) // 3, 8)
    R[y, :1800] = band_[min(src, 83), :1800]
R[:YT, 1588:1800] = R[:YT, 1586:1588].mean(1, keepdims=True)
R[:YT, :1800] = cv2.GaussianBlur(R[:YT, :1800], (0, 0), sigmaX=2, sigmaY=8)
# the door stack continues beyond the jamb towards the camera: its own panels mirrored, with the top line of the stack
# rising and the bottom line falling like in the end image (one flat plane, seen only while the jamb passes)
Rsrc = R.copy()
srcx0, srcx1 = 1640, 1755
ytop_s = lambda x: 492 + 0.605 * (1757 - x)
ybot_s = lambda x: 1120 - 0.57 * (1775 - x)
ytop_d = lambda x: 492 - 0.605 * (x - XS)
ybot_d = lambda x: 1118 + 0.57 * (x - XS)
mapx = np.zeros((h, w - XS), np.float32); mapy = np.zeros((h, w - XS), np.float32)
ws = srcx1 - srcx0
xs_ = np.arange(XS, w).astype(np.float32)
u = (xs_ - XS) / 1.45
tri_ = np.where((u % (2 * ws)) < ws, u % (2 * ws), 2 * ws - (u % (2 * ws)))        # triangle wave through the panels
xsrc = srcx1 - tri_
for i_, x in enumerate(range(XS, w)):
    xr = xsrc[i_]
    v = (np.arange(h) - ytop_d(x)) / max(1.0, ybot_d(x) - ytop_d(x))
    yv_ = ytop_s(xr) + v * (ybot_s(xr) - ytop_s(xr))
    span_ = 2.0 * (858.0 - 520.0)
    pv_ = np.mod(yv_ - 520.0, span_)
    mapy[:, i_] = 520.0 + np.minimum(pv_, span_ - pv_)           # never the console or the vase
    mapx[:, i_] = xr
S_ext = cv2.remap(Rsrc, mapx, mapy, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
lum = S_ext.mean(2, keepdims=True); blue = (S_ext[..., 0:1] > lum[..., 0:1] * 1.08).astype(np.float32)
lum3 = np.repeat(lum, 3, 2) * np.array([0.92, 0.97, 1.0], np.float32)
S_ext = S_ext * 0.45 + lum3 * 0.55
S_ext = S_ext * (1 - blue * 0.6) + np.dstack([lum[..., 0] * 0.92, lum[..., 0] * 0.97, lum[..., 0]]) * blue * 0.6   # no sky blue through the panels
R[:, XS:] = S_ext
floor_ref = np.median(Clr[1150:1180, 1100:1700], axis=(0, 1))
for x in range(XS, w):
    ty, by = int(ytop_d(x)), int(ybot_d(x))
    if ty > 0:
        R[:ty, x] = R[:ty, XS - 1]
    if by < h:
        fl_y = (np.arange(by, h) - by) % 16
        fl_x = (x - XS) % 560
        R[by:, x] = G[1168 + fl_y, 1180 + fl_x]
R = np.clip(R, 0, 255)

# 8. front colour: frame 0 == K. Low alpha pixels use the leaf colour itself (no room colour in the fringe)
a3 = a[..., None]
Fexact = np.where(a3 > 0.02, (K - (1 - a3) * R) / np.maximum(a3, 0.02), K)
F = np.clip(Fexact, 0, 255)
# decontaminate the semi transparent fringes of the leaves
mix = np.clip((0.85 - a) / 0.45, 0, 1)[..., None] * (band | leaf_final).astype(np.float32)[..., None]
F = F * (1 - mix) + Fc * mix
F[a <= 0.02] = K[a <= 0.02]
F = np.where((a3 >= 0.999), K, F)
pg = (a_g > 0.01) & (a_leaf < 0.02) & (ar < 0.02) & (outside < 0.02)
F[pg] = VEIL_C
for y_ in rail_rows:
    F[y_, ZX0:ZX1] = rc[y_][ZX0:ZX1]
cv2.imwrite(os.path.join(OUT, 'bung3-R.png'), np.clip(R + 0.5, 0, 255).astype(np.uint8))
cv2.imwrite(os.path.join(OUT, 'bung3-F.png'), np.dstack([np.clip(F + 0.5, 0, 255), a * 255 + 0.5]).astype(np.uint8))
comp = a3 * F + (1 - a3) * R
e = np.abs(comp - K)
print('recompose MAD all', float(e.mean()), 'in 4 row crop', float(e[4:-4].mean()), 'max', float(e.max()))
if PREV:
    crop = (slice(460, 1300), slice(800, 1950))
    vis = (np.array([255, 0, 255]) * (1 - a3) + F * a3)[crop]
    cv2.imwrite(os.path.join(PREV, 'b3v3-F.png'), vis.astype(np.uint8))
    cv2.imwrite(os.path.join(PREV, 'b3v3-R.png'), np.clip(R[crop], 0, 255).astype(np.uint8))
    cv2.imwrite(os.path.join(PREV, 'b3v3-a.png'), (a[crop] * 255).astype(np.uint8))
    cv2.imwrite(os.path.join(PREV, 'b3v3-comp.png'), np.clip(comp[crop], 0, 255).astype(np.uint8))
    cv2.imwrite(os.path.join(PREV, 'b3v3-Rbig.jpg'), cv2.resize(np.clip(R, 0, 255).astype(np.uint8), None, fx=.6, fy=.6))
