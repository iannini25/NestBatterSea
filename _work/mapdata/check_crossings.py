# Independent check: every place where a stored route crosses the Thames centreline
# (waterway=river, River Thames, from OpenStreetMap via Overpass) must be on a bridge.
#   python check_crossings.py   (reads ../../assets/map/places.json)
import json, os, math, urllib.request, urllib.parse
HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, '..', '..', 'assets', 'map', 'places.json'), encoding='utf-8'))
cache = os.path.join(HERE, 'thames_centreline.json')
if not os.path.exists(cache):
    q = '[out:json][timeout:60];way["waterway"="river"]["name"="River Thames"](51.44,-0.24,51.50,-0.12);out geom;'
    req = urllib.request.Request('https://overpass-api.de/api/interpreter', data=urllib.parse.urlencode({'data': q}).encode(), headers={'User-Agent': 'NestBatterseaSiteBuild/1.0'})
    d = json.load(urllib.request.urlopen(req, timeout=90))
    json.dump([[[p['lon'], p['lat']] for p in w['geometry']] for w in d['elements']], open(cache, 'w'))
river = json.load(open(cache))
BR = {'Wandsworth Bridge': (-0.187725, 51.464877), 'Battersea Bridge': (-0.1725, 51.481111), 'Albert Bridge': (-0.1667, 51.4823),
      'Chelsea Bridge': (-0.15, 51.484722), 'Putney Bridge': (-0.2133, 51.4666), 'Battersea Railway Bridge': (-0.179167, 51.473056)}
def m(a, b): return math.hypot((a[0] - b[0]) * 69400, (a[1] - b[1]) * 110540)
def inter(p1, p2, p3, p4):
    d = (p2[0] - p1[0]) * (p4[1] - p3[1]) - (p2[1] - p1[1]) * (p4[0] - p3[0])
    if d == 0: return None
    t = ((p3[0] - p1[0]) * (p4[1] - p3[1]) - (p3[1] - p1[1]) * (p4[0] - p3[0])) / d
    u = ((p3[0] - p1[0]) * (p2[1] - p1[1]) - (p3[1] - p1[1]) * (p2[0] - p1[0])) / d
    return (p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1])) if 0 <= t <= 1 and 0 <= u <= 1 else None
bad = 0
for p in D['places']:
    for mode in ('foot', 'car'):
        line = p[mode]['line']
        xs = []
        for i in range(len(line) - 1):
            for w in river:
                for j in range(len(w) - 1):
                    x = inter(line[i], line[i + 1], w[j], w[j + 1])
                    if x: xs.append(x)
        for x in xs:
            name, dist = min(((n, m(x, c)) for n, c in BR.items()), key=lambda t: t[1])
            ok = dist < 120 and name != 'Battersea Railway Bridge'
            bad += not ok
            print(f"{p['id']:10s} {mode:4s} crosses at {x[1]:.5f},{x[0]:.5f}  nearest {name} {dist:.0f} m  {'OK' if ok else 'NOT ON A BRIDGE'}")
print('river ways', len(river), '· crossings off a bridge:', bad)
