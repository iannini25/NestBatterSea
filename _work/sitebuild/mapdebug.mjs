// Map debugging: node sitebuild/mapdebug.mjs [url]
import puppeteer from 'puppeteer-core';
const URL_ = process.argv[2] || 'http://localhost:8080/';
const sleep = ms => new Promise(r => setTimeout(r, ms));
const browser = await puppeteer.launch({
  executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: 'new',
  args: ['--ignore-gpu-blocklist', '--enable-gpu', '--use-angle=d3d11', '--no-sandbox'],
});
const p = await browser.newPage();
await p.setViewport({ width: 1600, height: 900 });
p.on('console', m => console.log('console', m.type(), m.text().slice(0, 300)));
p.on('pageerror', e => console.log('pageerror', e.message));
p.on('requestfailed', r => { if (!/kaspersky/.test(r.url())) console.log('failed', r.url().slice(0, 140), r.failure()?.errorText); });
let tiles = 0;
p.on('response', r => { if (/openfreemap/.test(r.url())) { tiles++; if (r.status() >= 400) console.log('http', r.status(), r.url()); } });
await p.goto(URL_, { waitUntil: 'load', timeout: 120000 });
await p.waitForFunction('window.NestMotion && window.NestMotion.ready', { timeout: 30000 }).catch(() => {});
await p.evaluate(() => document.getElementById('map').scrollIntoView({ block: 'center' }));
await p.waitForFunction('window.MapView && ["ready","static"].includes(MapView.state())', { timeout: 60000 }).catch(e => console.log('wait', e.message));
await sleep(4000);
console.log(await p.evaluate(() => {
  const m = MapView.map(), box = document.getElementById('map'), gl = box.querySelector('.map-gl'), cv = box.querySelector('canvas');
  return { state: MapView.state(), cls: box.className, gl: gl && getComputedStyle(gl).opacity, canvas: cv && [cv.width, cv.height, cv.clientWidth, cv.clientHeight],
    loaded: m && m.loaded(), style: m && m.isStyleLoaded(), feats: m && m.queryRenderedFeatures().length, layers: m && m.getStyle().layers.length,
    zoom: m && m.getZoom(), markers: box.querySelectorAll('.mk').length };
}));
console.log('openfreemap responses', tiles);
await p.screenshot({ path: 'sitebuild/out/mapdebug.png' });
await browser.close();
