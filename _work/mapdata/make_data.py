# Build assets/map/places.json (map page) and the photographs, and refresh the eight places of
# the Location section (assets/site/map/places.json) with the same routes.
#   python make_data.py <download dir>
# Inputs next to this script: places_src.py, routes_raw.json (build_routes.py), candidates.json
# (commons_candidates.py), picks.json ({id: [candidate index or File: title, focus y 0..1]}),
# footprint.json (the site building, OpenStreetMap way 306984713).
import json, os, sys, io, math, re, time, urllib.request, urllib.parse
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from places_src import P, SITE, CATS

ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(ROOT, 'assets', 'map')
PH = os.path.join(OUT, 'photos')
os.makedirs(PH, exist_ok=True)
DL = sys.argv[1]
os.makedirs(DL, exist_ok=True)
UA = {'User-Agent': 'NestBatterseaSiteBuild/1.0 (static site build)'}
routes = json.load(open(os.path.join(HERE, 'routes_raw.json'), encoding='utf-8'))['routes']
cands = json.load(open(os.path.join(HERE, 'candidates.json'), encoding='utf-8'))
picks = json.load(open(os.path.join(HERE, 'picks.json'), encoding='utf-8'))
foot = json.load(open(os.path.join(HERE, 'footprint.json')))

CAT_COL = {'river': '#92B7CA', 'transport': '#e9e4da', 'parks': '#9cc5a1', 'food': '#ffd9a0', 'culture': '#e5b3a3', 'everyday': '#b7c0ea'}
BRIDGES = {'Wandsworth Bridge': (-0.187725, 51.464877), 'Battersea Bridge': (-0.1725, 51.481111),
           'Albert Bridge': (-0.1667, 51.4823), 'Chelsea Bridge': (-0.15, 51.484722), 'Putney Bridge': (-0.2133, 51.4666)}

def xy(p, lat0=51.47):
    return (p[0] * 111320 * math.cos(math.radians(lat0)), p[1] * 110540)

def seg_dist(p, a, b):
    p, a, b = xy(p), xy(a), xy(b)
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = 0 if dx == dy == 0 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)

def line_dist(p, line):
    return min(seg_dist(p, line[i], line[i + 1]) for i in range(len(line) - 1)) if len(line) > 1 else 1e9

def rdp(pts, eps):
    if len(pts) < 3: return pts
    a, b = pts[0], pts[-1]
    i, dm = 0, 0
    for k in range(1, len(pts) - 1):
        d = seg_dist(pts[k], a, b)
        if d > dm: i, dm = k, d
    if dm > eps: return rdp(pts[:i + 1], eps)[:-1] + rdp(pts[i:], eps)
    return [a, b]

def bridges_on(line):
    return [n for n, c in BRIDGES.items() if line_dist(c, line) < 40]

def api(params):
    # answers are kept in the download folder: a second run asks Commons nothing
    key = re.sub(r'[^A-Za-z0-9]+', '_', params.get('titles', ''))[:120]
    cache = os.path.join(DL, 'api_' + key + '.json')
    if os.path.exists(cache): return json.load(open(cache, encoding='utf-8'))
    url = 'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode({'action': 'query', 'format': 'json', **params})
    for k in range(7):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                d = json.load(r)
            json.dump(d, open(cache, 'w', encoding='utf-8'))
            return d
        except Exception as e:
            print('  api retry', e); time.sleep(10 + 10 * k)
    raise SystemExit('commons api failed')

