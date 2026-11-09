import os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

def patch(path, pairs):
    s = open(path, encoding='utf-8').read()
    for o, n in pairs:
        assert o in s, (path, o[:80])
        s = s.replace(o, n)
    open(path, 'w', encoding='utf-8').write(s)

patch('apartments.js', [
# LOFT 4 lower: the shower room keeps no photo; the lower en suite is identical to the upper one
("""        { id: 'shower', name: 'Shower room', poly: [[1240, 667], [1305, 667], [1305, 778], [1240, 778]], floor: 'stone', photo: 'loft4-shower', hot: [1272, 722] },""",
 """        { id: 'shower', name: 'Shower room', poly: [[1240, 667], [1305, 667], [1305, 778], [1240, 778]], floor: 'stone' },"""),
("""        { id: 'ensuite1', name: 'En suite', poly: [[1380, 667], [1447, 667], [1447, 778], [1380, 778]], floor: 'stone', photo: 'loft4-ensuite', hot: [1413, 722] },""",
 """        { id: 'ensuite1', name: 'En suite', poly: [[1380, 667], [1447, 667], [1447, 778], [1380, 778]], floor: 'stone' },"""),
# upper landing gets the gallery view over the double height living room
("""        { id: 'landing', name: 'Landing', poly: [[1131, 507], [1236, 507], [1236, 618], [1305, 618], [1305, 662], [1163, 662], [1163, 559], [1131, 559]], floor: 'oak' },""",
 """        { id: 'landing', name: 'Gallery landing', poly: [[1131, 507], [1236, 507], [1236, 618], [1305, 618], [1305, 662], [1163, 662], [1163, 559], [1131, 559]], floor: 'oak', photo: 'loft4-gallery', hot: [1190, 590] },"""),
# Bungalow 3: the shower room keeps no photo, the en suite is the bathroom photo, the garden is clickable
("""        { id: 'shower', name: 'Shower room', poly: [[787, 510], [905, 510], [905, 550], [787, 550]], floor: 'stone' , photo: 'bung3-bath', hot: [845, 530] },""",
 """        { id: 'shower', name: 'Shower room', poly: [[787, 510], [905, 510], [905, 550], [787, 550]], floor: 'stone' },
        { id: 'garden', name: 'Private garden', poly: [[337, 280], [622, 280], [622, 327], [490, 327], [490, 550], [473, 550], [473, 532]], floor: 'none', exterior: true, photo: 'bung3-garden', hot: [430, 330] },"""),
# en suite vanity on the north wall so the view through the door is clear
("""        { t: 'vanity', at: [918, 490], w: 0.7, d: 0.4, r: 90 },""",
 """        { t: 'vanity', at: [928, 477], w: 0.7, d: 0.4, r: 0 },"""),
("""    'loft4-ensuite': { level: 'upper', eye: [1350, 716, 1.6], look: [1447, 722, 0.9], fov: 70 },""",
 """    'loft4-ensuite': { level: 'upper', eye: [1383, 716, 1.6], look: [1447, 716, 1.0], fov: 88 },
    'loft4-gallery': { level: 'upper', eye: [1196, 530, 1.6], look: [1372, 392, 0.2], fov: 78 },"""),
("""    'bung3-bath': { level: 'main', eye: [745, 472, 1.65], look: [742, 550, 0.75], fov: 82 },
    'bung3-ensuite': { level: 'main', eye: [880, 486, 1.6], look: [988, 512, 0.9], fov: 78 },""",
 """    'bung3-bath': { level: 'main', eye: [733, 478, 1.65], look: [737, 550, 0.7], fov: 90 },
    'bung3-ensuite': { level: 'main', eye: [916, 543, 1.6], look: [985, 470, 0.95], fov: 86 },"""),
])

# rooms with floor 'none' (exterior zones) must not build a floor slab
patch('build.js', [
("""    for (const room of lv.rooms) {
      const mat = room.floor === 'stone' ? M.tiles() : M.oakFloor();""",
 """    for (const room of lv.rooms) {
      if (room.floor === 'none') {
        rooms.push({ ...room, level: li, mesh: null, polyM: room.poly.map(P), hotM: room.hot ? P(room.hot) : null });
        continue;
      }
      const mat = room.floor === 'stone' ? M.tiles() : M.oakFloor();"""),
])
print('patched')
