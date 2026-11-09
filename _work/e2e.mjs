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
check('The window label marks the level as illustrative', /Levels 23 and 24, illustrative position/.test(hov.tagtxt));
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
// with js/tracks.js the outline follows the window frame by frame and stays on the whole way;
// without a track it starts on the window and fades as the camera leaves
const trailOp = () => p.evaluate(() => {
  const v = document.querySelector('#vid'), pts = (document.querySelector('#trailpoly').getAttribute('points') || '').trim();
  const xy = pts ? pts.split(' ').map(q => q.split(',').map(Number)) : [];
  const xs = xy.map(q => q[0]), ys = xy.map(q => q[1]);
  // where the track says the window is now, in card pixels (object-fit: cover of the 16:9 frame)
  let want = null;
  if (typeof FLIGHT_TRACKS !== 'undefined' && FLIGHT_TRACKS.loft4) {
    const t = FLIGHT_TRACKS.loft4, i = Math.min(t.frames.length - 1, Math.round(v.currentTime * (t.fps || 60)));
    const f = App.fit(), vw = v.videoWidth || 16, vh = v.videoHeight || 9, s = Math.max(f.W / vw, f.H / vh), dw = vw * s, dh = vh * s;
    const [u0, v0, u1, v1] = t.frames[i];
    want = [(f.W - dw) / 2 + u0 * dw, (f.H - dh) / 2 + v0 * dh, (f.W - dw) / 2 + u1 * dw, (f.H - dh) / 2 + v1 * dh];
  }
  return { t: v.currentTime, op: +getComputedStyle(document.querySelector('#trail')).opacity, n: xy.length, box: xy.length ? [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)] : null, want };
});
await p.waitForFunction(() => { const v = document.querySelector('#vid'); return !v.paused && v.currentTime > 0.01; }, { timeout: 20000 });
// js/tracks.js loads on intent (the hover above) and is in place before the video plays
const TRACKED = await p.evaluate(() => typeof FLIGHT_TRACKS !== 'undefined' && !!FLIGHT_TRACKS && !!FLIGHT_TRACKS.loft4 && Array.isArray(FLIGHT_TRACKS.loft4.frames));
const early = await trailOp();
await p.waitForFunction(() => document.querySelector('#vid').currentTime > 1.5, { timeout: 20000 });
const mid = await trailOp();
await shot(p, '03-flight-mid');
if (TRACKED) {
  const off = mid.box && mid.want ? Math.max(...mid.box.map((v, k) => Math.abs(v - mid.want[k]))) : 1e9;
  const grew = mid.box && early.box && (mid.box[2] - mid.box[0]) > (early.box[2] - early.box[0]) * 1.3;
  check('During the flight the outline follows the window on every frame (js/tracks.js)', mid.n === 4 && mid.op > .95 && grew && off < 12,
    `t=${mid.t.toFixed(2)}s opacity ${mid.op} · ${mid.box && (mid.box[2] - mid.box[0]).toFixed(0)} px wide · ${off.toFixed(1)} px from the track`);
} else {
  check('Window outline sits on the window, then fades as the camera leaves', early.n === 4 && (early.op > 0 || early.t > 0.38) && mid.op === 0, `t=${early.t.toFixed(2)}s ${early.op.toFixed(2)} · t=${mid.t.toFixed(2)}s ${mid.op}`);
}
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
check('Hovering a room previews it in the mini card', await text(p, '#mini-k') === 'Have a look', await text(p, '#mini-n'));
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
const tourMini = await p.evaluate(() => ({ k: document.querySelector('#mini-k').textContent, n: document.querySelector('#mini-n').textContent, label: document.querySelector('#minicard').getAttribute('aria-label'), arrow: document.querySelector('#mnext').getAttribute('aria-label'), cap: document.querySelector('#cap-t').textContent, sub: document.querySelector('#cap-s').textContent }));
check('The first view is captioned by what it shows', tourMini.cap === 'Dining and kitchen' && /living room|gallery/i.test(tourMini.sub), `${tourMini.cap} · ${tourMini.sub}`);
check('In the tour the mini card previews the next view, its arrow says view', /^(Another view|Next room)$/.test(tourMini.k) && tourMini.n !== tourMini.cap && /^Next view: /.test(tourMini.label) && tourMini.arrow === 'Next view', JSON.stringify(tourMini));
await p.click('#mnext');
await sleep(1300);
const cap2 = await text(p, '#cap-t');
check('Tour arrows move between rooms', cap1 !== cap2 && cap2 === tourMini.n, `${cap1} → ${cap2}`);
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

