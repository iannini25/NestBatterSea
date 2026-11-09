# Probe English Wikipedia for coordinates and lead images of candidate places.
# python -I wiki_probe.py  -> prints a table, writes wiki_probe.json next to it
import json, urllib.request, urllib.parse, sys, os, time

UA = {'User-Agent': 'NestBatterseaSiteBuild/1.0 (static site, one off build script)'}
TITLES = sys.argv[1:] or []

def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)

def wiki(titles):
    q = {'action': 'query', 'format': 'json', 'redirects': 1, 'prop': 'coordinates|pageimages|description',
         'piprop': 'name|original', 'titles': '|'.join(titles)}
    return get('https://en.wikipedia.org/w/api.php?' + urllib.parse.urlencode(q))

out = {}
for i in range(0, len(TITLES), 20):
    d = wiki(TITLES[i:i + 20])
    norm = {n['to']: n['from'] for n in d['query'].get('normalized', []) + d['query'].get('redirects', [])}
    for p in d['query']['pages'].values():
        c = (p.get('coordinates') or [{}])[0]
        out[p.get('title')] = {'lat': c.get('lat'), 'lon': c.get('lon'), 'image': p.get('pageimage'), 'desc': p.get('description'), 'missing': 'missing' in p}
    time.sleep(1)
for k, v in out.items():
    print(f"{k:45s} {v['lat']} {v['lon']} {v['image']}  | {v['desc']}")
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wiki_probe.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
