import os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

def patch(path, pairs):
    s = open(path, encoding='utf-8').read()
    for o, n in pairs:
        assert o in s, (path, o[:80])
        s = s.replace(o, n)
    open(path, 'w', encoding='utf-8').write(s)

patch('build.js', [
("""  root.add(facade);

  // poses in world metres""",
"""  // dark bronze cladding on the solid parts of the facade (exterior views only)
  for (const c of apt.cladding || []) {
    const [ax, az] = P([c[0], c[1]]), [bx, bz] = P([c[2], c[3]]);
    const h = c[4] || topY;
    F.box(facade, Math.max(0.03, bx - ax), h, Math.max(0.03, bz - az), M.cladding(), (ax + bx) / 2, -0.3, (az + bz) / 2);
  }
  root.add(facade);

  // poses in world metres"""),
])

patch('materials.js', [
("""  soffit: () => cached('soffit', () => new THREE.MeshStandardMaterial({ map: oakVeneerTexture(), color: 0xd9b48c, roughness: 0.6 })),""",
 """  soffit: () => cached('soffit', () => new THREE.MeshStandardMaterial({ map: oakVeneerTexture(), color: 0xb79a7c, roughness: 0.6 })),
  cladding: () => cached('cladding', () => new THREE.MeshStandardMaterial({ color: 0x3e3530, roughness: 0.55, metalness: 0.35 })),"""),
])

patch('apartments.js', [
# LOFT 4: the tree sits at the south end of the garden, left of the open door
("""    trees: [{ at: [1431, 410], h: 2.6 }, { at: [1340, 296], h: 1.5, shrub: true }, { at: [1180, 296], h: 1.3, shrub: true }],""",
 """    trees: [{ at: [1433, 462], h: 2.7 }, { at: [1340, 296], h: 1.5, shrub: true }, { at: [1180, 296], h: 1.3, shrub: true }],"""),
("""  facadeEdge: [[[1075, 280], [1465, 280]], [[1465, 280], [1465, 488]]],""",
 """  facadeEdge: [[[1075, 280], [1465, 280]], [[1465, 280], [1465, 488]]],
  // the full height solid wall south of the garden (the dark strip of the official render)
  cladding: [[1465, 488, 1470, 796, 6.6], [1399, 488, 1470, 507, 6.6]],"""),
("""    'loft4-arrive': { level: 'lower', eye: [1760, 408, 2.55], look: [1380, 408, 2.55], fov: 56 },""",
 """    'loft4-arrive': { level: 'lower', eye: [1880, 404, 3.0], look: [1380, 404, 3.0], fov: 56 },"""),
("""  facadeEdge: [[[473, 550], [337, 280]], [[337, 280], [622, 280]], [[738, 280], [943, 280]]],""",
 """  facadeEdge: [[[473, 550], [337, 280]], [[337, 280], [622, 280]], [[738, 280], [943, 280]]],
  cladding: [[622, 276, 738, 300, 3.5], [795, 276, 867, 300, 3.5], [943, 276, 988, 300, 3.5]],"""),
])
print('patched')
