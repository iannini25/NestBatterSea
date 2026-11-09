// Render the dollhouse with headless Chrome (GPU) and save screenshots.
// node shot.mjs <outDir> <apt> <jobs.json | inline json>
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
page.on('console', (m) => logs.push(m.type() + ': ' + m.text()));
page.on('pageerror', (e) => logs.push('pageerror: ' + e.message));
await page.goto(`http://localhost:8080/_work/plan3d/dev.html?apt=${apt}`, { waitUntil: 'networkidle0' });
await page.waitForFunction('window.ready === true', { timeout: 20000 }).catch(() => {});
await new Promise((r) => setTimeout(r, 800));
for (const j of jobs) {
  await page.evaluate(async (j) => {
    const v = window.viewer;
    if (j.interior !== undefined) v.setInterior(j.interior, !!j.exterior);
    if (j.level !== undefined) await v.setLevel(j.level, false);
    if (j.az !== undefined) await v.frame(false, j.az, j.polar ?? 0.86);
    if (j.pose) v.setPose(j.pose);
    v.renderNow();
  }, j);
  await new Promise((r) => setTimeout(r, j.wait || 600));
  await page.evaluate(() => window.viewer.renderNow());
  await page.screenshot({ path: `${outDir}/${j.name}.png` });
}
console.log(logs.slice(0, 30).join('\n'));
await browser.close();
