// Quick look at the map page: console, state, screenshots.  node probe_map.mjs <outdir> [hash] [w] [h]
import puppeteer from 'puppeteer-core';
const OUT = process.argv[2], HASH = process.argv[3] || '', W = +(process.argv[4] || 1440), H = +(process.argv[5] || 900);
const b = await puppeteer.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: 'new', args: ['--ignore-gpu-blocklist', '--enable-gpu', '--use-angle=d3d11', '--no-sandbox'] });
const p = await b.newPage();
await p.setViewport({ width: W, height: H, deviceScaleFactor: 1, isMobile: W < 600, hasTouch: W < 600 });
p.on('console', m => { if (['error', 'warn'].includes(m.type())) console.log('console', m.type(), m.text()); });
p.on('pageerror', e => console.log('pageerror', e.message));
p.on('requestfailed', r => console.log('failed', r.url(), r.failure()?.errorText));
p.on('response', r => { if (r.status() >= 400) console.log('http', r.status(), r.url()); });
await p.goto('http://localhost:8080/map.html' + HASH, { waitUntil: 'networkidle2', timeout: 90000 });
await p.waitForFunction('window.MapPage && MapPage.state() !== "loading"', { timeout: 40000 }).catch(() => console.log('timeout state'));
const sleep = ms => new Promise(r => setTimeout(r, ms));
await sleep(1800); await p.screenshot({ path: `${OUT}/probe-a.png` });
await sleep(3500); await p.screenshot({ path: `${OUT}/probe-b.png` });
console.log(await p.evaluate(() => JSON.stringify({ state: MapPage.state(), active: MapPage.active(), zoom: MapPage.map()?.getZoom(), pitch: MapPage.map()?.getPitch(), bearing: MapPage.map()?.getBearing() })));
await b.close();
