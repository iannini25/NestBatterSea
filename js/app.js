/* ============================================================
   NEST BATTERSEA | interaction, notched card layout
   tower -> flight -> home -> (inside | plan -> room) -> back
   The hero card is the stage. Every camera move is a video that
   starts on the still it leaves from and ends on the still it
   arrives at, so nothing jumps: only the camera moves. During a
   flight the window outline follows the home frame by frame
   (js/tracks.js, written with the videos).
   Below the card: notched section cards, the exterior views
   lightbox, the plan tabs and the places list. Scroll motion
   lives in js/motion.js (GSAP), the map in js/map.js.
   ============================================================ */
const App = (() => {

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const NS = 'http://www.w3.org/2000/svg';
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
const touch = matchMedia('(hover: none)').matches;
const MQ = matchMedia('(max-width: 860px), (max-width: 1100px) and (orientation: portrait)');
let mobile = MQ.matches;
const conn = navigator.connection || {};
// phones (and Save Data) get the 720p clips; elsewhere the card size decides
const SMALL = (matchMedia('(pointer: coarse)').matches && Math.min(innerWidth, innerHeight) <= 600) || !!conn.saveData;
const AV1 = document.createElement('video').canPlayType('video/mp4; codecs="av01.0.08M.08"') === 'probably';
const av1For = name => AV1 && typeof VIDEO_AV1 !== 'undefined' && (VIDEO_AV1 === true || (Array.isArray(VIDEO_AV1) && VIDEO_AV1.includes(name)));
let HI = true;                                   // 1080p unless the card is small
// the clips and their end frames carry the page's cache version, so a new render is never served stale
const vsrc = (name, rev) => `assets/video/${name}${rev ? '-rev' : ''}${HI ? '' : '-720'}${av1For(name) ? '-av1' : ''}.mp4${VER}`;
const stillOf = r => `assets/stills/${r.flight}-last.jpg${VER}`;
const stillIn = r => `assets/stills/${r.inside}-last.jpg${VER}`;
const byId = id => RESIDENCES.find(r => r.id === id);
const pad2 = n => String(n).padStart(2, '0');
const HF = typeof HANDOFF_FADE === 'number' ? HANDOFF_FADE : .15;   // walk in clip to photograph, seconds
// scripts that load on demand carry the same cache version as this one
const VER = (() => { const m = (document.querySelector('script[src*="js/app"]') || {}).src?.match(/[?&]v=(\w+)/); return m ? `?v=${m[1]}` : ''; })();
const addScript = src => new Promise(res => { const s = document.createElement('script'); s.src = src + VER; s.onload = s.onerror = () => res(); document.head.appendChild(s); });
/* window tracks of the forward flights (js/tracks.js, written with the videos):
   { id: { fps, frames: [[u0, v0, u1, v1]], h: [[3x3 facade homography, row major]] } }
   (older tracks carried cam: [[cx, cy, w]] for a flat zoom instead of h). Loaded at the first
   sign of intent (pointing at a home, the mini card, a fly button), never with the page. */
let tracksP = null;
const TRACKS = () => (typeof FLIGHT_TRACKS !== 'undefined' && FLIGHT_TRACKS ? FLIGHT_TRACKS : null);
const loadTracks = () => TRACKS() ? Promise.resolve() : (tracksP || (tracksP = addScript('js/tracks.js')));

const el = {
  html: document.documentElement, body: document.body, card: $('#card'), frame: $('#frame'), master: $('#master'),
  windows: $('#windows'), dimhole: $('#dimhole'), motion: $('#motion'), vid: $('#vid'), trail: $('#trail'),
  trailpoly: $('#trailpoly'), still: $('#still'), stillimg: $('#stillimg'), photos: $('#photos'), plan: $('#plan'),
  plan3d: $('#plan3d'), plan2d: $('#plan2d'), planimg: $('#planimg'), tag: $('#tag'), tl: $('#tl'), tr: $('#tr'),
  logo: $('.logo'), back: $('#back'), backlbl: $('#backlbl'), mini: $('#mini'), miniNav: $('.mini-nav'),
  minicard: $('#minicard'), miniImg: $('#mini-img'), miniAvif: $('#mini-avif'), miniWebp: $('#mini-webp'), miniK: $('#mini-k'), miniN: $('#mini-n'), miniS: $('#mini-s'),
  minibar: $('#minibar'), mprev: $('#mprev'), mnext: $('#mnext'), picker: $('#picker'), panel: $('#panel'),
  ppanel: $('#ppanel'), toggle: $('#pp-toggle'), rooms: $('#pp-rooms'), hinttxt: $('#hinttxt'), note: $('#note'),
  capI: $('#cap-i'), capT: $('#cap-t'), capS: $('#cap-s'), bprev: $('#bprev'), bnext: $('#bnext'), facade: $('#facade'),
  ppkick: $('#pp-kick'), band: $('#band'), cap: $('#cap'), tourt: $('#tourt'), ttfg: $('#tt-fg'), ttn: $('#tt-n')
};

let state = 'boot', cur = null, busy = false, armed = null, sel = 0, hot = null, returning = false;
let fit = { s: 1, W: 1, H: 1, cs: 1, cx: 0, cy: 0 }, zoomK = 1, settleId = 0, kbd = false, heroSeen = true;

/* ---------- tiny tween (no external libraries) --------------------- */
const ease = t => 1 - Math.pow(1 - t, 3);
const easeIO = t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
function tween(dur, fn, e = ease) {
  if (reduced || dur <= 0) { fn(1); return Promise.resolve(); }
  return new Promise(res => {
    const t0 = performance.now();
    const step = now => {
      const t = Math.min(1, (now - t0) / (dur * 1000));
      fn(e(t));
      t < 1 ? requestAnimationFrame(step) : res();
    };
    requestAnimationFrame(step);
  });
}
const wait = ms => new Promise(r => setTimeout(r, reduced ? 0 : ms));
const raf = () => new Promise(r => requestAnimationFrame(r));
const idle = fn => (window.requestIdleCallback ? requestIdleCallback(fn, { timeout: 2000 }) : setTimeout(fn, 900));
const show = (n, o = 1) => { n.style.visibility = 'visible'; n.style.opacity = o; };
const hide = n => { n.style.opacity = 0; n.style.visibility = 'hidden'; };
const fade = (n, to, dur) => {
  if (to > 0) n.style.visibility = 'visible';
  const from = parseFloat(n.style.opacity || (to > 0 ? 0 : 1));
  return tween(dur, k => { n.style.opacity = from + (to - from) * k; }).then(() => { if (to === 0) n.style.visibility = 'hidden'; });
};

/* ---------- state, window title, stage lock ------------------------ */
const STAGED = s => s !== 'boot' && s !== 'tower';
function setBusy(b) { busy = b; el.body.classList.toggle('busy', b); }
function setState(s) {
  const was = STAGED(state);
  state = s;
  el.body.dataset.state = s;
  if (s === 'tower') breathe.start();
  const now = STAGED(s);
  if (was !== now) {
    el.body.classList.toggle('staged', now);
    lockPage(now);
    el.back.tabIndex = now ? 0 : -1;
    el.back.setAttribute('aria-hidden', String(!now));
    el.facade.setAttribute('aria-hidden', String(now));     // the tower image is not what the stage shows
    if (now && hot) highlight(hot, false);
    notchUpdate(true);
  }
  el.plan.toggleAttribute('inert', s === 'room');           // the model's room labels sit under the photograph
  backLabel(); band(); renderMini(); title();
  tourSync();                                               // the tour runs only while a view is on screen
}
// on the stage the page below is locked: no scrolling, no focus, hidden from assistive tech
function lockPage(on) {
  el.html.classList.toggle('locked', on);
  $$('main > .sec, .foot').forEach(n => n.toggleAttribute('inert', on));
  if (on && scrollY) scrollTo(0, 0);
  // the scroll motion refreshes its triggers when the page scroll is locked or unlocked
  document.dispatchEvent(new CustomEvent('nest:lock', { detail: { locked: on } }));
}
function title() {
  const parts = [];
  if (cur && STAGED(state)) {
    parts.push(cur.name);
    if (state === 'plan') parts.push('Floor plan');
    if ((state === 'inside' || state === 'room') && shots.list[shots.i]) parts.push(shots.list[shots.i].name);
  }
  const ov = $('.overlay.open');
  if (ov) parts.unshift(ov.getAttribute('aria-label'));
  document.title = parts.length ? parts.concat('Nest Battersea').join(' | ') : 'Nest Battersea | Sky homes above the Thames';
}
function backLabel() {
  const t = { flight: 'Back to the tower', home: 'Back to the tower', inside: 'Back outside', plan: 'Back to the residence', room: 'Back to the plan' }[state];
  if (t) el.backlbl.textContent = t;
}
// one width for every label, so the notch only moves when the stage opens or closes
function backWidth() {
  el.back.style.minWidth = '';
  if (mobile) return;
  const keep = el.backlbl.textContent;
  let w = 0;
  ['Back to the tower', 'Back to the residence', 'Back to the plan', 'Back outside'].forEach(l => {
    el.backlbl.textContent = l; w = Math.max(w, el.back.offsetWidth);
  });
  el.backlbl.textContent = keep;
  el.back.style.minWidth = Math.ceil(w) + 'px';
}
async function toTop() {
  if (scrollY < 1) return;
  scrollTo({ top: 0, behavior: reduced ? 'auto' : 'smooth' });
  const t0 = performance.now();
  while (scrollY > 0.5 && performance.now() - t0 < 1600) await raf();
  scrollTo(0, 0);
}

/* ---------- media: fetch once, play from memory -------------------- */
const blobs = {}, prog = {};
function fetchBlob(url) {
  if (!blobs[url]) blobs[url] = (async () => {
    try {
      const r = await fetch(url);
      if (!r.ok) throw new Error(url);
      const total = +r.headers.get('content-length') || 0;
      if (!r.body || !total) return URL.createObjectURL(await r.blob());
      const reader = r.body.getReader(), parts = [];
      let got = 0;
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        parts.push(value); got += value.length; prog[url] = got / total;
      }
      return URL.createObjectURL(new Blob(parts, { type: 'video/mp4' }));
    } catch (e) { return url; }
  })();
  return blobs[url];
}
function loadImg(src) {
  return new Promise(res => { const i = new Image(); i.onload = i.onerror = () => res(i); i.src = src; });
}
function prefetch(r) {
  if (!r) return;
  if (!reduced) { fetchBlob(vsrc(r.flight)); loadTracks(); }
  loadImg(stillOf(r));
}
/* room photographs: the browser picks AVIF, WebP or JPEG; a stand in if a file is missing */
const missing = new Set();
const PIC = (id, ext) => `assets/interiors/${id}.${ext}${VER}`;   // versioned: Step inside ends on loft4/bung3-living
function setPhoto(img, id) {
  const pic = img.parentNode && img.parentNode.tagName === 'PICTURE' ? img.parentNode : null;
  if (pic) $$('source', pic).forEach(x => x.remove());
  const standin = () => PHOTO_STANDIN[id] || `${PIC(id, 'jpg')}`;
  if (missing.has(id)) { img.onerror = null; img.src = standin(); return; }
  if (pic) pic.insertAdjacentHTML('afterbegin', `<source type="image/avif" srcset="${PIC(id, 'avif')}"><source type="image/webp" srcset="${PIC(id, 'webp')}">`);
  img.onerror = () => {
    img.onerror = null;
    missing.add(id);
    if (pic) $$('source', pic).forEach(x => x.remove());
    img.src = standin();
  };
  img.src = `${PIC(id, 'jpg')}`;
}
function decodeImg(img) {
  return new Promise(res => {
    let done = false;
    const end = () => { if (!done) { done = true; res(); } };
    const dec = () => (img.decode ? img.decode().then(end, end) : end());
    if (img.complete && img.naturalWidth) return dec();
    img.addEventListener('load', dec, { once: true });
    img.addEventListener('error', () => setTimeout(end, 500), { once: true });
    setTimeout(end, 6000);
  });
}

/* ---------- facade framing: cover fit inside the card --------------- */
function layout() {
  const r = el.card.getBoundingClientRect();
  if (!r.width || !r.height) return;
  mobile = MQ.matches;
  fit.W = r.width; fit.H = r.height;
  fit.s = Math.max(fit.W / MASTER.w, fit.H / MASTER.h);
  applyZoom(zoomK);
  HI = !SMALL && Math.max(fit.W, fit.H * 16 / 9) * Math.min(devicePixelRatio || 1, 2) >= 1500;
  notchUpdate(false);
  if (hot) placeTag(hot);
  if (mobile && state === 'plan') planSheet();
}
function applyZoom(k) {
  zoomK = k;
  const s = fit.s * k;
  const x = (fit.W - MASTER.w * s) / 2, y = (fit.H - MASTER.h * s) / 2;
  el.frame.style.transform = `translate(${x}px,${y}px) scale(${s})`;
  fit.cs = s; fit.cx = x; fit.cy = y;
}
const toCard = (px, py) => [fit.cx + px * fit.cs, fit.cy + py * fit.cs];
let layoutQ = 0;
const relayout = () => { if (!layoutQ) layoutQ = requestAnimationFrame(() => { layoutQ = 0; layout(); }); };

/* ---------- the notches ------------------------------------------- */
// measured from the UI that sits in each notch, so the curves always wrap it exactly
const N = { cur: null, raf: 0 };
const cssPx = n => parseFloat(getComputedStyle(el.html).getPropertyValue(n)) || 0;
function notchTarget() {
  const g = cssPx('--g'), f = cssPx('--f'), R = cssPx('--R');
  const c = el.card.getBoundingClientRect();
  const hb = el.logo.offsetHeight;
  let right = el.tl.offsetLeft + el.logo.offsetWidth;
  if (STAGED(state)) right = el.tl.offsetLeft + el.back.offsetLeft + el.back.offsetWidth;
  const tl = { w: right - c.left + g, h: hb + g, r: hb / 2 + g };
  const th = el.tr.offsetHeight;
  const tr = { w: c.right - el.tr.offsetLeft + g, h: th + g, r: th / 2 + g };
  const br = [];
  if (!mobile && el.mini.offsetParent) {
    const mr = parseFloat(getComputedStyle(el.minicard).borderTopLeftRadius) || 22;
    const nh = el.miniNav.offsetHeight;
    br.push({ w: el.minicard.offsetWidth + g, h: el.minicard.offsetHeight + g, r: mr + g },
            { w: el.miniNav.offsetWidth + g, h: nh + g, r: nh / 2 + g });
  }
  return { R, f, tl, tr, br };
}
function notchApply(spec) {
  const c = el.card.getBoundingClientRect();
  Notch.apply(el.card, c.width, c.height, spec);
}
function notchUpdate(animate) {
  const t = notchTarget();
  cancelAnimationFrame(N.raf);
  if (!animate || reduced || !N.cur || N.cur.br.length !== t.br.length) { N.cur = t; notchApply(t); return; }
  const from = N.cur, t0 = performance.now(), dur = 560;
  const L = (a, b, k) => a + (b - a) * k;
  const mix = (a, b, k) => ({ w: L(a.w, b.w, k), h: L(a.h, b.h, k), r: L(a.r, b.r, k) });
  const step = now => {
    const k = easeIO(Math.min(1, (now - t0) / dur));
    N.cur = { R: t.R, f: t.f, tl: mix(from.tl, t.tl, k), tr: mix(from.tr, t.tr, k), br: t.br.map((s, i) => mix(from.br[i], s, k)) };
    notchApply(N.cur);
    if (k < 1) N.raf = requestAnimationFrame(step);
  };
  N.raf = requestAnimationFrame(step);
}

/* ---------- the two available windows ------------------------------- */
function svgEl(tag, attrs) { const n = document.createElementNS(NS, tag); for (const k in attrs) n.setAttribute(k, attrs[k]); return n; }
function polyOf(r) { const [x0, y0, x1, y1] = r.window; return r.poly || [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]; }
function grow(pts, d) {
  const cx = pts.reduce((a, p) => a + p[0], 0) / pts.length, cy = pts.reduce((a, p) => a + p[1], 0) / pts.length;
  return pts.map(([x, y]) => [x + Math.sign(x - cx) * d, y + Math.sign(y - cy) * d]);
}
const ptsAttr = pts => pts.map(p => p.map(v => +v.toFixed(2)).join(',')).join(' ');
function buildWindows() {
  RESIDENCES.forEach(r => {
    const [x0, y0, x1, y1] = r.window;
    const pts = polyOf(r), w = x1 - x0, h = y1 - y0;
    const cx = pts.reduce((a, p) => a + p[0], 0) / pts.length, cy = pts.reduce((a, p) => a + p[1], 0) / pts.length;
    const pad = touch ? 26 : 12;                           // the bay is small on screen: a generous hit area
    const g = svgEl('g', { class: 'win', 'data-id': r.id });   // keyboard and screen readers use the mini card
    const glow = svgEl('polygon', { class: 'glow', points: ptsAttr(grow(pts, 3)) });
    const edge = svgEl('polygon', { class: 'edge', points: ptsAttr(pts) });
    const ring = svgEl('circle', { class: 'ring', cx, cy, r: 7 });
    const beacon = svgEl('circle', { class: 'beacon', cx, cy, r: 3.2 });
    const hit = svgEl('rect', { class: 'hit', x: x0 - pad, y: y0 - pad, width: w + 2 * pad, height: h + 2 * pad });
    g.append(glow, edge, ring, beacon, hit);
    el.windows.appendChild(g);
    r._g = g; r._glow = glow; r._ring = ring;
    r._hole = 'M' + grow(pts, 1.5).map(p => p.map(v => v.toFixed(1)).join(' ')).join('L') + 'Z';
    hit.addEventListener('pointerenter', e => { if (e.pointerType !== 'touch') { highlight(r, true); prefetch(r); } });
    hit.addEventListener('pointerleave', e => { if (e.pointerType !== 'touch') highlight(r, false); });
    hit.addEventListener('click', e => { e.stopPropagation(); pick(r); });
  });
  breathe.start();
}
// a slow breathing glow on each available window, so they read as lit and open
const breathe = (() => {
  let id = 0;
  const t0 = performance.now();
  const frame = now => {
    id = 0;
    if (state !== 'tower' && state !== 'boot') return;
    if (!heroSeen || document.hidden) return;
    const t = (now - t0) / 1000;
    RESIDENCES.forEach((r, i) => {
      if (r._g.classList.contains('on')) return;
      const k = (Math.sin(t * 1.6 + i * 1.7) + 1) / 2, p = (t * .55 + i * .5) % 1;
      r._glow.style.opacity = (.18 + .22 * k).toFixed(3);
      r._ring.setAttribute('r', (6 + 9 * p).toFixed(2));
      r._ring.style.opacity = (.85 * (1 - p)).toFixed(3);
    });
    id = requestAnimationFrame(frame);
  };
  return { start() { if (!reduced && !id) id = requestAnimationFrame(frame); } };
})();

function placeTag(r) {
  const [x0, y0, x1] = r.window;
  const [sx, sy] = toCard((x0 + x1) / 2, y0);
  const half = Math.min(150, fit.W / 2 - 12);
  el.tag.style.left = Math.min(Math.max(sx, half + 12), fit.W - half - 12) + 'px';
  el.tag.style.top = Math.max(sy, mobile ? 150 : 130) + 'px';
}
function highlight(r, on) {
  if (state !== 'tower' && state !== 'boot') on = false;
  if (on) {
    if (hot && hot !== r) highlight(hot, false);
    hot = r;
    r._g.classList.add('on');
    el.dimhole.setAttribute('d', r._hole);
    el.body.classList.add('dim');
    el.tag.querySelector('b').textContent = r.name;
    el.tag.querySelector('.tag-sp').textContent = `${r.beds} bed · ${r.interior} m² · garden ${r.garden} m²`;
    el.tag.querySelector('.tag-lv').textContent = `${r.levels}, illustrative position`;
    el.tag.querySelector('em').textContent = touch ? 'Tap again to fly in' : 'Click to fly in';
    placeTag(r);
    el.tag.classList.add('on');
    const i = RESIDENCES.indexOf(r);
    if (i !== sel) { sel = i; renderMini(); }
    markPicker();
  } else {
    r._g.classList.remove('on');
    if (hot === r) {
      hot = null;
      el.body.classList.remove('dim');
      el.tag.classList.remove('on', 'armed');
    }
    if (armed === r) armed = null;
    markPicker();
  }
}
let briefT = 0;
function highlightBrief(r) {
  clearTimeout(briefT);
  highlight(r, true);
  briefT = setTimeout(() => { if (hot === r && armed !== r && !el.minicard.matches(':hover')) highlight(r, false); }, 2400);
}
// a residence chosen on the tower: on touch the first tap shows it, the second flies
function pick(r) {
  if (state !== 'tower') return;
  if (touch && armed !== r) { arm(r); return; }
  fly(r);
}
function arm(r) {
  highlight(r, true);
  armed = r;
  el.tag.classList.add('armed');
  markPicker();
  prefetch(r);
}

/* ---------- mobile picker: a small two part toggle ------------------ */
function buildPicker() {
  el.picker.innerHTML = RESIDENCES.map(r =>
    `<button type="button" data-id="${r.id}" aria-label="${r.name}, ${r.levels}, illustrative">${r.name}</button>`).join('');
  $$('button', el.picker).forEach(b => {
    const r = byId(b.dataset.id);
    b.addEventListener('pointerenter', e => { if (e.pointerType === 'mouse') { highlight(r, true); prefetch(r); } });
    b.addEventListener('pointerleave', e => { if (e.pointerType === 'mouse') highlight(r, false); });
    b.addEventListener('click', e => { e.stopPropagation(); pick(r); });
  });
}
function markPicker() {
  $$('button', el.picker).forEach(b => b.classList.toggle('on', !!hot && b.dataset.id === hot.id));
}

/* ---------- the mini card in the bottom right notch ------------------ */
let planHover = null, miniKey = '', miniT = 0;
function other(r) { return RESIDENCES[(RESIDENCES.indexOf(r) + 1) % RESIDENCES.length]; }
const specLine = r => `${r.beds} bed · ${r.interior} m² · garden ${r.garden} m²`;
function miniModel() {
  const n = RESIDENCES.length;
  const home = r => ({ thumb: r.thumb, label: `Fly to ${r.name}, ${r.beds} bedrooms, ${r.interior} square metres, ${r.levels}, illustrative` });
  if (state === 'boot' || state === 'tower') {
    const r = RESIDENCES[sel];
    return { k: `Open to explore · ${sel + 1} of ${n}`, n: r.name, s: specLine(r), ...home(r), nav: 'residence' };
  }
  if (!cur) return null;
  if (state === 'flight') {
    return { k: returning ? 'Back to the tower' : 'Flying in', n: cur.name, s: `${cur.levels}, illustrative`, thumb: cur.thumb, off: true, nav: 'off' };
  }
  if (state === 'home') {
    const o = other(cur);
    return { k: 'Also open to explore', n: o.name, s: specLine(o), ...home(o), nav: 'residence' };
  }
  if (state === 'inside' || state === 'room') {
    // the band already captions the photograph on screen: the card shows where a click goes next
    const s = shots.list[shots.i], L = shots.list.length;
    if (!s) return null;
    const nx = shots.list[(shots.i + 1) % L], same = nx.room === s.room;
    return { k: same ? 'Another view' : 'Next room', n: nx.name, s: nx.sub || cur.name, shot: nx, label: `Next view: ${nx.name}`, nav: 'view', kind: 'next' };
  }
  if (state === 'plan') {
    const rm = planHover || cur.rooms[0];
    return { k: planHover ? 'Have a look' : 'Choose a room', n: rm.name, s: levelName(cur, rm.level), photo: rm.open || rm.photo, label: `${rm.name}, see the photograph`, nav: 'room' };
  }
  return { keep: true, off: true, nav: 'off' };
}
function setMiniImg(m) {
  const img = el.miniImg, id = m.shot ? m.shot.id : m.photo;
  img.onerror = null;
  el.miniAvif.removeAttribute('srcset'); el.miniWebp.removeAttribute('srcset');
  if (m.thumb) { el.miniWebp.srcset = m.thumb + '.webp'; img.src = m.thumb + '.jpg'; return; }
  if (!id) return;
  if (missing.has(id)) { img.src = PHOTO_STANDIN[id] || `${PIC(id, 'jpg')}`; return; }
  el.miniAvif.srcset = `${PIC(id, 'avif')}`; el.miniWebp.srcset = `${PIC(id, 'webp')}`;
  img.onerror = () => { img.onerror = null; missing.add(id); el.miniAvif.removeAttribute('srcset'); el.miniWebp.removeAttribute('srcset'); img.src = PHOTO_STANDIN[id] || ''; };
  img.src = `${PIC(id, 'jpg')}`;
}
function renderMini(instant) {
  const m = miniModel();
  if (!m) return;
  const off = !!m.off;
  el.minicard.setAttribute('aria-disabled', String(off));
  const navOff = m.nav === 'off';
  [el.mprev, el.mnext].forEach(b => b.setAttribute('aria-disabled', String(navOff)));
  const what = m.nav === 'room' ? 'room' : m.nav === 'view' ? 'view' : 'residence';
  el.mprev.setAttribute('aria-label', `Previous ${what}`);
  el.mnext.setAttribute('aria-label', `Next ${what}`);
  el.minicard.dataset.kind = m.kind || '';
  if (m.keep) return;
  if (m.label) el.minicard.setAttribute('aria-label', m.label); else el.minicard.removeAttribute('aria-label');
  const key = [m.k, m.n, m.s, m.thumb || (m.shot && m.shot.id) || m.photo].join('|');
  if (key === miniKey) return;
  const first = !miniKey;
  miniKey = key;
  const put = () => { el.miniK.textContent = m.k; el.miniN.textContent = m.n; el.miniS.textContent = m.s || ''; setMiniImg(m); };
  clearTimeout(miniT);
  if (instant || first || reduced) { put(); el.mini.classList.remove('swap'); return; }
  el.mini.classList.add('swap');
  miniT = setTimeout(() => {
    put();
    const done = () => el.mini.classList.remove('swap');
    (el.miniImg.decode ? el.miniImg.decode() : Promise.resolve()).then(done, done);
    setTimeout(done, 450);
  }, 190);
}
const miniBar = k => { el.minibar.style.transform = `scaleX(${Math.max(0, Math.min(1, k)).toFixed(4)})`; };
function miniGo() {
  if (busy) return;
  if (state === 'tower') return fly(RESIDENCES[sel]);
  if (state === 'home') return goTo(other(cur));
  if (state === 'inside' || state === 'room') return step(1);
  if (state === 'plan') return openRoom(planHover || cur.rooms[0]);
}
// previous / next: residences on the tower, rooms on the stage
function step(dir) {
  if (busy) return;
  const n = RESIDENCES.length;
  if (state === 'tower') { sel = (sel + dir + n) % n; renderMini(); highlightBrief(RESIDENCES[sel]); prefetch(RESIDENCES[sel]); return; }
  if (state === 'home') return goTo(RESIDENCES[(RESIDENCES.indexOf(cur) + dir + n) % n]);
  if (state === 'inside') return shotShow((shots.i + dir + shots.list.length) % shots.list.length);
  if (state === 'room') return roomGo((shots.i + dir + shots.list.length) % shots.list.length);
  if (state === 'plan') { const rs = cur.rooms; return openRoom(dir > 0 ? rs[0] : rs[rs.length - 1]); }
}

/* ---------- bottom band ------------------------------------------------ */
function band() {
  const s = state;
  const flat = viewer && viewer.mode === '2d';
  el.note.textContent = s === 'inside' || s === 'room' ? 'Interiors are illustrative'
    : s === 'plan' ? (flat ? 'Official diagrammatic plan' : 'Illustrative 3D model') : 'Levels are illustrative';
  if (s === 'plan') el.hinttxt.textContent = flat ? (touch ? 'Tap a room to look inside' : 'Choose a room to look inside')
    : touch ? (fit.W < 340 ? 'Drag to turn, tap a room' : 'Drag to turn, tap a room to look inside') : 'Drag to turn, click a room to look inside';
  else el.hinttxt.textContent = mobile ? (touch ? 'Tap a glowing window' : 'Point at a glowing window') : touch ? 'Tap a glowing window to explore' : 'Hover a glowing window to explore';
  // on phones the plan sheet hides the band note: its kicker says what the model is
  if (cur && s === 'plan') el.ppkick.textContent = `Floor plan · ${cur.ref}` + (mobile ? ` · ${flat ? 'Official plan' : 'Illustrative'}` : '');
  // the phone arrows in the band step through the views of the tour
  const tour = s === 'inside' || s === 'room';
  el.bprev.setAttribute('aria-label', tour ? 'Previous view' : 'Previous');
  el.bnext.setAttribute('aria-label', tour ? 'Next view' : 'Next');
  caption();
}
function caption() {
  const s = shots.list[shots.i];
  if (!s || (state !== 'inside' && state !== 'room')) return;
  el.capI.textContent = `${pad2(shots.i + 1)} / ${pad2(shots.list.length)}`;
  el.capT.textContent = s.name;
  el.capS.textContent = s.sub || '';
}

/* ---------- video playback -------------------------------------------- */
function prepVideo(src) {
  return new Promise(res => {
    const v = el.vid;
    v.pause();
    let done = false;
    const ok = () => { if (done) return; done = true; res(); };
    v.addEventListener('loadeddata', ok, { once: true });
    v.src = src;
    v.load();
    setTimeout(ok, 4000);
  });
}
function playVideo(onFrame) {
  return new Promise(res => {
    const v = el.vid;
    let done = false;
    const finish = () => { if (done) return; done = true; res(); };
    v.onended = finish;
    const tick = () => {
      if (done) return;
      if (onFrame && v.duration) onFrame(v.currentTime, v.duration);
      if (v.duration && v.currentTime >= v.duration - 0.02) finish(); else requestAnimationFrame(tick);
    };
    const go = () => { requestAnimationFrame(tick); setTimeout(finish, ((v.duration || 7) + 2) * 1000); };
    const p = v.play();
    if (p && p.then) p.then(go).catch(finish); else go();
  });
}
/* the window outline on the tower framing (the hover outline's place) */
function outlineAt(r, op) {
  el.trailpoly.setAttribute('points', ptsAttr(polyOf(r).map(([x, y]) => toCard(x, y))));
  el.trail.style.opacity = op;
}
const OUT_FADE = .4;
/* During a flight the outline follows the window frame by frame. FLIGHT_TRACKS gives, for each
   frame of the forward clip, the camera over the facade image (cam: centre and width in master
   px) or at least the window box in the 16:9 video frame (frames). The video is drawn with
   object-fit: cover, so a point of the frame lands at the same place as on the tower framing
   at frame 0. The reversed clip reads frame N - 1 - i. Without a track: the old fade. */
const trackOf = r => {
  const T = TRACKS(), t = T && T[r.id];
  return t && Array.isArray(t.frames) && t.frames.length > 1 ? t : null;
};
function trackPts(r, t, i) {
  const n = t.frames.length;
  i = Math.max(0, Math.min(n - 1, i));
  const vw = el.vid.videoWidth || 16, vh = el.vid.videoHeight || 9;
  const s = Math.max(fit.W / vw, fit.H / vh), dw = vw * s, dh = vh * s, ox = (fit.W - dw) / 2, oy = (fit.H - dh) / 2;
  const pts = polyOf(r);
  let uv;
  if (t.h && t.h[i]) {                           // the camera's perspective: facade plane to frame
    const [a, b, c, d, e, f, g, k, m] = t.h[i];
    uv = pts.map(([X, Y]) => { const w = g * X + k * Y + m; return [(a * X + b * Y + c) / w, (d * X + e * Y + f) / w]; });
  } else if (t.cam && t.cam[i]) {
    const [cx, cy, w] = t.cam[i], h = w * 9 / 16;
    uv = pts.map(([X, Y]) => [(X - cx) / w + .5, (Y - cy) / h + .5]);
  } else {                                       // the home's outline drawn inside the tracked box
    const [u0, v0, u1, v1] = t.frames[i], [x0, y0, x1, y1] = r.window;
    uv = pts.map(([X, Y]) => [u0 + (X - x0) / (x1 - x0) * (u1 - u0), v0 + (Y - y0) / (y1 - y0) * (v1 - v0)]);
  }
  return uv.map(([u, v]) => [ox + u * dw, oy + v * dh]);
}
// draws the tracked outline on every video frame; returns a stop function
function followTrack(r, t, rev) {
  const v = el.vid, n = t.frames.length, fps = t.fps || 60;
  let live = true, id = 0;
  const draw = time => {
    const k = Math.round(time * fps);
    el.trailpoly.setAttribute('points', ptsAttr(trackPts(r, t, rev ? n - 1 - k : k)));
    const d = v.duration || n / fps;
    // forward: on the window the whole way, gone over the last 0.4 s; back: it fades in at the end
    const op = rev ? (time - (d - OUT_FADE)) / OUT_FADE : (d - time) / OUT_FADE;
    el.trail.style.opacity = Math.max(0, Math.min(1, op)).toFixed(3);
  };
  if (typeof v.requestVideoFrameCallback === 'function') {
    const cb = (now, meta) => { if (!live) return; draw(meta.mediaTime); id = v.requestVideoFrameCallback(cb); };
    id = v.requestVideoFrameCallback(cb);
    return { draw: null, stop() { live = false; try { v.cancelVideoFrameCallback(id); } catch (e) {} } };
  }
  return { draw, stop() { live = false; } };     // no frame callback: drawn from currentTime on each paint
}

/* ---------- the flight ------------------------------------------------ */
// With prefers-reduced-motion every camera move is skipped: the site cuts
// straight to the frame the move would have ended on.
async function fly(r) {
  if (busy || state !== 'tower' || !r) return;
  setBusy(true);
  clearTimeout(briefT);
  if (hot) highlight(hot, false);
  armed = null; cur = r; returning = false; sel = RESIDENCES.indexOf(r);
  RESIDENCES.forEach(x => x._g.classList.remove('on'));
  await toTop();
  settleId++;                                            // the opening settle must end on frame 0
  if (zoomK !== 1) { const z0 = zoomK; await tween(.3, k => applyZoom(z0 + (1 - z0) * k)); }
  setState('flight');
  const arrive = stillOf(r), url = vsrc(r.flight);
  let loading = true;
  (async () => { while (loading) { miniBar((prog[url] || 0) * .999); await raf(); } })();
  // the window track comes with the video; a slow track never holds the flight back
  const [src] = await Promise.all([reduced ? null : fetchBlob(url), loadImg(arrive), reduced ? null : Promise.race([loadTracks(), wait(2500)])]);
  loading = false; miniBar(0);
  if (!reduced) {
    await prepVideo(src);
    outlineAt(r, 1);
    await fade(el.motion, 1, .25);
    hide(el.still);
    const tr = trackOf(r), follow = tr && followTrack(r, tr, false);
    await playVideo((t, d) => {
      if (!follow) el.trail.style.opacity = Math.max(0, 1 - t / OUT_FADE).toFixed(3);   // untracked: fade as the camera leaves
      else if (follow.draw) follow.draw(t);
      miniBar(t / d);
    });
    if (follow) follow.stop();
    el.trail.style.opacity = 0;
  }
  await showStill(arrive);                               // decoded before the video gives way
  show(el.still);
  hide(el.motion);
  miniBar(0);
  fillPanel(r);
  setBusy(false);
  setState('home');
  focusSoft($('#panel [data-act="inside"]'));
  if (!reduced) idle(() => { if (cur === r) { fetchBlob(vsrc(r.flight, true)); fetchBlob(vsrc(r.inside)); } });
}
async function toTower() {
  if (busy || state !== 'home' || !cur) return;
  setBusy(true);
  const r = cur;
  returning = true;
  disposeViewer();
  setState('flight');
  if (!reduced) {
    const src = await fetchBlob(vsrc(r.flight, true));
    await prepVideo(src);
    show(el.motion);
    await wait(30);
    hide(el.still);
    outlineAt(r, 0);
    const tr = trackOf(r), follow = tr && followTrack(r, tr, true);
    await playVideo((t, d) => {
      if (!follow) el.trail.style.opacity = Math.max(0, Math.min(1, (t - d + OUT_FADE) / OUT_FADE)).toFixed(3);
      else if (follow.draw) follow.draw(t);
      miniBar(t / d);
    });
    if (follow) { follow.stop(); outlineAt(r, 1); }      // lands exactly on the tower outline
  }
  hide(el.still);
  cur = null; returning = false;
  miniBar(0);
  setBusy(false);
  setState('tower');
  await fade(el.motion, 0, .3);
  // the outline lingers on the window the visitor came back from, then the glow takes over
  if (!reduced) { await wait(900); if (state === 'tower') await fade(el.trail, 0, .6); }
  el.trail.style.opacity = 0;
}

/* ---------- step inside, and the photographs ------------------------- */
const shots = { list: [], i: 0, mode: '' };
const levelName = (r, lv) => (r.levelNames && r.levelNames[lv]) || '';
// every room photograph, plus the extra views a room has; captioned by what each one shows
function shotList(r) {
  const out = [];
  r.rooms.forEach(x => {
    const lv = levelName(r, x.level);
    out.push({ id: x.photo, name: x.cap || x.name, room: x.name, sub: x.sub || lv, level: x.level, view: !!x.view });
    (x.more || []).forEach(m => out.push({ id: m.photo, name: m.cap || x.cap || x.name, room: x.name, sub: m.sub || lv, level: x.level, view: !!(m.view || x.view) }));
  });
  return out;
}
function shotsBuild(list, mode) {
  shots.list = list; shots.mode = mode; shots.i = 0; shots.seen = false;
  tour.anim = null; tour.paused = false;
  el.photos.innerHTML = list.map(s => `<figure class="shot" aria-hidden="true"><picture><img alt="${cur.name}, ${s.name.toLowerCase()}, ${s.sub.charAt(0).toLowerCase() + s.sub.slice(1)}, illustrative ${s.view ? 'view' : 'interior'}" decoding="async"></picture></figure>`).join('');
}
function fillShot(ix) {
  const f = $$('.shot', el.photos)[ix];
  if (!f || f.dataset.set) return f;
  f.dataset.set = '1';
  setPhoto(f.querySelector('img'), shots.list[ix].id);
  return f;
}
// rest: the view is shown at its hand over framing, without motion (the way back outside)
function shotShow(i, instant, rest) {
  const figs = $$('.shot', el.photos);
  if (!figs.length) return;
  shots.i = i;
  const n = figs.length;
  [i, (i + 1) % n, (i - 1 + n) % n].forEach(fillShot);    // the room shown and its neighbours
  // the first view of the tour is where the walk in hands over: it starts exactly at rest
  const fresh = shots.mode === 'tour' && i === 0 && !shots.seen;
  shots.seen = true;
  // views that change on their own are not read out; the ones the visitor asks for are
  el.cap.setAttribute('aria-live', tour.auto ? 'off' : 'polite');
  figs.forEach((f, ix) => {
    const on = ix === i;
    f.style.transition = instant || reduced ? 'none' : `opacity ${XFADE}s cubic-bezier(.22,.61,.24,1)`;
    f.style.opacity = on ? 1 : 0;
    f.setAttribute('aria-hidden', String(!on));             // only the photograph on screen is announced
    if (on) tourMotion(f.querySelector('img'), ix, fresh, rest);
  });
  caption(); renderMini(); title();
  tourSync();
}

/* ---------- the tour: each view drifts back a touch while a ring counts down its
   seconds, then the next one fades in on its own. The zoom is the clock: the ring
   reads it, pausing it pauses both, and its end turns the page. */
const DWELL = 6, XFADE = .8;                               // seconds on a view, crossfade to the next
const tour = { anim: null, hold: new Set(), paused: false, auto: false, raf: 0, n: -1 };
const tourOn = () => (state === 'inside' || state === 'room') && !reduced;
function tourMotion(img, ix, fresh, rest) {
  if (img._tour) { img._tour.cancel(); img._tour = null; }
  const iw = fit.H * 16 / 9, amp = (iw - fit.W) / 2 - 2, wide = amp > 40;
  // portrait screens: the photograph keeps its full width and drifts sideways a little as well
  Object.assign(img.style, wide ? { width: iw + 'px', left: '50%', marginLeft: (-iw / 2) + 'px' } : { width: '', left: '', marginLeft: '' });
  img.style.transition = 'none';
  img.style.transform = 'translateX(0px) scale(1)';
  tour.anim = null;
  if (reduced || rest) return;
  const dir = ix % 2 ? 1 : -1, d = wide ? Math.min(amp, 110) : 0;
  // the hand over view moves on gently from the clip's last frame (scale 1, no jump); the others zoom out
  const kf = fresh
    ? [{ transform: 'translateX(0px) scale(1)' }, { transform: 'translateX(0px) scale(1.03)' }]
    : [{ transform: `translateX(${(dir * d).toFixed(1)}px) scale(1.05)` }, { transform: `translateX(${(-dir * d).toFixed(1)}px) scale(1)` }];
  const a = img.animate(kf, { duration: DWELL * 1000, easing: fresh ? 'cubic-bezier(.45,0,.55,1)' : 'cubic-bezier(.22,.61,.24,1)', fill: 'forwards' });
  a.pause();
  a.onfinish = () => { if (tour.anim === a) tourNext(); };
  img._tour = a; tour.anim = a;
}
function tourSync() {
  const a = tour.anim;
  const run = !!a && tourOn() && !tour.paused && !tour.hold.size && !document.hidden && !busy;
  if (a && run && a.playState === 'finished') return tourNext();   // the time ran out while held
  if (a && a.playState !== 'finished') run ? a.play() : a.pause();
  el.tourt.classList.toggle('off', tour.paused);
  el.tourt.setAttribute('aria-pressed', String(tour.paused));
  el.tourt.setAttribute('aria-label', tour.paused ? 'Play the tour' : 'Pause the tour');
  cancelAnimationFrame(tour.raf);
  const tick = () => { tourDraw(); if (run) tour.raf = requestAnimationFrame(tick); };
  tick();
}
function tourDraw() {
  const a = tour.anim, t = a ? Math.min(1, (+a.currentTime || 0) / (DWELL * 1000)) : 0;
  el.ttfg.style.strokeDashoffset = t.toFixed(4);
  const n = Math.max(1, Math.ceil(DWELL * (1 - t) - 1e-3));
  if (n !== tour.n) { tour.n = n; el.ttn.textContent = n; }
}
function tourNext() {
  if (!tourOn() || busy) return;
  tour.auto = true;
  try { step(1); } finally { tour.auto = false; }
}
// back to the hand over framing, so the way out starts exactly where the clip ended
function tourSettle(img) {
  const a = img && img._tour;
  tour.anim = null; tourSync();
  if (!a) return Promise.resolve();
  const from = getComputedStyle(img).transform;
  a.cancel(); img._tour = null;
  if (reduced || from === 'none' || from === 'matrix(1, 0, 0, 1, 0, 0)') return Promise.resolve();
  return img.animate([{ transform: from }, { transform: 'translateX(0px) scale(1)' }], { duration: 700, easing: 'cubic-bezier(.22,.61,.24,1)' }).finished.catch(() => {});
}
/* hand over between the walk in's last frame and the living room photograph */
function handoff(r, k) {
  const h = r.handoff || { x: 0, y: 0, s: 1 };
  const iw = Math.max(fit.W, fit.H * 16 / 9), ih = Math.max(fit.H, fit.W * 9 / 16);
  el.stillimg.style.transform = `translate(${(h.x / 100 * iw * k).toFixed(2)}px,${(h.y / 100 * ih * k).toFixed(2)}px) scale(${(1 + (h.s - 1) * k).toFixed(5)})`;
}
async function showStill(src) {
  if (!el.stillimg.src.endsWith(src)) { el.stillimg.src = src; await decodeImg(el.stillimg); }
}
async function inside() {
  if (busy || state !== 'home' || !cur) return;
  setBusy(true);
  const r = cur;
  disposeViewer();
  setState('moving');
  shotsBuild(shotList(r), 'tour');
  const first = fillShot(0).querySelector('img');
  const [src] = await Promise.all([reduced ? null : fetchBlob(vsrc(r.inside)), loadImg(stillIn(r)), decodeImg(first)]);
  if (!reduced) {
    await prepVideo(src);
    show(el.motion);
    await fade(el.still, 0, 0);           // the clip opens exactly on the arrival frame: a straight swap, no dissolve
    await playVideo((t, d) => miniBar(t / d));
    // the last frame stays and eases onto the photograph while it fades in on top
    await showStill(stillIn(r));
    handoff(r, 0);
    show(el.still);
    hide(el.motion);
    el.photos.style.opacity = 0; el.photos.style.visibility = 'visible';
    shotShow(0, true);
    // the clip ends on the photograph itself: a short crossfade (HANDOFF_FADE), no move
    await Promise.all([tween(HF, k => handoff(r, k)), fade(el.photos, 1, HF)]);
  } else {
    show(el.photos);
    shotShow(0, true);
  }
  hide(el.still);
  el.stillimg.style.transform = '';
  hide(el.motion);
  miniBar(0);
  setBusy(false);
  setState('inside');
  if (!reduced) idle(() => fetchBlob(vsrc(r.inside, true)));
}
async function outside() {
  if (busy || state !== 'inside' || !cur) return;
  const r = cur;
  setBusy(true);
  // the first view comes back at rest (it fades in over the one on screen), or eases back to rest
  if (shots.i !== 0) { shotShow(0, false, true); await wait(900); }
  setState('moving');
  if (!reduced) {
    await tourSettle($('.shot img', el.photos));
    const [src] = await Promise.all([fetchBlob(vsrc(r.inside, true)), loadImg(stillIn(r))]);
    // the same hand over, backwards: the photograph fades while the last frame eases back
    await showStill(stillIn(r));
    handoff(r, 1);
    show(el.still);
    await Promise.all([tween(HF, k => handoff(r, 1 - k), t => Math.pow(t, 3)), fade(el.photos, 0, HF)]);
    el.stillimg.style.transform = '';
    await prepVideo(src);
    show(el.motion);
    await wait(30);
    hide(el.still);
    await playVideo((t, d) => miniBar(t / d));
  }
  await showStill(stillOf(r));
  if (reduced) show(el.still);
  else { el.still.style.opacity = 0; await fade(el.still, 1, .25); }
  hide(el.photos);
  hide(el.motion);
  el.photos.innerHTML = '';
  miniBar(0);
  setBusy(false);
  setState('home');
}

/* ---------- panels ----------------------------------------------------- */
function specsHTML(r) {
  return [['Bedrooms', r.beds], ['People', r.persons], ['Interior', `${r.interior} m²`], ['Garden', `${r.garden} m²`]]
    .map(([k, v]) => `<div><dt>${k}</dt><dd>${v}</dd></div>`).join('');
}
function fillPanel(r) {
  $('#p-kick').textContent = `${r.ref} · ${r.type}`;
  $('#p-name').textContent = r.name;
  $('#p-specs').innerHTML = specsHTML(r);
  $('#p-level').textContent = `${r.levels}, illustrative position`;
  $('#p-fine').textContent = FINE;
}
function focusSoft(n) { if (kbd && n) n.focus({ preventScroll: true }); }

/* ---------- the floor plan: 3D dollhouse, or the official plan ---------- */
let viewer = null, planLevel = 0, plan3dMod = null, pendingDive = null, levelBusy = false;
function loadPlan3d() {
  // the bundle carries the same cache version as the page scripts
  if (!plan3dMod) plan3dMod = import(new URL('assets/js/plan3d.js' + VER, document.baseURI).href).catch(() => null);
  return plan3dMod;
}
function fillPlanPanel(r) {
  $('#pp-kick').textContent = `Floor plan · ${r.ref}`;
  $('#pp-name').textContent = r.name;
  $('#pp-specs').innerHTML = specsHTML(r);
  $('#pp-level').textContent = `${r.levels}, illustrative position`;
  buildToggle(r.levelNames.length > 1 ? r.levelNames : [], 0);
}
function buildToggle(labels, active) {
  planLevel = active;
  el.toggle.innerHTML = labels.length > 1 ? labels.map((l, i) =>
    `<button type="button" data-i="${i}" aria-pressed="${i === active}"${i === active ? ' class="on"' : ''}>${l}</button>`).join('') : '';
  $$('button', el.toggle).forEach(b => b.addEventListener('click', () => setLevel(+b.dataset.i)));
  fillRooms();
}
function markToggle() {
  $$('button', el.toggle).forEach(b => { const on = +b.dataset.i === planLevel; b.classList.toggle('on', on); b.setAttribute('aria-pressed', String(on)); });
}
function fillRooms() {
  const r = cur;
  if (!r) return;
  const multi = r.levelNames.length > 1;
  const list = r.rooms.filter(x => !multi || x.level === planLevel);
  el.rooms.innerHTML = list.map(x => `<li><button type="button" data-photo="${x.photo}"><i aria-hidden="true"></i>${x.name}<svg aria-hidden="true"><use href="#i-arrow"/></svg></button></li>`).join('');
  $$('button', el.rooms).forEach(b => {
    const x = r.rooms.find(q => q.photo === b.dataset.photo);
    b.addEventListener('click', () => openRoom(x));
    b.addEventListener('pointerenter', () => planHoverSet(x));
    b.addEventListener('pointerleave', () => planHoverSet(null));
    b.addEventListener('focus', () => planHoverSet(x));
    b.addEventListener('blur', () => planHoverSet(null));
  });
}
function planHoverSet(x) {
  planHover = x || null;
  $$('button', el.rooms).forEach(b => b.classList.toggle('hot', !!x && b.dataset.photo === x.photo));
  if (state === 'plan') renderMini();
}
// rooms picked on the model come from the viewer: match them to the list by photograph
const asRoom = room => room && (cur.rooms.find(q => q.photo === room.photo) || { photo: room.photo, name: room.name, level: planLevel });
async function setLevel(i) {
  if (!viewer || planLevel === i || levelBusy) return;
  planLevel = i;
  markToggle(); fillRooms(); planHoverSet(null);
  if (viewer.mode === '3d') {
    levelBusy = true;
    try { await viewer.v.setLevel(i, !reduced); } catch (e) {}
    levelBusy = false;
  } else setPlan2d(i);
}
function setPlan2d(i) {
  const r = cur, p = r.plans[Math.min(i, r.plans.length - 1)];
  el.planimg.style.opacity = 0;
  setTimeout(() => {
    el.planimg.onload = () => { el.planimg.style.opacity = 1; };
    el.planimg.src = p.src;
    el.planimg.alt = `${r.name}, ${p.label}, official diagrammatic plan`;
  }, reduced ? 0 : 180);
}
function planSheet() { el.card.style.setProperty('--pph', (el.ppanel.offsetHeight + 16) + 'px'); }
async function ensureViewer(r) {
  if (viewer && viewer.id === r.id) {
    if (viewer.mode === '3d') buildToggle(viewer.v.levels.map(l => l.label), viewer.v.level);
    else { buildToggle(r.plans.length > 1 ? r.plans.map(p => p.label) : [], viewer.level || 0); el.plan2d.classList.add('on'); }
    return;
  }
  disposeViewer();
  const mod = await loadPlan3d();
  if (state !== 'plan' || cur !== r) return;
  if (mod && mod.createViewer) {
    try {
      const v = mod.createViewer(el.plan3d, {
        apt: r.id,
        onRoom: room => { if (state === 'plan' && room && room.photo) openRoom(asRoom(room)); },
        onHover: room => { if (state === 'plan') planHoverSet(asRoom(room)); }
      });
      viewer = { id: r.id, v, mode: '3d' };
      $('#pp-note').textContent = 'Illustrative model drawn from the official diagrammatic plan.';
      buildToggle(v.levels.map(l => l.label), v.level || 0);
      requestAnimationFrame(() => el.plan3d.classList.add('ready'));
      return;
    } catch (e) { el.plan3d.innerHTML = ''; }
  }
  viewer = { id: r.id, v: null, mode: '2d', level: 0 };
  $('#pp-note').textContent = 'Diagrammatic plan from the Nest Battersea design and access documentation (Wandsworth 2025/0907).';
  el.plan2d.classList.add('on');
  buildToggle(r.plans.length > 1 ? r.plans.map(p => p.label) : [], 0);
  setPlan2d(0);
}
function disposeViewer() {
  if (!viewer) return;
  if (viewer.v) { try { viewer.v.dispose(); } catch (e) {} }
  viewer = null; planHover = null; pendingDive = null;
  el.plan3d.classList.remove('ready');
  el.plan3d.innerHTML = '';
  el.plan2d.classList.remove('on');
}
async function plan() {
  if (busy || state !== 'home' || !cur) return;
  setBusy(true);
  const r = cur;
  fillPlanPanel(r);
  planHover = null;
  if (!viewer || viewer.id !== r.id) el.plan.classList.add('loading');
  setState('plan');
  if (mobile) planSheet();
  await fade(el.plan, 1, .5);
  await ensureViewer(r);
  el.plan.classList.remove('loading');
  setBusy(false);
  band();
  renderMini();
}
async function planClose() {
  if (busy || state !== 'plan') return;
  setBusy(true);
  await fade(el.plan, 0, .45);
  setBusy(false);
  setState('home');
}
async function openRoom(x) {
  if (busy || state !== 'plan' || !cur || !x) return;
  setBusy(true);
  const list = shotList(cur);
  const want = x.open || x.photo;                          // the view that looks into the room chosen
  const i = Math.max(0, list.findIndex(s => s.id === want));
  setState('moving');
  shotsBuild(list, 'room');
  const ready = decodeImg(fillShot(i).querySelector('img'));
  if (viewer && viewer.mode === '3d' && !reduced) {
    try { pendingDive = viewer.v.dive(list[i].id); await pendingDive; } catch (e) {}
  }
  await ready;
  void el.photos.offsetWidth;
  show(el.photos);
  shotShow(i);
  setBusy(false);
  setState('room');
}
function roomGo(j) {
  shotShow(j);
  const s = shots.list[j];
  // the camera follows behind the photograph, so the way back starts in this room
  if (viewer && viewer.mode === '3d' && !reduced) {
    const v = viewer.v;
    pendingDive = Promise.resolve(pendingDive).catch(() => {}).then(() => v.dive(s.id)).catch(() => {});
  }
}
async function backToPlan() {
  if (busy || state !== 'room') return;
  setBusy(true);
  setState('moving');
  await fade(el.photos, 0, .6);
  el.photos.innerHTML = '';
  if (viewer && viewer.mode === '3d') {
    try { await pendingDive; } catch (e) {}
    try { await viewer.v.frame(!reduced); } catch (e) {}
    const lv = viewer.v.level || 0;
    if (lv !== planLevel) { planLevel = lv; markToggle(); fillRooms(); }
  }
  planHover = null;
  setBusy(false);
  setState('plan');
}

/* ---------- navigation ------------------------------------------------- */
async function back() {
  if (busy) return;
  if (state === 'inside') return outside();
  if (state === 'room') return backToPlan();
  if (state === 'plan') return planClose();
  if (state === 'home') return toTower();
}
async function goTo(r) {
  closeOverlay(true);
  if (busy || !r || state === 'boot') return;
  if (state === 'tower') return fly(r);
  if (cur === r) { while (state !== 'home' && !busy) { const s = state; await back(); if (state === s) break; } return; }
  while (state !== 'tower') { const s = state; await back(); if (state === s) break; }
  if (state === 'tower') fly(r);
}
// the logo and the menu leave the stage at once, without replaying every camera move
async function resetToTower() {
  while (busy) await wait(120);
  if (!STAGED(state)) return;
  el.vid.pause();
  await Promise.all([fade(el.still, 0, .45), fade(el.photos, 0, .45), fade(el.plan, 0, .45), fade(el.motion, 0, .45)]);
  disposeViewer();
  el.photos.innerHTML = '';
  el.trail.style.opacity = 0;
  cur = null; armed = null;
  setState('tower');
}
async function navTo(id) {
  closeOverlay(true);
  if (STAGED(state)) await resetToTower();
  const t = document.getElementById(id);
  if (!t) return;
  await raf();
  // cards that start at their very top keep clear of the floating buttons
  const flush = t.matches('.duo-card, .loc, .talk');
  const y = t.getBoundingClientRect().top + scrollY - (flush ? cssPx('--hb') + cssPx('--m') * 2 : 0);
  scrollTo({ top: Math.max(0, y), behavior: reduced ? 'auto' : 'smooth' });
}

/* ---------- overlays ------------------------------------------------ */
let lastFocus = null;
function openOverlay(name, topic) {
  const from = document.activeElement;
  closeOverlay(true);
  const o = $(`.overlay[data-overlay="${name}"]`);
  if (!o) return;
  lastFocus = from;
  $$('[data-srcset]', o).forEach(n => { n.srcset = n.dataset.srcset; n.removeAttribute('data-srcset'); });
  $$('[data-src]', o).forEach(n => { n.src = n.dataset.src; n.removeAttribute('data-src'); });
  o.classList.add('open');
  if (name === 'register') {
    o.classList.remove('sent');
    if (cur) $('#form-home').value = cur.id;
    if (topic) { const sel = $('#form-topic'); if ([...sel.options].some(op => op.value === topic)) sel.value = topic; }
  }
  setTimeout(() => { const f = o.querySelector('input, .x'); f && f.focus({ preventScroll: true }); }, reduced ? 0 : 280);
  title();
}

/* ---------- lightbox: exterior views, plans, the location image ------------------ */
const LB = { items: [], i: 0, el: null };
const LB_NAMES = { views: 'Exterior views', plans: 'Plans and diagrams', location: 'Location' };
function lbItems(group) {
  return $$(`[data-lb="${group}"]`).map(b => {
    const cap = b.querySelector('.view-cap');
    return {
      src: b.dataset.src, w: b.dataset.w.split(',').map(Number), ratio: +b.dataset.ratio || 1.5,
      title: cap ? cap.querySelector('b').textContent : b.dataset.title || '',
      text: cap ? cap.querySelector('span:last-child').textContent
        : (b.querySelector('.duo-plan-cap') || {}).textContent || (b.classList.contains('plan-open') ? $('#plancap').textContent : ''),
      alt: (b.querySelector('img') || {}).alt || ''
    };
  });
}
function lbShow(i, first) {
  const n = LB.items.length;
  LB.i = (i + n) % n;
  const it = LB.items[LB.i], o = LB.el, fig = $('#lbfig'), img = $('#lbimg');
  const set = ext => it.w.map(w => `${it.src}-${w}.${ext} ${w}w`).join(', ');
  const put = () => {
    $('#lb-avif').srcset = set('avif'); $('#lb-webp').srcset = set('webp');
    ['#lb-avif', '#lb-webp'].forEach(q => { $(q).sizes = '100vw'; });
    img.sizes = '100vw'; img.srcset = set('jpg');
    img.src = `${it.src}-${it.w[it.w.length - 1]}.jpg`;
    img.alt = it.alt;
    img.width = it.w[it.w.length - 1]; img.height = Math.round(img.width / it.ratio);
    $('#lbn').textContent = `${pad2(LB.i + 1)} / ${pad2(n)}`;
    $('#lbt').textContent = it.title;
    $('#lbs').textContent = it.text;
    const done = () => fig.classList.remove('swap');
    (img.decode ? img.decode() : Promise.resolve()).then(done, done);
    setTimeout(done, 700);
  };
  o.classList.toggle('single', n < 2);
  if (first || reduced) { put(); return; }
  fig.classList.add('swap');
  setTimeout(put, 200);
}
function lbOpen(btn) {
  LB.el = $('.overlay[data-overlay="lightbox"]');
  const group = btn.dataset.lb;
  LB.items = lbItems(group);
  LB.el.setAttribute('aria-label', LB_NAMES[group] || 'Images');
  lbShow(Math.max(0, LB.items.findIndex(x => x.src === btn.dataset.src)), true);
  openOverlay('lightbox');
}
function lbStep(d) { if (LB.el && LB.el.classList.contains('open') && LB.items.length > 1) lbShow(LB.i + d); }
function lbSwipe() {
  const fig = $('#lbfig');
  let x0 = null, y0 = 0;
  fig.addEventListener('pointerdown', e => { x0 = e.clientX; y0 = e.clientY; });
  fig.addEventListener('pointerup', e => {
    if (x0 === null) return;
    const dx = e.clientX - x0, dy = e.clientY - y0;
    x0 = null;
    if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.4) { LB.swiped = performance.now(); lbStep(dx < 0 ? 1 : -1); }
  });
}
function closeOverlay(silent) {
  const o = $('.overlay.open');
  if (!o) return false;
  o.classList.remove('open');
  if (!silent && lastFocus && lastFocus.focus) lastFocus.focus({ preventScroll: true });
  title();
  return true;
}
function trapFocus(e) {
  const o = $('.overlay.open');
  const f = $$('button, [href], input, select', o).filter(n => n.offsetParent);
  if (!f.length) return;
  const a = f[0], z = f[f.length - 1];
  if (e.shiftKey && document.activeElement === a) { e.preventDefault(); z.focus(); }
  else if (!e.shiftKey && document.activeElement === z) { e.preventDefault(); a.focus(); }
  else if (!o.contains(document.activeElement)) { e.preventDefault(); a.focus(); }
}
function bindForm() {
  const form = $('#form');
  form.addEventListener('submit', e => {
    e.preventDefault();
    let ok = true;
    form.querySelectorAll('input[required]').forEach(i => {
      const good = i.checkValidity() && i.value.trim() !== '';
      i.classList.toggle('bad', !good);
      ok = ok && good;
    });
    if (!ok) { form.querySelector('.bad').focus(); return; }
    form.closest('.overlay').classList.add('sent');
    form.reset();
  });
}

