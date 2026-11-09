# Derived web images for the site (never touches the originals).
#   python _work/make_web_images.py
# Writes WebP copies of the facade, section crops and residence thumbnails
# into assets/facade and assets/site, and prints the tiny inline placeholder.
import base64, io, os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)
OUT = P('assets', 'site')
os.makedirs(OUT, exist_ok=True)


def save(im, name, sizes=None, jpg=True, q=80):
    """name without extension; sizes = list of widths (None = as is)."""
    im = im.convert('RGB')
    outs = []
    for w in (sizes or [im.width]):
        h = round(im.height * w / im.width)
        r = im.resize((w, h), Image.LANCZOS) if w != im.width else im
        suffix = f'-{w}' if sizes and len(sizes) > 1 else ''
        fn = os.path.join(OUT, f'{name}{suffix}.webp')
        r.save(fn, 'WEBP', quality=q, method=6)
        outs.append(fn)
    if jpg:
        w = (sizes or [im.width])[-1]
        h = round(im.height * w / im.width)
        r = im.resize((w, h), Image.LANCZOS) if w != im.width else im
        fn = os.path.join(OUT, f'{name}.jpg')
        r.save(fn, 'JPEG', quality=82, optimize=True, progressive=True)
        outs.append(fn)
    for f in outs:
        print(f'{os.path.relpath(f, ROOT):46s} {os.path.getsize(f) // 1024:5d} KB')


# 1. the facade (hero, LCP): WebP copies next to the JPGs
for w in (1600, 2560):
    src = Image.open(P('assets', 'facade', f'master-{w}.jpg')).convert('RGB')
    fn = P('assets', 'facade', f'master-{w}.webp')
    src.save(fn, 'WEBP', quality=82, method=6)
    print(f'{os.path.relpath(fn, ROOT):46s} {os.path.getsize(fn) // 1024:5d} KB')

# tiny placeholder painted while the facade loads
ph = Image.open(P('assets', 'facade', 'master-1600.jpg')).convert('RGB').resize((48, 27), Image.LANCZOS)
buf = io.BytesIO(); ph.save(buf, 'JPEG', quality=60, optimize=True)
print('placeholder data uri bytes', len(buf.getvalue()))
with open(os.path.join(OUT, 'placeholder.txt'), 'w') as f:
    f.write('data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode())

# 2. building section: two small squares
tower = Image.open(P('_refs', 'cgi-oficial', 'tower-night.png')).convert('RGB')
save(tower.crop((0, 30, 680, 710)), 'crown', [480])
# the terrace crop was taken from the first LOFT 4 arrival still, kept in _work/web-src
save(Image.open(P('_work', 'web-src', 'terrace-src.jpg')).convert('RGB'), 'terrace', [480])

# 3. residence thumbnails for the mini card, from the delivered room photographs
for k, photo in (('loft4', 'loft4-kitchen'), ('bung3', 'bung3-terrace')):
    im = Image.open(P('assets', 'interiors', f'{photo}.jpg')).convert('RGB')   # 1920 x 1080
    w, h = 1290, 860                                                            # 3:2, centred
    x, y = (im.width - w) // 2, (im.height - h) // 2
    save(im.crop((x, y, x + w, y + h)), f'thumb-{k}', [264])

# 4. location: the official dusk aerial
aer = Image.open(P('_refs', 'cgi-oficial', '02-dusk-aerial.png')).convert('RGB')
save(aer, 'aerial', [800, 1160])
