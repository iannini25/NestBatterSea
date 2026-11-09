// The static picture of the Location map (the fallback and the placeholder of the live map).
//   node sitebuild/make_static_map.mjs [page url]
// Renders the live MapLibre map of the page at fixed sizes, without its controls, and saves
// assets/site/map/static-1600.(webp|jpg), static-960.* and static-phone-720.* (via Python/Pillow).
import puppeteer from 'puppeteer-core';
import fs from 'node:fs';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const URL_ = process.argv[2] || 'http://localhost:8080/';
const OUT = new URL('../../assets/site/map/', import.meta.url);
const TMP = new URL('./out/', import.meta.url);
fs.mkdirSync(TMP, { recursive: true });
const sleep = ms => new Promise(r => setTimeout(r, ms));
const browser = await puppeteer.launch({
  executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: 'new',
  args: ['--ignore-gpu-blocklist', '--enable-gpu', '--use-angle=d3d11', '--no-sandbox'],
});
async function render(vp, w, h, file) {
  const p = await browser.newPage();
  await p.setViewport(vp);
  await p.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }]);   // no camera settle
  p.on('pageerror', e => console.log('pageerror', e.message));
  await p.goto(URL_, { waitUntil: 'load', timeout: 120000 });
  // the map card alone, filling the window at the size of the picture
  await p.addStyleTag({ content: `
    .mapcard{position:fixed!important;inset:0!important;margin:0!important;z-index:9999!important;transform:none!important;opacity:1!important}
    .mapcard .ncard{clip-path:none!important;border-radius:0!important;height:100%!important}
    .map-shell{display:block!important;height:100%!important;min-height:0!important}
    #map{width:${w}px!important;height:${h}px!important}
    html{overflow:hidden!important;scrollbar-gutter:auto!important}
    .places,.map-static,.n-tl,.maplibregl-control-container,.mk-site .mk-pulse,.tl,.tr{display:none!important}` });
  await p.waitForFunction('window.MapView && MapView.state() === "ready"', { timeout: 60000 });
  await p.evaluate(() => new Promise(r => { const m = MapView.map(); m.resize(); m.once('idle', r); setTimeout(r, 8000); }));
  await sleep(1500);
  const el = await p.$('#map');
  await el.screenshot({ path: fileURLToPath(new URL(file, TMP)) });
  console.log('rendered', file, await p.evaluate(() => { const m = MapView.map(); return { zoom: m.getZoom().toFixed(2), center: m.getCenter(), bearing: m.getBearing(), pitch: m.getPitch() }; }));
  await p.close();
}
await render({ width: 1600, height: 1000, deviceScaleFactor: 1 }, 1600, 1000, 'map-desktop.png');
await render({ width: 360, height: 430, deviceScaleFactor: 2, isMobile: true, hasTouch: true }, 360, 430, 'map-phone.png');
await browser.close();
const py = `
from PIL import Image
import os
tmp, out = r'${fileURLToPath(TMP).replace(/[\\/]+$/, '')}', r'${fileURLToPath(OUT).replace(/[\\/]+$/, '')}'
d = Image.open(os.path.join(tmp, 'map-desktop.png')).convert('RGB')
for w in (1600, 960):
    r = d.resize((w, round(d.height * w / d.width)), Image.LANCZOS) if w != d.width else d
    r.save(os.path.join(out, f'static-{w}.webp'), 'WEBP', quality=82, method=6)
    r.save(os.path.join(out, f'static-{w}.jpg'), 'JPEG', quality=84, optimize=True, progressive=True)
ph = Image.open(os.path.join(tmp, 'map-phone.png')).convert('RGB')
ph.save(os.path.join(out, 'static-phone-720.webp'), 'WEBP', quality=82, method=6)
ph.save(os.path.join(out, 'static-phone-720.jpg'), 'JPEG', quality=84, optimize=True, progressive=True)
for f in sorted(os.listdir(out)):
    print(f, os.path.getsize(os.path.join(out, f)) // 1024, 'KB')
`;
console.log(execFileSync('python', ['-c', py]).toString());
