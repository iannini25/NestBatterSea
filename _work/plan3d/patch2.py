import os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

def patch(path, pairs):
    s = open(path, encoding='utf-8').read()
    for o, n in pairs:
        assert o in s, (path, o[:80])
        s = s.replace(o, n)
    open(path, 'w', encoding='utf-8').write(s)

patch('viewer.js', [
# interior only meshes and an exterior mode for the arrival frame guide
("""  function setInterior(on) {
    interiorMode = on;
    for (const lv of model.levels) {
      lv.interior.visible = on;
      lv.group.visible = true;
      lv.group.position.y = lv.base;
    }""",
"""  function setInterior(on, exterior = false) {
    interiorMode = on;
    for (const lv of model.levels) {
      lv.interior.visible = on;
      lv.group.visible = true;
      lv.group.position.y = lv.base;
      lv.interiorOnly.forEach((o) => (o.visible = on));
    }
    model.facade.visible = on && exterior;"""),
])

patch('apartments.js', [
# LOFT 4: art above the lower sofa, front door, poses tuned, arrival frame pose
("""        { t: 'floorLamp', at: [1250, 492] },
        // dining and kitchen""",
"""        { t: 'floorLamp', at: [1250, 492] },
        { t: 'art', at: [1290, 506], w: 1.5, h: 1.05, r: 0, y: 1.25, tone: 0 },
        { t: 'door', at: [1160, 744], w: 0.9, r: 90 },
        // dining and kitchen"""),
("""    'loft4-living': { level: 'lower', eye: [1392, 410, 1.55], look: [1120, 432, 1.45], fov: 62 },""",
 """    'loft4-living': { level: 'lower', eye: [1368, 418, 1.5], look: [1120, 430, 2.05], fov: 66 },
    'loft4-arrive': { level: 'lower', eye: [1760, 408, 2.55], look: [1380, 408, 2.55], fov: 56 },"""),
("""  exterior: {
    planting: [[[1075, 280], [1465, 280], [1465, 488], [1398, 488], [1398, 312], [1075, 312]]],""",
 """  facadeEdge: [[[1075, 280], [1465, 280]], [[1465, 280], [1465, 488]]],
  exterior: {
    planting: [[[1075, 280], [1465, 280], [1465, 488], [1398, 488], [1398, 312], [1075, 312]]],"""),
# Bungalow 3: art on the long living room wall, front door, poses, arrival frame
("""        { t: 'floorLamp', at: [640, 520] },""",
 """        { t: 'floorLamp', at: [640, 520] },
        { t: 'art', at: [548, 547], w: 1.4, h: 1.0, r: 180, y: 1.2, tone: 1 },
        { t: 'door', at: [642, 644], w: 0.9, r: 180 },"""),
("""    'bung3-living': { level: 'main', eye: [560, 336, 1.55], look: [575, 560, 1.15], fov: 64 },""",
 """    'bung3-living': { level: 'main', eye: [562, 338, 1.5], look: [470, 560, 1.15], fov: 66 },
    'bung3-arrive': { level: 'main', eye: [562, 40, 1.6], look: [562, 327, 1.6], fov: 56 },"""),
("""  exterior: {
    planting: [
      [[337, 280], [473, 280], [473, 532]],""",
 """  facadeEdge: [[[473, 550], [337, 280]], [[337, 280], [622, 280]], [[738, 280], [943, 280]]],
  exterior: {
    planting: [
      [[337, 280], [473, 280], [473, 532]],"""),
])
print('patched')
