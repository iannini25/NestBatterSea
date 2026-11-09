/* ============================================================
   NEST BATTERSEA — interaction
   States: facade -> flight -> residence -> (interior | plan)
   The flight is a real rendered camera move. Going back plays
   the reversed render, so the camera retraces its own path.
   ============================================================ */
const App = (() => {

const IW = 4096, IH = 2294;      // master facade render
const $  = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];
const NS = 'http://www.w3.org/2000/svg';

const el = {
  boot:$('#boot'), fill:$('#boot .fill'), pc:$('#pc'),
  facade:$('#facade'), frame:$('#facade .frame'), tower:$('#towerimg'),
  masks:$('#masks'), hot:$('#hotspots'),
  flight:$('#flight'), vid:$('#vid'),
  still:$('#still'), stillimg:$('#stillimg'),
  gallery:$('#gallery'), plan:$('#plan'), sheet:$('#sheet'), planimg:$('#planimg'),
  hero:$('#hero'), rail:$('#rail'), railitems:$('#railitems'),
  top:$('#top'), bot:$('#bot'), tag:$('#tag'),
  panel:$('#panel'), back:$('#back'), backlbl:$('#backlbl'),
  capbar:$('#capbar'), dots:$('#dots'),
  scrim:$('#scrim')
};

let state = 'boot';      // boot | facade | flight | residence | interior | plan
let cur   = null;        // current residence
let shotI = 0;
let planI = 0;
let base  = {};          // cover-fit transform of the facade

/* ---------- preload ------------------------------------------------ */
const CRITICAL = [
  'assets/facade/tower-2k.jpg',
  'assets/facade/arrive-loft4.jpg',
  'assets/facade/arrive-bung3.jpg',
  'assets/interiors/living.jpg'
];

function preload(){
  let done = 0;
  const total = CRITICAL.length;
  const step = () => {
    done++;
    const p = Math.round(done/total*100);
    el.pc.textContent = p;
    gsap.to(el.fill, {width:p+'%', duration:.5, ease:'power2.out'});
    if (done === total) setTimeout(start, 420);
  };
  CRITICAL.forEach(src => {
    const i = new Image();
    i.onload = i.onerror = step;
    i.src = src;
  });
  // videos warm up in the background, they are not blocking
  RESIDENCES.forEach(r => {
    const v = document.createElement('video');
    v.preload = 'auto'; v.muted = true; v.src = r.flight;
  });
}

/* ---------- facade framing ------------------------------------------ */
function layout(){
  const vw = innerWidth, vh = innerHeight;
  const s  = Math.max(vw/IW, vh/IH);
  base = { s, x:(vw-IW*s)/2, y:(vh-IH*s)/2, vw, vh };
  gsap.set(el.frame, {x:base.x, y:base.y, scale:s, transformOrigin:'0 0',
                      width:IW, height:IH});
}

/* ---------- hotspots ------------------------------------------------ */
function pts(p){ return p.map(a=>a.join(',')).join(' '); }

function buildHotspots(){
  LET.forEach(u => {
    const g = document.createElementNS(NS,'g');
    const dark = document.createElementNS(NS,'polygon');
    dark.setAttribute('points', pts(u.poly));
    dark.setAttribute('fill','#05070B');
    dark.setAttribute('opacity','.66');
    g.appendChild(dark);
    const hit = document.createElementNS(NS,'polygon');
    hit.setAttribute('points', pts(u.poly));
    hit.setAttribute('fill','transparent');
    hit.style.cursor = 'default';
    g.appendChild(hit);
    bindTag(hit, u.name, 'Let', true);
    el.hot.appendChild(g);
  });

  RESIDENCES.forEach(r => {
    const g = document.createElementNS(NS,'g');
    g.style.cursor = 'pointer';

    const glow = document.createElementNS(NS,'polygon');
    glow.setAttribute('points', pts(r.poly));
    glow.setAttribute('fill','#FFE2B0');
    glow.setAttribute('filter','url(#soft)');
    glow.setAttribute('opacity','.22');

    const lit = document.createElementNS(NS,'polygon');
    lit.setAttribute('points', pts(r.poly));
    lit.setAttribute('fill','#FFD9A0');
    lit.setAttribute('opacity','.10');

    const edge = document.createElementNS(NS,'polygon');
    edge.setAttribute('points', pts(r.poly));
    edge.setAttribute('fill','none');
    edge.setAttribute('stroke','#92B7CA');
    edge.setAttribute('stroke-width','2');
    edge.setAttribute('vector-effect','non-scaling-stroke');
    edge.setAttribute('opacity','0');

    const hit = document.createElementNS(NS,'polygon');
    hit.setAttribute('points', pts(r.poly));
    hit.setAttribute('fill','transparent');

    g.append(glow, lit, edge, hit);
    el.hot.appendChild(g);
    r._g = {glow, lit, edge};

    gsap.to(glow, {opacity:.40, duration:2.8, repeat:-1, yoyo:true,
                   ease:'sine.inOut', delay:Math.random()*1.8});

    bindTag(hit, r.name, r.type, false, r);

    hit.addEventListener('pointerenter', () => {
      if (state !== 'facade') return;
      gsap.to(edge, {opacity:1, duration:.4});
      gsap.to(lit,  {opacity:.26, duration:.4});
      markRail(r.id, true);
    });
    hit.addEventListener('pointerleave', () => {
      gsap.to(edge, {opacity:0, duration:.4});
      gsap.to(lit,  {opacity:.10, duration:.4});
      markRail(r.id, false);
    });
    hit.addEventListener('click', () => { if (state === 'facade') fly(r); });
  });
}

function bindTag(node, title, sub, let_, r){
  node.addEventListener('pointerenter', () => {
    if (state !== 'facade') return;
    el.tag.querySelector('.t').textContent = title;
    const s = el.tag.querySelector('.s');
    s.textContent = sub;
    s.className = 's mono' + (let_ ? ' sold' : '');
    gsap.to(el.tag, {opacity:1, duration:.28});
  });
  node.addEventListener('pointerleave', () =>
    gsap.to(el.tag, {opacity:0, duration:.2}));
}

addEventListener('pointermove', e => {
  el.tag.style.left = e.clientX + 'px';
  el.tag.style.top  = e.clientY + 'px';
});

/* ---------- rail ---------------------------------------------------- */
function buildRail(){
  el.railitems.innerHTML = RESIDENCES.map(r => `
    <button class="item" data-id="${r.id}">
      <span class="r1"><span class="nm">${r.name}</span>
      <span class="ar">${r.interior}</span></span>
      <span class="r2">${r.beds} · ${r.tier}</span>
    </button>`).join('');
  $$('#rail .item').forEach(b => {
    const r = RESIDENCES.find(x => x.id === b.dataset.id);
    b.addEventListener('click', () => { if (state === 'facade') fly(r); });
    b.addEventListener('pointerenter', () => {
      if (state !== 'facade') return;
      gsap.to(r._g.edge, {opacity:1, duration:.4});
      gsap.to(r._g.lit,  {opacity:.26, duration:.4});
    });
    b.addEventListener('pointerleave', () => {
      gsap.to(r._g.edge, {opacity:0, duration:.4});
      gsap.to(r._g.lit,  {opacity:.10, duration:.4});
    });
  });
}
function markRail(id, on){
  const b = document.querySelector(`#rail .item[data-id="${id}"]`);
  if (b) b.classList.toggle('sel', on);
}

/* ---------- intro --------------------------------------------------- */
function start(){
  state = 'facade';
  layout();
  gsap.to(el.boot, {opacity:0, duration:.8, ease:'power2.inOut',
    onComplete:() => el.boot.style.display = 'none'});

  const tl = gsap.timeline({delay:.15});
  tl.to(el.facade, {opacity:1, duration:1.6, ease:'power2.out'}, 0)
    .fromTo(el.frame, {scale:base.s*1.07}, {scale:base.s, duration:2.6, ease:'power2.out'}, 0)
    .fromTo('#top',   {opacity:0, y:-16}, {opacity:1, y:0, duration:.9}, .5)
    .fromTo('#bot',   {opacity:0, y:16},  {opacity:1, y:0, duration:.9}, .6)
    .fromTo('#hero .eyebrow', {opacity:0, y:12}, {opacity:1, y:0, duration:.8}, .7)
    .fromTo('#hero h1 .ln i', {yPercent:110}, {yPercent:0, duration:1.1,
             ease:'power3.out', stagger:.08}, .8)
    .fromTo('#hero p', {opacity:0, y:12}, {opacity:1, y:0, duration:.8}, 1.3)
    .set(el.rail, {visibility:'visible'}, 1.2)
    .fromTo(el.rail, {opacity:0, x:26}, {opacity:1, x:0, duration:.9}, 1.2)
    .fromTo(el.hot,  {opacity:0}, {opacity:1, duration:1.4}, 1.0);
}

/* ---------- the flight ---------------------------------------------- */
function playVideo(src, onEnd){
  return new Promise(res => {
    const v = el.vid;
    v.onended = onEnd;              // set BEFORE src; never clobbered
    v.src = src;
    v.currentTime = 0;
    let fired = false;
    const go = () => {
      if (fired) return; fired = true;
      v.play().catch(()=>{});
      res();
    };
    if (v.readyState >= 3) go();
    else {
      v.addEventListener('canplay', go, {once:true});
      v.addEventListener('loadeddata', go, {once:true});
      setTimeout(go, 2500);         // safety: never strand the user
    }
    // safety net: if 'ended' never fires, finish on duration
    v.addEventListener('timeupdate', function tick(){
      if (v.duration && v.currentTime >= v.duration - 0.06){
        v.removeEventListener('timeupdate', tick);
        if (typeof onEnd === 'function') onEnd();
      }
    });
  });
}

function fly(r){
  cur = r; state = 'flight';
  gsap.to(el.tag, {opacity:0, duration:.2});

  // chrome out
  gsap.to([el.hero, el.rail, el.bot], {opacity:0, duration:.55, ease:'power2.in',
    pointerEvents:'none'});
  gsap.to(el.top, {opacity:0, y:-14, duration:.55, pointerEvents:'none'});
  gsap.to(el.hot, {opacity:0, duration:.45});

  // hand over from the still facade to the rendered flight.
  // the video's first frame IS the facade render, so the cut is invisible.
  gsap.set(el.flight, {visibility:'visible'});
  let landed = false;
  const onArrive = () => { if (landed) return; landed = true; arrive(r); };
  playVideo(r.flight, onArrive).then(() => {
    gsap.to(el.flight, {opacity:1, duration:.35, ease:'none'});
    gsap.to(el.facade, {opacity:0, duration:.35, delay:.35});
  });
  gsap.to(el.scrim, {opacity:.5, duration:1.2});
}

function arrive(r){
  state = 'residence';
  // the still is the video's own final frame -> zero jump
  el.stillimg.src = r.arrive;
  gsap.set(el.still, {visibility:'visible', opacity:1});
  gsap.to(el.flight, {opacity:0, duration:.3, delay:.05,
    onComplete:() => gsap.set(el.flight, {visibility:'hidden'})});
  gsap.to(el.scrim, {opacity:1, duration:.6});

  fillPanel(r);
  gsap.set([el.panel, el.back], {visibility:'visible'});
  gsap.fromTo(el.back,  {opacity:0, x:-14}, {opacity:1, x:0, duration:.6, delay:.15});
  gsap.fromTo(el.panel, {opacity:0, x:34},  {opacity:1, x:0, duration:.8, delay:.25,
    ease:'power3.out'});
  el.backlbl.textContent = 'Back to the tower';
}

function fillPanel(r){
  $('#p-kick').textContent = r.status === 'available' ? 'Available' : 'Let';
  $('#p-name').textContent = r.name;
  $('#p-sub').textContent  = `${r.type} · ${r.ref}`;
  $('#specs').innerHTML = r.specs.map(([k,v,alt]) => `
    <div class="row"><span class="k">${k}</span>
    <span class="v">${v}${alt ? `<em>${alt}</em>` : ''}</span></div>`).join('');
  $('#p-fine').textContent = FINE;
}

/* ---------- interiors ------------------------------------------------ */
function inside(){
  if (!cur) return;
  state = 'interior'; shotI = 0;

  el.gallery.innerHTML = cur.shots.map((s,i) => `
    <figure class="shot" data-i="${i}"><img src="${s.src}" alt="${s.t}"></figure>`).join('');
  el.dots.innerHTML = cur.shots.map((_,i) =>
    `<span class="${i===0?'on':''}"></span>`).join('');
  $('#cap-n').textContent = String(cur.shots.length).padStart(2,'0');

  gsap.set(el.gallery, {visibility:'visible'});
  gsap.to(el.gallery, {opacity:1, duration:.8, ease:'power2.inOut'});
  gsap.to(el.panel, {opacity:0, x:26, duration:.5,
    onComplete:() => gsap.set(el.panel, {visibility:'hidden'})});
  gsap.set(el.capbar, {visibility:'visible'});
  gsap.fromTo(el.capbar, {opacity:0, y:18}, {opacity:1, y:0, duration:.7, delay:.35});
  el.backlbl.textContent = 'Back to the window';
  showShot(0, true);
}

function showShot(i, instant){
  const figs = $$('#gallery .shot');
  if (!figs.length) return;
  figs.forEach((f,ix) => {
    gsap.to(f, {opacity: ix===i ? 1 : 0, duration: instant ? 0 : .9, ease:'power2.inOut'});
    if (ix === i) gsap.fromTo(f.querySelector('img'),
      {scale:1.07}, {scale:1, duration: instant ? 1.6 : 2.4, ease:'power2.out'});
  });
  $('#cap-i').textContent = String(i+1).padStart(2,'0');
  const t = $('#cap-t');
  gsap.fromTo(t, {opacity:0, y:12}, {opacity:1, y:0, duration:.55,
    onStart:() => t.textContent = cur.shots[i].t});
  $$('#dots span').forEach((d,ix) => d.classList.toggle('on', ix===i));
}

function shot(dir){
  if (state !== 'interior') return;
  shotI = (shotI + dir + cur.shots.length) % cur.shots.length;
  showShot(shotI);
}

/* ---------- plan ----------------------------------------------------- */
function plan(){
  if (!cur) return;
  state = 'plan'; planI = 0;

  $('#plan-name').textContent = cur.name;
  $('#plan-sub').textContent  = `${cur.type} · ${cur.ref}`;
  $('#plan-rows').innerHTML = cur.specs.map(([k,v]) => `
    <div class="rw"><span class="k">${k}</span><span class="v">${v}</span></div>`).join('');
  $('#plan-toggle').innerHTML = cur.plans.map((p,i) =>
    `<button class="${i===0?'on':''}" data-i="${i}">${p.label}</button>`).join('');
  $$('#plan-toggle button').forEach(b =>
    b.addEventListener('click', () => setPlan(+b.dataset.i)));
  setPlan(0, true);

  gsap.set(el.plan, {visibility:'visible'});
  gsap.to(el.plan, {opacity:1, duration:.7, ease:'power2.inOut'});
  gsap.to(el.panel, {opacity:0, x:26, duration:.5,
    onComplete:() => gsap.set(el.panel, {visibility:'hidden'})});
  gsap.fromTo(el.sheet,
    {rotateX:62, rotateZ:-28, y:90, opacity:0, scale:.88},
    {rotateX:26, rotateZ:-12, y:0, opacity:1, scale:1,
     duration:1.5, ease:'power3.out'});
  gsap.fromTo('#plan .meta > *', {opacity:0, y:22},
    {opacity:1, y:0, duration:.75, stagger:.07, delay:.45, ease:'power3.out'});
  el.backlbl.textContent = 'Back to the window';
}

function setPlan(i, instant){
  planI = i;
  $$('#plan-toggle button').forEach((b,ix) => b.classList.toggle('on', ix===i));
  if (instant){ el.planimg.src = cur.plans[i].src; return; }
  gsap.to(el.planimg, {opacity:0, duration:.28, onComplete:() => {
    el.planimg.src = cur.plans[i].src;
    gsap.to(el.planimg, {opacity:1, duration:.4});
  }});
}

/* drag to rotate the plan — the dollhouse feel, without a 3D engine */
(function dragPlan(){
  let on=false, sx=0, sy=0, rx=26, rz=-12, brx=26, brz=-12;
  const set = () => gsap.to(el.sheet, {rotateX:rx, rotateZ:rz,
                     duration:.7, ease:'power3.out'});
  const down = e => { if (state!=='plan') return; on=true;
    const p = e.touches ? e.touches[0] : e; sx=p.clientX; sy=p.clientY; brx=rx; brz=rz; };
  const move = e => { if(!on) return;
    const p = e.touches ? e.touches[0] : e;
    rz = Math.max(-60, Math.min(36, brz + (p.clientX-sx)*.22));
    rx = Math.max(2,  Math.min(70, brx + (p.clientY-sy)*.22));
    set(); };
  const up = () => on=false;
  el.plan.addEventListener('pointerdown', down);
  addEventListener('pointermove', move);
  addEventListener('pointerup', up);
})();

/* ---------- back ----------------------------------------------------- */
function back(){
  if (state === 'interior'){
    state = 'residence';
    gsap.to(el.capbar, {opacity:0, y:14, duration:.45,
      onComplete:() => gsap.set(el.capbar, {visibility:'hidden'})});
    gsap.to(el.gallery, {opacity:0, duration:.7,
      onComplete:() => gsap.set(el.gallery, {visibility:'hidden'})});
    gsap.set(el.panel, {visibility:'visible'});
    gsap.fromTo(el.panel, {opacity:0, x:30}, {opacity:1, x:0, duration:.7, delay:.2});
    el.backlbl.textContent = 'Back to the tower';
    return;
  }
  if (state === 'plan'){
    state = 'residence';
    gsap.to(el.sheet, {rotateX:62, rotateZ:-28, y:70, opacity:0, scale:.9, duration:.7});
    gsap.to(el.plan, {opacity:0, duration:.6, delay:.1,
      onComplete:() => gsap.set(el.plan, {visibility:'hidden'})});
    gsap.set(el.panel, {visibility:'visible'});
    gsap.fromTo(el.panel, {opacity:0, x:30}, {opacity:1, x:0, duration:.7, delay:.25});
    el.backlbl.textContent = 'Back to the tower';
    return;
  }
  if (state === 'residence'){
    // fly out: the reversed render retraces the exact path in
    state = 'flight';
    gsap.to([el.panel, el.back], {opacity:0, duration:.4,
      onComplete:() => gsap.set([el.panel, el.back], {visibility:'hidden'})});

    gsap.set(el.flight, {visibility:'visible'});
    let done = false;
    const onLand = () => { if (done) return; done = true; land(); };
    playVideo(cur.flightRev, onLand).then(() => {
      gsap.to(el.flight, {opacity:1, duration:.25});
      gsap.to(el.still,  {opacity:0, duration:.25, delay:.25,
        onComplete:() => gsap.set(el.still, {visibility:'hidden'})});
    });
  }
}

function land(){
  state = 'facade';
  gsap.set(el.facade, {opacity:1});
  layout();
  gsap.to(el.flight, {opacity:0, duration:.35,
    onComplete:() => gsap.set(el.flight, {visibility:'hidden'})});
  gsap.to(el.scrim, {opacity:1, duration:.6});
  gsap.to([el.hero, el.rail, el.bot], {opacity:1, duration:.8, delay:.2,
    pointerEvents:'auto'});
  gsap.to(el.top, {opacity:1, y:0, duration:.8, delay:.2, pointerEvents:'auto'});
  gsap.to(el.hot, {opacity:1, duration:.9, delay:.3});
  cur = null;
}

function home(){ if (state !== 'facade') back(); }
function enquire(){
  alert('Demo — this is where the enquiry form or the agent\'s WhatsApp would open.');
}

/* ---------- wiring --------------------------------------------------- */
addEventListener('resize', () => { if (state === 'facade') layout(); });
addEventListener('keydown', e => {
  if (e.key === 'Escape' && state !== 'facade' && state !== 'flight') back();
  if (state === 'interior'){
    if (e.key === 'ArrowRight') shot(1);
    if (e.key === 'ArrowLeft')  shot(-1);
  }
});

addEventListener('DOMContentLoaded', () => {
  buildHotspots();
  buildRail();
  layout();
  preload();
});

return { back, inside, plan, shot, home, enquire };
})();
