import os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

def patch(path, pairs):
    s = open(path, encoding='utf-8').read()
    for o, n in pairs:
        assert o in s, (path, o[:80])
        s = s.replace(o, n)
    open(path, 'w', encoding='utf-8').write(s)

patch('build.js', [
# stone lining on the walls of wet rooms, only where a wall really exists (door gaps stay open)
("""    // walls: lower walls rise to the ceiling, upper walls also fill the slab below them""",
"""    // wet rooms: large format stone on the walls, wherever the room edge meets a wall
    const inWall = (px, py) => lv.walls.some((w) => px >= w[0] - 0.5 && px <= w[2] + 0.5 && py >= w[1] - 0.5 && py <= w[3] + 0.5);
    for (const room of lv.rooms) {
      if (room.floor !== 'stone') continue;
      const poly = room.poly;
      // centroid to know which side is inside
      let cxr = 0, cyr = 0;
      poly.forEach((p) => { cxr += p[0]; cyr += p[1]; });
      cxr /= poly.length; cyr /= poly.length;
      for (let i = 0; i < poly.length; i++) {
        const a = poly[i], b = poly[(i + 1) % poly.length];
        const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
        if (len < 2) continue;
        const ux = (b[0] - a[0]) / len, uy = (b[1] - a[1]) / len;
        let nx = -uy, ny = ux;
        const mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2;
        if ((cxr - mx) * nx + (cyr - my) * ny < 0) { nx = -nx; ny = -ny; }
        // walk the edge in 2 px steps and collect runs that are backed by a wall
        let run = null;
        const flush = (t1) => {
          if (!run) return;
          const t0 = run;
          run = null;
          if (t1 - t0 < 4) return;
          const pa = [a[0] + ux * t0 + nx * 0.4, a[1] + uy * t0 + ny * 0.4];
          const pb = [a[0] + ux * t1 + nx * 0.4, a[1] + uy * t1 + ny * 0.4];
          const [qax, qaz] = P(pa), [qbx, qbz] = P(pb);
          const L = Math.hypot(qbx - qax, qbz - qaz);
          const grp = new THREE.Group();
          grp.position.set(qax, 0, qaz);
          grp.rotation.y = Math.atan2(-(qbz - qaz), qbx - qax);
          F.box(grp, L, 2.4, 0.012, M.tiles(), L / 2, 0, 0, { cast: false });
          interior.add(grp);
        };
        for (let t = 0; t <= len; t += 2) {
          const backed = inWall(a[0] + ux * t - nx * 2, a[1] + uy * t - ny * 2);
          if (backed && run === null) run = t;
          if (!backed && run !== null) flush(t);
        }
        flush(len);
      }
    }

    // walls: lower walls rise to the ceiling, upper walls also fill the slab below them"""),
# bed throw colour option
("""        case 'bed': o = F.bed(f.w, f.d, f.single); break;""",
 """        case 'bed': o = F.bed(f.w, f.d, f.single, f.throw); break;"""),
])

patch('furniture.js', [
("""export function bed(w = 1.8, d = 2.05, single = false) {""",
 """export function bed(w = 1.8, d = 2.05, single = false, throwTone) {"""),
("""  rbox(g, w + 0.08, 0.035, 0.48, 0.017, single ? M.sage() : M.rust(), 0, frameH + 0.245, d / 2 - 0.36);""",
 """  const tm = throwTone === 'sage' ? M.sage() : throwTone === 'oat' ? M.oat() : throwTone === 'rust' ? M.rust() : single ? M.sage() : M.rust();
  rbox(g, w + 0.08, 0.035, 0.48, 0.017, tm, 0, frameH + 0.245, d / 2 - 0.36);"""),
])

