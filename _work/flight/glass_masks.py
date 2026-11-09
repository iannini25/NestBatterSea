"""
Glass masks for Step inside, drawn on the flight's last frame (built at 3840 x 2160, coordinates
below in 1920 x 1080 pixels of that frame). Panes come from the measured mullion grid; foreground
objects in front of the glass (tree, parasol, planting, the lamp) stay opaque, with the glass seen
between the branches.
"""
import cv2
import numpy as np

S = 2  # the masks are built on the 2x frame


def lum(img):
    return cv2.cvtColor(img, cv2.COLOR_BGR2LAB)[..., 0].astype(np.float32)


def stripes_v(mask, xs, half, y0=0, y1=None):
    y1 = mask.shape[0] if y1 is None else y1
    for x in xs:
        mask[y0:y1, int((x - half) * S):int((x + half) * S) + 1] = 0


def loft4(img):
    h, w = img.shape[:2]
    L = lum(img)
    m = np.zeros((h, w), np.float32)
    m[int(283 * S):int(852 * S), int(600 * S):int(1274 * S)] = 1
    stripes_v(m, [660.5, 726.5, 796.0, 864.5, 934.5, 1003.5, 1073.5, 1142.5, 1210.0], 3.5)
    m[int(620 * S):int(635 * S), :] = 0                     # transom
    # foreground: the tree (glass only in the bright gaps between branches), trunk, parasol, lamp
    tree = np.zeros((h, w), np.uint8)
    pts = np.array([(655, 600), (690, 500), (760, 470), (900, 462), (1000, 500), (1066, 590),
                    (1050, 690), (960, 760), (860, 790), (760, 780), (680, 730)], np.float32) * S
    cv2.fillPoly(tree, [pts.astype(np.int32)], 1)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    chroma = np.hypot(lab[..., 1] - 128, lab[..., 2] - 128)
    # glass between the branches: bright and neutral; branches and leaves: darker or tinted
    gaps = (chroma < 9.5).astype(np.uint8)          # glass chroma 5 to 7, branches and leaves 12 to 18
    gaps = cv2.morphologyEx(gaps, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(np.float32)
    m = np.where(tree > 0, m * gaps, m)
    # the trunk: thin and dark, so it is cut by colour below the canopy
    trunk = np.zeros((h, w), np.uint8)
    trunk[int(700 * S):int(852 * S), int(796 * S):int(836 * S)] = 1
    m = np.where(trunk > 0, m * (chroma < 9.5) * (L > 120), m)
    par = np.zeros((h, w), np.uint8)
    cv2.ellipse(par, (int(1086 * S), int(712 * S)), (int(132 * S), int(36 * S)), 0, 0, 360, 1, -1)
    m[par > 0] = 0
    m[int(712 * S):int(852 * S), int(1081 * S):int(1095 * S)] = 0  # parasol pole
    shrub = np.zeros((h, w), np.uint8)
    cv2.ellipse(shrub, (int(1150 * S), int(770 * S)), (int(55 * S), int(40 * S)), 0, 0, 360, 1, -1)
    m = np.where(shrub > 0, m * (chroma < 9.5), m)
    cv2.circle(m, (int(815 * S), int(772 * S)), int(16 * S), 0, -1)  # the lamp's core (its glow is added back)
    return m


def bung3(img):
    h, w = img.shape[:2]
    m = np.zeros((h, w), np.uint8)
    # glass between the soffit and the top of the planter (the planter and its plants stay in front)
    poly = np.array([(737, 491), (1203, 539), (1203, 652), (737, 604)], np.float32) * S
    cv2.fillPoly(m, [poly.astype(np.int32)], 1)
    m = m.astype(np.float32)
    stripes_v(m, [853.0, 996.0, 1018.5, 1047.0, 1100.5, 1150.5, 1202.0], 3.0)
    return m


def build(home, img):
    m = loft4(img) if home == 'loft4' else bung3(img)
    m = cv2.morphologyEx((m > 0.5).astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(np.float32)
    return cv2.GaussianBlur(m, (0, 0), 1.4)


if __name__ == '__main__':
    import sys
    for home in sys.argv[1:] or ['loft4', 'bung3']:
        img = cv2.imread(f'out/{home}-end-2x.png')
        m = build(home, img)
        np.save(f'out/{home}-glass-2x.npy', m.astype(np.float16))
        ov = img.astype(np.float32)
        ov[..., 2] = ov[..., 2] * (1 - 0.55 * m) + 255 * 0.55 * m
        ov[..., 1] = ov[..., 1] * (1 - 0.35 * m)
        cv2.imwrite(f'out/{home}-glass-check.jpg', cv2.resize(ov.astype(np.uint8), (1920, 1080), interpolation=cv2.INTER_AREA),
                    [cv2.IMWRITE_JPEG_QUALITY, 85])
        print(home, 'mask coverage', round(float(m.mean()), 4))