// ---------------------------------------------------------------- the page below the card
// GSAP and ScrollTrigger: pinned versions from cdnjs, loaded after the page
const gs = await p.evaluate(() => ({ html: document.documentElement.classList.contains('gsap'), ver: window.gsap && gsap.version, st: !!window.ScrollTrigger,
  srcs: [...document.scripts].map(s => s.src).filter(s => /gsap|ScrollTrigger|maplibre/i.test(s)), pinned: document.documentElement.classList.contains('gsap-pin') }));
check('GSAP 3.12.5 with ScrollTrigger runs the scroll motion (cdnjs, loaded after the page)', gs.html && gs.ver === '3.12.5' && gs.st && gs.srcs.every(s => /cdnjs\.cloudflare\.com\/ajax\/libs\/gsap\/3\.12\.5\//.test(s)), gs.srcs.join(', '));
check('MapLibre is not loaded until the Location section comes near', !gs.srcs.some(s => /maplibre/i.test(s)) && await p.evaluate(() => !performance.getEntriesByType('resource').some(e => /maplibre|openfreemap/.test(e.name))));
// scroll down like a visitor, then nothing may stay hidden
const pageH = await p.evaluate(() => document.documentElement.scrollHeight);
for (let y = 0; y < pageH; y += 450) { await p.evaluate(y => scrollTo(0, y), y); await sleep(110); }
await sleep(1800);
const hidden = await p.evaluate(() => {
  const vis = e => { let o = 1; for (let n = e; n && n !== document.body; n = n.parentElement) { const s = getComputedStyle(n); if (s.display === 'none' || s.visibility === 'hidden') return 0; o *= +s.opacity; } return o; };
  return [...document.querySelectorAll('main [data-reveal], main [data-lines], main .lines .ln > i, main [data-stagger] > *, main .sticker')].filter(e => vis(e) < .95).map(e => e.className || e.tagName);
});
check('Every section reveals as it scrolls in; nothing stays hidden', !hidden.length, hidden.slice(0, 6).join(', ') || 'all visible');
check('Below the fold images load lazily, each with its size', await p.evaluate(() => [...document.querySelectorAll('.sec img, .foot img')].every(i => i.loading === 'lazy' && i.getAttribute('width') && i.getAttribute('height'))));
check('Section images are responsive (AVIF or WebP sources with srcset)', await p.evaluate(() => [...document.querySelectorAll('main .sec picture')].every(pc => pc.querySelector('source[type="image/avif"], source[type="image/webp"]'))));
const SECTIONS = [['vision', '40-section-vision'], ['views', '41-section-views'], ['residences', '42-section-residences'], ['homes', '43-section-homes'], ['affordable', '44-section-affordable'], ['sustainability', '45-section-sustainability'], ['location', '46-section-location'], ['contact', '48-section-contact']];
for (const [id, name] of SECTIONS) {
  await p.evaluate(id => window.scrollTo(0, document.getElementById(id).getBoundingClientRect().top + scrollY - 20), id);
  await sleep(1400);
  await shot(p, name);
}
check('All nine sections are on the page', await p.evaluate(() => ['vision', 'views', 'residences', 'homes', 'affordable', 'accessible', 'sustainability', 'location', 'contact'].every(id => document.getElementById(id))));
if (gs.pinned) {
  // the exterior views slide sideways while the section is pinned
  const vx = await p.evaluate(async () => {
    const st = ScrollTrigger.getAll().find(s => s.pin), row = document.querySelector('#vrow');
    scrollTo(0, st.start + (st.end - st.start) * .6);
    await new Promise(r => setTimeout(r, 1300));
    return { x: gsap.getProperty(row, 'x'), count: document.querySelector('#vcount').textContent, top: document.querySelector('#viewspin').getBoundingClientRect().top };
  });
  check('Exterior views: pinned, the row slides sideways and the counter follows', vx.x < -200 && Math.abs(vx.top) < 2 && +vx.count > 1, JSON.stringify(vx));
}
// lightbox: open a view, step with the keyboard, close
await p.evaluate(() => document.querySelectorAll('#vlist .view-btn')[1].click());
await sleep(900);
const lb1 = await p.evaluate(() => ({ open: document.querySelector('.lightbox').classList.contains('open'), title: document.title, n: document.querySelector('#lbn').textContent, t: document.querySelector('#lbt').textContent, src: document.querySelector('#lbimg').currentSrc, w: document.querySelector('#lbimg').naturalWidth }));
await shot(p, '49-lightbox');
await p.keyboard.press('ArrowRight');
await sleep(900);
const lb2 = await p.evaluate(() => ({ n: document.querySelector('#lbn').textContent, t: document.querySelector('#lbt').textContent }));
await p.keyboard.press('Escape');
await sleep(500);
check('Exterior views open full screen in a lightbox; arrows step, Escape closes', lb1.open && lb1.title === 'Exterior views | Nest Battersea' && lb1.n === '02 / 09' && lb1.w >= 1200 && lb2.n === '03 / 09' && lb2.t !== lb1.t && await p.evaluate(() => !document.querySelector('.lightbox').classList.contains('open')), `${lb1.t} → ${lb2.t} · ${lb1.src.split('/').pop()}`);
// the official plans of the twelve homes
await p.evaluate(() => document.getElementById('homes').scrollIntoView({ block: 'start' }));
await sleep(900);
await p.evaluate(() => document.querySelector('.plan-tabs [data-plan="double-lower-private"]').click());
await sleep(1200);
const typ = await p.evaluate(() => ({ img: document.querySelector('.plan-open img').currentSrc, rows: document.querySelectorAll('.typ-list li').length, open: [...document.querySelectorAll('.typ-list li.open b')].map(b => b.textContent), fly: document.querySelectorAll('.typ-list [data-act="fly"]').length }));
check('Homes: twelve private typologies with the official plans; only LOFT 4 and Bungalow 3 lead anywhere', typ.rows === 12 && /double-lower-private/.test(typ.img) && typ.open.join() === 'Bungalow 3,LOFT 4' && typ.fly === 2, `${typ.rows} rows · ${typ.img.split('/').pop()}`);
// the map: lazy, styled, cooperative, with the walking routes
await p.evaluate(() => document.getElementById('map').scrollIntoView({ block: 'center' }));
await p.waitForFunction('window.MapView && ["ready", "static"].includes(MapView.state())', { timeout: 40000 }).catch(() => {});
await sleep(3800);
const mp = await p.evaluate(() => ({ state: MapView.state(), canvas: !!document.querySelector('#map canvas'), markers: document.querySelectorAll('#map .mk').length, site: !!document.querySelector('#map .mk-site'),
  attrib: (document.querySelector('#map .maplibregl-ctrl-attrib') || {}).textContent || '', coop: !!document.querySelector('#map .maplibregl-cooperative-gesture-screen'), lib: [...document.scripts].some(s => /cdnjs\.cloudflare\.com\/ajax\/libs\/maplibre-gl\/4\.7\.1\//.test(s.src)) }));
check(`Location map: MapLibre 4.7.1 with OpenFreeMap tiles, site and ${mp.markers} places, attribution (${mp.state})`, mp.state === 'ready' ? mp.canvas && mp.markers === 8 && mp.site && /OpenStreetMap/.test(mp.attrib) && /OpenFreeMap/.test(mp.attrib) && mp.lib : mp.state === 'static', JSON.stringify(mp).slice(0, 160));
await shot(p, '50-map');
if (mp.state === 'ready') {
  // a wheel over the map scrolls the page, it does not zoom the map
  const box = await p.evaluate(() => { const r = document.getElementById('map').getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; });
  const z0 = await p.evaluate(() => MapView.map().getZoom()), y0 = await p.evaluate(() => scrollY);
  await p.mouse.move(box.x, box.y);
  await p.mouse.wheel({ deltaY: 300 });
  await sleep(900);
  const z1 = await p.evaluate(() => MapView.map().getZoom()), y1 = await p.evaluate(() => scrollY);
  check('The map never captures the page scroll (cooperative gestures)', Math.abs(z1 - z0) < .01 && y1 > y0 + 100, `zoom ${z0.toFixed(2)} → ${z1.toFixed(2)} · scroll ${y0} → ${y1}`);
  await p.evaluate(() => document.getElementById('map').scrollIntoView({ block: 'center' }));
  await sleep(500);
  await p.hover('#placelist [data-place="clapham"]');
  await sleep(2200);
  const rt = await p.evaluate(() => { const f = MapView.map().querySourceFeatures('route'); return { n: f.length, on: (document.querySelector('#map .mk.on') || {}).dataset?.place, list: (document.querySelector('#placelist .on') || {}).dataset?.place }; });
  check('Pointing at a place in the list draws its walk on the map', rt.n > 0 && rt.on === 'clapham' && rt.list === 'clapham', JSON.stringify(rt));
  await shot(p, '51-map-route');
  const links = await p.evaluate(() => ({ rows: [...document.querySelectorAll('#placelist a[data-place]')].every(a => a.getAttribute('href') === `map.html#place=${a.dataset.place}`), open: (document.querySelector('#map .map-open') || {}).getAttribute?.('href') }));
  check('Every place in the list and the map itself open the map page (map.html#place=id)', links.rows && links.open === 'map.html', JSON.stringify(links));
  await p.mouse.move(box.x - 120, box.y - 60);
  await sleep(700);
  check('Hovering the map shows the way to the full map', await p.evaluate(() => +getComputedStyle(document.querySelector('#map .map-open')).opacity > .9));
  await shot(p, '51b-map-hover');
  await p.mouse.move(5, 300);
}
check('Location: official image, four area images marked illustrative, Google Maps link', await p.evaluate(() => document.querySelectorAll('.area-pic img').length === 4 && /Images of the area are illustrative/.test(document.querySelector('.loc-fine').textContent) && !!document.querySelector('a[href^="https://www.google.com/maps/search/"]') && !!document.querySelector('.area-main[data-lb]')));
// talk to us: every contact route, and the inline form validates, then opens a prefilled email to the team
const talk = await p.evaluate(() => ({ mail: [...document.querySelectorAll('#contact a[href^="mailto:"]')].map(a => a.getAttribute('href')), tel: [...document.querySelectorAll('#contact a[href^="tel:"]')].map(a => a.getAttribute('href')), topics: document.querySelectorAll('#contact .topic').length, addr: /40 Rosebery Avenue/.test(document.querySelector('#contact').textContent) }));
check('Talk to us: email, phone, address, planning and the five enquiry chips', talk.mail.length === 1 && talk.mail[0].startsWith('mailto:henry@theccp.net') && talk.tel[0] === 'tel:+447736121014' && talk.addr && talk.topics === 5, JSON.stringify(talk));
await p.evaluate(() => { window.__tkMail = null; window.NestTalkOpen = u => { window.__tkMail = u; }; document.querySelector('#tk-form').scrollIntoView({ block: 'center' }); });
await sleep(500);
await p.click('#tk-form button[type="submit"]');
await sleep(200);
const tkBad = await p.evaluate(() => ({ n: document.querySelectorAll('#tk-form .tk-f.bad').length, focus: document.activeElement && document.activeElement.id, msg: document.querySelector('#tk-first-e').textContent }));
await p.type('#tk-first', 'Test');
await p.type('#tk-last', 'Person');
await p.type('#tk-email', 'test@example.com');
await p.click('#contact .topic[data-topic="thames"]');
await p.click('#tk-form button[type="submit"]');
await sleep(500);
const tk = await p.evaluate(() => ({ url: window.__tkMail || '', done: !document.querySelector('#tk-done').hidden, form: document.querySelector('#tk-form').hidden, who: document.querySelector('#tk-done h3').textContent }));
await shot(p, '48b-contact-sent');
check('Talk to us: the form validates, then opens a prefilled email to the team with the chosen topic', tkBad.n === 3 && tkBad.focus === 'tk-first' && !!tkBad.msg && tk.url.startsWith('mailto:henry@theccp.net?') && /Thames%20Path/.test(tk.url) && /Test%20Person/.test(tk.url) && tk.done && tk.form && tk.who === 'Thank you, Test', JSON.stringify({ tkBad, done: tk.done, who: tk.who }));
await p.evaluate(() => { document.querySelector('#tk-done [data-tk="reset"]').click(); delete window.NestTalkOpen; });
await sleep(300);
// fly from the residences section: the page scrolls back up and the card becomes the stage
await p.evaluate(() => document.getElementById('residences').scrollIntoView({ block: 'start' }));
await sleep(900);
await p.click('.home[data-id="bung3"] .home-copy .cta');
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
check('The map button at the top opens the neighbourhood map page', await p.evaluate(() => { const a = document.querySelector('.tr [data-target="location"]'); return a.tagName === 'A' && a.getAttribute('href') === 'map.html'; }));
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
  const metas = [...document.querySelectorAll('meta[name], meta[property]')].filter(m => !/^(viewport)$/.test(m.getAttribute('name') || '')).map(m => m.content).join(' ');
  return document.body.textContent.replace(/\s+/g, ' ') + ' ' + attrs + ' ' + metas + ' ' + document.title;
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
  if (w === 1920) {
    const lazy = await q.evaluate(() => performance.getEntriesByType('resource').map(e => e.name).filter(n => /js\/tracks\.js|js\/map\.js|maplibre|openfreemap|assets\/video/.test(n)));
    check('First load carries no flight track, map script, map tiles or video (they come on intent)', !lazy.length, lazy.join(', ') || 'none');
  }
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
const phPlan = await p.evaluate(() => {
  const h = document.querySelector('#hint'), b = document.querySelector('#band'), r = h.getBoundingClientRect(), sheet = document.querySelector('#ppanel').getBoundingClientRect();
  return { kick: document.querySelector('#pp-kick').textContent, hint: h.textContent, band: +getComputedStyle(b).opacity, shown: getComputedStyle(h).display !== 'none' && r.height > 0, above: r.bottom <= sheet.top + 1, inView: r.top > 0 };
});
check('Phone plan: the sheet says the model is illustrative and the drag hint shows above it', /Illustrative|Official plan/.test(phPlan.kick) && phPlan.band > .9 && phPlan.shown && phPlan.above && phPlan.inView, JSON.stringify(phPlan));
await p.tap('#back');
await waitState(p, 'home');
await p.tap('#panel [data-act="inside"]');
await waitState(p, 'inside', 40000);
await sleep(600);
await shot(p, '31-phone-inside');
const phTour = await p.evaluate(() => ({ mark: getComputedStyle(document.querySelector('#cap-i'), '::after').content, cap: document.querySelector('#cap-i').textContent }));
check('Phone tour: the counter carries the illustrative mark', /Illustrative/.test(phTour.mark), `${phTour.cap}${phTour.mark.replace(/"/g, '')}`);
await p.tap('.bnav [data-act="next"]');
await sleep(1200);
check('Phone: tour arrows in the band, named for views', (await text(p, '#cap-i')).startsWith('02') && await p.evaluate(() => document.querySelector('#bnext').getAttribute('aria-label') === 'Next view'));
await p.tap('.logo');
await waitState(p, 'tower', 20000);
// the page on a phone: scrolled through like a visitor, then a full page picture
{
  const H = await p.evaluate(() => document.documentElement.scrollHeight);
  for (let y = 0; y < H; y += 420) { await p.evaluate(y => scrollTo(0, y), y); await sleep(90); }
  await sleep(1500);
  const ov = await p.evaluate(() => ({ sw: document.documentElement.scrollWidth, vw: document.documentElement.clientWidth, pin: document.documentElement.classList.contains('gsap-pin') }));
  check('Phone: no sideways overflow, no pinned gallery (light motion on small screens)', ov.sw <= ov.vw && !ov.pin, JSON.stringify(ov));
  await p.evaluate(() => scrollTo(0, 0));
  await sleep(600);
}
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
  await f.waitForFunction('App.state() === "home" && !App.busy()', { timeout: 40000 });
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

// ======================================================= without JavaScript: the page is complete and still
{
  const n = await browser.newPage();
  await n.setViewport({ width: 1600, height: 900 });
  await n.setJavaScriptEnabled(false);
  await n.goto(URL_, { waitUntil: 'load', timeout: 120000 });
  const nj = await n.evaluate(() => {
    const vis = e => { let o = 1; for (let k = e; k && k !== document.body; k = k.parentElement) { const s = getComputedStyle(k); if (s.display === 'none' || s.visibility === 'hidden') return 0; o *= +s.opacity; } return o; };
    const els = [...document.querySelectorAll('main .sec h2, main .sec p, main .sec li, main .sec img, footer dd')];
    return { n: els.length, hidden: els.filter(e => vis(e) < .99).map(e => e.tagName + '.' + e.className).slice(0, 5), map: !!document.querySelector('#map .map-static img') };
  });
  check('Without JavaScript every section is fully visible (nothing waits for motion)', nj.n > 100 && !nj.hidden.length && nj.map, `${nj.n} elements · ${nj.hidden.join(', ') || 'none hidden'}`);
  await n.evaluate(() => document.getElementById('location').scrollIntoView());
  await shot(n, '52-no-javascript-location');
  await n.close();
}

// ======================================================= the neighbourhood map page (map.html)
{
  const MAP = new URL('map.html', URL_).href;
  const m = await browser.newPage();
  await m.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1 });
  listen(m, 'map');
  await m.goto(MAP, { waitUntil: 'networkidle2', timeout: 120000 });
  await m.waitForFunction('window.MapPage && ["ready", "static", "failed"].includes(MapPage.state())', { timeout: 40000 }).catch(() => {});
  await sleep(4200);
  const mi = await m.evaluate(() => ({ state: MapPage.state(), places: MapPage.data().places.length, markers: document.querySelectorAll('.pm').length, home: !!document.querySelector('.mk-home'),
    tower: !!MapPage.map().getLayer('home-3d'), logo: (document.querySelector('.tl .logo') || {}).getAttribute?.('href'), logoImg: /logo-light\.png/.test((document.querySelector('.tl .logo img') || {}).src || ''),
    photos: document.querySelectorAll('#plist img').length, attrib: (document.querySelector('.maplibregl-ctrl-attrib') || {}).textContent || '' }));
  check(`Map page: ${mi.places} places with photographs, home marked with the tower, official logo back to the site (${mi.state})`, mi.state === 'ready' && mi.places >= 30 && mi.markers === mi.places && mi.home && mi.tower && mi.logo === 'index.html' && mi.logoImg && mi.photos === mi.places && /OpenStreetMap/.test(mi.attrib), JSON.stringify(mi).slice(0, 200));
  await shot(m, '60-mappage-overview');
  // the wheel: up zooms in, down zooms out
  const z0 = await m.evaluate(() => MapPage.map().getZoom());
  await m.mouse.move(900, 450);
  for (let k = 0; k < 4; k++) { await m.mouse.wheel({ deltaY: -120 }); await sleep(60); }
  await sleep(900);
  const z1 = await m.evaluate(() => MapPage.map().getZoom());
  for (let k = 0; k < 8; k++) { await m.mouse.wheel({ deltaY: 120 }); await sleep(60); }
  await sleep(900);
  const z2 = await m.evaluate(() => MapPage.map().getZoom());
  check('Map page: the wheel up zooms in, down zooms out', z1 > z0 + .2 && z2 < z1 - .2, `${z0.toFixed(2)} → ${z1.toFixed(2)} → ${z2.toFixed(2)}`);
  // a place in the list: the camera flies, the walk is drawn
  await m.click('#plist [data-place="imperial"]');
  await sleep(3600);
  const im = await m.evaluate(() => {
    const p = MapPage.data().places.find(q => q.id === 'imperial'), f = MapPage.map().querySourceFeatures('route');
    const W = [-0.187725, 51.464877], B = [-0.1725, 51.481111];
    const d = (a, b) => Math.hypot((a[0] - b[0]) * 69400, (a[1] - b[1]) * 110540);
    // distance from a point to the line, segment by segment (metres, local flat projection)
    const near = (line, c) => Math.min(...line.slice(1).map((q, i) => {
      const a = line[i], ax = (a[0] - c[0]) * 69400, ay = (a[1] - c[1]) * 110540, bx = (q[0] - c[0]) * 69400, by = (q[1] - c[1]) * 110540;
      const dx = bx - ax, dy = by - ay, t = Math.max(0, Math.min(1, -(ax * dx + ay * dy) / ((dx * dx + dy * dy) || 1)));
      return Math.hypot(ax + t * dx, ay + t * dy);
    }));
    // the longest straight step of each line: a jump across the water would show here
    const jump = line => Math.max(...line.slice(1).map((q, i) => d(q, line[i])));
    return { hash: location.hash, active: MapPage.active(), drawn: f.length, card: document.querySelector('#detail h2')?.textContent, bridgeFoot: p.foot.bridge, bridgeCar: p.car.bridge,
      footNear: Math.round(Math.min(near(p.foot.line, W), near(p.foot.line, B))), carNear: Math.round(Math.min(near(p.car.line, W), near(p.car.line, B))),
      jumpFoot: Math.round(jump(p.foot.line)), jumpCar: Math.round(jump(p.car.line)), footMin: Math.round(p.foot.s / 60), carMin: Math.round(p.car.s / 60), photo: document.querySelector('#detail .d-ph img')?.naturalWidth };
  });
  check('Map page: a click on a place flies there, draws the walk and shows its card with photograph', im.active === 'imperial' && im.hash === '#place=imperial' && im.drawn > 0 && im.card === 'Imperial Wharf' && im.photo > 0, JSON.stringify(im).slice(0, 220));
  check('Imperial Wharf: walk and drive cross the Thames on a bridge, never straight over the water', im.bridgeFoot && im.bridgeCar && im.footNear < 30 && im.carNear < 30 && im.jumpFoot < 420 && im.jumpCar < 420, `walk ${im.footMin} min by ${im.bridgeFoot} · car ${im.carMin} min by ${im.bridgeCar} · ${im.footNear}/${im.carNear} m from the bridge deck · longest straight step ${im.jumpFoot}/${im.jumpCar} m`);
  await shot(m, '61-mappage-imperial-walk');
  // every place across the river reaches it by a bridge
  const cross = await m.evaluate(() => MapPage.data().places.filter(p => ['chelsea', 'imperial', 'fulham', 'physic', 'kings', 'stamford', 'chelwest'].includes(p.id)).map(p => [p.id, p.foot.bridge, p.car.bridge]).filter(x => !x[1] || !x[2]));
  check('Every place across the river: both routes name the bridge they cross', !cross.length, JSON.stringify(cross));
  // walk or car: the way and the times change
  const walkLine = await m.evaluate(() => JSON.stringify(MapPage.route().line));
  await m.click('.modes [data-mode="car"]');
  await sleep(3000);
  const car = await m.evaluate(w => ({ mode: MapPage.mode(), hash: location.hash, differs: JSON.stringify(MapPage.route().line) !== w, body: document.body.dataset.mode, time: document.querySelector('#plist [data-place="imperial"] .pl-t b').textContent, pressed: document.querySelector('#detail .d-mode[data-mode="car"]').getAttribute('aria-pressed') }), walkLine);
  check('Map page: Car switches the route, the times and the address', car.mode === 'car' && car.differs && car.hash === '#place=imperial&mode=car' && car.pressed === 'true', JSON.stringify(car));
  await shot(m, '62-mappage-imperial-car');
  await m.click('.looks [data-look="sat"]');
  await sleep(3500);
  check('Map page: satellite look with Esri imagery', await m.evaluate(() => MapPage.map().getLayoutProperty('sat', 'visibility') === 'visible' && /Esri/.test(document.querySelector('.maplibregl-ctrl-attrib').textContent)));
  await shot(m, '63-mappage-satellite');
  await m.click('.looks [data-look="night"]');
  await m.click('.modes [data-mode="foot"]');
  // no note under the list; the credits live in the map's small attribution ("i"), photo credits open from there
  const at = await m.evaluate(() => ({ note: /Routes follow the streets/.test(document.getElementById('panel').textContent), folded: !document.querySelector('.maplibregl-ctrl-attrib').classList.contains('maplibregl-compact-show'),
    link: !!document.querySelector('.maplibregl-ctrl-attrib [data-credits]') }));
  await m.click('.maplibregl-ctrl-attrib-button');
  await sleep(300);
  await m.click('.maplibregl-ctrl-attrib [data-credits]');
  await sleep(400);
  at.opened = await m.evaluate(() => !document.getElementById('credits').hidden && document.querySelectorAll('#creditlist li').length);
  check('Map page: no note under the list; attribution folded in the corner, photo credits open from it', !at.note && at.folded && at.link && at.opened >= 30, JSON.stringify(at));
  await m.keyboard.press('Escape');
  // category filters: icons only, the name on hover, the chosen one named beside them
  const ch = await m.evaluate(() => [...document.querySelectorAll('#chips .chip')].map(b => ({ label: b.getAttribute('aria-label'), text: [...b.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent.trim()).join(''), svg: !!b.querySelector('svg') })));
  await m.hover('#chips .chip[data-cat="parks"]');
  await sleep(400);
  const tip = await m.evaluate(() => +getComputedStyle(document.querySelector('#chips .chip[data-cat="parks"] .chip-tip')).opacity);
  await m.click('#chips .chip[data-cat="parks"]');
  await sleep(1500);
  const cf = await m.evaluate(() => ({ now: document.getElementById('chipsnow').textContent, pressed: document.querySelector('#chips .chip[data-cat="parks"]').getAttribute('aria-pressed'), shown: [...document.querySelectorAll('#plist li')].filter(li => !li.hidden).length, markers: document.querySelectorAll('.pm:not(.off)').length }));
  check('Map page: category filters are icons with a name on hover; Parks filters the list and the map', ch.length === 7 && ch.every(c => c.label && !c.text && c.svg) && tip > .9 && cf.now === 'Parks' && cf.pressed === 'true' && cf.markers < 12, JSON.stringify({ n: ch.length, tip, ...cf }));
  await shot(m, '63b-mappage-filter-parks');
  await m.click('#chips .chip[data-cat="all"]');
  // the map page text keeps the site rules
  const mtext = await m.evaluate(() => { document.getElementById('credits').hidden = false; const t = document.body.innerText + ' ' + [...document.querySelectorAll('[aria-label],[alt]')].map(e => (e.getAttribute('aria-label') || '') + ' ' + (e.getAttribute('alt') || '')).join(' ') + ' ' + document.title; document.getElementById('credits').hidden = true; return t; });
  const md = mtext.match(/.{0,16}[‐-―−-].{0,16}/g), mp2 = mtext.match(/[£$€]\s?\d|\bpcm\b|per\s+(month|week)|asking|for sale|\bprices?\b|\brents?\b(?<!build to rent)|\brental\b/gi);
  check('Map page: no dash or hyphen, no price, rent or sale in the text', !md && !mp2, (md || []).concat(mp2 || []).slice(0, 4).join(' ¦ ') || 'none');
  await m.close();
  // a deep link, as the section's list sends it
  const dl = await browser.newPage();
  await dl.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1 });
  listen(dl, 'map-deeplink');
  await dl.goto(new URL('index.html', URL_).href, { waitUntil: 'networkidle2', timeout: 120000 });
  await dl.evaluate(() => document.getElementById('location').scrollIntoView({ block: 'center' }));
  await sleep(800);
  await Promise.all([dl.waitForNavigation({ waitUntil: 'load', timeout: 60000 }), dl.evaluate(() => document.querySelector('#placelist [data-place="pier"]').click())]);
  await dl.waitForFunction('window.MapPage && MapPage.state() === "ready"', { timeout: 40000 }).catch(() => {});
  await sleep(3800);
  const dk = await dl.evaluate(() => ({ url: location.pathname + location.hash, active: MapPage.active(), card: document.querySelector('#detail h2')?.textContent, drawn: MapPage.map().querySourceFeatures('route').length }));
  check('Around the corner opens the map page on that place', /map\.html#place=pier$/.test(dk.url) && dk.active === 'pier' && dk.drawn > 0, JSON.stringify(dk));
  await shot(dl, '64-mappage-deeplink-pier');
  await dl.close();
  // a phone
  const ph = await browser.newPage();
  await ph.setViewport({ width: 390, height: 844, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
  listen(ph, 'map-phone');
  await ph.goto(MAP + '#place=lake', { waitUntil: 'load', timeout: 120000 });
  await ph.waitForFunction('window.MapPage && MapPage.state() === "ready"', { timeout: 40000 }).catch(() => {});
  await sleep(4000);
  const pq = await ph.evaluate(() => ({ w: document.documentElement.scrollWidth, card: !document.getElementById('detail').hidden, active: MapPage.active() }));
  check('Map page on a phone: no sideways scroll, the place card opens from the address', pq.w <= 390 && pq.card && pq.active === 'lake', JSON.stringify(pq));
  await shot(ph, '65-mappage-phone-lake');
  await ph.evaluate(() => MapPage.select(null));
  await sleep(2600);
  await shot(ph, '66-mappage-phone-list');
  await ph.close();
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
  await r.keyboard.press('Escape');
  await r.waitForFunction('App.state() === "tower" && !App.busy()', { timeout: 10000 });
  await r.waitForFunction('window.NestMotion && window.NestMotion.ready', { timeout: 30000 }).catch(() => {});
  const H = await r.evaluate(() => document.documentElement.scrollHeight);
  for (let y = 0; y < H; y += 500) { await r.evaluate(y => scrollTo(0, y), y); await sleep(80); }
  await sleep(1200);
  const calm = await r.evaluate(() => {
    const moved = [...document.querySelectorAll('main [data-depth]:not(.sticker), main .px picture, #card')].filter(e => { const t = getComputedStyle(e).transform; return t && t !== 'none' && !/^matrix\(1, 0, 0, 1, 0, 0\)$/.test(t); });
    return { pin: document.documentElement.classList.contains('gsap-pin'), moved: moved.length, lag: getComputedStyle(document.querySelector('#card')).translate };
  });
  check('Reduced motion: no parallax, no pinning, sections only fade in', !calm.pin && calm.moved === 0, JSON.stringify(calm));
  await r.close();
}
await browser.close();
const errs = logs.filter(l => /error|requestfailed|http [45]/.test(l));
check('No console errors or failed requests', errs.length === 0, errs.slice(0, 4).join(' | '));
if (pendingPhotos.length) note(`${pendingPhotos.length} room photographs not delivered yet, stand ins shown: ${pendingPhotos.join(', ')} (${expected.length} expected 404s ignored)`);
fs.writeFileSync(`${OUT}/report.json`, JSON.stringify({ results, logs, expected, pendingPhotos }, null, 2));
console.log(`\n${results.filter(r => r.ok).length}/${results.length} passed`);