/* ---------- sections ---------------------------------------------------- */
// The section content is in the HTML (it reads without JavaScript); this only enhances it.
function bindSections() {
  // intent: warm up the flight of a home the visitor points at
  $$('[data-act="fly"][data-id]').forEach(b => b.addEventListener('pointerenter', () => prefetch(byId(b.dataset.id))));
  lbSwipe();
  planTabs();
  viewsCount();
  viewsDrag();
  ecoIcons();
  placeList();
  lazyMap();
}
/* every section card with data-notch keeps a concave notch around the element in its corner,
   in the same language as the hero card */
function notchCards() {
  const cards = $$('[data-notch]');
  if (!cards.length || !Notch.supported) return;
  const cut = c => {
    const wrap = c.parentNode, W = c.offsetWidth, H = c.offsetHeight;
    if (!W || !H) return;
    const g = mobile ? 7 : 9, R = parseFloat(getComputedStyle(c).borderTopLeftRadius) || 24;
    const spec = { R, f: mobile ? 14 : 18 };
    c.dataset.notch.split(' ').forEach(k => {
      const n = wrap.querySelector(`:scope > .n-${k}`);
      if (!n || !n.offsetWidth) return;
      const sz = { w: n.offsetWidth + g, h: n.offsetHeight + g, r: Math.min(n.offsetHeight, n.offsetWidth) / 2 + g };
      if (k === 'br') spec.br = [sz]; else spec[k] = sz;
    });
    Notch.apply(c, W, H, spec);
  };
  cards.forEach(cut);
  if ('ResizeObserver' in window) {
    const ro = new ResizeObserver(es => es.forEach(e => cut(e.target)));
    cards.forEach(c => ro.observe(c));
  }
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => cards.forEach(cut));
}
// numbered markers laid over the labels of the official plans: key, label, then x y w h in the 1440 x 1105 image
const PLAN_PINS = {
  'single-private': 'b1 01 239 862 127 64|b2 02 154 573 127 64|b3 03 435 194 126 64|b4 04 1184 147 126 64|b5 05 1225 866 126 64|b6 06 888 940 126 64',
  'double-lower-private': 'l1 01 228 879 82 64|l2 02 204 623 82 64|l3 03 457 167 82 64|l4 04 1207 143 81 65|l5 05 1223 859 81 64|l6 06 911 952 81 64',
  'double-upper-private': 'l1 01 228 879 81 64|l2 02 200 625 82 64|l3 03 457 167 82 65|l4 04 1207 144 81 63|l5 05 1222 859 82 64|l6 06 911 952 81 64',
  'single-studios': 'b1 01 239 862 127 65|b2 02 154 573 127 64|b3 03 436 194 125 64|b4a 4A 1196 144 125 63|s1 S1 1222 609 112 64|s2 S2 1239 894 109 65|b6 06 888 940 126 63',
  'aff-single': 'b1 01 239 862 127 79|b2 02 168 559 127 79|b3 03 443 179 126 78|b4 04 1182 137 127 78|b5 05 1208 856 126 77|b6 06 890 927 126 78',
  'aff-lower': 'd1 01 231 867 126 79|d2 02 214 589 127 78|d3 03 449 148 126 82|d4 04 1185 146 127 79|d5 05 1208 853 126 77|d6 06 890 940 126 78',
  'aff-upper': 'd1 01 231 868 126 77|d2 02 215 590 125 77|d3 03 449 150 126 78|d4 04 1195 115 126 79|d5 05 1218 860 126 78|d6 06 885 945 127 78'
};
const pinList = plan => (PLAN_PINS[plan] || '').split('|').filter(Boolean).map(s => s.split(' '));
const PIN_NAMES = { b4a: 'Bungalow 4A', s1: 'Studio 1', s2: 'Studio 2' };   // homes on the plans that have no row in a list
// the floor plates of the Homes and Affordable sections: tabs switch the plate, and the homes listed
// beside it light up their marker (pointing at one) or bring up their floor (choosing one)
function planTabs() {
  $$('[data-planbox]').forEach(box => {
    const tabs = $$('[role="tab"][data-plan]', box), btn = $('.plan-open', box);
    if (!btn) return;
    const view = btn.parentNode, pic = btn.querySelector('picture'), img = btn.querySelector('img');
    const pins = $('.plan-pins', view), cap = $('.plan-cap, .aplan-cap', box), hid = $('.duo-plan-cap', btn), keys = $$('.aplan-key', box);
    const ws = btn.dataset.w.split(',');
    let cur = (tabs.find(t => t.classList.contains('on')) || tabs[0]).dataset.plan;
    keys.forEach(k => { k.hidden = !k.dataset.key.split(' ').includes(cur); });   // without JS every key list stays visible
    const rows = $$('li[data-k]', box);
    // a marker and its row light up together, whichever one the visitor points at
    const mark = () => {
      const h = box.dataset.hot;
      $$('i', pins).forEach(i => i.classList.toggle('hot', i.dataset.k === h));
      rows.forEach(r => r.classList.toggle('hot', r.dataset.k === h));
    };
    // markers: a house icon (one or two storeys) over each official label, named when lit
    const name = k => { const r = rows.find(x => x.dataset.k === k); return r ? $('b', r).textContent : PIN_NAMES[k] || ''; };
    const draw = () => {
      if (!pins) return;
      pins.innerHTML = pinList(cur).map(([k, , x, y, w, h]) =>
        `<i data-k="${k}" style="left:${(x / 14.4).toFixed(2)}%;top:${(y / 11.05).toFixed(2)}%;width:${(w / 14.4).toFixed(2)}%;height:${(h / 11.05).toFixed(2)}%"><svg><use href="#i-${/^[ld]/.test(k) ? 'loft' : 'bung'}"/></svg><b>${name(k)}</b></i>`).join('');
      mark();
    };
    const pick = k => {
      rows.forEach(x => x.classList.toggle('pick', x.dataset.k === k));
      box.dataset.pick = box.dataset.hot = k;
      mark();
    };
    if (pins) {
      pins.addEventListener('pointerover', e => { const i = e.target.closest('i[data-k]'); if (i && e.pointerType === 'mouse') { box.dataset.hot = i.dataset.k; mark(); } });
      pins.addEventListener('pointerleave', () => { box.dataset.hot = box.dataset.pick || ''; mark(); });
      pins.addEventListener('click', e => { const i = e.target.closest('i[data-k]'); if (i) pick(i.dataset.k); });
    }
    const show = t => {
      if (!t || t.dataset.plan === cur) return;
      tabs.forEach(x => { const on = x === t; x.classList.toggle('on', on); x.setAttribute('aria-selected', String(on)); });
      cur = t.dataset.plan;
      keys.forEach(k => { k.hidden = !k.dataset.key.split(' ').includes(cur); });
      const base = `assets/site/plans/${cur}`, set = ext => ws.map(w => `${base}-${w}.${ext} ${w}w`).join(', ');
      const put = () => {
        const [av, wb] = pic.querySelectorAll('source');
        av.srcset = set('avif'); wb.srcset = set('webp');
        img.src = `${base}-1440.jpg`;
        img.alt = t.dataset.alt;
        btn.dataset.src = base; btn.dataset.title = t.dataset.title;
        btn.setAttribute('aria-label', `Enlarge the plan: ${t.dataset.title}`);
        if (cap) cap.textContent = t.dataset.cap;
        if (hid) hid.textContent = t.dataset.cap;
        draw();
        const done = () => view.classList.remove('swap');
        (img.decode ? img.decode() : Promise.resolve()).then(done, done);
        setTimeout(done, 800);
      };
      if (reduced) return put();
      view.classList.add('swap');
      setTimeout(put, 220);
    };
    tabs.forEach(t => t.addEventListener('click', () => show(t)));
    draw();
    rows.forEach(li => {
      const k = li.dataset.k, b = $('.typ-show', li);
      const hot = on => { box.dataset.hot = on ? k : (box.dataset.pick || ''); mark(); };
      li.addEventListener('pointerenter', e => { if (e.pointerType === 'mouse') hot(true); });
      li.addEventListener('pointerleave', () => hot(false));
      if (b) { b.addEventListener('focus', () => hot(true)); b.addEventListener('blur', () => hot(false)); }
      (b || li).addEventListener('click', () => {
        pick(k);
        if (!pinList(cur).some(p => p[0] === k)) show(tabs.find(t => t.dataset.plan === li.dataset.plan));
        const r = view.getBoundingClientRect();
        if (r.bottom < 80 || r.top > innerHeight - 80) view.scrollIntoView({ block: 'center', behavior: reduced ? 'auto' : 'smooth' });
      });
    });
  });
}
// the exterior views counter follows the card in view (native scrolling; motion.js drives it when pinned)
function viewsCount() {
  const track = $('#vtrack'), out = $('#vcount'), cards = $$('#vlist .view');
  if (!track || !out || !cards.length) return;
  let q = 0;
  const run = () => {
    q = 0;
    if (el.html.classList.contains('gsap-pin')) return;
    const x = track.scrollLeft + track.clientWidth * .35;
    let i = 0;
    cards.forEach((c, k) => { if (c.offsetLeft <= x) i = k; });
    out.textContent = pad2(i + 1);
  };
  track.addEventListener('scroll', () => { if (!q) q = requestAnimationFrame(run); }, { passive: true });
}
// the exterior views follow the mouse: grab the row and drag it, let go and it glides on and settles on a
// view with an eased stop; a sideways wheel or trackpad swipe glides the same way. Touch keeps native
// scrolling. Natively the track scrolls sideways; while motion.js pins the section the page scroll is what
// slides the row, so the drag moves the page there. A drag never opens a view: only a still click does.
function viewsDrag() {
  const track = $('#vtrack'), pin = $('#viewspin'), cards = $$('#vlist .view');
  if (!track || !cards.length) return;
  const pinned = () => el.html.classList.contains('gsap-pin');
  const get = () => pinned() ? scrollY : track.scrollLeft;
  const put = v => { if (pinned()) scrollTo(0, v); else track.scrollLeft = v; };
  const range = () => {
    if (!pinned()) return [0, Math.max(0, track.scrollWidth - track.clientWidth)];
    const st = window.ScrollTrigger && ScrollTrigger.getAll().find(s => s.pin === pin);
    return st ? [st.start, st.end] : [scrollY, scrollY];
  };
  const clamp = v => { const [a, b] = range(); return Math.min(b, Math.max(a, v)); };
  // while pinned, only once the section holds the screen (never pull the page to it)
  const live = () => { if (!pinned()) return true; const [a, b] = range(); return b > a && scrollY >= a - 2 && scrollY <= b + 2; };
  // natively the row comes to rest with a view at its start, as the CSS snapping would put it
  const rest = v => {
    if (pinned()) return clamp(v);
    const pad = parseFloat(getComputedStyle(track).scrollPaddingLeft) || 0;
    const base = track.getBoundingClientRect().left - track.scrollLeft;
    let best = v, d = Infinity;
    cards.forEach(c => { const p = clamp(c.getBoundingClientRect().left - base - pad); if (Math.abs(p - v) < d) { d = Math.abs(p - v); best = p; } });
    return best;
  };
  let down = null, moved = false, vel = 0, lx = 0, lt = 0, block = 0, wt = 0;
  let cur = 0, goal = 0, ease = .2, last = 0, raf = 0, t0 = 0;
  const free = on => track.classList.toggle('free', on);
  const stop = () => { cancelAnimationFrame(raf); raf = 0; if (!down && !wt) free(false); };
  const loop = now => {
    raf = 0;
    if (Math.abs(get() - last) > 2) return stop();               // the visitor scrolled some other way: let go
    const k = 1 - Math.pow(1 - ease, Math.min(64, Math.max(4, now - t0)) / 16.67);   // the same ease at any frame rate
    t0 = now;
    cur += (goal - cur) * k;
    if (Math.abs(goal - cur) < .4) cur = goal;
    put(cur);
    last = get();
    if (cur !== goal) raf = requestAnimationFrame(loop);
    else if (!down && !wt) free(false);
  };
  const glide = (to, e) => {
    goal = to; ease = e;
    if (reduced) { cancelAnimationFrame(raf); raf = 0; cur = goal; put(goal); last = get(); if (!down && !wt) free(false); return; }
    if (!raf) { cur = last = get(); t0 = performance.now(); raf = requestAnimationFrame(loop); }
  };
  track.addEventListener('dragstart', e => e.preventDefault());
  // a mouse press neither selects text nor focuses the view (focus would scroll a pinned row to it)
  track.addEventListener('mousedown', e => { if (e.button === 0) e.preventDefault(); });
  track.addEventListener('pointerdown', e => {
    if (e.pointerType !== 'mouse' || e.button !== 0 || !live()) return;
    cancelAnimationFrame(raf); raf = 0;
    down = { x: e.clientX, at: get(), id: e.pointerId };
    moved = false; vel = 0; lx = e.clientX; lt = e.timeStamp;
  });
  track.addEventListener('pointermove', e => {
    if (!down || e.pointerId !== down.id) return;
    const dx = e.clientX - down.x;
    if (!moved) {
      if (Math.abs(dx) < 6) return;
      moved = true;
      try { track.setPointerCapture(e.pointerId); } catch (_) { /* released already */ }
      track.classList.add('grabbing');
      free(true);
      const s = getSelection && getSelection();
      if (s && s.removeAllRanges) s.removeAllRanges();
    }
    const dt = Math.max(1, e.timeStamp - lt);
    vel = .75 * ((e.clientX - lx) / dt) + .25 * vel;               // px per ms, smoothed
    lx = e.clientX; lt = e.timeStamp;
    // while pinned the scrub of the row already eases it: the page follows the hand directly
    glide(clamp(down.at - dx), pinned() ? 1 : .38);
  });
  const up = e => {
    if (!down || e.pointerId !== down.id) return;
    const was = moved, still = e.timeStamp - lt > 90;
    down = null; moved = false;
    track.classList.remove('grabbing');
    if (!was) return;
    block = performance.now();                                       // the click that ends a drag opens nothing
    // momentum: carry on in the direction of the throw, then settle with an ease out
    const throwTo = goal - (still || reduced ? 0 : vel) * 420;
    glide(rest(clamp(throwTo)), .085);
  };
  track.addEventListener('pointerup', up);
  track.addEventListener('pointercancel', up);
  track.addEventListener('click', e => {
    if (performance.now() - block < 400) { e.preventDefault(); e.stopPropagation(); block = 0; }
  }, true);
  // a sideways wheel or trackpad swipe over the row glides it; an upright wheel still scrolls the page
  track.addEventListener('wheel', e => {
    let dx = e.deltaX;
    const dy = e.deltaY;
    if (e.shiftKey && !dx) dx = dy;
    else if (Math.abs(dx) <= Math.abs(dy)) return;
    if (!live() || down) return;
    const k = e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? track.clientWidth : 1;
    const from = raf ? goal : get(), to = clamp(from + dx * k);
    if (to === from && !raf) return;                                  // at an end: nothing to move
    e.preventDefault();
    free(true);
    clearTimeout(wt);
    wt = setTimeout(() => { wt = 0; if (!down) glide(rest(goal), .1); }, 140);
    glide(to, .16);
  }, { passive: false });
}
// the Built with less tiles: each icon draws as large as the room its tile already has allows, up to
// twice its old size. Its slot stays 40px tall (see the CSS), so no tile ever changes size.
function ecoIcons() {
  const list = $('.eco-figs'), icons = $$('.eco-figs li > svg');
  if (!list || !icons.length) return;
  const fit = () => {
    let room = Infinity;
    icons.forEach(s => {
      const t = s.parentNode.querySelector('span');
      if (t) room = Math.min(room, t.getBoundingClientRect().top - s.getBoundingClientRect().top - 40 - 10);
    });
    const size = Math.max(40, Math.min(63, Math.floor(40 + room)));
    list.style.setProperty('--eco-ic', `${size}px`);
  };
  fit();
  if ('ResizeObserver' in window) new ResizeObserver(fit).observe(list);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(fit);
}
// the map script itself loads only when the Location section comes near (it then loads MapLibre)
function lazyMap() {
  const box = $('#map');
  if (!box) return;
  let asked = false;
  const go = () => { if (!asked && !window.MapView) { asked = true; addScript('js/map.js'); } };
  if (!('IntersectionObserver' in window)) return go();
  const io = new IntersectionObserver(es => { if (es.some(e => e.isIntersecting)) { io.disconnect(); go(); } }, { rootMargin: '1600px 0px' });
  io.observe(box);
}
// the places list beside the map: pointing at a place previews its walk on the live map,
// a click opens the map page on that place (each row is a link to map.html#place=id)
function placeList() {
  const list = $('#placelist');
  if (!list) return;
  let t = 0;
  const focus = id => {
    clearTimeout(t);
    t = setTimeout(() => {
      $$('#placelist [data-place]').forEach(x => x.classList.toggle('on', x.dataset.place === id));
      if (window.MapView) MapView.focus(id);
    }, id ? 90 : 260);
  };
  $$('#placelist [data-place]').forEach(b => {
    b.addEventListener('pointerenter', e => { if (e.pointerType === 'mouse') focus(b.dataset.place); });
    b.addEventListener('focus', () => focus(b.dataset.place));
  });
  list.addEventListener('pointerleave', () => focus(null));
  list.addEventListener('focusout', e => { if (!list.contains(e.relatedTarget)) focus(null); });
}
function magnetic() {
  if (touch || reduced) return;
  $$('.cta').forEach(c => {
    let box = null;
    c.addEventListener('pointerenter', e => { if (e.pointerType === 'mouse') box = c.getBoundingClientRect(); });
    c.addEventListener('pointermove', e => {
      if (!box) return;
      const dx = e.clientX - (box.left + box.width / 2), dy = e.clientY - (box.top + box.height / 2);
      c.style.transform = `translate(${(dx * .08).toFixed(1)}px,${(dy * .22).toFixed(1)}px)`;
    });
    c.addEventListener('pointerleave', () => { box = null; c.style.transform = ''; });
  });
}

