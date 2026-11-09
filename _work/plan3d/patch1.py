import os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

def patch(path, pairs):
    s = open(path, encoding='utf-8').read()
    for o, n in pairs:
        assert o in s, (path, o[:80])
        s = s.replace(o, n)
    open(path, 'w', encoding='utf-8').write(s)

patch('build.js', [
("""  const slab = (poly, t, topMat, sideMat, tile) => {
    const shape = new THREE.Shape(poly.map((p) => { const [x, z] = P(p); return new THREE.Vector2(x, -z); }));
    const geo = new THREE.ExtrudeGeometry(shape, { depth: t, bevelEnabled: false });
    scaleUV(geo, 1 / tile);
    const m = new THREE.Mesh(geo, [topMat, sideMat]);""",
"""  const slab = (poly, t, topMat, sideMat, tile, bottomMat = sideMat) => {
    const shape = new THREE.Shape(poly.map((p) => { const [x, z] = P(p); return new THREE.Vector2(x, -z); }));
    const geo = new THREE.ExtrudeGeometry(shape, { depth: t, bevelEnabled: false });
    scaleUV(geo, 1 / tile);
    // ExtrudeGeometry puts both lids in group 0: the first half is the bottom lid
    const g0 = geo.groups[0];
    const half = g0.count / 2;
    geo.groups.splice(0, 1, { start: g0.start, count: half, materialIndex: 2 }, { start: g0.start + half, count: half, materialIndex: 0 });
    const m = new THREE.Mesh(geo, [topMat, sideMat, bottomMat]);"""),
("""      const m = slab(room.poly, slabT, mat, upper ? M.wall() : M.slab(), tile);""",
 """      const m = slab(room.poly, slabT, mat, upper ? M.wall() : M.slab(), tile, upper ? M.ceiling() : M.slab());"""),
("""      const c = slab(room.poly, 0.02, M.ceiling(), M.ceiling(), 4);
      c.position.y = ch;
      c.castShadow = false;
      interior.add(c);""",
"""      const c = slab(room.poly, 0.02, M.ceiling(), M.ceiling(), 4);
      c.position.y = ch;
      c.castShadow = false;
      interior.add(c);
      // recessed downlights on a 1.6 m grid
      const pts = room.poly.map(P);
      let mnx = Infinity, mxx = -Infinity, mnz = Infinity, mxz = -Infinity;
      pts.forEach(([x, z]) => { mnx = Math.min(mnx, x); mxx = Math.max(mxx, x); mnz = Math.min(mnz, z); mxz = Math.max(mxz, z); });
      const nx = Math.max(1, Math.round((mxx - mnx) / 1.6)), nz = Math.max(1, Math.round((mxz - mnz) / 1.6));
      for (let i = 0; i < nx; i++) for (let k = 0; k < nz; k++) {
        const dl = new THREE.Mesh(new THREE.CircleGeometry(0.045, 20), M.bulb());
        dl.rotation.x = Math.PI / 2;
        dl.position.set(mnx + ((i + 0.5) * (mxx - mnx)) / nx, ch - 0.005, mnz + ((k + 0.5) * (mxz - mnz)) / nz);
        interior.add(dl);
      }"""),
("""        case 'pendantRound': o = F.pendantRound(); o.position.y = 1.85; lights.push({ at: f.at, y: 1.8, i: 8 }); break;""",
"""        case 'pendantRound': o = F.pendantRound(); o.position.y = 1.85; lights.push({ at: f.at, y: 1.8, i: 8 }); break;
        case 'art': o = F.art(f.w, f.h, f.tone); o.position.y = f.y || 0.9; break;
        case 'door': o = F.door(f.w); break;"""),
("""  // poses in world metres""","""  // meshes that only belong in the eye level views (mirrors)
  levels.forEach((lv) => {
    lv.interiorOnly = [];
    lv.group.traverse((o) => { if (o.userData.interiorOnly) { lv.interiorOnly.push(o); o.visible = false; } });
  });

  // facade context for the exterior arrival frame: the slab above the home with its
  // dark bronze edge and warm timber soffit, as on the official render
  const facade = new THREE.Group();
  facade.name = 'facade';
  facade.visible = false;
  const topY = apt.levels.length * apt.floorToFloor;
  const all = [];
  apt.levels.forEach((lv) => lv.rooms.forEach((r) => all.push(r.poly)));
  ex.planting.forEach((p) => all.push(p));
  ex.paving.forEach((p) => all.push(p));
  for (const poly of all) {
    const sl = slab(poly, 0.42, M.slab(), M.bronze(), 1, M.soffit());
    sl.position.y = topY;
    facade.add(sl);
  }
  for (const e of apt.facadeEdge || []) {
    const [ax, az] = P(e[0]), [bx, bz] = P(e[1]);
    const L = Math.hypot(bx - ax, bz - az);
    const grp = new THREE.Group();
    grp.position.set(ax, topY, az);
    grp.rotation.y = Math.atan2(-(bz - az), bx - ax);
    F.box(grp, L, 1.1, 0.015, M.glass(), L / 2, 0.42, 0, { cast: false });
    F.box(grp, L, 0.04, 0.05, M.bronze(), L / 2, 1.52, 0);
    facade.add(grp);
  }
  root.add(facade);

  // poses in world metres"""),
("""  return { root, levels, poses, size, P };""", """  return { root, levels, poses, size, P, facade };"""),
("""    for (let x = minx + 0.2; x < maxx; x += 0.42) {
      for (let z = minz + 0.2; z < maxz; z += 0.42) {""", """    for (let x = minx + 0.15; x < maxx; x += 0.3) {
      for (let z = minz + 0.15; z < maxz; z += 0.3) {"""),
("""        if (inside(x + jx, z + jz)) blobs.push([x + jx, 0.25 + (seed % 7) * 0.025, z + jz, 0.26, 0.2, 0.26]);""",
 """        if (inside(x + jx, z + jz)) blobs.push([x + jx, 0.32 + (seed % 9) * 0.035, z + jz, 0.24, 0.26, 0.24]);"""),
("""    if (blobs.length) F.foliage(ext, blobs, { count: Math.min(5000, blobs.length * 70), size: 0.1, seed: blobs.length, colors: [0, 1, 2, 3, 4] });""",
 """    if (blobs.length) F.foliage(ext, blobs, { count: Math.min(12000, blobs.length * 150), size: 0.095, seed: blobs.length, colors: [0, 1, 2, 3, 4] });"""),
])

