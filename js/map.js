/* ============================================================
   NEST BATTERSEA | the Location map
   MapLibre GL JS 4.7.1 (cdnjs) with OpenFreeMap vector tiles
   (tiles.openfreemap.org, no key) in a style written for the
   site: a near black base, muted roads, deep blue water with a
   soft rim, low 3D buildings and quiet labels. Places and walking
   routes come from assets/site/map/places.json, computed once
   from OpenStreetMap (the site never calls a router).
   ------------------------------------------------------------
   The library loads only when the section comes near. Until then,
   and whenever WebGL or the network fails, the static picture of
   the same map stays in place. Page scrolling is never captured:
   cooperative gestures ask for Ctrl + scroll or two fingers.
   ============================================================ */
const MapView = (() => {
  const LIB = 'https://cdnjs.cloudflare.com/ajax/libs/maplibre-gl/4.7.1/';
  const TILES = 'https://tiles.openfreemap.org/planet';
  const GLYPHS = 'https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf';
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const C = {
    bg: '#161922', park: '#17231f', water: '#0d2030', rim: 'rgba(146,183,202,.38)', aero: '#1b1f2c',
    path: '#272d3b', minor: '#232836', mid: '#2a3042', major: '#333b4f', rail: '#2c3344',
    bld: '#1b1f2a', bldLo: '#1d2231', bldMid: '#232a3b', bldHi: '#2c3549',
    label: '#a3abb9', road: '#7b8392', waterLabel: '#92B7CA', parkLabel: '#6f8b80',
    blue: '#92B7CA', blueHi: '#C9E2EF'
  };
  const F = { r: ['Noto Sans Regular'], b: ['Noto Sans Bold'], i: ['Noto Sans Italic'] };
  const NAME = ['coalesce', ['get', 'name:en'], ['get', 'name:latin'], ['get', 'name']];
  // the site never shows a dash or hyphen, not even in a map label
  const CLEAN = ['!', ['any', ['in', '-', ['to-string', NAME]], ['in', '–', ['to-string', NAME]], ['in', '—', ['to-string', NAME]]]];
  const z = (...stops) => ['interpolate', ['exponential', 1.5], ['zoom'], ...stops];

  function style() {
    const road = (id, classes, color, width, extra = {}) => ({
      id, type: 'line', source: 'ofm', 'source-layer': 'transportation',
      filter: ['all', ['in', ['get', 'class'], ['literal', classes]], ['!=', ['get', 'brunnel'], 'tunnel']],
      layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': color, 'line-width': width, ...extra }
    });
    return {
      version: 8, name: 'Nest Battersea night', glyphs: GLYPHS,
      sources: { ofm: { type: 'vector', url: TILES } },
      layers: [
        { id: 'bg', type: 'background', paint: { 'background-color': C.bg } },
        { id: 'green', type: 'fill', source: 'ofm', 'source-layer': 'landcover', filter: ['in', ['get', 'class'], ['literal', ['grass', 'wood']]],
          paint: { 'fill-color': C.park, 'fill-opacity': ['interpolate', ['linear'], ['zoom'], 10, .5, 14, .95] } },
        { id: 'green2', type: 'fill', source: 'ofm', 'source-layer': 'park', paint: { 'fill-color': C.park, 'fill-opacity': .8 } },
        { id: 'aero', type: 'fill', source: 'ofm', 'source-layer': 'aeroway', filter: ['==', ['geometry-type'], 'Polygon'], paint: { 'fill-color': C.aero } },
        { id: 'water', type: 'fill', source: 'ofm', 'source-layer': 'water', paint: { 'fill-color': C.water } },
        { id: 'water-rim', type: 'line', source: 'ofm', 'source-layer': 'water',
          paint: { 'line-color': C.rim, 'line-width': z(11, .4, 15, 1.2, 18, 2), 'line-blur': z(11, .4, 16, 1.2) } },
        { id: 'waterway', type: 'line', source: 'ofm', 'source-layer': 'waterway', paint: { 'line-color': C.water, 'line-width': z(10, .5, 16, 3) } },
        road('r-path', ['path', 'track'], C.path, z(14, .5, 18, 1.6), { 'line-dasharray': [1.5, 1.5] }),
        road('r-service', ['service'], C.minor, z(14, .4, 18, 3)),
        road('r-minor', ['minor'], C.minor, z(12, .35, 15, 1.6, 18, 8)),
        road('r-mid', ['tertiary', 'secondary'], C.mid, z(11, .5, 15, 3, 18, 14)),
        road('r-major', ['primary', 'trunk', 'motorway'], C.major, z(9, .6, 13, 2, 16, 6, 18, 18)),
        { id: 'rail', type: 'line', source: 'ofm', 'source-layer': 'transportation', filter: ['all', ['in', ['get', 'class'], ['literal', ['rail', 'transit']]], ['!=', ['get', 'brunnel'], 'tunnel']],
          paint: { 'line-color': C.rail, 'line-width': z(12, .6, 17, 1.8), 'line-dasharray': [3, 2.5] } },
        { id: 'bld-flat', type: 'fill', source: 'ofm', 'source-layer': 'building', minzoom: 13, maxzoom: 14.2, paint: { 'fill-color': C.bld, 'fill-opacity': .9 } },
        { id: 'bld-3d', type: 'fill-extrusion', source: 'ofm', 'source-layer': 'building', minzoom: 14,
          filter: ['!=', ['get', 'hide_3d'], true],
          paint: {
            'fill-extrusion-color': ['interpolate', ['linear'], ['coalesce', ['get', 'render_height'], 8], 0, C.bldLo, 40, C.bldMid, 120, C.bldHi],
            'fill-extrusion-height': ['interpolate', ['linear'], ['zoom'], 14, 0, 14.6, ['coalesce', ['get', 'render_height'], 8]],
            'fill-extrusion-base': ['coalesce', ['get', 'render_min_height'], 0],
            'fill-extrusion-opacity': .9, 'fill-extrusion-vertical-gradient': true
          } },
        // labels: quiet, letter spaced, never hyphenated
        { id: 'l-water', type: 'symbol', source: 'ofm', 'source-layer': 'waterway', minzoom: 12, filter: ['all', ['==', ['get', 'class'], 'river'], CLEAN],
          layout: { 'symbol-placement': 'line', 'text-field': NAME, 'text-font': F.i, 'text-size': z(12, 11, 16, 15), 'text-letter-spacing': .3, 'symbol-spacing': 420 },
          paint: { 'text-color': C.waterLabel, 'text-halo-color': C.water, 'text-halo-width': 1.2 } },
        { id: 'l-water-pt', type: 'symbol', source: 'ofm', 'source-layer': 'water_name', filter: CLEAN,
          layout: { 'text-field': NAME, 'text-font': F.i, 'text-size': 12, 'text-letter-spacing': .25 },
          paint: { 'text-color': C.waterLabel, 'text-halo-color': C.water, 'text-halo-width': 1 } },
        { id: 'l-park', type: 'symbol', source: 'ofm', 'source-layer': 'poi', minzoom: 14, filter: ['all', ['==', ['get', 'class'], 'park'], ['<=', ['coalesce', ['get', 'rank'], 99], 20], CLEAN],
          layout: { 'text-field': NAME, 'text-font': F.i, 'text-size': 11, 'text-letter-spacing': .08, 'text-max-width': 8 },
          paint: { 'text-color': C.parkLabel, 'text-halo-color': C.bg, 'text-halo-width': 1.2 } },
        { id: 'l-road', type: 'symbol', source: 'ofm', 'source-layer': 'transportation_name', minzoom: 14.5,
          filter: ['all', ['in', ['get', 'class'], ['literal', ['minor', 'tertiary', 'secondary', 'primary', 'trunk']]], CLEAN],
          layout: { 'symbol-placement': 'line', 'text-field': NAME, 'text-font': F.r, 'text-size': z(14.5, 9.5, 18, 12), 'text-letter-spacing': .04 },
          paint: { 'text-color': C.road, 'text-halo-color': C.bg, 'text-halo-width': 1.4 } },
        { id: 'l-place', type: 'symbol', source: 'ofm', 'source-layer': 'place', minzoom: 11.5,
          filter: ['all', ['in', ['get', 'class'], ['literal', ['suburb', 'quarter', 'neighbourhood', 'town', 'village']]], CLEAN],
          layout: { 'text-field': ['upcase', NAME], 'text-font': F.b, 'text-size': z(12, 9.5, 16, 12), 'text-letter-spacing': .22, 'text-max-width': 9 },
          paint: { 'text-color': C.label, 'text-opacity': .78, 'text-halo-color': C.bg, 'text-halo-width': 1.4 } }
      ]
    };
  }

  // ------------------------------------------------------------------
  let map = null, data = null, box = null, state = 'idle', active = null, revealed = false;
  const markers = {};
  function webgl() {
    try { const c = document.createElement('canvas'); return !!(window.WebGLRenderingContext && (c.getContext('webgl2') || c.getContext('webgl'))); }
    catch (e) { return false; }
  }
  const css = href => new Promise((res, rej) => {
    if (document.querySelector(`link[href="${href}"]`)) return res();
    const l = document.createElement('link'); l.rel = 'stylesheet'; l.href = href; l.crossOrigin = 'anonymous';
    l.onload = res; l.onerror = rej; document.head.appendChild(l);
  });
  const js = src => new Promise((res, rej) => {
    if (window.maplibregl) return res();
    const s = document.createElement('script'); s.src = src; s.async = true; s.crossOrigin = 'anonymous';
    s.onload = res; s.onerror = rej; document.head.appendChild(s);
  });
  const placeOf = id => data && data.places.find(p => p.id === id);
  const walk = p => p.mode === 'door' ? 'at the door' : p.mode === 'walk' ? `about ${p.walk_min} min on foot${p.bridge ? ', by ' + p.bridge : ''}` : `${p.straight_km} km across the river, straight line`;

  // the camera that frames every place, as the static picture shows it
  function overview(m) {
    const pts = [[data.site.lon, data.site.lat], ...data.places.map(p => [p.lon, p.lat])];
    const b = pts.reduce((a, p) => a.extend(p), new maplibregl.LngLatBounds(pts[0], pts[0]));
    const w = m.getContainer().clientWidth;
    const pad = w < 600 ? { top: 70, bottom: 40, left: 30, right: 30 } : { top: 110, bottom: 70, left: 90, right: 90 };
    const cam = m.cameraForBounds(b, { padding: pad, bearing: -14 }) || { center: [-0.165, 51.472], zoom: 13.6 };
    return { center: cam.center, zoom: Math.min(15, cam.zoom), bearing: -14, pitch: 38 };
  }

  function addMarkers(m) {
    const site = document.createElement('div');
    site.className = 'mk-site';
    site.setAttribute('role', 'img');
    site.setAttribute('aria-label', 'Nest Battersea, 38 Lombard Road');
    site.innerHTML = '<span class="mk-pulse"></span><span class="mk-dot"></span><span class="mk-lbl">Nest Battersea</span>';
    new maplibregl.Marker({ element: site, anchor: 'center' }).setLngLat([data.site.lon, data.site.lat]).addTo(m);
    data.places.forEach((p, i) => {
      const b = document.createElement('button');
      b.type = 'button'; b.className = 'mk'; b.dataset.place = p.id;
      b.setAttribute('aria-label', `${p.name}, ${walk(p)}`);
      b.innerHTML = `${i + 1}<span>${p.name} · ${p.mode === 'walk' ? p.walk_min + ' min walk' : p.mode === 'door' ? 'at the door' : p.straight_km + ' km'}</span>`;
      // a place on the section map opens the map page on that place
      b.addEventListener('click', e => { e.stopPropagation(); location.href = `map.html#place=${p.id}`; });
      b.addEventListener('pointerenter', () => { if (!active) b.classList.add('on'); });
      b.addEventListener('pointerleave', () => { if (active !== p.id) b.classList.remove('on'); });
      markers[p.id] = new maplibregl.Marker({ element: b, anchor: 'center' }).setLngLat([p.lon, p.lat]).addTo(m);
    });
  }

  function addLayers(m) {
    m.addSource('tpath', { type: 'geojson', data: { type: 'Feature', properties: {}, geometry: data.thamesPath } });
    m.addLayer({ id: 'tpath', type: 'line', source: 'tpath', layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': C.blue, 'line-opacity': .75, 'line-width': z(12, 1, 16, 2.2), 'line-dasharray': [0.1, 2.2] } });
    m.addSource('route', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
    m.addLayer({ id: 'route-glow', type: 'line', source: 'route', layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': C.blue, 'line-width': 10, 'line-blur': 7, 'line-opacity': .35 } });
    m.addLayer({ id: 'route', type: 'line', source: 'route', filter: ['!=', ['get', 'mode'], 'line'], layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': C.blueHi, 'line-width': 3 } });
    // across the river there is no walk: a dashed straight line
    m.addLayer({ id: 'route-line', type: 'line', source: 'route', filter: ['==', ['get', 'mode'], 'line'], layout: { 'line-cap': 'round' },
      paint: { 'line-color': C.blueHi, 'line-width': 2.5, 'line-dasharray': [1.2, 1.8] } });
  }

  // a place chosen in the list or on the map: its walk is drawn and framed
  function select(id) {
    active = id;
    document.querySelectorAll('#placelist [data-place]').forEach(x => x.classList.toggle('on', x.dataset.place === id));
    Object.entries(markers).forEach(([k, mk]) => mk.getElement().classList.toggle('on', k === id));
    // before the style has loaded there is no route source yet: the choice is kept in `active`
    // and drawn once the map is ready (boot calls select(active) then)
    if (!map || state !== 'ready' || !map.getSource('route')) return;
    const p = id && placeOf(id), src = map.getSource('route');
    const dur = reduced ? 0 : 1400;
    if (!p) { src.setData({ type: 'FeatureCollection', features: [] }); map.easeTo({ ...overview(map), duration: dur }); return; }
    const site = [data.site.lon, data.site.lat];
    const line = p.route && p.route.length > 1 ? p.route : [site, [p.lon, p.lat]];
    src.setData({ type: 'Feature', properties: { mode: p.mode }, geometry: { type: 'LineString', coordinates: p.mode === 'door' ? [] : line } });
    const all = p.mode === 'door' ? [site, [p.lon, p.lat]] : [site, ...line, [p.lon, p.lat]];
    const b = all.reduce((a, q) => a.extend(q), new maplibregl.LngLatBounds(all[0], all[0]));
    const w = map.getContainer().clientWidth, pad = w < 600 ? 60 : 120;
    const cam = map.cameraForBounds(b, { padding: pad, bearing: -14 });
    if (cam) map.easeTo({ center: cam.center, zoom: Math.min(p.mode === 'door' ? 16.4 : 16, cam.zoom), bearing: -14, pitch: 45, duration: dur });
  }

  async function boot() {
    if (state !== 'idle') return;
    state = 'loading';
    if (!webgl()) { state = 'static'; return; }
    try {
      const [, , d] = await Promise.all([css(LIB + 'maplibre-gl.css'), js(LIB + 'maplibre-gl.js'),
        fetch('assets/site/map/places.json').then(r => { if (!r.ok) throw new Error('places'); return r.json(); })]);
      data = d;
      const gl = document.createElement('div');
      gl.className = 'map-gl';
      box.appendChild(gl);
      map = new maplibregl.Map({
        container: gl, style: style(), center: [data.site.lon, data.site.lat], zoom: 13.6, pitch: 38, bearing: -14,
        cooperativeGestures: true, attributionControl: false, maxPitch: 60, minZoom: 11.5, maxZoom: 18,
        maxBounds: [[-0.32, 51.40], [-0.02, 51.54]], fadeDuration: 0, dragRotate: true, touchPitch: false
      });
      map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'top-right');
      map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right');
      map.jumpTo(overview(map));
      const fail = setTimeout(() => { if (state !== 'ready') { state = 'static'; gl.remove(); } }, 15000);
      map.on('error', () => { if (state === 'loading' && !map.isStyleLoaded()) { /* tiles retry; the timer decides */ } });
      // a click (not a drag) anywhere on the section map opens the full map page
      map.on('click', () => { location.href = active ? `map.html#place=${active}` : 'map.html'; });
      map.on('load', () => {
        addLayers(map);
        addMarkers(map);
        map.once('idle', () => {
          clearTimeout(fail);
          if (state !== 'loading') return;
          state = 'ready';
          box.classList.add('ready');
          if (active) select(active);
          seen();
        });
      });
      addEventListener('resize', () => { if (map && !active) map.jumpTo(overview(map)); });
    } catch (e) {
      state = 'static';
    }
  }
  // the first time the live map is in full view: a slow settle of the camera
  function seen() {
    if (revealed || reduced || !map) return;
    const r = box.getBoundingClientRect();
    if (r.top > innerHeight * .35 || r.bottom < innerHeight * .4) return;
    revealed = true;
    if (active) return;
    const o = overview(map);
    map.jumpTo({ ...o, bearing: o.bearing + 14, pitch: 22, zoom: o.zoom - .35 });
    map.easeTo({ ...o, duration: 3200, easing: t => 1 - Math.pow(1 - t, 3) });
  }

  function init() {
    box = document.getElementById('map');
    if (!box) return;
    if (!('IntersectionObserver' in window)) return boot();
    // load only when the section comes near: about a screen and a half ahead
    const io = new IntersectionObserver(es => {
      if (es.some(e => e.isIntersecting)) { io.disconnect(); boot(); }
    }, { rootMargin: '1200px 0px' });
    io.observe(box);
    addEventListener('scroll', () => { if (state === 'ready' && !revealed) seen(); }, { passive: true });
  }

  return { init, focus: select, state: () => state, map: () => map, style };
})();
window.MapView = MapView;
// js/app.js adds this script when the Location section comes near, usually long after the page loaded
if (document.readyState === 'loading') addEventListener('DOMContentLoaded', () => MapView.init());
else MapView.init();
