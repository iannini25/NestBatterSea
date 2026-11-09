# High quality re-export of the site images (never touches the sources).
#   python _work/sitebuild/make_hq_images.py [group ...]
# Groups: views, vision, floats, res, area, interiors, thumbs
#
# Every image goes back to its best source (official renders in _work/official and
# _refs/cgi-oficial, the lossless room and area PNGs in _work/photos/split) and is written
# as AVIF + WebP + JPEG at a few widths with higher quality settings than the first pass.
# Widths above the source are a careful local upscale (Lanczos + mild unsharp mask): used only
# where the source is the only one there is and the image is shown larger on 2x screens.
# The facade master, the plans, the map, the flight stills and the videos are not touched here.
# Backup of the files this replaced: _work/backup_images_before_hq/
import os, sys
import numpy as np
from PIL import Image, ImageFilter
import cv2

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = lambda *a: os.path.join(ROOT, *a)
SPLIT = P('_work', 'photos', 'split')
Q = dict(avif=72, webp=88, jpg=88)          # full screen room photos, shown 1:1
QV = dict(avif=66, webp=86, jpg=86)         # cards shown downscaled on screen: views, residence cards
LOG = []


def resize(im, w, h=None):
    """Lanczos to (w, h); above the source size, a mild unsharp mask restores edge contrast."""
    h = h or round(im.height * w / im.width)
    if (w, h) == im.size:
        return im
    r = im.resize((w, h), Image.LANCZOS)
    if w > im.width:
        k = w / im.width                       # stronger enlargement, slightly wider radius
        r = r.filter(ImageFilter.UnsharpMask(radius=0.8 * k, percent=40, threshold=3))
    return r


def write(im, base, q=Q, jpg=True, avif=True):
    im = im.convert('RGB')
    os.makedirs(os.path.dirname(base), exist_ok=True)
    out = []
    if avif:
        im.save(base + '.avif', 'AVIF', quality=q['avif'], speed=4)
        out.append('.avif')
    im.save(base + '.webp', 'WEBP', quality=q['webp'], method=6)
    out.append('.webp')
    if jpg:
        im.save(base + '.jpg', 'JPEG', quality=q['jpg'], optimize=True, progressive=True)
        out.append('.jpg')
    sz = '  '.join(f'{e[1:]} {os.path.getsize(base + e) // 1024} KB' for e in out)
    rel = os.path.relpath(base, ROOT).replace('\\', '/')
    print(f'  {rel:52s} {im.width}x{im.height}  {sz}')
    LOG.append((rel, im.size))


def save(im, folder, name, widths, suffix=lambda w: f'-{w}', q=Q):
    for w in widths:
        write(resize(im, w), P('assets', 'site', folder, name + suffix(w)), q=q)


def views():
    # the seven verified views: the grey ruler frame cropped as in make_site_images.py
    crop = (26, 26, 26, 40)
    src = {
        'lombard-road': '2153_020_72_00', 'junction': '2153_050_72_01', 'fulham': '2153_110_72_00',
        'imperial-park': '2153_120_72_00', 'marina': '2153_160_72_00', 'york-road': '2153_210_72_00',
        'mendip-court': '2153_220_72_00'}
    for name, f in src.items():
        im = Image.open(P('_work', 'official', f + '.jpg')).convert('RGB')
        l, t, r, b = crop
        save(im.crop((l, t, im.width - r, im.height - b)), 'views', name, [640, 1280, 1868], q=QV)
    # night river render, 4204 x 3153: a near native 3840 for the lightbox on 2x screens
    im = Image.open(P('_work', 'official', '2153_031_72_00-1-1.jpg')).convert('RGB')
    save(im, 'views', 'river-night', [640, 1280, 1920, 2560, 3840], q=QV)
    # the wide aerial is 2000 px at most: 2880 is the careful upscale for 2x screens
    im = Image.open(P('_work', 'official', '2153_022_72_02_Wide.jpg')).convert('RGB')
    save(im, 'views', 'thames-wide', [1000, 2000, 2880], q=QV)
    # dusk aerial: 02-dusk-aerial.png is a 255 colour palette copy (dithered sky). The same
    # frame is cut from the truecolour 05-cgi-a.jpg (registered with SIFT: scale 1.00688,
    # offset 14.29, 28.08), then 1600 and 2320 are careful upscales for large and 2x screens.
    src = cv2.cvtColor(cv2.imread(P('_refs', 'cgi-oficial', '05-cgi-a.jpg')), cv2.COLOR_BGR2RGB)
    sc, x0, y0 = 1.006879815506011, 14.29356584, 28.07748905
    nw, nh = round(1160 * sc), round(680 * sc)            # 1168 x 685, the frame at native scale
    A = np.float32([[1, 0, -x0], [0, 1, -y0]])             # sub pixel shift only, no scaling
    nat = Image.fromarray(cv2.warpAffine(src, A, (nw, nh), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE))
    for w in [640, 1160, 1600, 2320]:
        write(resize(nat, w, round(w * 680 / 1160)), P('assets', 'site', 'views', f'dusk-aerial-{w}'), q=QV)


