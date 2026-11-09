// Render the 3D floor plan model from custom poses (plan px + height in m), e.g. from outside a window.
// node ai/shot-ext.mjs <outDir> <apt> '<json [{name, level, eye:[x,y,h], look:[x,y,h], fov, interior, exterior}]>' [W] [H]
import puppeteer from 'puppeteer-core';
import fs from 'fs';
const [, , outDir, apt = 'loft4', jobsArg = '[]', W = '1920', H = '1080'] = process.argv;
const jobs = JSON.parse(fs.existsSync(jobsArg) ? fs.readFileSync(jobsArg, 'utf8') : jobsArg);
fs.mkdirSync(outDir, { recursive: true });
const browser = await puppeteer.launch({
  executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: 'new',
  args: ['--ignore-gpu-blocklist', '--enable-gpu', '--use-angle=d3d11', '--no-sandbox'],
});
const page = await browser.newPage();
await page.setViewport({ width: +W, height: +H, deviceScaleFactor: 1 });
const logs = [];
page.on('console', (m) => logs.push(m.type() + ': ' + m.text()));
page.on('pageerror', (e) => logs.push('pageerror: ' + e.message));
await page.goto(`http://localhost:8080/_work/plan3d/dev.html?apt=${apt}`, { waitUntil: 'networkidle0' });
await page.waitForFunction('window.ready === true', { timeout: 20000 }).catch(() => {});
await new Promise((r) => setTimeout(r, 1000));
for (const j of jobs) {
  await page.evaluate(async (j) => {
    const v = window.viewer, m = v.model;
    v.setInterior(j.interior !== false, !!j.exterior);
    const li = j.level || 0;
    await v.setLevel(li, false);
    const ref = Object.values(m.poses)[0];
    const base = (m.levels[li] && m.levels[li].base) || 0;
    const [ex, ez] = m.P([j.eye[0], j.eye[1]]), [lx, lz] = m.P([j.look[0], j.look[1]]);
    m.poses.__ext = { level: li, eye: ref.eye.clone().set(ex, base + j.eye[2], ez), look: ref.look.clone().set(lx, base + j.look[2], lz), fov: j.fov };
    v.setPose('__ext');
    v.renderNow();
  }, j);
  await new Promise((r) => setTimeout(r, j.wait || 900));
  await page.evaluate(() => window.viewer.renderNow());
  await page.screenshot({ path: `${outDir}/${j.name}.png` });
}
console.log(logs.slice(0, 20).join('\n'));
await browser.close();
