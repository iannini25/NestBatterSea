import puppeteer from 'puppeteer-core';
const out = process.argv[2];
const browser = await puppeteer.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: 'new', args: ['--ignore-gpu-blocklist', '--enable-gpu', '--use-angle=d3d11', '--no-sandbox'] });
const page = await browser.newPage();
await page.setViewport({ width: 1600, height: 900 });
const logs = [];
page.on('pageerror', (e) => logs.push('pageerror: ' + e.message));
await page.goto('http://localhost:8080/_work/plan3d/preview.html', { waitUntil: 'networkidle0' });
await new Promise((r) => setTimeout(r, 1200));
await page.evaluate(() => document.querySelectorAll('#home button')[1].click());
await new Promise((r) => setTimeout(r, 1800));
await page.screenshot({ path: out + '/pv-b3.png' });
// hover the garden zone through the viewer API: move the mouse over the garden hotspot
const box = await page.evaluate(() => { const b = [...document.querySelectorAll('.p3-hot')].find((x) => x.textContent.includes('garden')); const r = b && b.getBoundingClientRect(); return r ? [r.x + 6, r.y + 6] : null; });
if (box) { await page.mouse.move(box[0], box[1]); await new Promise((r) => setTimeout(r, 600)); await page.screenshot({ path: out + '/pv-b3-hover.png' }); }
console.log(logs.join('\n'), 'garden hotspot', box);
await browser.close();
