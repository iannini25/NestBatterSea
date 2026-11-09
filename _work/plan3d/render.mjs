// QA renders of the dollhouse from src/ (devqa.html) or from the site bundle (preview).
// node render.mjs <outDir> <apt> <jobs.json | inline json> [W] [H]
// Jobs (all coordinates in plan px, heights in metres above that level's floor):
//   { name, top: { level, rect: [x0, y0, x1, y1], k, clip } }     orthographic plan view, clip = section height
//   { name, orbit: { level, az, polar, zoom, target: [x, y, h] }, cut: true|false }
//   { name, pose: 'loft4-living' }                                  a photo pose (interior on)
//   { name, cam: { level, eye: [x, y, h], look: [x, y, h], fov }, interior: true|false }
import puppeteer from 'puppeteer-core';
import fs from 'fs';
const [, , outDir, apt = 'loft4', jobsArg = '[]', W = '1600', H = '900'] = process.argv;
const jobs = JSON.parse(fs.existsSync(jobsArg) ? fs.readFileSync(jobsArg, 'utf8') : jobsArg);
fs.mkdirSync(outDir, { recursive: true });
const browser = await puppeteer.launch({
  executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  headless: 'new',
  args: ['--ignore-gpu-blocklist', '--enable-gpu', '--use-angle=d3d11', '--no-sandbox'],
});
const page = await browser.newPage();
await page.setViewport({ width: +W, height: +H, deviceScaleFactor: 1 });
const logs = [];
page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') logs.push(m.type() + ': ' + m.text()); });
page.on('pageerror', (e) => logs.push('pageerror: ' + e.message));
await page.goto(`http://localhost:8080/_work/plan3d/${process.env.QA_PAGE || 'devqa.html'}?apt=${apt}`, { waitUntil: 'networkidle0' });
await page.waitForFunction('window.ready === true', { timeout: 20000 });
await new Promise((r) => setTimeout(r, 600));
let vp = [+W, +H];
for (const j of jobs) {
  const want = j.top ? [Math.round((j.top.rect[2] - j.top.rect[0]) * j.top.k), Math.round((j.top.rect[3] - j.top.rect[1]) * j.top.k)] : [j.W || +W, j.H || +H];
  if (want[0] !== vp[0] || want[1] !== vp[1]) {
    await page.setViewport({ width: want[0], height: want[1], deviceScaleFactor: 1 });
    vp = want;
    await new Promise((r) => setTimeout(r, 300));
  }
  const data = await page.evaluate(async (j) => {
    const v = window.viewer, T = window.THREE, m = v.model, A = window.APARTMENTS[m.root.name];
    const settle = (n = 48) => { for (let i = 0; i < n; i++) v.renderNow(); };
    const full = () => m.levels.forEach((l) => l.cuts.forEach((u) => { const c = u.userData.cut; if (!c.parts) { u.scale.y = 1; return; } c.top = c.full; c.parts.forEach((p) => { p.o.visible = true; p.o.scale.y = 1; }); }));
    v.setInterior(!!j.interior || !!j.pose, !!j.exterior);
    if (j.top) {
      const t = j.top;
      await v.setLevel(t.level, false);
      if (j.hideAbove) m.levels.forEach((l, k) => { l.group.visible = k <= t.level; });
      if (t.solo) m.levels.forEach((l, k) => { l.group.visible = k === t.level; });
      full();
      const lv = m.levels[t.level];
      const [ax, az] = m.P([t.rect[0], t.rect[1]]), [bx, bz] = m.P([t.rect[2], t.rect[3]]);
      const cam = new T.OrthographicCamera(-(bx - ax) / 2, (bx - ax) / 2, (bz - az) / 2, -(bz - az) / 2, 0.1, 300);
      cam.position.set((ax + bx) / 2, 80, (az + bz) / 2);
      cam.up.set(0, 0, -1);
      cam.lookAt((ax + bx) / 2, 0, (az + bz) / 2);
      v.renderer.clippingPlanes[0].constant = lv.base + (t.clip ?? A.wallH + 0.01);
      v.renderer.render(v.scene, cam);
      const url = v.renderer.domElement.toDataURL('image/png');
      await v.setLevel(t.level, false);
      return url;
    }
    if (j.pose) {
      v.setPose(j.pose);
      settle(4);
      return v.renderer.domElement.toDataURL('image/png');
    }
    if (j.cam || j.orbit) {
      let level, eye, look, fov;
      if (j.cam) {
        level = j.cam.level;
        const lvb = level * A.floorToFloor;
        const [ex, ez] = m.P(j.cam.eye), [lx, lz] = m.P(j.cam.look);
        eye = new T.Vector3(ex, lvb + j.cam.eye[2], ez);
        look = new T.Vector3(lx, lvb + j.cam.look[2], lz);
        fov = j.cam.fov;
      } else {
        const o = j.orbit;
        level = o.level || 0;
        await v.setLevel(level, false);
        await v.frame(false, o.az ?? -0.62, o.polar ?? 0.8);
        const fitDist = v.camera.position.distanceTo(v.controls.target);
        const lvb = m.levels[level].base;
        look = o.target ? (() => { const [x, z] = m.P(o.target); return new T.Vector3(x, lvb + (o.target[2] ?? 0.6), z); })() : new T.Vector3(0, lvb + 0.6, 0);
        const d = fitDist * (o.zoom ?? 1);
        const az = o.az ?? -0.62, po = o.polar ?? 0.8;
        eye = look.clone().add(new T.Vector3(Math.sin(po) * Math.sin(az), Math.cos(po), Math.sin(po) * Math.cos(az)).multiplyScalar(d));
        // the viewer's vertical fov of 30 degrees, as a horizontal fov for setPose
        fov = (2 * Math.atan(Math.tan((30 * Math.PI) / 360) * v.camera.aspect) * 180) / Math.PI;
      }
      await v.setLevel(level, false);
      if (j.interior) v.setInterior(true, !!j.exterior);
      m.poses.__qa = { level, eye, look, fov };
      v.setPose('__qa');
      if (j.cut === false) {
        full();
        v.renderer.render(v.scene, v.camera);
      } else settle();
      return v.renderer.domElement.toDataURL('image/png');
    }
    return null;
  }, j);
  if (data) fs.writeFileSync(`${outDir}/${j.name}.png`, Buffer.from(data.split(',')[1], 'base64'));
}
if (logs.length) console.log(logs.slice(0, 30).join('\n'));
console.log('rendered', jobs.length);
await browser.close();
