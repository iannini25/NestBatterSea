# Quick Commons search: print title, licence and size for each query (no downloads).
import json, sys, urllib.request, urllib.parse, re, html
UA = {'User-Agent': 'NestBatterseaSiteBuild/1.0 (static site build)'}
for q in sys.argv[1:]:
    url = 'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode({'action': 'query', 'format': 'json', 'generator': 'search', 'gsrsearch': q + ' filetype:bitmap', 'gsrnamespace': 6, 'gsrlimit': 12,
                                                                              'prop': 'imageinfo', 'iiprop': 'size|extmetadata'})
    d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60))
    print('==', q)
    for p in sorted(d.get('query', {}).get('pages', {}).values(), key=lambda p: p.get('index', 99)):
        ii = p['imageinfo'][0]; lic = html.unescape(re.sub('<[^>]+>', '', ii.get('extmetadata', {}).get('LicenseShortName', {}).get('value', '')))
        print(f"   {ii['width']}x{ii['height']} {lic:14s} {p['title']}")
