// Audit: every <img> on the page, its rendered CSS size vs the pixels it was served.
//   node probe_imgs.mjs [url] [width] [height] [dpr]
import puppeteer from 'puppeteer-core';
const URL_ = process.argv[2] || 'http://localhost:8080/';
const W = +(process.argv[3] || 1920), H = +(process.argv[4] || 1080), DPR = +(process.argv[5] || 1);
const sleep = ms => new Promise(r => setTimeout(r, ms));
const browser = await puppeteer.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: 'new',
  args: ['--ignore-gpu-blocklist', '--enable-gpu', '--use-angle=d3d11', '--no-sandbox'] });
const p = await browser.newPage();
await p.setViewport({ width: W, height: H, deviceScaleFactor: DPR });
await p.goto(URL_, { waitUntil: 'networkidle2', timeout: 120000 });
await sleep(1500);
const SH = await p.evaluate(() => document.documentElement.scrollHeight);
const seen = new Map();
for (let y = 0; y < SH + H; y += Math.round(H * 0.5)) {
  await p.evaluate(y => scrollTo(0, y), y); await sleep(400);
  const rows = await p.evaluate(() => [...document.images].map(i => {
    const r = i.getBoundingClientRect();
    return { src: (i.currentSrc || i.src).replace(location.origin + '/', '').replace(/\?.*$/, ''), nw: i.naturalWidth, nh: i.naturalHeight, w: Math.round(r.width), h: Math.round(r.height), vis: r.bottom > 0 && r.top < innerHeight && r.width > 0, fit: getComputedStyle(i).objectFit, cls: (i.closest('[class]') || {}).className || '' };
  }).filter(o => o.vis && o.nw));
  for (const o of rows) { const k = o.src; const prev = seen.get(k); if (!prev || o.w > prev.w) seen.set(k, o); }
}
const real = await p.evaluate(async list => { const o = {}; for (const s of list) { await new Promise(r => { const i = new Image(); i.onload = i.onerror = () => { o[s] = [i.naturalWidth, i.naturalHeight]; r(); }; i.src = s; }); } return o; }, [...seen.keys()]);
for (const [k, o] of seen) { if (real[k]) { o.nw = real[k][0]; o.nh = real[k][1]; } }
console.log(`viewport ${W}x${H} @${DPR}x`);
for (const o of seen.values()) {
  // object-fit cover: the image pixels needed = box scaled to cover
  let need = o.w;
  if (o.fit === 'cover' && o.nw && o.nh) need = Math.max(o.w, o.h * o.nw / o.nh);
  const ratio = o.nw / (need * DPR);
  console.log(`${ratio.toFixed(2).padStart(5)}  box ${String(o.w).padStart(5)}x${String(o.h).padEnd(5)} need ${String(Math.round(need * DPR)).padStart(5)}px  served ${o.nw}x${o.nh}  ${o.src}  [${String(o.cls).slice(0, 30)}]`);
}
await browser.close();
