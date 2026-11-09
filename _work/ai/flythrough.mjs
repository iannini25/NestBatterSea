// Fly the 3D floor plan model camera from pose A to pose B (plan px + height m), one PNG per frame.
// node ai/flythrough.mjs <outDir> <apt> <frames> '<json {level, a:{eye,look,fov}, b:{eye,look,fov}, interior, exterior}>' [W] [H]
import puppeteer from 'puppeteer-core';
import fs from 'fs';
const [, , outDir, apt = 'loft4', N = '121', spec = '{}', W = '1280', H = '720'] = process.argv;
const s = JSON.parse(spec);
fs.mkdirSync(outDir, { recursive: true });
const browser = await puppeteer.launch({
  executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: 'new',
  args: ['--ignore-gpu-blocklist', '--enable-gpu', '--use-angle=d3d11', '--no-sandbox'],
});
const page = await browser.newPage();
await page.setViewport({ width: +W, height: +H, deviceScaleFactor: 1 });
await page.goto(`http://localhost:8080/_work/plan3d/dev.html?apt=${apt}`, { waitUntil: 'networkidle0' });
await page.waitForFunction('window.ready === true', { timeout: 20000 }).catch(() => {});
await new Promise((r) => setTimeout(r, 1000));
await page.evaluate(async (s) => {
  const v = window.viewer;
  v.setInterior(s.interior !== false, !!s.exterior);
  await v.setLevel(s.level || 0, false);
}, s);
const n = +N;
// smootherstep ease
const ease = (t) => t * t * t * (t * (t * 6 - 15) + 10);
const lerp = (a, b, t) => a.map((v, i) => v + (b[i] - v) * t);
for (let i = 0; i < n; i++) {
  const t = ease(i / (n - 1));
  const eye = lerp(s.a.eye, s.b.eye, t), look = lerp(s.a.look, s.b.look, t), fov = s.a.fov + (s.b.fov - s.a.fov) * t;
  await page.evaluate((j) => {
    const v = window.viewer, m = v.model;
    const ref = Object.values(m.poses)[0];
    const base = (m.levels[j.level] && m.levels[j.level].base) || 0;
    const [ex, ez] = m.P([j.eye[0], j.eye[1]]), [lx, lz] = m.P([j.look[0], j.look[1]]);
    m.poses.__f = { level: j.level, eye: ref.eye.clone().set(ex, base + j.eye[2], ez), look: ref.look.clone().set(lx, base + j.look[2], lz), fov: j.fov };
    v.setPose('__f');
    v.renderNow();
  }, { eye, look, fov, level: s.level || 0 });
  await new Promise((r) => setTimeout(r, 60));
  await page.evaluate(() => window.viewer.renderNow());
  await page.screenshot({ path: `${outDir}/f${String(i).padStart(4, '0')}.png` });
}
await browser.close();
console.log('frames', n);
