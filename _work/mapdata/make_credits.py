# Write assets/map/credits.html: every photograph of the map page with its author and licence,
# and the map data credits. The map page links it from its attribution control ("Photo credits").
#   python make_credits.py
import json, os, re, html
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
D = json.load(open(os.path.join(ROOT, 'assets', 'map', 'places.json'), encoding='utf-8'))
clean = lambda s: html.escape(re.sub(r'\s+', ' ', re.sub(r'[‐-―−-]', ' ', s or '')).strip())
rows = []
for p in D['places']:
    ph = p['photo']
    rows.append(f'<li><img src="photos/{p["id"]}-sq.webp" alt="" width="52" height="52" loading="lazy"><span><b>{clean(p["name"])}</b>'
                f'<br>Photo by <a href="{html.escape(ph["page"])}">{clean(ph["author"])}</a>, <a href="{html.escape(ph["licenceUrl"])}">{clean(ph["licence"])}</a>, '
                f'via Wikimedia Commons, cropped and resized.</span></li>')
page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Nest Battersea | Map credits</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600&amp;display=swap">
<style>
:root{{--page:#0f1116;--surf:#1a1d25;--line:rgba(255,255,255,.075);--blue:#92B7CA;--paper:#f3efe8;--p2:rgba(243,239,232,.74);--p3:rgba(243,239,232,.5)}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--page);color:var(--paper);font-family:'Poppins',system-ui,sans-serif;font-weight:300;line-height:1.55;padding:28px 16px 48px}}
main{{max-width:760px;margin:0 auto;display:grid;gap:14px}}
.logo img{{height:34px;width:auto}}
.eyebrow{{font-size:10.5px;font-weight:500;letter-spacing:.22em;text-transform:uppercase;color:var(--blue);margin-top:18px}}
h1{{font-size:28px;font-weight:600;letter-spacing:-.03em}}
p,li{{font-size:13px;color:var(--p2)}}
a{{color:var(--paper)}}
ol{{list-style:none;display:grid;gap:10px;margin-top:6px}}
li{{display:grid;grid-template-columns:52px 1fr;gap:14px;align-items:center;padding:10px;border-radius:16px;background:var(--surf);border:1px solid var(--line)}}
li img{{width:52px;height:52px;border-radius:12px;object-fit:cover}}
b{{color:var(--paper);font-weight:500}}
.back{{display:inline-flex;align-items:center;height:44px;padding:0 20px;border-radius:999px;background:var(--blue);color:#161922;text-decoration:none;font-weight:500;font-size:13.5px;justify-self:start}}
</style></head>
<body><main>
<a class="logo" href="../../index.html"><img src="../brand/logo-light.png" alt="Nest Battersea" width="300" height="150"></a>
<p class="eyebrow">Credits</p>
<h1>Photographs and map data</h1>
<p>Map data © OpenStreetMap contributors (ODbL). Vector tiles by OpenFreeMap. Satellite imagery © Esri, Maxar, Earthstar Geographics and the GIS User Community. Routes by OSRM on routing.openstreetmap.de (FOSSGIS), computed once and stored with the page; they cross the Thames on its bridges only. Times are approximate and drives are without traffic.</p>
<p>The photographs of the places are from Wikimedia Commons, each under the licence named beside it.</p>
<ol>
{chr(10).join(rows)}
</ol>
<a class="back" href="../../map.html">Back to the map</a>
</main></body></html>
'''
open(os.path.join(ROOT, 'assets', 'map', 'credits.html'), 'w', encoding='utf-8').write(page)
print('wrote credits.html,', len(rows), 'photographs')
