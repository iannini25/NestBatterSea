# Find openly licensed Wikimedia Commons photographs for every place and draw contact sheets.
# python -I commons_candidates.py <download dir> <sheet dir>
# Writes candidates.json (index, title, licence, author, size) for the picker.
import json, os, sys, time, urllib.request, urllib.parse, io, re, html
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from places_src import P

DL, SHEET = sys.argv[1], sys.argv[2]
os.makedirs(DL, exist_ok=True); os.makedirs(SHEET, exist_ok=True)
UA = {'User-Agent': 'NestBatterseaSiteBuild/1.0 (static site, one off build script; contact via site owner)'}
OK_LIC = re.compile(r'^(CC BY(-SA)? [1-4]\.0|CC0|Public domain|PD|CC BY 2\.5|CC BY-SA 2\.5|CC BY-SA 3\.0 igo|Attribution)', re.I)

def api(params):
    url = 'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode({'action': 'query', 'format': 'json', **params})
    for k in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return json.load(r)
        except Exception as e:
            time.sleep(2 + 3 * k)
    return {}

def clean(s):
    return html.unescape(re.sub('<[^>]+>', '', s or '')).strip()

def info(pages):
    out = []
    for p in pages:
        ii = (p.get('imageinfo') or [{}])[0]
        if not ii or ii.get('mime') not in ('image/jpeg', 'image/png', 'image/webp'): continue
        m = ii.get('extmetadata', {})
        lic = clean(m.get('LicenseShortName', {}).get('value'))
        out.append({'title': p['title'], 'w': ii.get('width'), 'h': ii.get('height'), 'thumb': ii.get('thumburl'),
                    'lic': lic, 'licurl': m.get('LicenseUrl', {}).get('value', ''), 'artist': clean(m.get('Artist', {}).get('value'))[:120],
                    'page': ii.get('descriptionurl'), 'ok': bool(OK_LIC.match(lic)) and (ii.get('width') or 0) >= 800})
    return out

II = {'prop': 'imageinfo', 'iiprop': 'url|size|mime|extmetadata', 'iiurlwidth': 300}
allc = {}
for pl in P:
    cands, seen = [], set()
    if pl.get('lead'):
        d = api({'titles': 'File:' + pl['lead'], **II})
        cands += info(d.get('query', {}).get('pages', {}).values())
    for q in pl['q']:
        d = api({'generator': 'search', 'gsrsearch': q + ' filetype:bitmap', 'gsrnamespace': 6, 'gsrlimit': 8, **II})
        pages = sorted(d.get('query', {}).get('pages', {}).values(), key=lambda p: p.get('index', 99))
        cands += info(pages)
        time.sleep(.4)
    uniq = []
    for c in cands:
        if c['title'] in seen: continue
        seen.add(c['title']); uniq.append(c)
    uniq = [c for c in uniq if c['ok']][:14]
    allc[pl['id']] = uniq
    # contact sheet: 7 columns
    W, H, cols = 300, 200, 7
    rows = max(1, (len(uniq) + cols - 1) // cols)
    sheet = Image.new('RGB', (cols * W, rows * (H + 34)), (20, 22, 28))
    dr = ImageDraw.Draw(sheet)
    for i, c in enumerate(uniq):
        try:
            with urllib.request.urlopen(urllib.request.Request(c['thumb'], headers=UA), timeout=40) as r:
                im = Image.open(io.BytesIO(r.read())).convert('RGB')
            im.thumbnail((W, H))
            x, y = (i % cols) * W, (i // cols) * (H + 34)
            sheet.paste(im, (x + (W - im.width) // 2, y + (H - im.height) // 2))
            dr.text((x + 4, y + H + 2), f"{i} {c['lic']} {c['w']}x{c['h']}", fill=(220, 220, 220))
            dr.text((x + 4, y + H + 17), c['title'][5:48], fill=(150, 160, 170))
        except Exception as e:
            print('  thumb fail', c['title'], e)
        time.sleep(.15)
    sheet.save(os.path.join(SHEET, f"{pl['id']}.jpg"), quality=80)
    print(pl['id'], len(uniq), flush=True)
json.dump(allc, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'candidates.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
