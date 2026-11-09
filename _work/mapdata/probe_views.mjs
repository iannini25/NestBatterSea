// Screenshots of the map page in several states.  node probe_views.mjs <outdir>
import puppeteer from 'puppeteer-core';
const OUT = process.argv[2];
const sleep = ms => new Promise(r => setTimeout(r, ms));
const b = await puppeteer.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: 'new', args: ['--ignore-gpu-blocklist', '--enable-gpu', '--use-angle=d3d11', '--no-sandbox'] });
const log = (...a) => console.log(...a);
async function page(w, h, hash, mobile) {
  const p = await b.newPage();
  await p.setViewport({ width: w, height: h, deviceScaleFactor: mobile ? 2 : 1, isMobile: !!mobile, hasTouch: !!mobile });
  p.on('console', m => { if (['error', 'warn'].includes(m.type())) log('console', m.type(), m.text()); });
  p.on('pageerror', e => log('pageerror', e.message));
  await p.goto('http://localhost:8080/map.html' + hash, { waitUntil: 'networkidle2', timeout: 90000 });
  await p.waitForFunction('window.MapPage && MapPage.state() === "ready"', { timeout: 40000 });
  await sleep(4500);
  return p;
}
let p = await page(1440, 900, '#place=power&mode=car');
await p.screenshot({ path: `${OUT}/v-power-car.png` });
await p.click('.looks [data-look="sat"]'); await sleep(4000);
await p.screenshot({ path: `${OUT}/v-power-car-sat.png` });
await p.evaluate(() => MapPage.select('nest')); await sleep(4200);
await p.screenshot({ path: `${OUT}/v-home-sat.png` });
await p.click('.looks [data-look="night"]'); await sleep(3000);
await p.screenshot({ path: `${OUT}/v-home-night.png` });
await p.evaluate(() => MapPage.select('stmarys')); await sleep(1300);
await p.screenshot({ path: `${OUT}/v-stmarys-mid.png` });
await sleep(3000);
await p.screenshot({ path: `${OUT}/v-stmarys.png` });
await p.close();
p = await page(1366, 768, '');
await p.screenshot({ path: `${OUT}/v-1366.png` });
await p.close();
p = await page(390, 844, '', true);
await p.screenshot({ path: `${OUT}/v-phone.png` });
await p.evaluate(() => MapPage.select('chelsea')); await sleep(4000);
await p.screenshot({ path: `${OUT}/v-phone-chelsea.png` });
await p.close();
await b.close();
