# top down renders of every level, solo, for the hole check
cd /c/Users/berna/Desktop/NestBatterSea-LONDON/_work/plan3d
OUT=${1:-qa/after}
node render.mjs $OUT loft4 '[{"name":"l4-lower-top","top":{"level":0,"rect":[985,275,1475,800],"k":3,"solo":true}},{"name":"l4-upper-top","top":{"level":1,"rect":[985,275,1475,800],"k":3,"solo":true}}]'
node render.mjs $OUT bung3 '[{"name":"b3-top","top":{"level":0,"rect":[330,270,1010,670],"k":3,"solo":true}}]'
python holes.py qa/apts.json loft4 lower $OUT/l4-lower-top.png 985 275 1475 800 3 $OUT/l4-lower-holes.png
python holes.py qa/apts.json loft4 upper $OUT/l4-upper-top.png 985 275 1475 800 3 $OUT/l4-upper-holes.png
python holes.py qa/apts.json bung3 main $OUT/b3-top.png 330 270 1010 670 3 $OUT/b3-holes.png
