// Horizontal overflow check: node sitebuild/overflow.mjs [url] [width] [height]
// Lists elements that stick out of the page on the right (outside scrolling containers).
import puppeteer from 'puppeteer-core';
const URL_ = process.argv[2] || 'http://localhost:8080/';
const W = +(process.argv[3] || 390), H = +(process.argv[4] || 844);
const browser = await puppeteer.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: 'new', args: ['--no-sandbox'] });
const p = await browser.newPage();
await p.setViewport({ width: W, height: H, deviceScaleFactor: 2, isMobile: W < 600, hasTouch: W < 600 });
await p.goto(URL_, { waitUntil: 'load', timeout: 120000 });
await p.waitForFunction('window.NestMotion && window.NestMotion.ready', { timeout: 30000 }).catch(() => {});
const H2 = await p.evaluate(() => document.documentElement.scrollHeight);
for (let y = 0; y < H2; y += 400) { await p.evaluate(y => scrollTo(0, y), y); await new Promise(r => setTimeout(r, 60)); }
await new Promise(r => setTimeout(r, 1500));
const out = await p.evaluate(() => {
  const vw = document.documentElement.clientWidth, res = [];
  const scrollerOf = el => { for (let n = el.parentElement; n; n = n.parentElement) { const s = getComputedStyle(n); if (/(auto|scroll|hidden|clip)/.test(s.overflowX) && n !== document.body && n !== document.documentElement) return n; } return null; };
  document.querySelectorAll('body *').forEach(el => {
    const r = el.getBoundingClientRect();
    if (!r.width || r.right <= vw + 1) return;
    if (scrollerOf(el)) return;
    res.push(`${el.tagName.toLowerCase()}${el.id ? '#' + el.id : ''}.${[...el.classList].join('.')} right=${Math.round(r.right)} (vw ${vw})`);
  });
  return { vw, inner: innerWidth, scrollW: document.documentElement.scrollWidth, list: res.slice(0, 20) };
});
console.log(JSON.stringify(out, null, 1));
await browser.close();
