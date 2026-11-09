"""Bungalow 3: foliage matte from the end image vs the clean plate aligned to it by dense optical flow
(the GPT plate redraws the sofa and rug a few px off; the flow absorbs that, it cannot invent leaves)."""
import os, cv2, numpy as np
H0 = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(H0, 'out')
K = cv2.imread(os.path.join(H0, '..', 'ai', 'gen', 'bung3-end-gpt3.png'))
Cl = cv2.imread(os.path.join(H0, '..', 'ai', 'gen', 'bung3-clean.png'))
h, w = K.shape[:2]
Hg = np.load(os.path.join(OUT, 'bung3-clean-H.npy'))
Clr = cv2.warpPerspective(Cl, Hg, (w, h), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
x0, x1, y0, y1 = 900, 1840, 440, 1300            # the opening and its planter
kc, cc = K[y0:y1, x0:x1], Clr[y0:y1, x0:x1]
g = lambda im: cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
dis.setPatchSize(16); dis.setPatchStride(4); dis.setGradientDescentIterations(25); dis.setVariationalRefinementAlpha(40)
fl = dis.calc(g(kc), g(cc), None)                  # for each end image px, where it is in the clean plate
# trust the flow only where the room is visible (above the planter, no foliage colours); elsewhere fill it
# smoothly from there (normalized convolution): the plate is never bent to imitate leaves
hsv = cv2.cvtColor(kc, cv2.COLOR_BGR2HSV).astype(np.float32)
fol = (((hsv[..., 0] >= 22) & (hsv[..., 0] <= 95) & (hsv[..., 1] > 45)) | (hsv[..., 2] < 75))
fol = cv2.dilate(fol.astype(np.uint8), np.ones((25, 25), np.uint8)).astype(bool)
ok = (~fol).astype(np.float32)
ok[(np.arange(kc.shape[0]) + y0 > 935)[:, None].repeat(kc.shape[1], 1)] = 0
num = np.dstack([cv2.GaussianBlur(fl[..., c] * ok, (0, 0), 25) for c in range(2)])
den = cv2.GaussianBlur(ok, (0, 0), 25)[..., None]
fill = num / np.maximum(den, 1e-4)
num2 = np.dstack([cv2.GaussianBlur(fl[..., c] * ok, (0, 0), 3) for c in range(2)]); den2 = cv2.GaussianBlur(ok, (0, 0), 3)[..., None]
loc = num2 / np.maximum(den2, 1e-4)
wl = np.clip(den2 * 3, 0, 1)
fl = (loc * wl + fill * (1 - wl)).astype(np.float32)
# below the visible room the fill holds the last good row (nothing to match there)
ylast = 935 - y0
mean = np.array([np.sum(fl[..., c] * ok) / max(1.0, ok.sum()) for c in range(2)], np.float32)
row = fl[ylast - 1].copy()
for yy_ in range(ylast, fl.shape[0]):
    k = min(1.0, (yy_ - ylast) / 45.0)
    fl[yy_] = row * (1 - k) + mean * k                 # below the visible room: a rigid shift (no bent lines)
yy, xx = np.mgrid[0:kc.shape[0], 0:kc.shape[1]].astype(np.float32)
cw = cv2.remap(cc, xx + fl[..., 0], yy + fl[..., 1], cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
lab = lambda im: cv2.cvtColor(im, cv2.COLOR_BGR2LAB).astype(np.float32)
d = np.sqrt(((lab(kc) - lab(cw)) ** 2).sum(2))
np.save(os.path.join(OUT, 'b3-flowdiff.npy'), d); cv2.imwrite(os.path.join(OUT, 'b3-cleanwarp.png'), cw)
S = os.environ['PREV']
v = np.clip(d * 4, 0, 255).astype(np.uint8)
cv2.imwrite(os.path.join(S, 'b3-flowdiff.jpg'), cv2.resize(np.hstack([kc, cv2.cvtColor(v, cv2.COLOR_GRAY2BGR)]), None, fx=0.6, fy=0.6))
print('done', d.mean())
