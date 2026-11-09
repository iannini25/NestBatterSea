/* ============================================================
   NEST BATTERSEA | the neighbourhood map page (map.html)
   MapLibre GL JS 4.7.1 (cdnjs) on the site's own night style
   (MapView.style() from js/map.js, OpenFreeMap vector tiles),
   with a satellite look (Esri World Imagery), 3D buildings, the
   tower marked in light, distance rings and every place with
   its photograph.
   ------------------------------------------------------------
   Routes are not asked of a router here: assets/map/places.json
   carries the walk and the drive to every place, computed once
   with OSRM (routing.openstreetmap.de) on OpenStreetMap streets,
   crossing the Thames on its bridges only. The page reads the
   place from its address: map.html#place=imperial&mode=car
   ============================================================ */
(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const body = document.body;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const narrow = () => innerWidth <= 860;
  const COL = { foot: '#C9E2EF', car: '#ffd9a0' };
  const RGB = { foot: '201,226,239', car: '255,217,160' };
  const ESRI = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';
  const TOWER_H = 110;                       // 34 storeys, drawn as a column of light

  let D = null, map = null, state = 'loading', mode = 'foot', active = null, look = 'night', cat = 'all', pitched = true;
  const markers = {}, rows = {};
  const anim = { raf: 0, flow: 0, line: null, cum: null, total: 0 };

  // ---------- small helpers
  const clean = s => String(s == null ? '' : s).replace(/[‐-―−-]/g, ' ').replace(/\s+/g, ' ').trim();
  const esc = s => clean(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const mins = s => Math.max(1, Math.round(s / 60));
  const dist = m => m < 950 ? `${Math.max(50, Math.round(m / 50) * 50)} m` : `${(m / 1000).toFixed(1)} km`;
  const placeOf = id => D && D.places.find(p => p.id === id);
  const catOf = id => D.cats.find(c => c.id === id) || D.cats[0];
  const SITE = () => [D.site.lon, D.site.lat];
  const R = 6371008.8, rad = d => d * Math.PI / 180;
  function metres(a, b) {
    const dl = rad(b[1] - a[1]), dn = rad(b[0] - a[0]);
    const h = Math.sin(dl / 2) ** 2 + Math.cos(rad(a[1])) * Math.cos(rad(b[1])) * Math.sin(dn / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(h));
  }
  function azimuth(a, b) {
    const y = Math.sin(rad(b[0] - a[0])) * Math.cos(rad(b[1]));
    const x = Math.cos(rad(a[1])) * Math.sin(rad(b[1])) - Math.sin(rad(a[1])) * Math.cos(rad(b[1])) * Math.cos(rad(b[0] - a[0]));
    return (Math.atan2(y, x) * 180 / Math.PI + 360) % 360;
  }
  function circle(c, r, n = 96) {
    const out = [];
    for (let i = 0; i <= n; i++) {
      const t = i / n * 2 * Math.PI;
      out.push([c[0] + (r * Math.sin(t)) / (111320 * Math.cos(rad(c[1]))), c[1] + (r * Math.cos(t)) / 110540]);
    }
    return out;
  }
  const fc = features => ({ type: 'FeatureCollection', features });
  const lineF = (coords, props = {}) => ({ type: 'Feature', properties: props, geometry: { type: 'LineString', coordinates: coords } });
  const ptF = (c, props = {}) => ({ type: 'Feature', properties: props, geometry: { type: 'Point', coordinates: c } });
  const ease = t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  const icon = (id, cls = '') => `<svg class="${cls}" aria-hidden="true"><use href="#${id}"/></svg>`;
  function webgl() {
    try { const c = document.createElement('canvas'); return !!(window.WebGLRenderingContext && (c.getContext('webgl2') || c.getContext('webgl'))); }
    catch (e) { return false; }
  }

  // ---------- the address: #place=id&mode=car
  function readHash() {
    const q = new URLSearchParams(location.hash.replace(/^#/, ''));
    const m = q.get('mode');
    return { place: q.get('place'), mode: m === 'car' || m === 'drive' ? 'car' : m === 'walk' || m === 'foot' ? 'foot' : null };
  }
  function writeHash() {
    const h = active ? `#place=${active}${mode === 'car' ? '&mode=car' : ''}` : mode === 'car' ? '#mode=car' : '';
    if (location.hash !== h) history.replaceState(null, '', h || location.pathname + location.search);
  }

  // ======================================================= the panel
  function buildChips() {
    const box = $('#chips');
    // icon only: the name shows on hover and keyboard focus, beside the row for the chosen one,
    // and on a long press on touch screens
    const all = [{ id: 'all', name: 'All places', color: '#f3efe8' }, ...D.cats];
    box.innerHTML = all.map(c => `<button type="button" class="chip" data-cat="${c.id}" aria-pressed="${c.id === cat}" aria-label="${esc(c.name)}" style="--c:${c.color}">${icon('c-' + c.id)}<span class="chip-tip" aria-hidden="true">${esc(c.name)}</span></button>`).join('');
    box.addEventListener('click', e => {
      const b = e.target.closest('[data-cat]');
      if (b) setCat(b.dataset.cat);
    });
    let press = 0;
    box.addEventListener('pointerdown', e => {
      const b = e.target.closest('[data-cat]');
      if (!b || e.pointerType === 'mouse') return;
      clearTimeout(press);
      press = setTimeout(() => { b.classList.add('tip'); setTimeout(() => b.classList.remove('tip'), 1400); }, 450);
    });
    ['pointerup', 'pointercancel', 'pointerleave'].forEach(t => box.addEventListener(t, () => clearTimeout(press)));
    box.addEventListener('contextmenu', e => { if (e.target.closest('[data-cat]')) e.preventDefault(); });
  }
  function setCat(c) {
    cat = c;
    $$('#chips .chip').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.cat === c)));
    const now = $('#chipsnow'), cc = c === 'all' ? { name: 'All places', color: '#f3efe8' } : catOf(c);
    now.textContent = clean(cc.name);
    now.style.setProperty('--c', cc.color);
    D.places.forEach(p => {
      const show = c === 'all' || p.cat === c || p.id === active;
      rows[p.id].parentNode.hidden = !show;
      if (markers[p.id]) markers[p.id].getElement().classList.toggle('off', !show);
    });
    if (map && state === 'ready' && !active) overview(1200);
  }

  function buildList() {
    const ol = $('#plist');
    const home = `<li style="--k:0"><button type="button" class="pl home" data-place="nest" style="--c:#f3efe8">
      <span class="pl-ph">${icon('i-home')}</span>
      <span class="pl-tx"><b>Nest Battersea</b><small>38 Lombard Road, SW11 3RP</small></span>
      <span class="pl-t"><b>Home</b><small>In planning</small></span></button></li>`;
    ol.innerHTML = home + D.places.map(p => {
      const c = catOf(p.cat);
      return `<li><button type="button" class="pl" data-place="${p.id}" style="--c:${c.color}">
        <span class="pl-ph"><img src="${p.photo.thumb}" alt="" width="104" height="104" loading="lazy" decoding="async"></span>
        <span class="pl-tx"><b>${esc(p.name)}</b><small>${esc(p.kind)}</small><span class="pl-bar"><i></i></span></span>
        <span class="pl-t"><b></b><small></small></span></button></li>`;
    }).join('');
    $$('.pl', ol).forEach(b => { rows[b.dataset.place] = b; });
    $$('.pl-ph img', ol).forEach(img => {
      const on = () => img.classList.add('in');
      if (img.complete && img.naturalWidth) on(); else img.addEventListener('load', on, { once: true });
    });
    ol.addEventListener('click', e => {
      const b = e.target.closest('[data-place]');
      if (!b) return;
      const id = b.dataset.place;
      select(active === id && id !== 'nest' ? null : id);
    });
    ol.addEventListener('pointerover', e => { const b = e.target.closest('[data-place]'); hover(b ? b.dataset.place : null); });
    ol.addEventListener('pointerleave', () => hover(null));
    fillTimes(false);
  }
  function hover(id) {
    Object.entries(markers).forEach(([k, m]) => m.getElement().classList.toggle('hov', k === id));
    Object.entries(rows).forEach(([k, r]) => r.classList.toggle('hov', k === id));
  }
  // times for the current mode, and the list sorted by them (the rows glide to their new place)
  function fillTimes(animate = true) {
    const max = Math.max(...D.places.map(p => p[mode].s));
    D.places.forEach(p => {
      const r = rows[p.id], t = p[mode];
      $('.pl-t b', r).textContent = `${mins(t.s)} min`;
      $('.pl-t small', r).textContent = dist(t.m);
      $('.pl-bar i', r).style.setProperty('--f', Math.max(.04, t.s / max).toFixed(3));
      r.setAttribute('aria-label', `${clean(p.name)}, ${clean(p.kind)}, ${mins(t.s)} minutes ${mode === 'car' ? 'by car' : 'on foot'}, ${dist(t.m)}`);
      const mk = markers[p.id];
      if (mk) $('.pm-lbl em', mk.getElement()).textContent = `${mins(t.s)} min ${mode === 'car' ? 'by car' : 'walk'}`;
    });
    const ol = $('#plist');
    const lis = $$('li', ol).slice(1);
    const before = new Map(lis.map(li => [li, li.getBoundingClientRect().top]));
    lis.sort((a, b) => placeOf($('[data-place]', a).dataset.place)[mode].s - placeOf($('[data-place]', b).dataset.place)[mode].s)
      .forEach((li, k) => { li.style.setProperty('--k', k + 1); ol.appendChild(li); });
    if (!animate || reduced) return;
    lis.forEach(li => {
      const dy = before.get(li) - li.getBoundingClientRect().top;
      if (!dy) return;
      li.animate([{ transform: `translateY(${dy}px)` }, { transform: 'none' }], { duration: 600, easing: 'cubic-bezier(.22,.61,.24,1)' });
    });
  }
  const order = () => $$('#plist li').filter(li => !li.hidden).map(li => $('[data-place]', li).dataset.place).filter(id => id !== 'nest');

  // ======================================================= the chosen place
  function detailHTML(p) {
    const c = catOf(p.cat), ph = p.photo, ids = order(), k = ids.indexOf(p.id);
    const tile = m => {
      const t = p[m];
      return `<button type="button" class="d-mode" data-mode="${m}" aria-pressed="${m === mode}">${icon(m === 'car' ? 'i-car' : 'i-walk')}<b>${mins(t.s)} min</b><small>${m === 'car' ? 'Car' : 'Walk'} · ${dist(t.m)}</small></button>`;
    };
    const t = p[mode];
    const via = (t.via || []).filter(v => !/^Bridges Court$/i.test(v) && v !== t.bridge).slice(0, 2).map(clean);
    let how;
    if (p.door) how = `${icon('i-arrow')}<span>Right outside the door, along the river.</span>`;
    else if (t.bridge) how = `${icon('i-bridge')}<span>Crosses the Thames on <b>${esc(t.bridge)}</b>${via.length ? `, by ${via.map(esc).join(' and ')}` : ''}.</span>`;
    else how = `${icon('i-arrow')}<span>${via.length ? `By ${via.map(esc).join(' and ')}` : 'Through the neighbourhood'}, on this side of the river.</span>`;
    return `
      <figure class="d-ph"><img src="${ph.src}" alt="${esc(p.name)}, photograph" width="720" height="480" decoding="async">
        <figcaption>Photo <a href="${ph.page}" target="_blank" rel="noopener">${esc(ph.author)}</a> · <a href="${ph.licenceUrl}" target="_blank" rel="noopener">${esc(ph.licence)}</a> · Wikimedia Commons</figcaption></figure>
      <button type="button" class="d-x" data-act="close" aria-label="Close">${icon('i-x')}</button>
      <div class="d-body">
        <p class="eyebrow d-cat" style="--c:${c.color}">${icon('c-' + c.id)}${esc(c.name)}</p>
        <h2>${esc(p.name)}</h2>
        <p class="d-kind">${esc(p.kind)}</p>
        <div class="d-modes">${tile('foot')}${tile('car')}</div>
        <p class="d-via">${how}</p>
        <div class="d-nav"><span class="n">${String(k + 1).padStart(2, '0')} / ${String(ids.length).padStart(2, '0')}</span>
          <div><button type="button" class="circ sm" data-act="step" data-d="-1" aria-label="Previous place">${icon('i-prev')}</button><button type="button" class="circ sm" data-act="step" data-d="1" aria-label="Next place">${icon('i-next')}</button></div></div>
      </div>`;
  }
  function homeHTML() {
    const s = D.site;
    return `
      <figure class="d-ph"><img src="${s.photo}" alt="Nest Battersea by the river at dusk, official image" width="720" height="480" decoding="async"><figcaption>Official image</figcaption></figure>
      <button type="button" class="d-x" data-act="close" aria-label="Close">${icon('i-x')}</button>
      <div class="d-body">
        <p class="eyebrow d-cat" style="--c:#f3efe8">${icon('i-home')}Home</p>
        <h2>Nest Battersea</h2>
        <p class="d-kind">${esc(s.address)}</p>
        <dl class="d-home-facts">${s.facts.map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join('')}</dl>
        <p class="d-via">${icon('i-info')}<span>The tower is drawn as a column of light where it is planned. Choose a place in the list to see the way there.</span></p>
      </div>`;
  }
  function renderDetail() {
    const box = $('#detail');
    if (!active) { box.hidden = true; box.innerHTML = ''; return; }
    box.innerHTML = active === 'nest' ? homeHTML() : detailHTML(placeOf(active));
    box.hidden = false;
    box.classList.remove('show'); void box.offsetWidth; box.classList.add('show');
    const img = $('.d-ph img', box);
    const on = () => img.classList.add('in');
    if (img.complete && img.naturalWidth) requestAnimationFrame(on); else img.addEventListener('load', on, { once: true });
  }
  function refreshModes() {
    $$('#detail .d-mode').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.mode === mode)));
    if (active && active !== 'nest') {
      const p = placeOf(active), via = $('#detail .d-via');
      const tmp = document.createElement('div');
      tmp.innerHTML = detailHTML(p);
      if (via) via.innerHTML = $('.d-via', tmp).innerHTML;
    }
  }

  // ======================================================= selection
  function select(id, o = {}) {
    if (id && id !== 'nest' && !placeOf(id)) id = null;
    active = id;
    body.classList.toggle('picked', !!id);
    body.classList.toggle('picking', !!id && id !== 'nest');
    Object.entries(rows).forEach(([k, r]) => r.classList.toggle('on', k === id));
    Object.entries(markers).forEach(([k, m]) => m.getElement().classList.toggle('on', k === id));
    if (id && rows[id]) {
      rows[id].parentNode.hidden = false;
      if (!narrow()) rows[id].scrollIntoView({ block: 'nearest', behavior: reduced ? 'auto' : 'smooth' });
    }
    writeHash();
    renderDetail();
    if (!map || state !== 'ready') return;
    if (!id) { clearRoute(); overview(o.dur); return; }
    if (id === 'nest') {
      clearRoute();
      const [x, y] = SITE(), bearing = map.getBearing() - 40;
      const cam = map.cameraForBounds([[x - .0016, y - .001], [x + .0016, y + .001]], { padding: pad(), bearing }) || { center: SITE() };
      map.flyTo({ center: cam.center, zoom: narrow() ? 16 : 16.4, pitch: pitched ? 62 : 0, bearing, duration: reduced ? 0 : 2600, curve: 1.3, essential: true });
      return;
    }
    drawRoute();
    frame(placeOf(id), o.dur);
  }
  function step(d) {
    const ids = order();
    if (!ids.length) return;
    const k = ids.indexOf(active);
    select(ids[(k + d + ids.length) % ids.length]);
  }
  function setMode(m, user = true) {
    if (m !== 'foot' && m !== 'car') return;
    const changed = m !== mode;
    mode = m;
    body.dataset.mode = m;
    $$('.modes [data-mode]').forEach(b => b.setAttribute('aria-checked', String(b.dataset.mode === m)));
    fillTimes(changed && user);
    refreshModes();
    writeHash();
    if (changed && map && state === 'ready' && active && active !== 'nest') {
      drawRoute();
      frame(placeOf(active), 1500);
    }
  }

  // ======================================================= the map
  function pad() {
    const m = 10, hb = narrow() ? 48 : 56;
    if (narrow()) {
      const card = $('#detail');
      const sheet = active ? (card.offsetHeight || innerHeight * .56) : body.classList.contains('folded') ? 132 : innerHeight * .48;
      return { top: hb + 2 * m + 30, bottom: Math.min(innerHeight * .62, sheet) + 24, left: 30, right: 56 };
    }
    const right = active ? 380 + 2 * m + 50 : 110;
    return { top: hb + 2 * m + 60, bottom: 70, left: 400 + 2 * m + 60, right };
  }
  function overviewCam() {
    // frame what is within about half an hour on foot; the farther places sit around the edges
    const shown = D.places.filter(p => cat === 'all' || p.cat === cat);
    const near = shown.filter(p => metres(SITE(), [p.lon, p.lat]) < 2300);
    const use = near.length >= 4 ? near : shown;
    const pts = [SITE(), ...use.map(p => [p.lon, p.lat])];
    const b = pts.reduce((a, q) => a.extend(q), new maplibregl.LngLatBounds(pts[0], pts[0]));
    const P = pad();
    const cam = map.cameraForBounds(b, { padding: { ...P, top: P.top - 20, bottom: Math.max(30, P.bottom - 30) }, bearing: -14 }) || { center: SITE(), zoom: 13.6 };
    return { center: cam.center, zoom: Math.max(narrow() ? 12.9 : 13.2,Math.min(15.6, cam.zoom - (pitched ? .1 : 0))), bearing: -14, pitch: pitched ? 48 : 0 };
  }
  function overview(dur) {
    map.flyTo({ ...overviewCam(), duration: reduced ? 0 : dur || 2000, curve: 1.2, essential: true });
  }
  // the camera turns so the way runs up the screen, home below, the place ahead
  function frame(p, dur) {
    const r = p[mode], site = SITE(), dest = [p.lon, p.lat];
    const pts = [site, dest, ...r.line];
    const b = pts.reduce((a, q) => a.extend(q), new maplibregl.LngLatBounds(site, site));
    const far = metres(site, dest);
    let bearing = far > 250 ? azimuth(site, dest) : map.getBearing();
    // the shorter turn
    const cur = map.getBearing();
    bearing = cur + (((bearing - cur) % 360) + 540) % 360 - 180;
    const cam = map.cameraForBounds(b, { padding: pad(), bearing }) || { center: dest, zoom: 15 };
    const zoom = Math.min(p.door ? 17.2 : 17, cam.zoom - (pitched ? .12 : .05));
    map.flyTo({ center: cam.center, zoom, bearing, pitch: pitched ? 55 : 0, duration: reduced ? 0 : dur || 2400, curve: 1.35, essential: true });
  }

  function style() {
    const s = window.MapView && MapView.style ? MapView.style() : { version: 8, glyphs: 'https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf', sources: { ofm: { type: 'vector', url: 'https://tiles.openfreemap.org/planet' } }, layers: [{ id: 'bg', type: 'background', paint: { 'background-color': '#161922' } }] };
    s.sources.esri = { type: 'raster', tiles: [ESRI], tileSize: 256, maxzoom: 19,
      attribution: 'Imagery © <a href="https://www.esri.com/" target="_blank" rel="noopener">Esri</a>, Maxar, Earthstar Geographics and the GIS User Community' };
    const at = s.layers.findIndex(l => l.id === 'bg') + 1;
    s.layers.splice(at, 0, { id: 'sat', type: 'raster', source: 'esri', layout: { visibility: 'none' },
      paint: { 'raster-saturation': -.2, 'raster-brightness-max': .82, 'raster-contrast': .08, 'raster-fade-duration': 250 } });
    // a little more legible here than in the section: brighter roads and labels
    s.layers.forEach(l => {
      if (l.id === 'l-road') l.paint['text-color'] = '#a6aebb';
      if (l.id === 'l-place') l.paint['text-opacity'] = .9;
      if (l.id === 'r-major') l.paint['line-color'] = '#3a4358';
      if (l.id === 'r-mid') l.paint['line-color'] = '#2f3649';
    });
    s.light = { anchor: 'viewport', color: '#fff1dc', intensity: .34, position: [1.3, 210, 40] };
    return s;
  }

  function addLayers() {
    const site = SITE();
    // distance rings around home
    const rings = [500, 1000, 2000, 3000];
    map.addSource('rings', { type: 'geojson', data: fc(rings.map(r => lineF(circle(site, r), { label: r < 1000 ? `${r} m` : `${r / 1000} km` }))) });
    map.addLayer({ id: 'rings', type: 'line', source: 'rings', paint: { 'line-color': '#92B7CA', 'line-opacity': .32, 'line-width': 1.1, 'line-dasharray': [2, 3] } }, 'bld-flat');
    map.addLayer({ id: 'rings-lbl', type: 'symbol', source: 'rings',
      layout: { 'symbol-placement': 'line', 'symbol-spacing': 520, 'text-field': ['get', 'label'], 'text-font': ['Noto Sans Bold'], 'text-size': 11, 'text-letter-spacing': .18, 'text-keep-upright': true },
      paint: { 'text-color': '#C9E2EF', 'text-opacity': .75, 'text-halo-color': '#0f1116', 'text-halo-width': 1.6 } });
    // the tower: a column of light on its footprint, rising when the page opens
    map.addSource('home', { type: 'geojson', data: { type: 'Feature', properties: {}, geometry: { type: 'Polygon', coordinates: [D.site.footprint] } } });
    map.addSource('home-pt', { type: 'geojson', data: ptF(site) });
    map.addLayer({ id: 'home-glow', type: 'circle', source: 'home-pt', paint: { 'circle-radius': ['interpolate', ['exponential', 2], ['zoom'], 12, 18, 16, 90, 18, 260], 'circle-color': '#C9E2EF', 'circle-opacity': .14, 'circle-blur': 1, 'circle-pitch-alignment': 'map' } }, 'bld-flat');
    map.addLayer({ id: 'home-3d', type: 'fill-extrusion', source: 'home',
      paint: { 'fill-extrusion-color': '#C9E2EF', 'fill-extrusion-opacity': .88, 'fill-extrusion-base': 0, 'fill-extrusion-height': 0,
        'fill-extrusion-height-transition': { duration: reduced ? 0 : 2600, delay: reduced ? 0 : 700 }, 'fill-extrusion-vertical-gradient': true } });
    // the way: the other mode faint and dashed, the chosen one bright with a moving light
    map.addSource('ghost', { type: 'geojson', data: fc([]) });
    map.addSource('route', { type: 'geojson', data: fc([]), lineMetrics: true });
    map.addSource('links', { type: 'geojson', data: fc([]) });
    map.addSource('comet', { type: 'geojson', data: fc([]) });
    const lc = { 'line-cap': 'round', 'line-join': 'round' };
    map.addLayer({ id: 'ghost', type: 'line', source: 'ghost', layout: lc, paint: { 'line-color': '#f3efe8', 'line-opacity': .38, 'line-width': 2, 'line-dasharray': [1, 2.2] } });
    map.addLayer({ id: 'route-casing', type: 'line', source: 'route', layout: lc, paint: { 'line-color': '#0b0e15', 'line-opacity': .6, 'line-width': ['interpolate', ['linear'], ['zoom'], 12, 6, 17, 13] } });
    map.addLayer({ id: 'route-glow', type: 'line', source: 'route', layout: lc, paint: { 'line-color': COL.foot, 'line-opacity': .4, 'line-blur': 8, 'line-width': ['interpolate', ['linear'], ['zoom'], 12, 10, 17, 26] } });
    map.addLayer({ id: 'route-line', type: 'line', source: 'route', layout: lc, paint: { 'line-width': ['interpolate', ['linear'], ['zoom'], 12, 3, 17, 6.5], 'line-gradient': grad('foot') } });
    map.addLayer({ id: 'route-flow', type: 'line', source: 'route', layout: lc, paint: { 'line-color': '#ffffff', 'line-opacity': .55, 'line-width': ['interpolate', ['linear'], ['zoom'], 12, 1.2, 17, 2.4], 'line-dasharray': [0, 4, 3] } });
    map.addLayer({ id: 'links', type: 'line', source: 'links', layout: lc, paint: { 'line-color': COL.foot, 'line-opacity': .7, 'line-width': 1.6, 'line-dasharray': [.6, 1.6] } });
    map.addLayer({ id: 'comet-glow', type: 'circle', source: 'comet', paint: { 'circle-radius': 16, 'circle-color': COL.foot, 'circle-opacity': .45, 'circle-blur': 1, 'circle-pitch-alignment': 'map' } });
    map.addLayer({ id: 'comet', type: 'circle', source: 'comet', paint: { 'circle-radius': 4.5, 'circle-color': '#ffffff', 'circle-stroke-color': COL.foot, 'circle-stroke-width': 2, 'circle-pitch-alignment': 'map' } });
    try { if (map.setSky) map.setSky({ 'sky-color': '#0f1116', 'horizon-color': '#1d2738', 'fog-color': '#0f1116', 'sky-horizon-blend': .7, 'horizon-fog-blend': .6, 'fog-ground-blend': .75, 'atmosphere-blend': 0 }); } catch (e) { /* older engines: no sky */ }
  }
  // the colour runs from faint at home to full at the place: the way reads in its direction
  const grad = m => ['interpolate', ['linear'], ['line-progress'], 0, `rgba(${RGB[m]},.35)`, .5, `rgba(${RGB[m]},.8)`, 1, COL[m]];

  function addMarkers() {
    const h = document.createElement('div');
    h.className = 'mk-home';
    h.setAttribute('role', 'button'); h.tabIndex = 0;
    h.setAttribute('aria-label', 'Nest Battersea, 38 Lombard Road, in planning');
    h.innerHTML = `<span class="h-pulse"></span><span class="h-pulse"></span><span class="h-dot"></span><span class="h-lbl"><span class="h-ic">${icon('i-home')}</span>Nest Battersea <small>In planning</small></span>`;
    const goHome = e => { e.stopPropagation(); select('nest'); };
    h.addEventListener('click', goHome);
    h.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); goHome(e); } });
    markers.nest = new maplibregl.Marker({ element: h, anchor: 'center' }).setLngLat(SITE()).addTo(map);
    D.places.forEach((p, k) => {
      const c = catOf(p.cat), b = document.createElement('button');
      b.type = 'button'; b.className = 'pm'; b.dataset.place = p.id;
      b.style.setProperty('--c', c.color); b.style.setProperty('--k', k);
      b.setAttribute('aria-label', clean(p.name));
      b.innerHTML = `<span class="pm-dot">${icon('c-' + c.id)}</span><span class="pm-lbl"><b>${esc(p.name)}</b><em></em></span>`;
      b.addEventListener('click', e => { e.stopPropagation(); select(active === p.id ? null : p.id); });
      b.addEventListener('pointerenter', () => hover(p.id));
      b.addEventListener('pointerleave', () => hover(null));
      markers[p.id] = new maplibregl.Marker({ element: b, anchor: 'center' }).setLngLat([p.lon, p.lat]).addTo(map);
    });
    fillTimes(false);
  }

  // ---------- the drawn way
  function clearRoute() {
    cancelAnimationFrame(anim.raf); clearInterval(anim.flow);
    anim.raf = 0; anim.line = null;
    ['ghost', 'route', 'links', 'comet'].forEach(id => map.getSource(id) && map.getSource(id).setData(fc([])));
  }
  function along(d) {
    const { line, cum } = anim;
    if (d <= 0) return { i: 0, pt: line[0] };
    if (d >= anim.total) return { i: line.length - 1, pt: line[line.length - 1] };
    let lo = 0, hi = cum.length - 1;
    while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (cum[mid] < d) lo = mid; else hi = mid; }
    const f = (d - cum[lo]) / ((cum[hi] - cum[lo]) || 1);
    return { i: lo, pt: [line[lo][0] + (line[hi][0] - line[lo][0]) * f, line[lo][1] + (line[hi][1] - line[lo][1]) * f] };
  }
  function drawRoute() {
    clearRoute();
    const p = placeOf(active), r = p[mode], other = p[mode === 'foot' ? 'car' : 'foot'];
    const site = SITE(), dest = [p.lon, p.lat];
    const line = r.line.length > 1 ? r.line : [site, dest];
    // colour of the chosen mode
    map.setPaintProperty('route-line', 'line-gradient', grad(mode));
    map.setPaintProperty('route-glow', 'line-color', COL[mode]);
    map.setPaintProperty('links', 'line-color', COL[mode]);
    map.setPaintProperty('comet-glow', 'circle-color', COL[mode]);
    map.setPaintProperty('comet', 'circle-stroke-color', COL[mode]);
    map.getSource('ghost').setData(other.line.length > 1 ? lineF(other.line) : fc([]));
    const links = [];
    if (metres(site, line[0]) > 8) links.push(lineF([site, line[0]]));
    if (metres(line[line.length - 1], dest) > 8) links.push(lineF([line[line.length - 1], dest]));
    map.getSource('links').setData(fc(links));
    anim.line = line;
    anim.cum = [0];
    for (let i = 1; i < line.length; i++) anim.cum.push(anim.cum[i - 1] + metres(line[i - 1], line[i]));
    anim.total = anim.cum[anim.cum.length - 1];
    const src = map.getSource('route'), comet = map.getSource('comet');
    if (reduced) { src.setData(lineF(line)); comet.setData(ptF(dest)); return; }
    const drawMs = Math.max(1300, Math.min(2800, 900 + anim.total * .55)), delay = 450;
    const loopMs = Math.max(2400, Math.min(6500, anim.total * 1.9));
    const t0 = performance.now(), mine = anim.line;
    let flowK = 0;
    const DASH = [[0, 4, 3], [.5, 4, 2.5], [1, 4, 2], [1.5, 4, 1.5], [2, 4, 1], [2.5, 4, .5], [3, 4, 0], [0, .5, 3, 3.5], [0, 1, 3, 3], [0, 1.5, 3, 2.5], [0, 2, 3, 2], [0, 2.5, 3, 1.5], [0, 3, 3, 1], [0, 3.5, 3, .5]];
    anim.flow = setInterval(() => { if (!document.hidden && anim.line === mine) map.setPaintProperty('route-flow', 'line-dasharray', DASH[flowK = (flowK + 1) % DASH.length]); }, 70);
    let drawn = false;
    const tick = now => {
      if (anim.line !== mine) return;
      const t = now - t0 - delay;
      if (t >= 0 && !drawn) {
        const e = ease(Math.min(1, t / drawMs));
        const { i, pt } = along(e * anim.total);
        src.setData(lineF([...line.slice(0, i + 1), pt].length > 1 ? [...line.slice(0, i + 1), pt] : [line[0], line[0]]));
        comet.setData(ptF(pt));
        if (t >= drawMs) { drawn = true; src.setData(lineF(line)); }
      } else if (drawn) {
        // a light that keeps running from home to the place
        const u = ((t - drawMs) % loopMs) / loopMs;
        comet.setData(ptF(along(ease(u) * anim.total).pt));
      }
      anim.raf = requestAnimationFrame(tick);
    };
    anim.raf = requestAnimationFrame(tick);
  }

  // ---------- the two looks
  let nightPaint = null;
  function setLook(l) {
    look = l;
    body.dataset.look = l;
    $$('.looks [data-look]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.look === l)));
    if (!map || !map.getLayer('sat')) return;
    const sat = l === 'sat';
    const vis = (id, on) => map.getLayer(id) && map.setLayoutProperty(id, 'visibility', on ? 'visible' : 'none');
    const paint = (id, k, v) => map.getLayer(id) && map.setPaintProperty(id, k, v);
    if (!nightPaint) nightPaint = { bld: map.getPaintProperty('bld-3d', 'fill-extrusion-color') };
    vis('sat', sat);
    ['green', 'green2', 'aero', 'water', 'waterway', 'r-path', 'r-service', 'r-minor', 'rail', 'bld-flat'].forEach(id => vis(id, !sat));
    paint('r-mid', 'line-opacity', sat ? .25 : 1);
    paint('r-major', 'line-opacity', sat ? .35 : 1);
    paint('water-rim', 'line-opacity', sat ? .35 : 1);
    paint('bld-3d', 'fill-extrusion-color', sat ? ['interpolate', ['linear'], ['coalesce', ['get', 'render_height'], 8], 0, '#cfc8bb', 60, '#e4ddd0', 150, '#f3efe8'] : nightPaint.bld);
    paint('bld-3d', 'fill-extrusion-opacity', sat ? .5 : .9);
    ['l-road', 'l-place', 'l-park', 'l-water', 'l-water-pt', 'rings-lbl'].forEach(id => { paint(id, 'text-halo-color', sat ? 'rgba(8,10,15,.9)' : (id.startsWith('l-water') ? '#0d2030' : '#0f1116')); paint(id, 'text-halo-width', sat ? 1.8 : 1.4); });
    paint('l-road', 'text-color', sat ? '#e6e2da' : '#a6aebb');
    paint('rings', 'line-color', sat ? '#ffffff' : '#92B7CA');
    paint('rings', 'line-opacity', sat ? .55 : .32);
  }

  // ---------- controls and keys
  function bind() {
    $$('.modes [data-mode]').forEach(b => b.addEventListener('click', () => setMode(b.dataset.mode)));
    $$('.looks [data-look]').forEach(b => b.addEventListener('click', () => setLook(b.dataset.look)));
    $('#detail').addEventListener('click', e => {
      const b = e.target.closest('[data-act], [data-mode]');
      if (!b) return;
      if (b.dataset.mode) return setMode(b.dataset.mode);
      if (b.dataset.act === 'close') return select(null);
      if (b.dataset.act === 'step') return step(+b.dataset.d);
    });
    $('#ctl').addEventListener('click', e => {
      const b = e.target.closest('[data-ctl]');
      if (!b || !map) return;
      const k = b.dataset.ctl;
      if (k === 'in') map.zoomIn({ duration: 500 });
      if (k === 'out') map.zoomOut({ duration: 500 });
      if (k === 'north') map.easeTo({ bearing: 0, duration: 900 });
      if (k === 'home') select(null);
      if (k === 'tilt') {
        pitched = !pitched;
        b.setAttribute('aria-pressed', String(pitched));
        map.easeTo({ pitch: pitched ? 55 : 0, duration: 1100 });
      }
    });
    $('#grab').addEventListener('click', () => body.classList.toggle('folded'));
    // the photo credits open from a link inside the map's own attribution (the "i" in the corner)
    const cr = $('#credits');
    document.addEventListener('click', e => {
      if (!e.target.closest('[data-credits]')) return;
      e.preventDefault();
      cr.hidden = false; $('.x', cr).focus();
    });
    cr.addEventListener('click', e => { if (e.target === cr || e.target.closest('[data-close]')) cr.hidden = true; });
    addEventListener('keydown', e => {
      if (e.key === 'Escape') { if (!cr.hidden) cr.hidden = true; else if (active) select(null); }
      if (active && active !== 'nest' && cr.hidden && !e.target.closest('input,textarea')) {
        if (e.key === 'ArrowRight') step(1);
        if (e.key === 'ArrowLeft') step(-1);
      }
    });
    addEventListener('hashchange', () => {
      const h = readHash();
      if (h.mode && h.mode !== mode) setMode(h.mode, false);
      if ((h.place || null) !== active) select(h.place);
    });
  }
  function buildCredits() {
    $('#creditlist').innerHTML = D.places.map(p => {
      const ph = p.photo;
      return `<li><img src="${ph.thumb}" alt="" width="44" height="44" loading="lazy"><span><b>${esc(p.name)}</b>: photo by <a href="${ph.page}" target="_blank" rel="noopener">${esc(ph.author)}</a>, <a href="${ph.licenceUrl}" target="_blank" rel="noopener">${esc(ph.licence)}</a>, via Wikimedia Commons${ph.changed ? ', cropped and resized' : ''}</span></li>`;
    }).join('');
  }

  // ======================================================= start
  async function boot() {
    try {
      const r = await fetch('assets/map/places.json?v=1');
      if (!r.ok) throw new Error('places');
      D = await r.json();
    } catch (e) { state = 'failed'; return; }
    buildChips(); buildList(); buildCredits(); bind();
    const h = readHash();
    if (h.mode) setMode(h.mode, false);
    if (!window.maplibregl || !webgl()) { state = 'static'; if (h.place) select(h.place); return; }
    map = new maplibregl.Map({
      container: 'mpmap', style: style(), center: SITE(), zoom: 12.3, pitch: 0, bearing: -70,
      minZoom: 11, maxZoom: 19, maxPitch: 70, maxBounds: [[-0.36, 51.38], [0.02, 51.56]],
      attributionControl: false, fadeDuration: 150, dragRotate: true, touchPitch: true, pitchWithRotate: true
    });
    map.addControl(new maplibregl.AttributionControl({ compact: true, customAttribution: '<a href="assets/map/credits.html" data-credits>Photo credits</a> | Routes: OSRM, <a href="https://routing.openstreetmap.de/" target="_blank" rel="noopener">FOSSGIS</a>' }), 'bottom-right');
    window.MapPage.map = () => map;
    const fail = setTimeout(() => { if (state !== 'ready') { state = 'static'; if (h.place) select(h.place); } }, 20000);
    map.on('rotate', () => { const n = $('#ctl .needle'); if (n) n.style.transform = `rotate(${-map.getBearing()}deg)`; });
    map.on('movestart', e => { if (e.originalEvent) body.classList.add('moved'); });
    map.on('load', () => {
      // the attribution stays the small "i" in the corner; a click on it opens the credits line
      const fold = () => { const a = $('.maplibregl-ctrl-attrib'); if (a) a.classList.remove('maplibregl-compact-show'); };
      fold(); map.once('idle', fold);
      addLayers();
      addMarkers();
      setLook(look);
      clearTimeout(fail);
      state = 'ready';
      body.classList.add('ready');
      setCat(cat);
      map.setPaintProperty('home-3d', 'fill-extrusion-height', TOWER_H);
      if (h.place && (h.place === 'nest' || placeOf(h.place))) select(h.place, { dur: 3000 });
      else { active = null; overview(reduced ? 0 : 3400); }
      setTimeout(() => body.classList.add('moved'), 9000);
    });
    let rz = 0;
    addEventListener('resize', () => { clearTimeout(rz); rz = setTimeout(() => { if (state === 'ready' && !active) map.jumpTo(overviewCam()); }, 200); });
  }

  window.MapPage = {
    state: () => state, map: () => map, data: () => D, active: () => active, mode: () => mode, look: () => look,
    select, setMode, setLook, route: () => active && active !== 'nest' && placeOf(active) ? placeOf(active)[mode] : null
  };
  if (document.readyState === 'loading') addEventListener('DOMContentLoaded', boot); else boot();
})();
