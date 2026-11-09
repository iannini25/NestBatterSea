# Geocode a few names with Nominatim (1 request a second, as its policy asks).
import json, urllib.request, urllib.parse, sys, time
UA = {'User-Agent': 'NestBatterseaSiteBuild/1.0 (static site, one off build script)'}
for q in sys.argv[1:]:
    url = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode({'q': q, 'format': 'jsonv2', 'limit': 2, 'viewbox': '-0.23,51.50,-0.12,51.44', 'bounded': 1})
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        d = json.load(r)
    for x in d:
        print(f"{q:40s} {float(x['lat']):.6f} {float(x['lon']):.6f} {x['osm_type']}/{x['osm_id']} {x['category']}:{x['type']} | {x['display_name'][:80]}")
    if not d: print(f"{q:40s} NONE")
    time.sleep(1.1)
