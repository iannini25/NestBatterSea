# Places around Nest Battersea for the Location map (run once; network needed).
#   python _work/sitebuild/make_places.py
# Coordinates come from OpenStreetMap (Overpass, ids below), walking routes from the
# FOSSGIS OSRM foot router (routing.openstreetmap.de, OSRM foot profile, about 4.5 km/h).
# Places across the river get a straight line distance instead of a route.
# Writes assets/site/map/places.json (small, static: the site never calls a router).
import json, math, os, time, urllib.request, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'assets', 'site', 'map', 'places.json')
UA = {'User-Agent': 'NestBatterseaSiteBuild/1.0 (one off research, local build)'}

SITE = {'id': 'nest', 'name': 'Nest Battersea', 'lat': 51.469488, 'lon': -0.1782451,
        'osm': 'way/306984713 (Heliport House, SW11 3RP)'}
PLACES = [
  # id, name, kind, lat, lon, osm id, route?  (river bus pier renamed from Plantation Wharf in April 2025)
  ('path', 'Thames Path', 'The riverside walk passes the door', 51.470765, -0.178441, 'Thames Path relation, by the river 140 m north', 'door'),
  ('pier', "St Mary's Wandsworth Pier", 'River bus, Uber Boat by Thames Clippers', 51.467097, -0.182413, 'node/3846551161', 'walk'),
  ('clapham', 'Clapham Junction', 'National Rail and London Overground', 51.464459, -0.170518, 'node/5735001231', 'walk'),
  ('northcote', 'Northcote Road', 'Independent shops, cafés and restaurants', 51.4605, -0.1665, 'way/4348721', 'walk'),
  ('lake', 'Battersea Park', 'The boating lake', 51.478398, -0.15412, 'relation/1115029', 'walk'),
  ('power', 'Battersea Power Station', 'Shops, restaurants and the Northern line', 51.481775, -0.144552, 'way/4965216', 'walk'),
  ('chelsea', 'Chelsea Harbour', 'Across the river', 51.474058, -0.179741, 'node/1141549036', 'line'),
  ('imperial', 'Imperial Wharf', 'London Overground, across the river', 51.475103, -0.182927, 'node/3749159483', 'line'),
]

def hav(a, b):
    R = 6371.0088
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))

def dp(pts, eps_m):
    """Douglas Peucker on [lon, lat] in metres (local equirectangular)."""
    if len(pts) < 3: return pts
    lat0 = math.radians(pts[0][1])
    xy = [(p[0] * 111320 * math.cos(lat0), p[1] * 110540) for p in pts]
    keep = [False] * len(pts); keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i, j = stack.pop()
        ax, ay = xy[i]; bx, by = xy[j]; dx, dy = bx - ax, by - ay; L = math.hypot(dx, dy) or 1e-9
        best, k = -1, -1
        for m in range(i + 1, j):
            px, py = xy[m]
            d = abs(dy * px - dx * py + bx * ay - by * ax) / L
            if d > best: best, k = d, m
        if best > eps_m:
            keep[k] = True; stack += [(i, k), (k, j)]
    return [p for p, f in zip(pts, keep) if f]

def get(url, data=None):
    req = urllib.request.Request(url, data=data, headers=UA)
    return json.load(urllib.request.urlopen(req, timeout=60))

places = []
for pid, name, kind, lat, lon, osm, mode in PLACES:
    p = {'id': pid, 'name': name, 'kind': kind, 'lat': lat, 'lon': lon, 'osm': osm,
         'straight_km': round(hav((SITE['lat'], SITE['lon']), (lat, lon)), 2), 'mode': mode}
    if mode == 'walk':
        u = (f'https://routing.openstreetmap.de/routed-foot/route/v1/driving/'
             f'{SITE["lon"]},{SITE["lat"]};{lon},{lat}?overview=full&geometries=geojson')
        d = get(u)
        r = d['routes'][0]
        p['walk_km'] = round(r['distance'] / 1000, 1)
        p['walk_min'] = int(round(r['duration'] / 60))
        p['route'] = [[round(x, 6), round(y, 6)] for x, y in dp(r['geometry']['coordinates'], 4)]
        time.sleep(1.1)
    places.append(p)
    print(pid, {k: v for k, v in p.items() if k != 'route'}, len(p.get('route', [])), 'route points')

# the Thames Path national trail, both banks, around the map view
bbox = '51.458,-0.200,51.488,-0.138'
q = f'[out:json][timeout:60];rel["route"~"foot|hiking"]["name"~"Thames Path",i]({bbox})->.r;way(r.r)({bbox});out geom;'
d = None
for host in ('https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter', 'https://lz4.overpass-api.de/api/interpreter'):
    for attempt in range(3):
        try:
            d = get(host, urllib.parse.urlencode({'data': q}).encode()); break
        except Exception as e:
            print('overpass retry', host, e); time.sleep(4)
    if d: break
lines = []
for e in d['elements']:
    g = [[round(pt['lon'], 6), round(pt['lat'], 6)] for pt in e.get('geometry', [])]
    if len(g) >= 2: lines.append(dp(g, 3))
print('thames path ways', len(lines), sum(len(l) for l in lines), 'points')

out = {
  'note': 'Coordinates from OpenStreetMap (ODbL). Walking routes from the OSRM foot profile on routing.openstreetmap.de, '
          'computed once on the build date; times and distances are approximate.',
  'built': time.strftime('%Y-%m-%d'),
  'site': SITE, 'places': places,
  'thamesPath': {'type': 'MultiLineString', 'coordinates': lines},
}
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
print('wrote', OUT, os.path.getsize(OUT) // 1024, 'KB')