def vision():
    im = Image.open(P('_refs', 'cgi-oficial', 'tower-night.png')).convert('RGB')     # 680 x 1840
    save(im.crop((0, 0, 680, 1200)), 'vision', 'tower', [420, 680, 1020])           # 1020: upscale for 2x
    save(im.crop((0, 0, 680, 760)), 'vision', 'crown', [420, 680, 1020])


def floats():
    # the two squares of the building section: 480 for 1x, the native source for 2x
    tower = Image.open(P('_refs', 'cgi-oficial', 'tower-night.png')).convert('RGB')
    crown = tower.crop((0, 30, 680, 710))
    write(resize(crown, 480), P('assets', 'site', 'crown'))
    write(crown, P('assets', 'site', 'crown-680'))
    terr = Image.open(P('_work', 'web-src', 'terrace-src.jpg')).convert('RGB')          # 700 x 700
    write(resize(terr, 480), P('assets', 'site', 'terrace'))
    write(terr, P('assets', 'site', 'terrace-700'))


def res():
    for photo in ['loft4-living-2', 'bung3-living-2']:
        im = Image.open(os.path.join(SPLIT, photo + '.png')).convert('RGB')
        save(im, 'res', photo, [800, 1440, 1920], q=QV)
    for photo in ['loft4-bed4', 'loft4-gallery', 'bung3-garden', 'bung3-terrace']:
        im = Image.open(os.path.join(SPLIT, photo + '.png')).convert('RGB')
        w = round(im.height * 4 / 5)
        x = (im.width - w) // 2
        save(im.crop((x, 0, x + w, im.height)), 'res', photo + '-tall', [420, 640], q=QV)


def area():
    for name in ['area-lake', 'area-northcote', 'area-power-station', 'area-riverside']:
        im = Image.open(os.path.join(SPLIT, name + '.png')).convert('RGB')
        # grainy illustrations: q64 still beats the first pass by about 2 dB at a lighter weight
        save(im, 'area', name, [640, 960, 1280, 1920], suffix=lambda w: '' if w == 1920 else f'-{w}',
             q=dict(avif=64, webp=84, jpg=86))


# Step inside ends exactly on these two photographs: they are the clips' last frames, owned by
# the video pipeline, and must stay pixel identical to them. Never re-export them here.
KEEP = {'loft4-living', 'bung3-living'}


def interiors():
    for f in sorted(os.listdir(SPLIT)):
        if not f.endswith('.png') or f.startswith('area-') or f[:-4] in KEEP:
            continue
        im = Image.open(os.path.join(SPLIT, f)).convert('RGB')
        write(im, P('assets', 'interiors', f[:-4]))


def vision2():
    # The vision section, second version (client: sharper, more beautiful images). No official image shows
    # the tower larger than tower-night.png (680 px wide), so the three slots use the high resolution
    # illustrative close ups made for the flights (2688 x 1520, same design); the site tags them Illustrative.
    gen = lambda f: Image.open(P('_work', 'ai', 'gen', f)).convert('RGB')
    # tall card, same 17:30 frame as the old tower crop: a Bungalow garden on its planted slab, the City beyond
    tall = gen('bung3-end-gpt3.png').crop((1827, 0, 2688, 1520))                    # 861 x 1520, native
    save(tall, 'vision', 'garden-tall', [420, 680, 1020])
    # squares: 480 for 1x, 960 for 2x (both from native pixels)
    olive = gen('loft4-end-gpt.png').crop((600, 160, 1880, 1440))                  # 1280, the LOFT window
    loft = gen('loft4-inside-final.png').crop((560, 0, 2080, 1520))                # 1520, inside the LOFT
    save(olive, 'vision', 'olive', [480, 960])
    save(loft, 'vision', 'loft-inside', [480, 960])


def thumbs():
    for k, photo in (('loft4', 'loft4-kitchen'), ('bung3', 'bung3-terrace')):
        im = Image.open(os.path.join(SPLIT, photo + '.png')).convert('RGB')
        w, h = 1290, 860
        x, y = (im.width - w) // 2, (im.height - h) // 2
        write(resize(im.crop((x, y, x + w, y + h)), 264), P('assets', 'site', f'thumb-{k}'), avif=False)


if __name__ == '__main__':
    for g in (sys.argv[1:] or ['views', 'vision', 'floats', 'res', 'area', 'interiors', 'thumbs']):
        print('==', g)
        globals()[g]()