patch('furniture.js', [
("""  mir.rotation.x = Math.PI / 2;
  mir.position.y = 1.55;""", """  mir.rotation.x = Math.PI / 2;
  mir.position.y = 1.55;
  mir.userData.interiorOnly = true;"""),
("""export { PALETTE };""", """// framed canvas hung on a wall, front facing +Z, bottom edge at y = 0
export function art(w = 1.2, h = 0.9, tone = 0) {
  const g = new THREE.Group();
  box(g, w, h, 0.035, M.oakDark(), 0, 0, 0);
  const c = document.createElement('canvas');
  c.width = 512; c.height = Math.round((512 * h) / w);
  const x = c.getContext('2d');
  const tones = [['#e9e1d3', '#c9b49a', '#a86440', '#8f9c82'], ['#efe8de', '#d6c8b2', '#5d6b78', '#b8925a']][tone % 2];
  x.fillStyle = tones[0]; x.fillRect(0, 0, c.width, c.height);
  x.fillStyle = tones[1]; x.beginPath(); x.ellipse(c.width * 0.36, c.height * 0.58, c.width * 0.26, c.height * 0.3, 0.3, 0, Math.PI * 2); x.fill();
  x.fillStyle = tones[2]; x.beginPath(); x.ellipse(c.width * 0.66, c.height * 0.42, c.width * 0.15, c.height * 0.2, -0.4, 0, Math.PI * 2); x.fill();
  x.strokeStyle = tones[3]; x.lineWidth = 7; x.beginPath(); x.moveTo(c.width * 0.12, c.height * 0.8); x.bezierCurveTo(c.width * 0.4, c.height * 0.2, c.width * 0.7, c.height * 0.95, c.width * 0.9, c.height * 0.3); x.stroke();
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  const m = new THREE.Mesh(new THREE.PlaneGeometry(w - 0.06, h - 0.06), new THREE.MeshStandardMaterial({ map: t, roughness: 0.9 }));
  m.position.set(0, h / 2, 0.019);
  g.add(m);
  return g;
}

// closed front door in oak with a brass pull, front facing +Z
export function door(w = 0.95) {
  const g = new THREE.Group();
  box(g, w, 2.2, 0.06, M.oakDark(), 0, 0, 0);
  box(g, 0.025, 0.6, 0.03, M.brass(), w / 2 - 0.12, 0.8, 0.045);
  box(g, w + 0.12, 0.06, 0.08, M.bronze(), 0, 2.2, 0);
  return g;
}

export { PALETTE };"""),
])

patch('materials.js', [
("""  clothes: (i) => cached('clothes' + i, () => new THREE.MeshStandardMaterial({ color: [0xe8e2d8, 0x8b9a86, 0x2f3540, 0xc9b49a, 0xa86440, 0xf3f0ea][i % 6], roughness: 0.95 })),""",
 """  clothes: (i) => cached('clothes' + i, () => new THREE.MeshStandardMaterial({ color: [0xe8e2d8, 0xa9b0a0, 0x4a4e57, 0xcdbba3, 0xb08a6e, 0xf3f0ea][i % 6], roughness: 0.95 })),
  soffit: () => cached('soffit', () => new THREE.MeshStandardMaterial({ map: oakVeneerTexture(), color: 0xd9b48c, roughness: 0.6 })),"""),
])
print('patched')
