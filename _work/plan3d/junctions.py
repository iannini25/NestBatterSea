# Wall junction check: list pairs of walls (and walls against glass ends) that come within
# 3 px of each other without overlapping, which would show as a slit in the model.
# python junctions.py <apts.json>
import sys, json

A = json.load(open(sys.argv[1]))
TOL = 3.0
for aid, apt in A.items():
    for lv in apt['levels']:
        rects = [tuple(w) for w in lv['walls']]
        issues = []
        for i, a in enumerate(rects):
            for j, b in enumerate(rects):
                if j <= i:
                    continue
                # gap along x and along y (negative = overlap)
                gx = max(b[0] - a[2], a[0] - b[2])
                gy = max(b[1] - a[3], a[1] - b[3])
                if gx > 0 and gx <= TOL and gy < 0:
                    issues.append(f'  x gap {gx:.1f} px between {list(a)} and {list(b)}')
                if gy > 0 and gy <= TOL and gx < 0:
                    issues.append(f'  y gap {gy:.1f} px between {list(a)} and {list(b)}')
                if gx == 0 and gy < 0 or gy == 0 and gx < 0:
                    issues.append(f'  touching only (no overlap) {list(a)} and {list(b)}')
        # glass ends that stop short of a wall
        for g in lv.get('glass', []):
            for p in (g['a'], g['b']):
                near = min((max(r[0] - p[0], p[0] - r[2], 0) ** 2 + max(r[1] - p[1], p[1] - r[3], 0) ** 2) ** 0.5 for r in rects)
                if 0 < near <= TOL:
                    issues.append(f'  glass end {p} is {near:.1f} px from the nearest wall')
        print(f'{aid} {lv["id"]}: {len(issues)} issues')
        for s in issues:
            print(s)
