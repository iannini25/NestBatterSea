// First load weight of the page: node sitebuild/weight.mjs [url] [label]
// Cold cache, no interaction. Sums the bytes on the wire (CDP encodedDataLength) until the
// network has been idle for 3 s, at 1600x900 and 390x844; then scrolls the whole page
// to report what lazy loading adds.
import puppeteer from 'puppeteer-core';
import fs from 'node:fs';
const URL_ = process.argv[2] || 'http://localhost:8080/';
const LABEL = process.argv[3] || 'run';
// antivirus suites inject their own scripts and polling into local pages: never count them
const foreign = u => /kaspersky|^data:|^blob:|^chrome-extension:/.test(u);
const sleep = ms => new Promise(r => setTimeout(r, ms));
const browser = await puppeteer.launch({
  executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: 'new',
  args: ['--ignore-gpu-blocklist', '--enable-gpu', '--use-angle=d3d11', '--autoplay-policy=no-user-gesture-required', '--no-sandbox'],
});
async function measure(vp, ua, scroll) {
  const p = await browser.newPage();
  if (ua) await p.setUserAgent(ua);
  await p.setViewport(vp);
  const cdp = await p.createCDPSession();
  await cdp.send('Network.enable');
  await cdp.send('Network.setCacheDisabled', { cacheDisabled: true });
  const reqs = new Map();
  let last = Date.now();
  cdp.on('Network.requestWillBeSent', e => { reqs.set(e.requestId, { url: e.request.url, type: e.type, bytes: 0 }); if (!foreign(e.request.url)) { last = Date.now(); if (process.env.TRACE) console.error('req', e.request.url.slice(0, 120)); } });
  cdp.on('Network.responseReceived', e => { const r = reqs.get(e.requestId); if (r) r.type = e.type; });
  cdp.on('Network.loadingFinished', e => { const r = reqs.get(e.requestId); if (r) { r.bytes = e.encodedDataLength; if (!foreign(r.url)) last = Date.now(); } });
  cdp.on('Network.loadingFailed', e => { const r = reqs.get(e.requestId); if (r) { r.failed = e.errorText; if (!foreign(r.url)) last = Date.now(); } });
  const settle = async () => { const t0 = Date.now(); while (Date.now() - last < 3000 && Date.now() - t0 < 25000) await sleep(250); };
  console.error('goto', vp.width);
  await p.goto(URL_, { waitUntil: 'load', timeout: 120000 });
  console.error('loaded');
  await settle();
  const sum = () => { const by = {}; let t = 0; for (const r of reqs.values()) { if (foreign(r.url)) continue; t += r.bytes; by[r.type] = (by[r.type] || 0) + r.bytes; } return { total: t, n: [...reqs.values()].filter(r => !foreign(r.url)).length, by }; };
  const first = sum();
  const list = [...reqs.values()].filter(r => !foreign(r.url)).map(r => `${(r.bytes / 1024).toFixed(1).padStart(8)} KB  ${r.type.padEnd(10)} ${r.url.replace(URL_, '')}`);
  let after = null;
  if (scroll) {
    const H = await p.evaluate(() => document.documentElement.scrollHeight);
    console.error('scroll', H);
    for (let y = 0; y < H; y += Math.round(vp.height * 0.7)) { await p.evaluate(y => scrollTo(0, y), y); await sleep(350); }
    last = Date.now();
    await settle();
    after = sum();
  }
  await p.close();
  return { first, after, list };
}
const IPHONE = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1';
const out = {};
out.desktop = await measure({ width: 1600, height: 900, deviceScaleFactor: 1 }, null, true);
out.phone = await measure({ width: 390, height: 844, deviceScaleFactor: 3, isMobile: true, hasTouch: true }, IPHONE, true);
await browser.close();
const kb = b => (b / 1024).toFixed(0) + ' KB';
for (const k of ['desktop', 'phone']) {
  const o = out[k];
  console.log(`\n== ${k}: first load ${kb(o.first.total)} in ${o.first.n} requests`, JSON.stringify(Object.fromEntries(Object.entries(o.first.by).map(([a, b]) => [a, kb(b)]))));
  if (o.after) console.log(`   after scrolling the whole page: ${kb(o.after.total)} in ${o.after.n} requests`);
  console.log(o.list.join('\n'));
}
fs.mkdirSync(new URL('./out/', import.meta.url), { recursive: true });
fs.writeFileSync(new URL(`./out/weight-${LABEL}.json`, import.meta.url), JSON.stringify(out, null, 2));