/* ---------- wiring ---------------------------------------------------- */
function bind() {
  document.addEventListener('click', e => {
    const lb = e.target.closest('[data-lb]');
    if (lb) { e.preventDefault(); return lbOpen(lb); }
    const a = e.target.closest('[data-act]');
    if (!a) {
      const swiped = performance.now() - (LB.swiped || 0) < 400;
      if (e.target.classList && (e.target.classList.contains('overlay') || (e.target.classList.contains('lb-fig') && !swiped))) closeOverlay();
      if (armed && state === 'tower' && !e.target.closest('.win, #picker, #tag')) highlight(armed, false);
      return;
    }
    const act = a.dataset.act;
    if (act === 'home') {
      e.preventDefault(); closeOverlay();
      if (STAGED(state)) resetToTower(); else scrollTo({ top: 0, behavior: reduced ? 'auto' : 'smooth' });
      return;
    }
    if (act === 'nav') { e.preventDefault(); return navTo(a.dataset.target); }
    if (act === 'overlay') return openOverlay(a.dataset.target);
    if (act === 'register') return openOverlay('register', a.dataset.topic);
    if (act === 'lbprev') return lbStep(-1);
    if (act === 'lbnext') return lbStep(1);
    if (act === 'close') return closeOverlay();
    if (act === 'back') return back();
    if (act === 'plan') return plan();
    if (act === 'inside') return inside();
    if (act === 'prev') return step(-1);
    if (act === 'next') return step(1);
    if (act === 'mini') return miniGo();
    if (act === 'tourpause') { tour.paused = !tour.paused; return tourSync(); }
    if (act === 'fly') return goTo(byId(a.dataset.id));
  });
  el.tag.addEventListener('click', e => { e.stopPropagation(); if (armed && state === 'tower') fly(armed); });
  // intent: warm up what the visitor is about to open
  el.minicard.addEventListener('pointerenter', () => {
    if (state === 'tower') { highlight(RESIDENCES[sel], true); prefetch(RESIDENCES[sel]); }
    if (state === 'home' && cur) prefetch(other(cur));
  });
  el.minicard.addEventListener('pointerleave', () => { if (state === 'tower' && hot && !armed) highlight(hot, false); });
  el.minicard.addEventListener('focus', () => { if (state === 'tower') prefetch(RESIDENCES[sel]); });
  $$('[data-act="plan"]').forEach(b => { b.addEventListener('pointerenter', loadPlan3d); b.addEventListener('focus', loadPlan3d); });
  $$('[data-act="inside"]').forEach(b => b.addEventListener('pointerenter', () => { if (cur && !reduced) fetchBlob(vsrc(cur.inside)); }));
  document.addEventListener('keydown', e => {
    if (e.key === 'Tab') kbd = true;
    if (e.key === 'Escape') { if (closeOverlay()) return; if (armed) { highlight(armed, false); return; } back(); return; }
    if ($('.overlay.open')) {
      if (e.key === 'Tab') trapFocus(e);
      if (e.key === 'ArrowRight') lbStep(1);
      if (e.key === 'ArrowLeft') lbStep(-1);
      return;
    }
    if (state === 'inside' || state === 'room') {
      if (e.key === 'ArrowRight') step(1);
      if (e.key === 'ArrowLeft') step(-1);
    }
  });
  document.addEventListener('pointerdown', () => { kbd = false; }, { passive: true });
  addEventListener('resize', relayout);
  addEventListener('scroll', () => { if (STAGED(state) && scrollY) scrollTo(0, 0); }, { passive: true });
  MQ.addEventListener && MQ.addEventListener('change', () => { mobile = MQ.matches; backWidth(); band(); relayout(); });
  if ('ResizeObserver' in window) {
    const ro = new ResizeObserver(relayout);
    [el.card, el.logo, el.tr, el.minicard, el.miniNav, el.back].forEach(n => ro.observe(n));
  }
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(es => { heroSeen = es[0].isIntersecting; if (heroSeen) breathe.start(); }).observe($('#top'));
  }
  document.addEventListener('visibilitychange', () => { if (!document.hidden) breathe.start(); tourSync(); });
  // the tour holds still while the visitor points at or tabs through its controls, or presses on the photograph
  const hold = (k, on) => { if (on) tour.hold.add(k); else tour.hold.delete(k); tourSync(); };
  [['band', el.band], ['mini', el.mini], ['back', el.back]].forEach(([k, n]) => {
    n.addEventListener('pointerenter', e => { if (e.pointerType !== 'touch') hold(k, true); });
    n.addEventListener('pointerleave', () => hold(k, false));
    n.addEventListener('focusin', () => { if (kbd) hold(k + 'f', true); });
    n.addEventListener('focusout', () => hold(k + 'f', false));
  });
  el.card.addEventListener('pointerdown', e => { if (tourOn() && !e.target.closest('button, a, .band')) hold('press', true); }, { passive: true });
  ['pointerup', 'pointercancel'].forEach(t => document.addEventListener(t, () => { if (tour.hold.has('press')) hold('press', false); }, { passive: true }));
  bindForm();
}

