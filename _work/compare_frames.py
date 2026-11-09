# side-by-side: generated frame | official imagery at the tracked framing
import json, sys, subprocess, tempfile, os
from PIL import Image
from nestgeo import Sources
video, report, out = sys.argv[1], sys.argv[2], sys.argv[3]
picks = [int(x) for x in sys.argv[4].split(',')]
rows = {r['frame']: r for r in json.load(open(report))['rows']}
src = Sources()
tiles = []
for f in picks:
    d = tempfile.mkdtemp()
    subprocess.run(['ffmpeg','-v','error','-i',video,'-vf',f'select=eq(n\,{f})','-frames:v','1',os.path.join(d,'a.png')],check=True)
    a = Image.open(os.path.join(d,'a.png')).convert('RGB').resize((800,450))
    r = rows[f]
    b = src.view(r['cx'], r['cy'], r['w'], out=(800,450))
    t = Image.new('RGB',(1610,450)); t.paste(a,(0,0)); t.paste(b,(810,0)); tiles.append(t)
H = sum(t.height for t in tiles) + 10*(len(tiles)-1)
c = Image.new('RGB',(1610,H),(255,255,255)); y=0
for t in tiles: c.paste(t,(0,y)); y += t.height+10
c.save(out, quality=88)