patch('apartments.js', [
# lower bedroom gets a sage throw and art, so the two stacked bedrooms read as different rooms
("""        { t: 'bed', at: [1402.5, 584], w: 1.85, d: 2.05, r: -90 },
        { t: 'nightstand', at: [1438, 534], r: -90 }, { t: 'nightstand', at: [1438, 634], r: -90 },
        { t: 'armchair', at: [1340, 530], r: 135 },
        { t: 'dressing', box: [1309, 667, 1376, 778], sides: ['w', 's'] },
        { t: 'wc', at: [1292, 690], r: -90 },""",
 """        { t: 'bed', at: [1402.5, 584], w: 1.85, d: 2.05, r: -90, throw: 'sage' },
        { t: 'nightstand', at: [1438, 534], r: -90 }, { t: 'nightstand', at: [1438, 634], r: -90 },
        { t: 'armchair', at: [1340, 530], r: 135 },
        { t: 'art', at: [1328, 584], w: 1.1, h: 0.8, r: 90, y: 1.2, tone: 1 },
        { t: 'dressing', box: [1309, 667, 1376, 778], sides: ['w', 's'] },
        { t: 'wc', at: [1292, 690], r: -90 },"""),
# better bathroom and bedroom viewpoints
("""    'loft4-bed1': { level: 'lower', eye: [1318, 648, 1.55], look: [1440, 560, 0.9], fov: 64 },
    'loft4-shower': { level: 'lower', eye: [1272, 670, 1.6], look: [1272, 760, 1.0], fov: 70 },
    'loft4-ensuite': { level: 'upper', eye: [1384, 700, 1.6], look: [1447, 730, 0.9], fov: 72 },
    'loft4-bed2': { level: 'upper', eye: [1115, 466, 1.55], look: [1010, 360, 0.9], fov: 64 },
    'loft4-bed3': { level: 'upper', eye: [1178, 496, 1.55], look: [1190, 335, 1.3], fov: 66 },
    'loft4-bed4': { level: 'upper', eye: [1318, 648, 1.55], look: [1440, 560, 0.9], fov: 64 },
    'loft4-bath': { level: 'upper', eye: [1262, 672, 1.6], look: [1262, 770, 0.9], fov: 72 },""",
 """    'loft4-bed1': { level: 'lower', eye: [1314, 655, 1.6], look: [1447, 560, 0.85], fov: 74 },
    'loft4-shower': { level: 'lower', eye: [1205, 752, 1.6], look: [1305, 745, 1.0], fov: 74 },
    'loft4-ensuite': { level: 'upper', eye: [1350, 716, 1.6], look: [1447, 722, 0.9], fov: 70 },
    'loft4-bed2': { level: 'upper', eye: [1120, 470, 1.6], look: [1002, 372, 0.85], fov: 74 },
    'loft4-bed3': { level: 'upper', eye: [1176, 498, 1.6], look: [1196, 329, 1.25], fov: 74 },
    'loft4-bed4': { level: 'upper', eye: [1314, 655, 1.6], look: [1447, 590, 0.85], fov: 74 },
    'loft4-bath': { level: 'upper', eye: [1252, 669, 1.65], look: [1278, 778, 0.85], fov: 82 },"""),
("""    'bung3-bed2': { level: 'main', eye: [790, 456, 1.55], look: [745, 335, 0.9], fov: 66 },
    'bung3-bed1': { level: 'main', eye: [872, 455, 1.55], look: [985, 380, 0.9], fov: 66 },
    'bung3-bath': { level: 'main', eye: [740, 506, 1.6], look: [745, 548, 0.8], fov: 74 },
    'bung3-ensuite': { level: 'main', eye: [925, 472, 1.6], look: [975, 540, 0.9], fov: 74 },""",
 """    'bung3-bed2': { level: 'main', eye: [800, 458, 1.6], look: [735, 330, 0.85], fov: 74 },
    'bung3-bed1': { level: 'main', eye: [870, 458, 1.6], look: [988, 372, 0.85], fov: 74 },
    'bung3-bath': { level: 'main', eye: [745, 472, 1.65], look: [742, 550, 0.75], fov: 82 },
    'bung3-ensuite': { level: 'main', eye: [880, 486, 1.6], look: [988, 512, 0.9], fov: 78 },"""),
])
print('patched')
