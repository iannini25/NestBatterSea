// Section screenshots of the page:  node sitebuild/shots.mjs [url] [outdir] [w x h ...]
// Scrolls like a visitor (in steps, so every reveal and parallax runs), then captures each
// section at the top of the screen and a few steps through the pinned exterior views.
import puppeteer from 'puppeteer-core';
import fs from 'node:fs';

const URL_ = process.argv[2] || 'http://localhost:8080/';
const OUT = process.argv[3] || 'qa/site-shots';
const sizes = (process.argv.slice(4).length ? process.argv.slice(4) : ['1600x900', '1920x1080', '390x844']).map(s => s.split('x').map(Number));
fs.mkdirSync(OUT, { recursive: true });
const sleep = ms => new Promise(r => setTimeout(r, ms));
const IPHONE = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1';
const browser = await puppeteer.launch({
  executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: 'new',
  args: ['--ignore-gpu-blocklist', '--enable-gpu', '--use-angle=d3d11', '--autoplay-policy=no-user-gesture-required', '--no-sandbox'],
});
const errors = [];
for (const [w, h] of sizes) {
  const phone = w < 600;
  const p = await browser.newPage();
  if (phone) await p.setUserAgent(IPHONE);
  await p.setViewport({ width: w, height: h, deviceScaleFactor: phone ? 3 : 1, isMobile: phone, hasTouch: phone });
  p.on('console', m => { if (['error', 'warn'].includes(m.type()) && !/kaspersky/i.test(m.location()?.url || '')) errors.push(`[${w}] ${m.type()}: ${m.text()} ${m.location()?.url || ''}`); });
  p.on('pageerror', e => errors.push(`[${w}] pageerror: ${e.message}`));
  p.on('requestfailed', r => { if (!/kaspersky|blob:/.test(r.url()) && !/ERR_ABORTED/.test(r.failure()?.errorText || '')) errors.push(`[${w}] failed: ${r.url()} ${r.failure()?.errorText}`); });
  p.on('response', r => { if (r.status() >= 400) errors.push(`[${w}] http ${r.status()} ${r.url()}`); });
  await p.goto(URL_, { waitUntil: 'load', timeout: 120000 });
  await p.waitForFunction('typeof App !== "undefined" && App.state() === "tower"', { timeout: 60000 });
  await p.waitForFunction('window.NestMotion && window.NestMotion.ready', { timeout: 30000 }).catch(() => errors.push(`[${w}] motion did not start`));
  await sleep(800);
  const tag = `${w}x${h}`;
  await p.screenshot({ path: `${OUT}/${tag}-00-hero.png` });
  // scroll down in steps like a visitor
  const H = await p.evaluate(() => document.documentElement.scrollHeight);
  for (let y = 0; y < H; y += Math.round(h * .5)) { await p.evaluate(y => scrollTo(0, y), y); await sleep(120); }
  await sleep(600);
  const ids = ['vision', 'views', 'residences', 'homes', 'affordable', 'sustainability', 'location', 'next', 'contact'];
  let k = 1;
  for (const id of ids) {
    const y = await p.evaluate(id => { const t = document.getElementById(id); return t.getBoundingClientRect().top + scrollY; }, id);
    await p.evaluate(y => scrollTo(0, Math.max(0, y - 20)), y);
    await sleep(1600);
    await p.screenshot({ path: `${OUT}/${tag}-${String(k++).padStart(2, '0')}-${id}.png` });
    if (id === 'views' && !phone) {
      for (const f of [.35, .7, 1]) {
        await p.evaluate((y, f) => { const st = (window.ScrollTrigger && ScrollTrigger.getAll().find(s => s.pin)); const end = st ? st.end : y + 2000; scrollTo(0, y + (end - y) * f); }, y, f);
        await sleep(1300);
        await p.screenshot({ path: `${OUT}/${tag}-${String(k - 1).padStart(2, '0')}-views-${Math.round(f * 100)}.png` });
      }
    }
    if (id === 'location') {
      await p.evaluate(() => document.getElementById('map').scrollIntoView({ block: 'center' }));
      await p.waitForFunction('window.MapView && ["ready","static"].includes(MapView.state())', { timeout: 30000 }).catch(() => errors.push(`[${w}] map not ready`));
      await sleep(3800);
      await p.screenshot({ path: `${OUT}/${tag}-${String(k - 1).padStart(2, '0')}-map.png` });
      const area = await p.evaluate(() => { const a = document.querySelector('.area'); return a.getBoundingClientRect().top + scrollY; });
      await p.evaluate(y => scrollTo(0, y - 40), area);
      await sleep(1500);
      await p.screenshot({ path: `${OUT}/${tag}-${String(k - 1).padStart(2, '0')}-area.png` });
    }
  }
  await p.evaluate(() => scrollTo(0, document.documentElement.scrollHeight));
  await sleep(1200);
  await p.screenshot({ path: `${OUT}/${tag}-99-footer.png` });
  console.log(tag, 'done', await p.evaluate(() => ({ map: window.MapView && MapView.state(), gsap: !!window.gsap, pin: document.documentElement.classList.contains('gsap-pin') })));
  await p.close();
}
await browser.close();
console.log(errors.length ? errors.join('\n') : 'no console errors');
