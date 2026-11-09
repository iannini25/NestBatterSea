// A few mid scroll frames (hero into the first section, layered parallax):
//   node sitebuild/midscroll.mjs [url] [outdir] [width] [height]
import puppeteer from 'puppeteer-core';
import fs from 'node:fs';
const URL_ = process.argv[2] || 'http://localhost:8080/';
const OUT = process.argv[3] || 'qa/site-shots/mid';
const W = +(process.argv[4] || 1600), H = +(process.argv[5] || 900);
fs.mkdirSync(OUT, { recursive: true });
const sleep = ms => new Promise(r => setTimeout(r, ms));
const browser = await puppeteer.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: 'new', args: ['--ignore-gpu-blocklist', '--enable-gpu', '--use-angle=d3d11', '--no-sandbox'] });
const p = await browser.newPage();
const phone = W < 600;
if (phone) await p.setUserAgent('Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1');
await p.setViewport({ width: W, height: H, deviceScaleFactor: phone ? 2 : 1, isMobile: phone, hasTouch: phone });
await p.goto(URL_, { waitUntil: 'load', timeout: 120000 });
await p.waitForFunction('window.NestMotion && window.NestMotion.ready', { timeout: 30000 }).catch(() => {});
await sleep(1500);
for (const f of [.25, .5, .8, 1.1]) {
  await p.evaluate(y => scrollTo(0, y), Math.round(H * f));
  await sleep(900);
  await p.screenshot({ path: `${OUT}/${W}-hero-${Math.round(f * 100)}.png` });
}
await browser.close();
