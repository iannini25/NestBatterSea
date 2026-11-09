// Reduced motion: scroll to the Location map, point at the places while the map is still loading
// and after it is ready, then open map.html. Prints any page error.  node mapdata/probe_reduced.mjs
import puppeteer from 'puppeteer-core';
const sleep = ms => new Promise(r => setTimeout(r, ms));
const b = await puppeteer.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: 'new', args: ['--ignore-gpu-blocklist', '--enable-gpu', '--use-angle=d3d11', '--no-sandbox'] });
let errors = 0;
for (const url of ['http://localhost:8080/', 'http://localhost:8080/map.html', 'http://localhost:8080/map.html#place=imperial&mode=car']) {
  const p = await b.newPage();
  await p.setViewport({ width: 1280, height: 800 });
  await p.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }]);
  p.on('pageerror', e => { errors++; console.log('pageerror', url, e.stack || e.message); });
  p.on('console', m => { if (m.type() === 'error') { errors++; console.log('console error', url, m.text()); } });
  await p.goto(url, { waitUntil: 'load', timeout: 90000 });
  if (url.endsWith('/')) {
    await p.evaluate(() => document.getElementById('location').scrollIntoView({ block: 'center' }));
    // point at every place as fast as possible, while MapLibre and the style are still loading
    for (let k = 0; k < 60; k++) {
      const ids = await p.evaluate(() => [...document.querySelectorAll('#placelist [data-place]')].map(a => a.dataset.place));
      for (const id of ids) { await p.hover(`#placelist [data-place="${id}"]`).catch(() => {}); await sleep(40); }
      if (await p.evaluate(() => window.MapView && MapView.state() === 'ready')) break;
    }
    await sleep(1500);
    for (const id of ['clapham', 'imperial', 'path']) { await p.hover(`#placelist [data-place="${id}"]`); await sleep(500); }
    await p.mouse.move(5, 5); await sleep(600);
    console.log('index state', await p.evaluate(() => MapView.state()));
  } else {
    await p.waitForFunction('window.MapPage && MapPage.state() === "ready"', { timeout: 40000 }).catch(() => {});
    await p.evaluate(() => { MapPage.select('chelsea'); MapPage.setMode('car'); MapPage.setMode('foot'); MapPage.select(null); MapPage.select('nest'); });
    await sleep(1500);
    console.log('map state', url, await p.evaluate(() => MapPage.state()));
  }
  await p.close();
}
console.log('errors', errors);
await b.close();