/* ---------- boot ------------------------------------------------------ */
function masterReady() {
  const img = el.master;
  const loaded = img.complete && img.naturalWidth ? Promise.resolve()
    : new Promise(res => { img.addEventListener('load', res, { once: true }); img.addEventListener('error', res, { once: true }); });
  return loaded.then(() => img.decode ? img.decode().catch(() => {}) : null);
}
function boot() {
  el.frame.style.width = MASTER.w + 'px';
  el.frame.style.height = MASTER.h + 'px';
  buildWindows(); buildPicker(); bindSections(); bind();
  backWidth(); layout(); band(); renderMini(true);
  requestAnimationFrame(() => requestAnimationFrame(() => el.body.classList.add('in')));
  notchCards(); magnetic();
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => { backWidth(); layout(); });
  masterReady().then(() => {
    el.card.classList.add('loaded');
    // open on a slow camera settle, never a frozen frame (stopped if the visitor flies first)
    const my = ++settleId;
    if (!reduced) applyZoom(1.06);
    setState('tower');
    breathe.start();
    tween(2.8, k => { if (settleId === my) applyZoom(1.06 - .06 * k); }, t => 1 - Math.pow(1 - t, 2.2));
  });
}
addEventListener('DOMContentLoaded', boot);

return {
  fly, back, goTo, step, state: () => state, busy: () => busy, cur: () => cur, viewer: () => viewer,
  notch: () => N.cur, fit: () => ({ ...fit }), RESIDENCES
};
})();
