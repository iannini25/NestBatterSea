// End-to-end check of the site with screenshots.  node e2e.mjs [url] [outdir]
import puppeteer from 'puppeteer-core';
import fs from 'node:fs';

const URL_ = process.argv[2] || 'http://localhost:8080/';
const OUT = process.argv[3] || 'evidence';
fs.mkdirSync(OUT, { recursive: true });
const ROOT = new URL('../', import.meta.url);
const HAS3D = fs.existsSync(new URL('assets/js/plan3d.js', ROOT));
const PHOTO_IDS = ['loft4-living', 'loft4-kitchen', 'loft4-gallery', 'loft4-bed1', 'loft4-bed2', 'loft4-bed3', 'loft4-bed4', 'loft4-bath',
  'bung3-living', 'bung3-kitchen', 'bung3-bed1', 'bung3-bed2', 'bung3-ensuite', 'bung3-garden'];
const pendingPhotos = PHOTO_IDS.filter(id => !fs.existsSync(new URL(`assets/interiors/${id}.jpg`, ROOT)));
const pendingRe = new RegExp(`assets/interiors/(${pendingPhotos.join('|') || 'none'})\\.jpg`);

const results = [];
const check = (name, ok, detail = '') => { results.push({ name, ok: !!ok, detail }); console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? '  ·  ' + detail : ''}`); };
const note = msg => console.log(`note  ${msg}`);
const sleep = ms => new Promise(r => setTimeout(r, ms));

const browser = await puppeteer.launch({
  executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  headless: 'new',
  args: ['--ignore-gpu-blocklist', '--enable-gpu', '--use-angle=d3d11', '--autoplay-policy=no-user-gesture-required', '--no-sandbox'],
});
const logs = [], expected = [], videos = {};
function listen(p, tag) {
  videos[tag] = [];
  p.on('request', r => { const m = r.url().match(/assets\/video\/([^?]+)/); if (m) videos[tag].push(m[1]); });
  p.on('console', m => {
    if (!['error', 'warn'].includes(m.type())) return;
    const where = (m.location() && m.location().url) || '';
    // Chromium reads one range past the end of a blob: video while demuxing; harmless, like the blob requestfailed below
    if (where.startsWith('blob:') && /ERR_REQUEST_RANGE_NOT_SATISFIABLE/.test(m.text())) return;
    const line = `[${tag}] ${m.type()}: ${m.text()} ${where}`;
    (pendingRe.test(where) ? expected : logs).push(line);
  });
  p.on('pageerror', e => logs.push(`[${tag}] pageerror: ${e.message}`));
  p.on('requestfailed', r => { if (!r.url().startsWith('blob:') && !/net::ERR_ABORTED/.test(r.failure() && r.failure().errorText)) logs.push(`[${tag}] requestfailed: ${r.url()} ${r.failure() && r.failure().errorText}`); });
  p.on('response', r => { if (r.status() >= 400) (pendingRe.test(r.url()) ? expected : logs).push(`[${tag}] http ${r.status()}: ${r.url()}`); });
}
async function open(viewport, ua, tag) {
  const p = await browser.newPage();
  if (ua) await p.setUserAgent(ua);
  await p.setViewport(viewport);
  listen(p, tag || viewport.width);
  await p.goto(URL_, { waitUntil: 'networkidle2', timeout: 120000 });
  await p.waitForFunction('typeof App !== "undefined" && App.state() === "tower"', { timeout: 60000 });
  return p;
}
const st = p => p.evaluate(() => App.state());
const waitState = (p, s, t = 40000) => p.waitForFunction(`App.state() === "${s}" && !App.busy()`, { timeout: t });
const shot = (p, n, opts = {}) => p.screenshot({ path: `${OUT}/${n}.png`, ...opts });
const winBox = (p, id) => p.evaluate(id => { const r = document.querySelector(`.win[data-id="${id}"] .edge`).getBoundingClientRect(); return { x: r.x, y: r.y, w: r.width, h: r.height, cx: r.x + r.width / 2, cy: r.y + r.height / 2 }; }, id);
const text = (p, sel) => p.evaluate(s => (document.querySelector(s) || {}).textContent || '', sel);

// geometry of the notches and what must never sit under them
async function notchReport(p) {
  return p.evaluate(() => {
    const card = document.querySelector('#card').getBoundingClientRect();
    const n = App.notch();
    const rects = [];
    if (n.tl) rects.push({ k: 'tl', x0: card.left, y0: card.top, x1: card.left + n.tl.w, y1: card.top + n.tl.h });
    if (n.tr) rects.push({ k: 'tr', x0: card.right - n.tr.w, y0: card.top, x1: card.right, y1: card.top + n.tr.h });
    let y = card.bottom;
    (n.br || []).forEach((s, i) => { rects.push({ k: 'br' + i, x0: card.right - s.w, y0: y - s.h, x1: card.right, y1: y }); y -= s.h; });
    const wins = [...document.querySelectorAll('.win .hit')].map(h => { const r = h.getBoundingClientRect(); return { id: h.parentNode.dataset.id, x0: r.left, y0: r.top, x1: r.right, y1: r.bottom, cx: (r.left + r.right) / 2, cy: (r.top + r.bottom) / 2 }; });
    const hitsWin = wins.map(w => { const e = document.elementFromPoint(w.cx, w.cy); return !!(e && e.closest && e.closest('.win') && e.closest('.win').dataset.id === w.id); });
    const overlap = wins.some(w => rects.some(r => w.x0 < r.x1 && w.x1 > r.x0 && w.y0 < r.y1 && w.y1 > r.y0));
    const inNotch = sel => { const e = document.querySelector(sel); if (!e || !e.offsetParent && getComputedStyle(e).position !== 'fixed') return null; const b = e.getBoundingClientRect(); const c = [(b.left + b.right) / 2, (b.top + b.bottom) / 2]; const hit = document.elementFromPoint(c[0], c[1]); return !!(hit && e.contains(hit)); };
    const title = document.querySelector('#hero-title').getBoundingClientRect();
    const fit = App.fit();
    const towerLeft = card.left + fit.cx + 1165 * fit.cs;
    return { clip: getComputedStyle(document.querySelector('#card')).clipPath.slice(0, 12), n, hitsWin, overlap, logo: inNotch('.logo'), tr: inNotch('.tr .reg') ?? inNotch('.tr .circ'), mini: inNotch('#minicard'), titleRight: title.right, towerLeft };
  });
}

// ======================================================= desktop 1600 x 900
let p = await open({ width: 1600, height: 900, deviceScaleFactor: 1 }, null, 'desktop');
await sleep(3200);
await p.mouse.move(800, 880);
await shot(p, '01-tower');
check('No video is fetched before the visitor shows intent', videos.desktop.length === 0, videos.desktop.join(', ') || 'none');
check('Window title uses | and no dash', await p.evaluate(() => /\|/.test(document.title) && !/[\u2010-\u2015-]/.test(document.title)), await p.title());
let nr = await notchReport(p);
check('Card is clipped by the notched outline', nr.clip.startsWith('path('), nr.clip);
check('Notches hold the logo, the buttons and the mini card', nr.logo && nr.tr && nr.mini && nr.n.br.length === 2, JSON.stringify({ tl: nr.n.tl, tr: nr.n.tr }));
check('Both available windows stay clickable, clear of every notch', nr.hitsWin.every(Boolean) && !nr.overlap);
check('Headline stays clear of the tower', nr.titleRight < nr.towerLeft - 8, `${nr.titleRight.toFixed(0)} < ${nr.towerLeft.toFixed(0)}`);
check('Logo pill sits at the top left', await p.evaluate(() => { const r = document.querySelector('.logo').getBoundingClientRect(); return r.left < 20 && r.top < 20 && /logo-light\.png/.test(document.querySelector('.logo img').src); }));

// hover only on available windows: the LOFT 4 window
const lw = await winBox(p, 'loft4');
await p.mouse.move(lw.cx, lw.cy, { steps: 5 });
await sleep(500);
const AV1 = await p.evaluate(() => document.createElement('video').canPlayType('video/mp4; codecs="av01.0.08M.08"') === 'probably');
const AV1CLIPS = await p.evaluate(() => (typeof VIDEO_AV1 === 'undefined' ? [] : VIDEO_AV1 === true ? ['loft4-flight', 'bung3-flight', 'loft4-inside', 'bung3-inside'] : VIDEO_AV1));
const hov = await p.evaluate(() => ({ on: document.querySelector('.win[data-id="loft4"]').classList.contains('on'), dim: document.body.classList.contains('dim'), tag: document.querySelector('#tag').classList.contains('on'), tagtxt: document.querySelector('#tag').innerText, mini: document.querySelector('#mini-n').textContent }));
check('Hover on the LOFT 4 window: outline, dim the rest, label, mini card', hov.on && hov.dim && hov.tag && hov.mini === 'LOFT 4', hov.tagtxt.replace(/\n/g, ' / '));
const cs = await p.evaluate(() => App.fit().cs);
check('Outline sits exactly on the traced window', Math.abs(lw.w - 49.4 * cs) < 2.5 && Math.abs(lw.h - 44.3 * cs) < 2.5, `${lw.w.toFixed(1)} x ${lw.h.toFixed(1)} px`);
await shot(p, '02-hover-loft4');
await p.mouse.move(lw.cx, lw.cy + lw.h * 2.2, { steps: 4 });
await sleep(450);
check('Hover ignores windows that are not available', await p.evaluate(() => !document.body.classList.contains('dim') && !document.querySelector('#tag').classList.contains('on')));
const bw = await winBox(p, 'bung3');
await p.mouse.move(bw.cx, bw.cy, { steps: 4 });
await sleep(700);
check('Hovering Bungalow 3 turns the mini card to it', await text(p, '#mini-n') === 'Bungalow 3');
await p.mouse.move(800, 880, { steps: 3 });
await sleep(300);

// fly to LOFT 4: sample the outline during the flight
await p.mouse.move(lw.cx, lw.cy, { steps: 3 });
await sleep(200);
await p.mouse.click(lw.cx, lw.cy);
await p.waitForFunction('App.state() === "flight"', { timeout: 15000 });
// the outline starts on the window, then fades as the camera leaves (the flights rise and curve)
const trailOp = () => p.evaluate(() => ({ t: document.querySelector('#vid').currentTime, op: +getComputedStyle(document.querySelector('#trail')).opacity, pts: document.querySelector('#trailpoly').getAttribute('points') || '' }));
await p.waitForFunction(() => { const v = document.querySelector('#vid'); return !v.paused && v.currentTime > 0.01; }, { timeout: 20000 });
const early = await trailOp();
await p.waitForFunction(() => document.querySelector('#vid').currentTime > 1.5, { timeout: 20000 });
const mid = await trailOp();
await shot(p, '03-flight-mid');
check('Window outline sits on the window, then fades as the camera leaves', early.pts.split(' ').length === 4 && (early.op > 0 || early.t > 0.38) && mid.op === 0, `t=${early.t.toFixed(2)}s ${early.op.toFixed(2)} · t=${mid.t.toFixed(2)}s ${mid.op}`);
await waitState(p, 'home');
await sleep(900);
await shot(p, '04-arrived-loft4');
const panel = await text(p, '#panel');
check('Arrival panel: name, typology, areas, garden, illustrative level, no price', /LOFT 4/.test(panel) && /134 m²/.test(panel) && /12 m²/.test(panel) && /illustrative/i.test(panel) && !/£|\$|€|pcm|per month/i.test(panel));
check('Arrival still is the flight video\'s own last frame', await p.evaluate(() => /loft4-flight-last\.jpg/.test(document.querySelector('#stillimg').src)));
{
  const want = `loft4-flight${AV1 && AV1CLIPS.includes('loft4-flight') ? '-av1' : ''}.mp4`;
  check('Flight in 1080p, AV1 where the browser plays it', videos.desktop.includes(want) && videos.desktop.every(v => !/-720/.test(v)), videos.desktop.join(', '));
}
await p.mouse.move(800, 450);
await p.mouse.wheel({ deltaY: 900 });
await sleep(400);
const wheelY = await p.evaluate(() => scrollY);
const stage = await p.evaluate(() => { scrollTo(0, 600); return new Promise(r => setTimeout(() => r({ y: scrollY, inert: document.querySelector('#residences').inert, locked: document.documentElement.classList.contains('locked'), back: getComputedStyle(document.querySelector('#back')).opacity, label: document.querySelector('#backlbl').textContent, copy: getComputedStyle(document.querySelector('.hero-copy')).opacity, tl: App.notch().tl.w }), 700)); });
stage.wheelY = wheelY;
check('Stage: scroll locked, page below inert, hero text gone, Back visible, notch opened for it', stage.y === 0 && wheelY === 0 && stage.inert && stage.locked && +stage.back > .9 && +stage.copy < .05 && stage.tl > 220, JSON.stringify(stage));

// floor plan: 3D dollhouse (or the official plan when the bundle is missing)
await p.click('#panel [data-act="plan"]');
await waitState(p, 'plan');
await p.waitForFunction(() => document.querySelector('#plan3d canvas') || document.querySelector('#plan2d.on'), { timeout: 30000 });
await sleep(2500);
await shot(p, '05-plan-loft4-lower');
const mode = await p.evaluate(() => App.viewer() && App.viewer().mode);
check(`Floor plan opens (${mode === '3d' ? '3D dollhouse' : 'official plan fallback'})`, HAS3D ? mode === '3d' : mode === '2d', `bundle ${HAS3D ? 'present' : 'missing'}`);
check('Title names the floor plan', /^LOFT 4 \| Floor plan \| Nest Battersea$/.test(await p.title()), await p.title());
const pp = await p.evaluate(() => ({ toggle: [...document.querySelectorAll('#pp-toggle button')].map(b => b.textContent), rooms: [...document.querySelectorAll('#pp-rooms button')].map(b => b.textContent.trim()), hot: document.querySelectorAll('.p3-hot').length, text: document.querySelector('#ppanel').textContent }));
check('Plan panel: specs, two level toggle, rooms of the lower floor', pp.toggle.join('|') === 'Lower floor|Upper floor' && pp.rooms.length >= 3 && /134 m²/.test(pp.text) && /illustrative/i.test(pp.text), `${pp.rooms.join(', ')}${mode === '3d' ? ` · ${pp.hot} hotspots on the model` : ''}`);
await p.click('#pp-toggle button[data-i="1"]');
await sleep(2200);
const up = await p.evaluate(() => ({ lv: App.viewer().mode === '3d' ? App.viewer().v.level : null, img: document.querySelector('#planimg').src, rooms: [...document.querySelectorAll('#pp-rooms button')].map(b => b.textContent.trim()) }));
check('Upper floor toggle switches the plan and the room list', (mode === '3d' ? up.lv === 1 : /loft4-upper/.test(up.img)) && up.rooms.includes('Principal bedroom'), up.rooms.join(', '));
await shot(p, '06-plan-loft4-upper');
// hover a room in the list: the mini card previews it, then open it
const rb = await p.$('#pp-rooms button');
await rb.hover();
await sleep(500);
check('Hovering a room previews it in the mini card', await text(p, '#mini-k') === 'Look inside', await text(p, '#mini-n'));
await rb.click();
await waitState(p, 'room', 30000);
await sleep(1300);
await shot(p, '07-room-from-plan');
const room1 = await p.evaluate(() => ({ t: document.querySelector('#cap-t').textContent, src: document.querySelector('#photos .shot[style*="opacity: 1"] img').currentSrc, title: document.title }));
check('A room opens on its photograph, with its name', room1.t.length > 2 && /assets\/interiors\/loft4-/.test(room1.src) && room1.title.includes(room1.t), `${room1.t} · ${room1.src.split('/').pop()}`);
await p.click('#mnext');
await sleep(1300);
const room2 = await text(p, '#cap-t');
check('Next room from the mini card', room2 !== room1.t, `${room1.t} → ${room2}`);
await p.click('#back');
await waitState(p, 'plan', 30000);
await sleep(1500);
check('Back to the plan returns to the model', await st(p) === 'plan' && await p.evaluate(() => getComputedStyle(document.querySelector('#photos')).visibility === 'hidden'));
if (mode === '3d') {
  const hot = await p.evaluate(() => { const h = [...document.querySelectorAll('.p3-hot')].find(e => e.style.display !== 'none'); if (!h) return null; const r = h.getBoundingClientRect(); return { x: r.x, y: r.y }; });
  if (hot) {
    await p.mouse.move(hot.x, hot.y, { steps: 3 });
    await sleep(400);
    await shot(p, '08-plan-hotspot-hover');
    await p.mouse.click(hot.x, hot.y);
    await waitState(p, 'room', 30000);
    check('A hotspot on the model dives into its room', true, await text(p, '#cap-t'));
    await p.keyboard.press('Escape');
    await waitState(p, 'plan', 30000);
  } else check('A hotspot on the model dives into its room', false, 'no visible hotspot');
}
await p.click('#back');
await waitState(p, 'home');

// step inside: continuous camera move into the room
const tStart = Date.now();
await p.click('#panel [data-act="inside"]');
await p.waitForFunction('App.state() === "moving"', { timeout: 15000 });
await p.waitForFunction(() => document.querySelector('#vid').currentTime > 1.5, { timeout: 25000 });
await shot(p, '09-step-inside-mid');
await waitState(p, 'inside');
await sleep(700);
await shot(p, '10-inside-loft4-01');
const firstShot = await p.evaluate(() => ({ src: document.querySelector('#photos .shot img').currentSrc, still: getComputedStyle(document.querySelector('#still')).visibility, tf: document.querySelector('#stillimg').style.transform }));
check('Step inside hands over to the living room photograph', /interiors\/loft4-living\.(avif|webp|jpg)/.test(firstShot.src) && firstShot.still === 'hidden', `${firstShot.src.split('/').pop()} · ${((Date.now() - tStart) / 1000).toFixed(1)} s`);
const cap1 = await text(p, '#cap-t');
await p.click('#mnext');
await sleep(1300);
const cap2 = await text(p, '#cap-t');
check('Tour arrows move between rooms', cap1 !== cap2, `${cap1} → ${cap2}`);
await shot(p, '11-inside-loft4-02');
await p.keyboard.press('ArrowRight');
await sleep(1000);
check('Keyboard moves between rooms', await p.evaluate(() => document.querySelector('#cap-i').textContent.startsWith('03')));
const loftShots = await p.evaluate(() => [...document.querySelectorAll('#photos img')].map(i => i.currentSrc).filter(Boolean));
await p.click('#back');
await waitState(p, 'home', 40000);
check('Back outside returns to the window', await st(p) === 'home');
await p.click('#back');
await waitState(p, 'tower', 40000);
await sleep(600);
await shot(p, '12-back-at-tower');
check('Back to the tower ends on the tower view, scroll unlocked', await st(p) === 'tower' && await p.evaluate(() => !document.documentElement.classList.contains('locked')));

// Bungalow 3 from the mini card
await p.click('#mnext');
await sleep(600);
check('Mini card arrows pick the other residence', await text(p, '#mini-n') === 'Bungalow 3');
await p.click('#minicard');
await waitState(p, 'home', 40000);
await sleep(700);
await shot(p, '13-arrived-bung3');
check('Bungalow 3 lands on its own window still', await p.evaluate(() => /bung3-flight-last\.jpg/.test(document.querySelector('#stillimg').src)));
await p.click('#panel [data-act="plan"]');
await waitState(p, 'plan');
await p.waitForFunction(() => document.querySelector('#plan3d canvas') || document.querySelector('#plan2d.on'), { timeout: 30000 });
await sleep(2200);
await shot(p, '14-plan-bung3');
check('Bungalow 3 plan has no level toggle and lists its rooms', await p.evaluate(() => document.querySelectorAll('#pp-toggle button').length === 0 && document.querySelectorAll('#pp-rooms button').length >= 5));
await p.keyboard.press('Escape');
await waitState(p, 'home');
await p.click('#panel [data-act="inside"]');
await waitState(p, 'inside', 40000);
await sleep(700);
await shot(p, '15-inside-bung3-01');
const b3Shots = await p.evaluate(() => [...document.querySelectorAll('#photos img')].map(i => i.currentSrc).filter(Boolean));
check('LOFT 4 and Bungalow 3 show different interiors', loftShots.every(s => !b3Shots.includes(s)), `${loftShots.length} / ${b3Shots.length} loaded`);
await p.keyboard.press('Escape');
await waitState(p, 'home', 40000);
await p.keyboard.press('Escape');
await waitState(p, 'tower', 40000);

// the page below the card
for (const [id, name] of [['building', '16-section-building'], ['location', '17-section-location'], ['residences', '18-section-residences'], ['register', '19-section-register']]) {
  await p.evaluate(id => { document.documentElement.classList.add('cv-off'); document.getElementById(id).scrollIntoView({ block: 'start' }); }, id);
  await sleep(1500);
  await shot(p, name);
}
check('Sections reveal as they scroll in', await p.evaluate(() => document.querySelectorAll('.rv.in').length >= 8), `${await p.evaluate(() => document.querySelectorAll('.rv.in').length)} revealed`);
check('Below the fold images load lazily', await p.evaluate(() => [...document.querySelectorAll('.sec img, .foot img')].every(i => i.loading === 'lazy')));
// fly from the residences section: the page scrolls back up and the card becomes the stage
await p.evaluate(() => document.getElementById('residences').scrollIntoView({ block: 'start' }));
await sleep(800);
await p.click('.rcard[data-id="bung3"] .cta');
await waitState(p, 'home', 40000);
check('"Fly to this home" scrolls up and flies', await p.evaluate(() => scrollY === 0 && App.cur().id === 'bung3'));
await p.click('.logo');
await waitState(p, 'tower', 20000);
check('The logo leaves the stage at once', await st(p) === 'tower');

// menus, overlays, register form
await p.click('.tr [data-target="menu"]');
await sleep(500);
check(`Menu opens (title "${await p.title()}")`, await p.evaluate(() => document.querySelector('.overlay[data-overlay="menu"]').classList.contains('open') && / \| /.test(document.title)));
await shot(p, '20-menu');
await p.click('.menu-item[data-target="location"]');
await sleep(1800);
check('Menu link scrolls to its section', await p.evaluate(() => { const r = document.getElementById('location').getBoundingClientRect(); return scrollY > 300 && Math.abs(r.top) < 140; }));
await p.click('.tr [data-target="location"]');
await sleep(500);
check('Location button opens its card', await p.evaluate(() => document.querySelector('.overlay[data-overlay="location"]').classList.contains('open')));
await shot(p, '21-location-card');
await p.keyboard.press('Escape');
await sleep(400);
await p.click('.tr .reg');
await sleep(600);
await p.click('#form button[type="submit"]');
await sleep(200);
const bad = await p.evaluate(() => document.querySelectorAll('#form .bad').length);
await p.type('#form input[name="name"]', 'Test Person');
await p.type('#form input[name="email"]', 'test@example.com');
await p.click('#form button[type="submit"]');
await sleep(400);
await shot(p, '22-register-done');
check('Register interest validates and confirms (nothing sent)', bad === 2 && await p.evaluate(() => document.querySelector('.drawer').classList.contains('sent')));
await p.keyboard.press('Escape');
await sleep(300);

// every text: no dashes or hyphens, no prices, nothing for sale, no rent besides "build to rent"
const all = await p.evaluate(() => {
  const attrs = [...document.querySelectorAll('[aria-label],[alt],[title]')].map(e => [e.getAttribute('aria-label'), e.getAttribute('alt'), e.getAttribute('title')].filter(Boolean).join(' ')).join(' ');
  return document.body.textContent.replace(/\s+/g, ' ') + ' ' + attrs + ' ' + document.querySelector('meta[name=description]').content + ' ' + document.title;
});
const dashes = all.match(/.{0,16}[\u2010-\u2015\u2212-].{0,16}/g);
check('No dash or hyphen anywhere in the text', !dashes, dashes ? dashes.slice(0, 5).join(' ¦ ') : 'none');
const price = all.match(/[£$€]\s?\d|\bpcm\b|per\s+(month|week)|asking|for sale|\bprices?\b|\brents?\b(?<!build to rent)|\brental\b/gi);
check('No price, rent or sale anywhere', !price, price ? price.join(', ') : 'none');
await p.close();

// ======================================================= other desktop sizes
for (const [w, h] of [[1920, 1080], [1366, 768]]) {
  const q = await open({ width: w, height: h, deviceScaleFactor: 1 }, null, `${w}`);
  await sleep(3000);
  await q.mouse.move(w / 2, h - 30);
  await shot(q, `23-tower-${w}x${h}`);
  const r = await notchReport(q);
  check(`${w}x${h}: notches hold their UI, windows clickable, headline clear of the tower`, r.clip.startsWith('path(') && r.logo && r.tr && r.mini && r.hitsWin.every(Boolean) && !r.overlap && r.titleRight < r.towerLeft - 8, `${r.titleRight.toFixed(0)} < ${r.towerLeft.toFixed(0)}`);
  const ov = await q.evaluate(() => { const a = document.querySelector('.meta-b').getBoundingClientRect(), b = document.querySelector('.mini-nav').getBoundingClientRect(), c = document.querySelector('.meta-a').getBoundingClientRect(), d = document.querySelector('.tr').getBoundingClientRect(); return a.bottom < b.top && c.top > d.bottom; });
  check(`${w}x${h}: right hand text clear of the notches`, ov);
  await q.close();
}
// retina close ups of the curves
{
  const q = await open({ width: 1600, height: 900, deviceScaleFactor: 2 }, null, 'retina');
  await sleep(3000);
  await q.mouse.move(800, 880);
  await shot(q, '24-retina-notch-top-left', { clip: { x: 0, y: 0, width: 260, height: 150 } });
  await shot(q, '25-retina-notch-bottom-right', { clip: { x: 1180, y: 680, width: 420, height: 220 } });
  await q.close();
}

// ======================================================= phone
const IPHONE = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1';
p = await open({ width: 390, height: 844, deviceScaleFactor: 3, isMobile: true, hasTouch: true }, IPHONE, 'phone');
await sleep(3200);
await shot(p, '26-phone-tower');
const ph = await p.evaluate(() => {
  const t = document.querySelector('#hero-title').getBoundingClientRect(), w = document.querySelector('.win[data-id="loft4"] .edge').getBoundingClientRect();
  const pk = document.querySelector('#picker').getBoundingClientRect(), b = document.querySelector('.win[data-id="bung3"] .edge').getBoundingClientRect();
  return { t: t.bottom, w: w.top, pk: pk.left, wr: Math.max(w.right, b.right), mini: getComputedStyle(document.querySelector('#mini')).display };
});
check('Phone: headline above the windows, picker clear of them, no bottom notch', ph.t < ph.w && ph.pk > ph.wr && ph.mini === 'none', JSON.stringify(ph));
const pr = await notchReport(p);
check('Phone: notches hold the logo and the two buttons, windows clickable', pr.clip.startsWith('path(') && pr.logo && pr.tr && pr.hitsWin.every(Boolean) && !pr.overlap);
await p.tap('#picker button[data-id="bung3"]');
await sleep(500);
check('Phone: the toggle picks a home and shows it', await p.evaluate(() => document.querySelector('#tag').classList.contains('on') && document.querySelector('.win[data-id="bung3"]').classList.contains('on') && App.state() === 'tower'));
await shot(p, '27-phone-picker');
await p.touchscreen.tap(30, 300);
await sleep(300);
const mw = await winBox(p, 'loft4');
await p.touchscreen.tap(mw.cx, mw.cy);
await sleep(500);
const first = await p.evaluate(() => ({ s: App.state(), tag: document.querySelector('#tag').classList.contains('on') }));
await shot(p, '28-phone-first-tap');
check('Phone: first tap highlights and labels, does not fly', first.s === 'tower' && first.tag);
await p.touchscreen.tap(mw.cx, mw.cy);
await waitState(p, 'home', 40000);
await sleep(700);
await shot(p, '29-phone-arrived');
check('Phone: second tap flies in, with the 720p clip', await st(p) === 'home' && videos.phone.length > 0 && videos.phone.every(v => /-720/.test(v)), videos.phone.join(', '));
await p.tap('#panel [data-act="plan"]');
await waitState(p, 'plan');
await p.waitForFunction(() => document.querySelector('#plan3d canvas') || document.querySelector('#plan2d.on'), { timeout: 30000 });
await sleep(2200);
await shot(p, '30-phone-plan');
await p.tap('#back');
await waitState(p, 'home');
await p.tap('#panel [data-act="inside"]');
await waitState(p, 'inside', 40000);
await sleep(600);
await shot(p, '31-phone-inside');
await p.tap('.bnav [data-act="next"]');
await sleep(1200);
check('Phone: tour arrows in the band', (await text(p, '#cap-i')).startsWith('02'));
await p.tap('.logo');
await waitState(p, 'tower', 20000);
await p.evaluate(() => { document.documentElement.classList.add('cv-off'); document.querySelectorAll('.rv').forEach(e => e.classList.add('in')); });
await sleep(800);
await shot(p, '32-phone-page', { fullPage: true });
await p.close();

// ======================================================= floor plan without the 3D bundle
{
  const f = await browser.newPage();
  await f.setViewport({ width: 1600, height: 900 });
  await f.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }]);
  await f.setRequestInterception(true);
  f.on('request', r => (/plan3d\.js/.test(r.url()) ? r.abort() : r.continue()));
  f.on('pageerror', e => logs.push(`[fallback] pageerror: ${e.message}`));
  await f.goto(URL_, { waitUntil: 'networkidle2' });
  await f.waitForFunction('typeof App !== "undefined" && App.state() === "tower"', { timeout: 60000 });
  await f.click('#minicard');
  await f.waitForFunction('App.state() === "home" && !App.busy()', { timeout: 20000 });
  await f.click('#panel [data-act="plan"]');
  await f.waitForFunction('App.state() === "plan" && !App.busy()', { timeout: 20000 });
  await sleep(700);
  await shot(f, '33-plan-fallback-2d');
  const a = await f.evaluate(() => ({ mode: App.viewer().mode, img: document.querySelector('#planimg').src, n: document.querySelectorAll('#pp-toggle button').length, note: document.querySelector('#note').textContent }));
  await f.click('#pp-toggle button[data-i="1"]');
  await sleep(600);
  const up = await f.evaluate(() => document.querySelector('#planimg').src);
  await f.click('#pp-rooms button');
  await f.waitForFunction('App.state() === "room" && !App.busy()', { timeout: 20000 });
  check('Without the 3D bundle the official plans take over and rooms still open', a.mode === '2d' && /loft4-lower/.test(a.img) && a.n === 2 && /loft4-upper/.test(up) && /official/i.test(a.note), a.note);
  await f.close();
}

// ======================================================= reduced motion
{
  const r = await browser.newPage();
  await r.setViewport({ width: 1280, height: 800 });
  await r.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }]);
  listen(r, 'reduced');
  await r.goto(URL_, { waitUntil: 'networkidle2' });
  await r.waitForFunction('typeof App !== "undefined" && App.state() === "tower"', { timeout: 60000 });
  await r.click('#mnext');
  const t0 = Date.now();
  await r.click('#minicard');
  await r.waitForFunction('App.state() === "home" && !App.busy()', { timeout: 10000 });
  const ms = Date.now() - t0;
  const played = await r.evaluate(() => document.querySelector('#vid').currentTime);
  check('Reduced motion: cuts straight to the home, no flight played', ms < 1500 && played === 0, `${ms} ms`);
  await r.close();
}
await browser.close();
const errs = logs.filter(l => /error|requestfailed|http [45]/.test(l));
check('No console errors or failed requests', errs.length === 0, errs.slice(0, 4).join(' | '));
if (pendingPhotos.length) note(`${pendingPhotos.length} room photographs not delivered yet, stand ins shown: ${pendingPhotos.join(', ')} (${expected.length} expected 404s ignored)`);
fs.writeFileSync(`${OUT}/report.json`, JSON.stringify({ results, logs, expected, pendingPhotos }, null, 2));
console.log(`\n${results.filter(r => r.ok).length}/${results.length} passed`);
