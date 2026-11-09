"""LOFT 4: layers of the end image (2688 x 1520, ai/gen/loft4-end-gpt.png).
F = the end image except the room seen through the glass: facade, window frame, mullions, transom,
    the olive tree, the parasol, the balcony lamp, the planters and the balustrade's top rail.
R = the room: the clean plate (same view, foreground removed), registered on the end image. The room
    is this one image everywhere (the flight shows it through the glass from the start), so nothing
    in the room ever changes."""
import os, cv2, numpy as np
H0 = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(H0, 'out')
K = cv2.imread(os.path.join(H0, '..', 'ai', 'gen', 'loft4-end-gpt.png'))
Cl = cv2.imread(os.path.join(H0, '..', 'ai', 'gen', 'loft4-clean.png'))
h, w = K.shape[:2]
Hg = np.load(os.path.join(OUT, 'loft4-clean-H.npy'))
R = cv2.warpPerspective(Cl, Hg, (w, h), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
s = 2                                               # zones are given in 1344 px coordinates
hsv = cv2.cvtColor(K, cv2.COLOR_BGR2HSV).astype(np.float32)
Hh, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
yy, xx = np.mgrid[0:h, 0:w]
WX0, WX1, WY0, WY1 = 326 * s, 970 * s, 132 * s, 668 * s           # glass area inside the outer frame
glass = (xx >= WX0) & (xx < WX1) & (yy >= WY0) & (yy < WY1)
# mullions and transom: dark thin straight members
g = cv2.cvtColor(K, cv2.COLOR_BGR2GRAY).astype(np.float32)
colv = np.median(g[WY0 + 8:178 * s, :], axis=0)                     # ceiling strip above the mezzanine slats
rowv = np.median(g[:, WX0 + 900:WX1 - 40], axis=1)                  # right part, beside the tree
loc = cv2.GaussianBlur(colv[None, :], (0, 0), 25)[0]
mull_cols = (colv < loc - 25) & (xx[0] >= WX0 - 10) & (xx[0] < WX1 + 10)
locr = cv2.GaussianBlur(rowv[:, None], (0, 0), 25)[:, 0]
trans_rows = (rowv < locr - 45) & (np.arange(h) > 880) & (np.arange(h) < 940)
mull = np.zeros((h, w), np.uint8)
mull[:, mull_cols] = 1
mull[trans_rows, :] = 1
mull &= glass.astype(np.uint8)
mull = cv2.dilate(mull, np.ones((3, 3), np.uint8))
# balcony things (zones), detected as dark or green, closed into solid shapes
zones = np.zeros((h, w), bool)
for x0, y0, x1, y1 in [(360, 296, 772, 668),     # olive tree
                       (655, 498, 930, 566),     # parasol canopy
                       (780, 520, 812, 668),     # parasol pole
                       (476, 580, 528, 668),     # balcony lamp
                       (320, 596, 1030, 672)]:   # planters
    zones[y0 * s:y1 * s, x0 * s:x1 * s] = True
greenish = (Hh >= 24) & (Hh <= 95) & (S > 55)
treez = np.zeros((h, w), bool); treez[296 * s:596 * s, 360 * s:772 * s] = True
plz = np.zeros((h, w), bool); plz[600 * s:668 * s, 320 * s:1030 * s] = True
plz[590 * s:632 * s, 676 * s:714 * s] = False                    # the vase on the dining table is inside
veg = (greenish & zones) | (treez & (V < 110)) | (plz & (V < 150) & (S > 40))
veg = cv2.morphologyEx(veg.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
veg = cv2.morphologyEx(veg, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
n, lbl, st, _ = cv2.connectedComponentsWithStats(veg, 8)
for i in range(1, n):
    if st[i, cv2.CC_STAT_AREA] < 60: veg[lbl == i] = 0
# the lamp's lit head and the parasol canopy are solid
lamp = np.zeros((h, w), np.uint8); cv2.ellipse(lamp, (502 * s, 600 * s), (12 * s, 7 * s), 0, 0, 360, 1, -1)
canopy = np.zeros((h, w), np.uint8)
cv2.ellipse(canopy, (793 * s, 530 * s), (127 * s, 24 * s), 0, 180, 360, 1, -1)
canopy[530 * s:552 * s, 666 * s:920 * s] |= ((V[530 * s:552 * s, 666 * s:920 * s] < 120)).astype(np.uint8)
rail = np.zeros((h, w), np.uint8); rail[569 * s:576 * s, WX0:1024 * s] = 1        # balustrade top rail
fg = (~glass).astype(np.uint8) | mull | veg | lamp | (canopy & zones) | rail
fga = cv2.GaussianBlur(fg.astype(np.float32), (0, 0), 0.9)
cv2.imwrite(os.path.join(OUT, 'loft4-F.png'), np.dstack([K, (fga * 255).astype(np.uint8)]))
# the room beyond the window's edges (seen through the glass at an angle): its own edges continued
# (ceiling up, floor down, side walls), never the facade around the window
box = R[WY0 + 4:WY1 - 4, WX0 + 4:WX1 - 4]
ext = cv2.copyMakeBorder(box, WY0 + 4, h - (WY1 - 4), WX0 + 4, w - (WX1 - 4), cv2.BORDER_REPLICATE)
ext = cv2.GaussianBlur(ext, (0, 0), 6)
inner = np.zeros((h, w), np.float32); inner[WY0 + 4:WY1 - 4, WX0 + 4:WX1 - 4] = 1
inner = cv2.GaussianBlur(inner, (0, 0), 3)[..., None]
R = (R * inner + ext * (1 - inner)).astype(np.uint8)
cv2.imwrite(os.path.join(OUT, 'loft4-R.png'), R)
S_ = os.environ.get('PREV')
if S_:
    comp = (K.astype(np.float32) * fga[..., None] + R.astype(np.float32) * (1 - fga[..., None])).astype(np.uint8)
    cv2.imwrite(os.path.join(S_, 'loft4-comp.jpg'), cv2.resize(comp, (1344, 760), interpolation=cv2.INTER_AREA))
    v = K.copy(); m = (fg.astype(bool) & glass); v[m] = (v[m] * 0.4 + np.array([255, 0, 255]) * 0.6).astype(np.uint8)
    cv2.imwrite(os.path.join(S_, 'loft4-matte.jpg'), cv2.resize(v, (1344, 760), interpolation=cv2.INTER_AREA))
print('mullion columns', int(mull_cols.sum()), 'transom rows', np.nonzero(trans_rows)[0].tolist())
