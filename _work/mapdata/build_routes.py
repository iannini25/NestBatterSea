# Precompute the walking and driving route from Nest Battersea to every place of the map page.
# python -I build_routes.py  ->  routes_raw.json (next to this script)
#
# Router: OSRM on routing.openstreetmap.de (FOSSGIS), profiles routed-foot and routed-car,
# OpenStreetMap data (ODbL). overview=full, geometries=geojson, steps=true.
# The river is crossed on bridges only: the foot profile also knows the river bus (a "ferry"
# step), and the car profile can take the Woolwich style ferries. A route with a ferry step is
# rejected and asked again through each Thames bridge nearby; the shortest of those is kept.
import json, os, sys, time, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from places_src import P, SITE

UA = {'User-Agent': 'NestBatterseaSiteBuild/1.0 (static site, one off build script)'}
BASE = {'foot': 'https://routing.openstreetmap.de/routed-foot/route/v1/foot/',
        'car': 'https://routing.openstreetmap.de/routed-car/route/v1/driving/'}
# the middle of each bridge deck (OpenStreetMap)
BRIDGES = {
    'Wandsworth Bridge': (-0.187725, 51.464877),
    'Battersea Bridge': (-0.172500, 51.481111),
    'Albert Bridge': (-0.166700, 51.482300),
    'Chelsea Bridge': (-0.150000, 51.484722),
    'Putney Bridge': (-0.213300, 51.466600),
}

def osrm(mode, pts):
    coords = ';'.join(f'{x:.6f},{y:.6f}' for x, y in pts)
    url = BASE[mode] + coords + '?overview=full&geometries=geojson&steps=true&continue_straight=true'
    for k in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                d = json.load(r)
            if d.get('code') == 'Ok': return d['routes'][0]
            print('  osrm', d.get('code'), d.get('message'))
            return None
        except Exception as e:
            print('  retry', mode, e); time.sleep(3 + 4 * k)
    return None

def has_ferry(rt):
    return any(s.get('mode') == 'ferry' for l in rt['legs'] for s in l['steps'])

def steps(rt):
    return [s for l in rt['legs'] for s in l['steps']]

def summarise(rt):
    # the named roads that carry most of the route, in route order
    dist = {}
    order = []
    for s in steps(rt):
        n = (s.get('name') or '').strip()
        if not n or s.get('mode') == 'ferry': continue
        if n not in dist: order.append(n)
        dist[n] = dist.get(n, 0) + s['distance']
    top = sorted(dist, key=lambda n: -dist[n])[:3]
    via = [n for n in order if n in top]
    bridge = next((n for n in order if 'Bridge' in n and n not in ('Bridges Court',) and dist[n] > 40), None)
    return via, bridge

def route(mode, dest):
    a = (SITE['lon'], SITE['lat'])
    b = (dest['lon'], dest['lat'])
    rt = osrm(mode, [a, b])
    forced = None
    if rt is None or has_ferry(rt):
        best = None
        for name, xy in BRIDGES.items():
            r2 = osrm(mode, [a, xy, b])
            time.sleep(.6)
            if r2 is None or has_ferry(r2): continue
            if best is None or r2['duration'] < best[1]['duration']: best = (name, r2)
        if best is None: raise SystemExit(f'no bridge route for {dest["id"]} {mode}')
        forced, rt = best
    coords = [[round(x, 6), round(y, 6)] for x, y in rt['geometry']['coordinates']]
    via, bridge = summarise(rt)
    return {'s': round(rt['duration']), 'm': round(rt['distance']), 'line': coords, 'via': via,
            'bridge': bridge or forced, 'forced_via': forced}

OUTF = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'routes_raw.json')
ONLY = sys.argv[1:]          # ids to (re)compute; the others are kept from the last run
out = {'built': time.strftime('%Y-%m-%d'), 'router': 'OSRM, routing.openstreetmap.de (FOSSGIS), OpenStreetMap data ODbL', 'routes': {}}
if ONLY and os.path.exists(OUTF):
    out['routes'] = json.load(open(OUTF, encoding='utf-8'))['routes']
for p in P:
    if ONLY and p['id'] not in ONLY: continue
    out['routes'][p['id']] = {}
    for mode in ('foot', 'car'):
        r = route(mode, p)
        out['routes'][p['id']][mode] = r
        print(f"{p['id']:11s} {mode:4s} {r['s']/60:5.1f} min {r['m']/1000:5.2f} km  bridge={r['bridge']}  forced={r['forced_via']}  via={r['via']}")
        time.sleep(.8)
json.dump(out, open(OUTF, 'w', encoding='utf-8'), ensure_ascii=False)