def fetch(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 1000: return
    for k in range(7):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
                open(path, 'wb').write(r.read()); return
        except Exception as e:
            print('  retry', e); time.sleep(10 + 10 * k)
    raise SystemExit('download failed ' + url)

def crop(im, ratio, fy=.5, fx=.5):
    w, h = im.size
    if w / h > ratio:
        nw = int(h * ratio); x = int((w - nw) * fx); return im.crop((x, 0, x + nw, h))
    nh = int(w / ratio); y = int((h - nh) * fy); return im.crop((0, y, w, y + nh))

import re, html as H
def clean(s): return H.unescape(re.sub('<[^>]+>', '', s or '')).strip()

places = []
for p in P:
    pk = picks[p['id']]
    sel, fy = pk[0], (pk[1] if len(pk) > 1 else .5)
    fx = pk[2] if len(pk) > 2 else .5
    if isinstance(sel, int): c = cands[p['id']][sel]; title = c['title']
    else: title = sel
    d = api({'titles': title, 'prop': 'imageinfo', 'iiprop': 'url|size|extmetadata', 'iiurlwidth': 1280})
    pg = list(d['query']['pages'].values())[0]
    ii = pg['imageinfo'][0]; m = ii.get('extmetadata', {})
    raw = os.path.join(DL, p['id'] + '.jpg')
    fetch(ii.get('thumburl') or ii['url'], raw)
    im = Image.open(raw).convert('RGB')
    big = crop(im, 1.5, fy, fx).resize((720, 480), Image.LANCZOS)
    big.save(os.path.join(PH, p['id'] + '.webp'), 'WEBP', quality=80, method=6)
    sq = crop(im, 1.0, fy, fx).resize((104, 104), Image.LANCZOS)
    sq.save(os.path.join(PH, p['id'] + '-sq.webp'), 'WEBP', quality=78, method=6)
    lic = clean(m.get('LicenseShortName', {}).get('value'))
    artist = clean(m.get('Artist', {}).get('value')) or 'Unknown'
    artist = re.sub(r'\s+', ' ', artist)[:80]
    photo = {'src': f"assets/map/photos/{p['id']}.webp", 'thumb': f"assets/map/photos/{p['id']}-sq.webp", 'title': title,
             'author': artist, 'licence': lic, 'licenceUrl': m.get('LicenseUrl', {}).get('value') or ii['descriptionurl'],
             'page': ii['descriptionurl'], 'changed': True}
    q = {'id': p['id'], 'name': p['name'], 'cat': p['cat'], 'kind': p['kind'], 'lat': p['lat'], 'lon': p['lon'], 'src': p['src'], 'photo': photo}
    if p.get('door'): q['door'] = True
    for mode in ('foot', 'car'):
        r = routes[p['id']][mode]
        line = rdp(r['line'], 1.2)
        br = bridges_on(r['line'])
        q[mode] = {'s': r['s'], 'm': r['m'], 'line': line, 'via': r['via'], 'bridge': br[0] if br else None}
    places.append(q)
    print(f"{p['id']:11s} {lic:14s} {artist[:30]:30s} walk {q['foot']['s']//60:3d} min {q['foot']['bridge']}  car {q['car']['s']//60:3d} min {q['car']['bridge']}")
    time.sleep(1.5)

site = dict(SITE)
site['footprint'] = foot
site['photo'] = 'assets/site/views/dusk-aerial-640.webp'
site['facts'] = [['Storeys', '34'], ['Homes', '143, of which 51 affordable'], ['Tenure', 'Build to rent'],
                 ['Status', 'In planning, not built'], ['Parking', 'Car free']]
data = {'note': 'Places and coordinates from OpenStreetMap (ODbL) and Wikipedia. Walking and driving routes from OSRM on routing.openstreetmap.de (FOSSGIS), '
                'computed once on the build date; the river is crossed on bridges only. Times are approximate; drives are without traffic. '
                'Photographs from Wikimedia Commons under the licence named with each.',
        'built': time.strftime('%Y-%m-%d'), 'site': site,
        'cats': [{'id': k, 'name': n, 'color': CAT_COL[k]} for k, n in CATS], 'places': places}
json.dump(data, open(os.path.join(OUT, 'places.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('wrote', os.path.getsize(os.path.join(OUT, 'places.json')), 'bytes')

# ---- the Location section: the same eight places, now with real walks across the bridges
sec = os.path.join(ROOT, 'assets', 'site', 'map', 'places.json')
S = json.load(open(sec, encoding='utf-8'))
by = {q['id']: q for q in places}
for sp in S['places']:
    q = by.get(sp['id'])
    if not q: continue
    f = q['foot']
    if sp.get('mode') == 'door': continue
    sp['mode'] = 'walk'
    sp['walk_km'] = round(f['m'] / 1000, 1)
    sp['walk_min'] = max(1, round(f['s'] / 60))
    sp['route'] = f['line']
    if f['bridge']: sp['bridge'] = f['bridge']
S['note'] = ('Coordinates from OpenStreetMap (ODbL). Walking routes from the OSRM foot profile on routing.openstreetmap.de, computed once on the build date '
             'and crossing the Thames on its bridges only; times and distances are approximate.')
S['built'] = time.strftime('%Y-%m-%d')
json.dump(S, open(sec, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
for sp in S['places']: print('section', sp['id'], sp['mode'], sp.get('walk_min'), sp.get('walk_km'), sp.get('bridge'))
