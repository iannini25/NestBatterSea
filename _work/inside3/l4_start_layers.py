"""LOFT 4: the two layers as seen by the flight's END camera (the start view of the Step inside), at
2560 x 1440 (F, R) and 5120 x 2880 (R2, from the upscaled room), so the Step inside starts exactly on
the flight's last frame. Uses the same scene as flight/render_full.py."""
import os, sys, argparse, cv2, numpy as np
H0 = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(H0, '..', 'flight')); os.chdir(os.path.join(H0, '..', 'flight'))
import render_full as RF, proxy as X
a = argparse.Namespace(home='loft4', key='../ai/gen/loft4-end-gpt.png', reg='out/hybrid/loft4-key-A.npy', end_scale=0.92, feather=0.035,
                       light=(0.0, 0.12), glow_fade=(1.0, 0.45), ease='smoother', layers='../inside3/out/loft4', room_depth=25.0)
f = RF.Flight(a)
end = f.cam(1.0)
print('end cam f', end.f, 'w', end.w, 'D', f.p.D1)
OUTD = os.path.join(H0, 'out')
F = cv2.imread(os.path.join(OUTD, 'loft4-F.png'), cv2.IMREAD_UNCHANGED)
R = cv2.imread(os.path.join(OUTD, 'loft4-R.png'))
hi = cv2.imread(os.path.join(OUTD, 'loft4-Rcrop-4k.png'))
T = lambda k: np.array([[1, 0, 0.5], [0, 1, 0.5], [0, 0, 1.0]]) @ np.diag([1 / k, 1 / k, 1]) @ np.array([[1, 0, -0.5], [0, 1, -0.5], [0, 0, 1.0]])
for k, tag in ((2560 / end.w, ''), (5120 / end.w, '2')):
    c = end.scaled(k)
    Hf, _ = X.h_plane(c, X.INLAY['plane'])
    Hk = X.INLAY['K'] @ Hf                                  # out px -> end image px (F)
    Hr = X._room_h(c, X.INLAY['room'])                       # out px -> end image px (R)
    if tag == '':
        Fo = cv2.warpPerspective(F, Hk, (c.w, c.h), flags=cv2.INTER_AREA | cv2.WARP_INVERSE_MAP if False else cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)
        Ro = cv2.warpPerspective(R, Hr, (c.w, c.h), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)
        cv2.imwrite(os.path.join(OUTD, 'loft4s-F.png'), Fo); cv2.imwrite(os.path.join(OUTD, 'loft4s-R.png'), Ro)
    else:
        # the room at twice the density: the upscaled room (crop x 640..1960, y 250..1360 of the end image)
        sx, sy = hi.shape[1] / 1320.0, hi.shape[0] / 1110.0
        Ah = np.array([[sx, 0, -640 * sx], [0, sy, -250 * sy], [0, 0, 1.0]])
        Rh = cv2.warpPerspective(hi, Ah @ Hr, (c.w, c.h), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_CONSTANT)
        Rl = cv2.warpPerspective(R, Hr, (c.w, c.h), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)
        cov = cv2.warpPerspective(np.ones(hi.shape[:2], np.float32), Ah @ Hr, (c.w, c.h), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_CONSTANT)
        cov = cv2.GaussianBlur(cv2.erode(cov, np.ones((25, 25), np.uint8)), (0, 0), 8)[..., None]
        # keep the exact low frequencies of the room layer, the detail of the upscale
        Rhf = Rh.astype(np.float32); Rlf = Rl.astype(np.float32)
        det = Rhf - cv2.GaussianBlur(Rhf, (0, 0), 4) + cv2.GaussianBlur(Rlf, (0, 0), 4)
        R2 = np.clip(Rlf * (1 - cov) + det * cov, 0, 255).astype(np.uint8)
        cv2.imwrite(os.path.join(OUTD, 'loft4s-R2.png'), R2)
print('ok')
