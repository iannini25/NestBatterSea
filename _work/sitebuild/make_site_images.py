# Responsive images for the new sections (never touches the originals).
# NOTE: views, vision, res (and area, interiors, thumbs) are now made by make_hq_images.py
# at higher quality and with extra widths; rerun that one, not the groups below, for those.
#   python _work/sitebuild/make_site_images.py [group ...]
# Every image is written as AVIF, WebP and JPEG at a few widths:  <name>-<w>.<ext>
# Groups: views (official verified views, ruler border cropped), plans (official plans,
# green slide keyed to paper), vision, res (residence card crops), og.
import os, sys
import numpy as np
from PIL import Image
import cv2

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = lambda *a: os.path.join(ROOT, *a)
SITE = P('assets', 'site')
PAPER = (243, 239, 232)


def save(im, folder, name, widths, q=(52, 78, 80)):
    """AVIF + WebP + JPEG at each width (never upscaled)."""
    out = os.path.join(SITE, folder)
    os.makedirs(out, exist_ok=True)
    im = im.convert('RGB')
    for w in widths:
        w = min(w, im.width)
        h = round(im.height * w / im.width)
        r = im.resize((w, h), Image.LANCZOS) if w != im.width else im
        base = os.path.join(out, f'{name}-{w}')
        r.save(base + '.avif', 'AVIF', quality=q[0], speed=6)
        r.save(base + '.webp', 'WEBP', quality=q[1], method=6)
        r.save(base + '.jpg', 'JPEG', quality=q[2], optimize=True, progressive=True)
        sz = [os.path.getsize(base + e) // 1024 for e in ('.avif', '.webp', '.jpg')]
        print(f'  {folder}/{name}-{w}  {w}x{h}  avif {sz[0]} KB  webp {sz[1]} KB  jpg {sz[2]} KB')
    return im.size


def views():
    # The seven verified views carry a grey ruler frame with tick labels and centre arrows:
    # about 13 px on three sides, 14 px plus labels up to 30 px at the bottom, arrows to 25 px.
    crop = (26, 26, 26, 40)                              # left, top, right, bottom
    src = {
        'lombard-road': '2153_020_72_00', 'junction': '2153_050_72_01', 'fulham': '2153_110_72_00',
        'imperial-park': '2153_120_72_00', 'marina': '2153_160_72_00', 'york-road': '2153_210_72_00',
        'mendip-court': '2153_220_72_00'}
    dims = {}
    for name, f in src.items():
        im = Image.open(P('_work', 'official', f + '.jpg')).convert('RGB')
        l, t, r, b = crop
        im = im.crop((l, t, im.width - r, im.height - b))
        dims[name] = save(im, 'views', name, [640, 1280, 1868])
    # the official renders without a frame
    im = Image.open(P('_work', 'official', '2153_031_72_00-1-1.jpg')).convert('RGB')
    dims['river-night'] = save(im, 'views', 'river-night', [640, 1280, 1920, 2560])
    im = Image.open(P('_work', 'official', '2153_022_72_02_Wide.jpg')).convert('RGB')
    dims['thames-wide'] = save(im, 'views', 'thames-wide', [1000, 2000])
    im = Image.open(P('_refs', 'cgi-oficial', '02-dusk-aerial.png')).convert('RGB')
    dims['dusk-aerial'] = save(im, 'views', 'dusk-aerial', [640, 1160])
    for k, v in dims.items():
        print(f'DIM {k} {v[0]} {v[1]}')


def keyed(path, box, bg=(71, 112, 76), lo=18, hi=60, plate=True, red=True, blank=()):
    """Crop an official plan slide and replace its dark green slide colour with paper."""
    im = Image.open(path).convert('RGB')
    a = np.asarray(im).astype(np.float32)
    g = np.array(bg, np.float32)
    if red:   # the red dashed site line and the red leader arrows: painted out
        rm = ((a[..., 0] > 170) & (a[..., 1] < 110) & (a[..., 2] < 110)).astype(np.uint8) * 255
        rm = cv2.dilate(rm, np.ones((3, 3), np.uint8))
        a = cv2.inpaint(a.astype(np.uint8), rm, 4, cv2.INPAINT_TELEA).astype(np.float32)
    d = np.abs(a - g).max(-1)
    alpha = np.clip((d - lo) / (hi - lo), 0, 1)
    if plate:  # keep only the floor plate: drop the annotations around it
        m = (d > 40).astype(np.uint8) * 255
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
        n, lab, st, _ = cv2.connectedComponentsWithStats(m)
        i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
        keep = (lab == i).astype(np.uint8) * 255
        keep = cv2.morphologyEx(keep, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
        keep = cv2.dilate(keep, np.ones((7, 7), np.uint8))
        cs, _ = cv2.findContours(keep, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        fill = np.zeros_like(keep)
        cv2.drawContours(fill, cs, -1, 255, -1)
        fill = cv2.GaussianBlur(fill, (5, 5), 0).astype(np.float32) / 255
        alpha = alpha * fill
    alpha = alpha[..., None]
    paper = np.array(PAPER, np.float32)
    fg = np.where(alpha > 0.02, (a - (1 - alpha) * g) / np.maximum(alpha, 0.02), paper)
    out = np.clip(alpha * np.clip(fg, 0, 255) + (1 - alpha) * paper, 0, 255).astype(np.uint8)
    for x0, y0, x1, y1 in blank:          # pieces of other drawings that fall inside the crop
        out[y0:y1, x0:x1] = PAPER
    return Image.fromarray(out).crop(box)


def plans():
    box = (60, 240, 1500, 1345)
    for name, f in [('single-private', 'fp-33'), ('double-lower-private', 'fp-31'), ('double-upper-private', 'fp-32'),
                    ('single-studios', 'fp-34'), ('single-affordable', 'fp-28'),
                    ('double-lower-affordable', 'aff-29'), ('double-upper-affordable', 'aff-30')]:
        im = keyed(P('_refs', 'plantas-oficiais', f + '.png'), box)
        print('DIM plan', name, im.size)
        save(im, 'plans', name, [720, 1440], q=(60, 84, 86))
    # the wheelchair accessible layout: the large illustrative plan only (no key plan, no notes)
    im = keyed(P('_refs', 'plantas-oficiais', 'wheelchair.png'), (630, 590, 1990, 1392), lo=10, hi=30, plate=False, red=False,
               blank=[(600, 560, 768, 768)])          # the corner of the key plan
    print('DIM plan wheelchair', im.size)
    save(im, 'plans', 'wheelchair', [720, 1360], q=(60, 84, 86))
    # the environmental diagram, as published
    im = Image.open(P('_refs', 'cgi-oficial', 'dd126.png')).convert('RGB')
    save(im, 'plans', 'environment', [600, 1200], q=(60, 84, 86))


def vision():
    im = Image.open(P('_refs', 'cgi-oficial', 'tower-night.png')).convert('RGB')     # 680 x 1840
    save(im.crop((0, 0, 680, 1200)), 'vision', 'tower', [420, 680])                  # the part the card shows
    save(im.crop((0, 0, 680, 760)), 'vision', 'crown', [420, 680])
    im = Image.open(P('_work', 'official', '2153_050_72_01.jpg')).convert('RGB')
    im = im.crop((26, 26, im.width - 26, im.height - 40))
    save(im, 'vision', 'street', [640, 1280])


def res():
    # residence cards: the main photograph and inset crops of the 1920 x 1080 interiors
    for photo in ['loft4-living-2', 'bung3-living-2']:
        im = Image.open(P('assets', 'interiors', photo + '.jpg')).convert('RGB')
        save(im, 'res', photo, [800, 1440])
    for photo in ['loft4-bed4', 'loft4-gallery', 'bung3-garden', 'bung3-terrace']:
        im = Image.open(P('assets', 'interiors', photo + '.jpg')).convert('RGB')
        w = round(im.height * 4 / 5)
        x = (im.width - w) // 2
        save(im.crop((x, 0, x + w, im.height)), 'res', photo + '-tall', [420, 640])


def og():
    im = Image.open(P('_work', 'official', '2153_031_72_00-1-1.jpg')).convert('RGB')    # 4204 x 3153
    w, h = im.width, round(im.width * 630 / 1200)
    y = round(im.height * 0.30)
    im = im.crop((0, y, w, y + h)).resize((1200, 630), Image.LANCZOS)
    im.save(os.path.join(SITE, 'share.jpg'), 'JPEG', quality=84, optimize=True, progressive=True)
    print('  share.jpg', os.path.getsize(os.path.join(SITE, 'share.jpg')) // 1024, 'KB')


if __name__ == '__main__':
    for g in (sys.argv[1:] or ['views', 'plans', 'vision', 'res', 'og']):
        print('==', g)
        globals()[g]()
