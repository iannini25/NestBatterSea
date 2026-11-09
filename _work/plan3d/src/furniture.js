// Procedural furniture for the dollhouse, in metres.
// Every builder returns a Group with its base at y = 0, centred on the origin,
// width along X, depth along Z and the front facing +Z.
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { M, PALETTE } from './materials.js';

const TILE = new Map(); // metres per texture tile, by material
export function tileOf(mat) { return TILE.get(mat) || mat.userData.tile || 1; }
export function setTile(mat, metres) { mat.userData.tile = metres; }

// Box with UVs in real-world metres so wood grain and stone keep their scale
export function boxGeo(w, h, d, tile = 1) {
  const g = new THREE.BoxGeometry(w, h, d);
  const uv = g.attributes.uv;
  const dims = [[d, h], [d, h], [w, d], [w, d], [w, h], [w, h]];
  for (let f = 0; f < 6; f++) {
    for (let k = 0; k < 4; k++) {
      const i = f * 4 + k;
      uv.setXY(i, uv.getX(i) * dims[f][0] / tile, uv.getY(i) * dims[f][1] / tile);
    }
  }
  return g;
}

export function box(parent, w, h, d, mat, x = 0, y = 0, z = 0, opts = {}) {
  const m = new THREE.Mesh(boxGeo(w, h, d, mat.userData.tile || 1), mat);
  m.position.set(x, y + h / 2, z);
  m.castShadow = opts.cast !== false;
  m.receiveShadow = true;
  if (opts.ry) m.rotation.y = opts.ry;
  parent.add(m);
  return m;
}

export function rbox(parent, w, h, d, r, mat, x = 0, y = 0, z = 0, opts = {}) {
  const m = new THREE.Mesh(new RoundedBoxGeometry(w, h, d, 3, Math.min(r, w / 2, h / 2, d / 2) * 0.999), mat);
  m.position.set(x, y + h / 2, z);
  m.castShadow = opts.cast !== false;
  m.receiveShadow = true;
  if (opts.rx) m.rotation.x = opts.rx;
  if (opts.rz) m.rotation.z = opts.rz;
  parent.add(m);
  return m;
}

export function cyl(parent, rt, rb, h, mat, x = 0, y = 0, z = 0, seg = 28) {
  const m = new THREE.Mesh(new THREE.CylinderGeometry(rt, rb, h, seg), mat);
  m.position.set(x, y + h / 2, z);
  m.castShadow = true;
  m.receiveShadow = true;
  parent.add(m);
  return m;
}

function seeded(seed) {
  let s = seed >>> 0;
  return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
}

// ---------- living ----------
export function sofa(w = 2.3, d = 0.9, mat = M.boucle()) {
  const g = new THREE.Group();
  const base = 0.1, seatH = 0.44, backH = 0.8, arm = 0.2;
  box(g, w - 0.06, base, d - 0.06, M.charcoal(), 0, 0, 0);
  rbox(g, w, seatH - base - 0.12, d, 0.05, mat, 0, base, 0);
  const n = w > 1.9 ? 3 : 2;
  const cw = (w - arm * 2) / n;
  for (let i = 0; i < n; i++) {
    const x = -w / 2 + arm + cw * (i + 0.5);
    rbox(g, cw - 0.015, 0.14, d - 0.3, 0.06, mat, x, seatH - 0.14, 0.11);
    rbox(g, cw - 0.03, backH - seatH + 0.06, 0.2, 0.08, mat, x, seatH - 0.08, -d / 2 + 0.17, { rx: -0.12 });
  }
  rbox(g, w, backH - base - 0.12, 0.16, 0.06, mat, 0, base + 0.08, -d / 2 + 0.08);
  rbox(g, arm, 0.52, d, 0.07, mat, -w / 2 + arm / 2, base + 0.04, 0);
  rbox(g, arm, 0.52, d, 0.07, mat, w / 2 - arm / 2, base + 0.04, 0);
  // two scatter cushions
  rbox(g, 0.42, 0.4, 0.13, 0.06, M.sage(), -w / 2 + arm + 0.28, seatH - 0.02, -d / 2 + 0.33, { rz: 0.12 });
  rbox(g, 0.4, 0.38, 0.13, 0.06, M.rust(), w / 2 - arm - 0.28, seatH - 0.02, -d / 2 + 0.33, { rz: -0.1 });
  return g;
}

export function armchair(mat = M.oat()) {
  const g = new THREE.Group();
  const w = 0.78, d = 0.8;
  box(g, 0.04, 0.38, 0.04, M.oakDark(), -0.33, 0, 0.33); box(g, 0.04, 0.38, 0.04, M.oakDark(), 0.33, 0, 0.33);
  box(g, 0.04, 0.38, 0.04, M.oakDark(), -0.33, 0, -0.33); box(g, 0.04, 0.38, 0.04, M.oakDark(), 0.33, 0, -0.33);
  rbox(g, w, 0.16, d, 0.06, mat, 0, 0.3, 0.02);
  rbox(g, w, 0.48, 0.16, 0.07, mat, 0, 0.42, -d / 2 + 0.08, { rx: -0.16 });
  rbox(g, 0.12, 0.26, d - 0.1, 0.05, mat, -w / 2 + 0.06, 0.42, 0.02);
  rbox(g, 0.12, 0.26, d - 0.1, 0.05, mat, w / 2 - 0.06, 0.42, 0.02);
  return g;
}

export function coffeeRound(dia = 1.0) {
  const g = new THREE.Group();
  cyl(g, dia * 0.28, dia * 0.32, 0.3, M.stone(), 0, 0, 0, 40);
  cyl(g, dia / 2, dia / 2, 0.06, M.stone(), 0, 0.3, 0, 56);
  // books and a bowl
  box(g, 0.24, 0.035, 0.17, M.linen(), 0.12, 0.36, 0.06, { ry: 0.3 });
  box(g, 0.22, 0.03, 0.16, M.rust(), 0.12, 0.395, 0.06, { ry: 0.22 });
  cyl(g, 0.11, 0.07, 0.07, M.ceramic(), -0.18, 0.36, -0.08, 24);
  return g;
}

export function rug(w, d, mat = M.rugWool()) {
  const g = new THREE.Group();
  const m = rbox(g, w, 0.014, d, 0.006, mat, 0, 0, 0, { cast: false });
  m.receiveShadow = true;
  return g;
}

export function bench(w = 1.6, d = 0.35) {
  const g = new THREE.Group();
  box(g, w, 0.05, d, M.oak(), 0, 0.38, 0);
  box(g, 0.05, 0.38, d - 0.04, M.oak(), -w / 2 + 0.06, 0, 0);
  box(g, 0.05, 0.38, d - 0.04, M.oak(), w / 2 - 0.06, 0, 0);
  rbox(g, w * 0.55, 0.07, d - 0.04, 0.03, M.oat(), -w * 0.15, 0.43, 0);
  return g;
}

export function console_(w = 1.4, d = 0.32) {
  const g = new THREE.Group();
  box(g, w, 0.04, d, M.oak(), 0, 0.78, 0);
  box(g, 0.04, 0.78, d, M.oak(), -w / 2 + 0.02, 0, 0);
  box(g, 0.04, 0.78, d, M.oak(), w / 2 - 0.02, 0, 0);
  box(g, w - 0.08, 0.03, d - 0.02, M.oak(), 0, 0.18, 0);
  cyl(g, 0.07, 0.05, 0.28, M.ceramic(), -w / 2 + 0.25, 0.82, 0, 20);
  box(g, 0.3, 0.05, 0.2, M.linen(), w / 2 - 0.3, 0.82, 0);
  return g;
}

export function floorLamp() {
  const g = new THREE.Group();
  cyl(g, 0.14, 0.16, 0.03, M.brass(), 0, 0, 0, 24);
  cyl(g, 0.012, 0.012, 1.45, M.brass(), 0, 0.03, 0, 8);
  cyl(g, 0.17, 0.23, 0.3, M.shade(), 0, 1.38, 0, 28);
  return g;
}

// ---------- dining and kitchen ----------
export function diningTable(w = 2.0, d = 0.9) {
  const g = new THREE.Group();
  box(g, w, 0.045, d, M.oak(), 0, 0.715, 0);
  const lx = w / 2 - 0.35;
  for (const sx of [-1, 1]) {
    box(g, 0.08, 0.7, d - 0.25, M.oak(), sx * lx, 0.015, 0);
    box(g, 0.1, 0.03, d - 0.15, M.oak(), sx * lx, 0, 0);
  }
  box(g, w - 0.8, 0.05, 0.06, M.oak(), 0, 0.6, 0);
  // a low bowl and a vase
  cyl(g, 0.2, 0.12, 0.08, M.ceramic(), 0.15, 0.76, 0, 32);
  cyl(g, 0.05, 0.07, 0.24, M.potDark(), -0.4, 0.76, 0.05, 16);
  return g;
}

export function chair() {
  const g = new THREE.Group();
  const w = 0.46, d = 0.5;
  for (const [x, z] of [[-0.19, 0.2], [0.19, 0.2], [-0.19, -0.2], [0.19, -0.2]]) box(g, 0.035, 0.45, 0.035, M.oak(), x, 0, z);
  rbox(g, w, 0.07, d, 0.03, M.oat(), 0, 0.43, 0);
  box(g, 0.035, 0.36, 0.035, M.oak(), -0.19, 0.47, -0.2);
  box(g, 0.035, 0.36, 0.035, M.oak(), 0.19, 0.47, -0.2);
  rbox(g, w - 0.02, 0.2, 0.05, 0.02, M.oak(), 0, 0.62, -0.22);
  return g;
}

export function stool() {
  const g = new THREE.Group();
  for (const a of [0, 1, 2, 3]) {
    const ang = a * Math.PI / 2 + Math.PI / 4;
    const leg = box(g, 0.025, 0.64, 0.025, M.oak(), Math.cos(ang) * 0.14, 0, Math.sin(ang) * 0.14);
    leg.rotation.z = Math.cos(ang) * 0.06;
    leg.rotation.x = -Math.sin(ang) * 0.06;
  }
  cyl(g, 0.19, 0.19, 0.05, M.oat(), 0, 0.64, 0, 28);
  return g;
}

export function island(w = 1.8, d = 0.9) {
  const g = new THREE.Group();
  box(g, w - 0.1, 0.06, d - 0.3, M.charcoal(), 0, 0, -0.08);
  box(g, w - 0.04, 0.84, d - 0.32, M.oak(), 0, 0.06, -0.09);
  box(g, w, 0.04, d, M.stone(), 0, 0.9, 0);
  // fruit bowl
  cyl(g, 0.17, 0.1, 0.07, M.ceramic(), 0.3, 0.94, -0.05, 28);
  return g;
}

// Kitchen run along its own X axis, length len, front facing +Z
export function kitchenRun({ len, depth = 0.62, tall = 0, sinkAt = 1, hobAt = 2, wallUnits = true, flip = false }) {
  const g = new THREE.Group();
  // s is the distance from the start of the run; flip runs it from the +X end
  const X = (s) => (flip ? len / 2 - s : -len / 2 + s);
  const mid = (a, b) => (X(a) + X(b)) / 2;
  if (tall > 0) {
    box(g, tall - 0.01, 2.35, depth, M.oak(), mid(0, tall), 0, 0);
    box(g, 0.012, 2.2, 0.01, M.oakDark(), mid(0, tall), 0.08, depth / 2 + 0.002);
  }
  const bw = len - tall;
  const bx = mid(tall, len);
  box(g, bw, 0.1, depth - 0.06, M.charcoal(), bx, 0, -0.03);
  box(g, bw, 0.78, depth - 0.02, M.oak(), bx, 0.1, -0.01);
  const doors = Math.max(2, Math.round(bw / 0.6));
  for (let i = 1; i < doors; i++) box(g, 0.006, 0.76, 0.006, M.oakDark(), X(tall + (bw * i) / doors), 0.11, depth / 2 - 0.005, { cast: false });
  box(g, bw, 0.035, depth, M.stone(), bx, 0.88, 0);
  const sx = X(sinkAt);
  box(g, 0.62, 0.012, 0.42, M.steel(), sx, 0.912, 0.02, { cast: false });
  box(g, 0.56, 0.01, 0.36, M.charcoal(), sx, 0.917, 0.02, { cast: false });
  cyl(g, 0.014, 0.014, 0.3, M.brass(), sx, 0.915, -depth / 2 + 0.1, 10);
  box(g, 0.02, 0.02, 0.2, M.brass(), sx, 1.2, -depth / 2 + 0.19);
  box(g, 0.78, 0.008, 0.5, M.blackGlass(), X(hobAt), 0.915, 0.02, { cast: false });
  box(g, bw, 0.6, 0.02, M.stone(), bx, 0.915, -depth / 2 + 0.01);
  if (wallUnits) {
    const uw = Math.min(bw, 2.6);
    box(g, uw, 0.7, 0.36, M.oak(), bx, 1.52, -depth / 2 + 0.18);
    box(g, 0.006, 0.68, 0.006, M.oakDark(), bx, 1.53, -depth / 2 + 0.365, { cast: false });
    box(g, uw - 0.02, 0.02, 0.3, M.bulb(), bx, 1.5, -depth / 2 + 0.17, { cast: false });
  }
  return g;
}

// ---------- bedrooms ----------
export function bed(w = 1.8, d = 2.05, single = false, throwTone) {
  const g = new THREE.Group();
  const frameH = 0.32;
  // the bed's head is at -Z, the foot faces +Z
  rbox(g, w + 0.06, frameH, d, 0.03, M.oat(), 0, 0.04, 0.02);
  box(g, w - 0.1, 0.04, d - 0.1, M.charcoal(), 0, 0, 0.02);
  rbox(g, w + 0.14, 1.05, 0.09, 0.04, M.oak(), 0, 0.02, -d / 2 - 0.02);
  rbox(g, w - 0.04, 0.2, d - 0.1, 0.06, M.linen(), 0, frameH, 0.02);
  // duvet folded back, a throw across the foot
  rbox(g, w + 0.04, 0.09, d * 0.72, 0.045, M.linen(), 0, frameH + 0.16, d * 0.13);
  rbox(g, w + 0.06, 0.05, 0.26, 0.025, M.linen(), 0, frameH + 0.22, d * 0.13 - d * 0.36 + 0.13);
  const tm = throwTone === 'sage' ? M.sage() : throwTone === 'oat' ? M.oat() : throwTone === 'rust' ? M.rust() : single ? M.sage() : M.rust();
  rbox(g, w + 0.08, 0.035, 0.48, 0.017, tm, 0, frameH + 0.245, d / 2 - 0.36);
  const pillows = single ? 1 : 2;
  const pw = (w - 0.2) / pillows;
  for (let i = 0; i < pillows; i++) {
    const x = -w / 2 + 0.1 + pw * (i + 0.5);
    rbox(g, pw - 0.06, 0.16, 0.36, 0.07, M.linen(), x, frameH + 0.18, -d / 2 + 0.3, { rx: -0.35 });
    rbox(g, pw - 0.14, 0.14, 0.12, 0.06, single ? M.oat() : M.sage(), x, frameH + 0.21, -d / 2 + 0.45, { rx: -0.2 });
  }
  return g;
}

export function nightstand() {
  const g = new THREE.Group();
  box(g, 0.48, 0.48, 0.4, M.oak(), 0, 0, 0);
  box(g, 0.44, 0.006, 0.006, M.oakDark(), 0, 0.3, 0.2, { cast: false });
  cyl(g, 0.06, 0.07, 0.2, M.ceramic(), 0.08, 0.48, -0.04, 20);
  cyl(g, 0.12, 0.15, 0.18, M.shade(), 0.08, 0.68, -0.04, 28);
  return g;
}

export function wardrobe(w = 1.2, d = 0.6) {
  const g = new THREE.Group();
  box(g, w, 2.35, d, M.oak(), 0, 0, 0);
  const n = Math.max(2, Math.round(w / 0.5));
  for (let i = 1; i < n; i++) box(g, 0.006, 2.25, 0.006, M.oakDark(), -w / 2 + (w * i) / n, 0.05, d / 2 + 0.001, { cast: false });
  return g;
}

export function desk(w = 1.2, d = 0.5) {
  const g = new THREE.Group();
  box(g, w, 0.035, d, M.oak(), 0, 0.72, 0);
  box(g, 0.035, 0.72, d - 0.05, M.oak(), -w / 2 + 0.03, 0, 0);
  box(g, 0.035, 0.72, d - 0.05, M.oak(), w / 2 - 0.03, 0, 0);
  box(g, 0.34, 0.24, 0.02, M.charcoal(), 0.1, 0.755, -0.12);
  cyl(g, 0.06, 0.07, 0.03, M.brass(), -w / 2 + 0.2, 0.755, -0.1, 16);
  cyl(g, 0.008, 0.008, 0.36, M.brass(), -w / 2 + 0.2, 0.78, -0.1, 8);
  cyl(g, 0.09, 0.11, 0.12, M.shade(), -w / 2 + 0.2, 1.1, -0.06, 20);
  return g;
}

export function deskChair() {
  const g = new THREE.Group();
  for (const [x, z] of [[-0.18, 0.18], [0.18, 0.18], [-0.18, -0.18], [0.18, -0.18]]) box(g, 0.03, 0.45, 0.03, M.oak(), x, 0, z);
  rbox(g, 0.44, 0.06, 0.44, 0.025, M.sage(), 0, 0.44, 0);
  rbox(g, 0.42, 0.22, 0.04, 0.02, M.oak(), 0, 0.62, -0.2);
  return g;
}

// open dressing room: hanging rails with clothes along the given walls of a box (local metres)
export function dressing(W, D, sides) {
  const g = new THREE.Group();
  const rnd = seeded(Math.round(W * 1000 + D * 77));
  const run = (len, place) => {
    const shelf = new THREE.Group();
    box(shelf, len, 0.03, 0.55, M.oak(), 0, 1.75, 0);
    box(shelf, len, 0.03, 0.55, M.oak(), 0, 0.02, 0);
    cyl(shelf, 0.012, 0.012, len, M.brass(), 0, 0, 0, 8).rotation.z = Math.PI / 2;
    shelf.children[shelf.children.length - 1].position.set(0, 1.62, 0);
    let x = -len / 2 + 0.06;
    while (x < len / 2 - 0.06) {
      const t = 0.03 + rnd() * 0.04;
      const h = 0.7 + rnd() * 0.55;
      box(shelf, t, h, 0.42, M.clothes(Math.floor(rnd() * 6)), x, 1.6 - h, 0, { cast: false });
      x += t + 0.012;
    }
    for (let i = 0; i < Math.floor(len / 0.35); i++) box(shelf, 0.28, 0.12, 0.3, M.clothes(Math.floor(rnd() * 6)), -len / 2 + 0.2 + i * 0.35, 0.05, 0.05);
    place(shelf);
    g.add(shelf);
  };
  // a side is 'w', 'e', 'n', 's', or { s, a, b }: a run along part of that wall,
  // a and b in metres from the north (for 'w' and 'e') or west (for 'n' and 's') end of the room
  for (const sd of sides) {
    const s = typeof sd === 'string' ? sd : sd.s;
    const part = typeof sd === 'string' ? null : sd;
    if (s === 'w' || s === 'e') {
      const a = part ? part.a : 0.05, b = part ? part.b : D - 0.05;
      const mid = -D / 2 + (a + b) / 2;
      if (s === 'w') run(b - a, (o) => { o.rotation.y = Math.PI / 2; o.position.set(-W / 2 + 0.3, 0, mid); });
      else run(b - a, (o) => { o.rotation.y = -Math.PI / 2; o.position.set(W / 2 - 0.3, 0, mid); });
    }
    if (s === 'n') {
      const a = part ? part.a : 0.05, b = part ? part.b : W - 0.05;
      run(b - a, (o) => { o.position.set(-W / 2 + (a + b) / 2, 0, -D / 2 + 0.3); });
    }
    if (s === 's') {
      const a = part ? part.a : 0.65, b = part ? part.b : W - 0.05;
      run(b - a, (o) => { o.rotation.y = Math.PI; o.position.set(-W / 2 + (a + b) / 2, 0, D / 2 - 0.3); });
    }
  }
  return g;
}

// open shelving with storage boxes along one wall of a box ('n' by default)
export function shelves(W, D, side = 'n') {
  const g = new THREE.Group();
  const inner = new THREE.Group();
  const along = side === 'n' || side === 's' ? W : D;
  const depth = side === 'n' || side === 's' ? D : W;
  for (let i = 0; i < 5; i++) box(inner, along - 0.1, 0.025, 0.4, M.oak(), 0, 0.3 + i * 0.45, -depth / 2 + 0.22);
  const rnd = seeded(5);
  for (let i = 0; i < 12; i++) box(inner, 0.3, 0.22, 0.3, M.clothes(Math.floor(rnd() * 6)), -along / 2 + 0.3 + (i % 4) * (along - 0.4) / 4, 0.325 + Math.floor(i / 4) * 0.45, -depth / 2 + 0.22);
  inner.rotation.y = { n: 0, s: Math.PI, w: Math.PI / 2, e: -Math.PI / 2 }[side] || 0;
  g.add(inner);
  return g;
}

// front loading washing machine, front facing +Z
export function washer() {
  const g = new THREE.Group();
  box(g, 0.6, 0.85, 0.58, M.ceramic(), 0, 0, 0);
  const ring = cyl(g, 0.2, 0.2, 0.02, M.steel(), -0.02, 0, 0.29, 36);
  ring.rotation.x = Math.PI / 2;
  ring.position.y = 0.42;
  const door = cyl(g, 0.16, 0.16, 0.025, M.blackGlass(), -0.02, 0, 0.3, 36);
  door.rotation.x = Math.PI / 2;
  door.position.y = 0.42;
  box(g, 0.56, 0.08, 0.01, M.charcoal(), 0, 0.75, 0.29, { cast: false });
  return g;
}

// a boxed in cistern or duct casing, w by d in plan, h high
export function boxing(w, d, h, mat = M.stone()) {
  const g = new THREE.Group();
  box(g, w, h, d, mat, 0, 0, 0);
  box(g, w + 0.01, 0.025, d + 0.01, M.stone(), 0, h, 0);
  return g;
}

export function utility(w = 2.0, d = 0.6) {
  const g = new THREE.Group();
  box(g, w, 0.86, d, M.oak(), 0, 0, 0);
  box(g, w, 0.035, d, M.stone(), 0, 0.86, 0);
  for (const x of [-0.32, 0.32]) {
    box(g, 0.6, 0.82, 0.02, M.ceramic(), x - w / 2 + 0.7, 0.02, d / 2 + 0.005);
    const door = cyl(g, 0.2, 0.2, 0.02, M.blackGlass(), x - w / 2 + 0.7, 0.45, d / 2 + 0.02, 32);
    door.rotation.x = Math.PI / 2;
    door.position.y = 0.45;
  }
  box(g, w, 0.5, 0.32, M.oak(), 0, 1.5, -d / 2 + 0.16);
  return g;
}

// ---------- bathrooms ----------
export function wc() {
  const g = new THREE.Group();
  box(g, 0.5, 1.05, 0.16, M.stone(), 0, 0, -0.27);
  rbox(g, 0.37, 0.36, 0.55, 0.13, M.ceramic(), 0, 0.03, 0.02);
  rbox(g, 0.38, 0.04, 0.5, 0.15, M.ceramic(), 0, 0.4, 0.03);
  box(g, 0.2, 0.12, 0.01, M.steel(), 0, 0.85, -0.185, { cast: false });
  return g;
}

export function vanity(w = 0.9, d = 0.45) {
  const g = new THREE.Group();
  box(g, w, 0.42, d, M.oak(), 0, 0.42, 0);
  box(g, w, 0.03, d, M.stone(), 0, 0.84, 0);
  cyl(g, Math.min(0.2, w * 0.25), 0.15, 0.13, M.ceramic(), 0, 0.87, 0.02, 32);
  cyl(g, 0.012, 0.012, 0.2, M.brass(), 0, 0.87, -d / 2 + 0.06, 10);
  box(g, 0.016, 0.016, 0.12, M.brass(), 0, 1.07, -d / 2 + 0.11);
  // round mirror above, only seen in the interior views
  const mir = cyl(g, Math.min(0.32, w * 0.36), Math.min(0.32, w * 0.36), 0.02, M.mirror(), 0, 1.5, -d / 2 + 0.01, 48);
  mir.rotation.x = Math.PI / 2;
  mir.position.y = 1.55;
  mir.userData.interiorOnly = true;
  return g;
}

export function bath(w = 1.6, d = 0.75) {
  const g = new THREE.Group();
  const shape = new THREE.Shape();
  const rx = w / 2, rz = d / 2, c = Math.min(rx, rz) * 0.95;
  shape.moveTo(-rx + c, -rz);
  shape.lineTo(rx - c, -rz);
  shape.quadraticCurveTo(rx, -rz, rx, -rz + c);
  shape.lineTo(rx, rz - c);
  shape.quadraticCurveTo(rx, rz, rx - c, rz);
  shape.lineTo(-rx + c, rz);
  shape.quadraticCurveTo(-rx, rz, -rx, rz - c);
  shape.lineTo(-rx, -rz + c);
  shape.quadraticCurveTo(-rx, -rz, -rx + c, -rz);
  const hole = new THREE.Path();
  const ix = rx - 0.06, iz = rz - 0.06, ic = c * 0.9;
  hole.moveTo(-ix + ic, -iz);
  hole.lineTo(ix - ic, -iz);
  hole.quadraticCurveTo(ix, -iz, ix, -iz + ic);
  hole.lineTo(ix, iz - ic);
  hole.quadraticCurveTo(ix, iz, ix - ic, iz);
  hole.lineTo(-ix + ic, iz);
  hole.quadraticCurveTo(-ix, iz, -ix, iz - ic);
  hole.lineTo(-ix, -iz + ic);
  hole.quadraticCurveTo(-ix, -iz, -ix + ic, -iz);
  shape.holes.push(hole);
  const shell = new THREE.Mesh(new THREE.ExtrudeGeometry(shape, { depth: 0.56, bevelEnabled: true, bevelThickness: 0.02, bevelSize: 0.02, bevelSegments: 3, curveSegments: 16 }), M.ceramic());
  shell.rotation.x = -Math.PI / 2;
  shell.castShadow = shell.receiveShadow = true;
  g.add(shell);
  const inner = new THREE.Mesh(new THREE.ShapeGeometry(new THREE.Shape(hole.getPoints(24))), M.ceramic());
  inner.rotation.x = -Math.PI / 2;
  inner.position.y = 0.1;
  g.add(inner);
  cyl(g, 0.012, 0.012, 0.9, M.brass(), rx - 0.02, 0, -rz - 0.1, 10);
  return g;
}

// riserSide puts the riser and head on that wall ('ne' corner by default)
export function showerTray(W, D, screenSide, riserSide) {
  const g = new THREE.Group();
  box(g, W, 0.03, D, M.tiles(), 0, 0, 0, { cast: false });
  box(g, 0.14, 0.004, 0.02, M.steel(), 0, 0.031, 0, { cast: false });
  const glass = M.glass();
  if (screenSide === 'n' || screenSide === 's') box(g, W * 0.7, 2.0, 0.01, glass, -W * 0.15, 0.03, screenSide === 'n' ? -D / 2 : D / 2, { cast: false });
  if (screenSide === 'w' || screenSide === 'e') box(g, 0.01, 2.0, D * 0.7, glass, screenSide === 'w' ? -W / 2 : W / 2, 0.03, -D * 0.15, { cast: false });
  // riser on the middle of a wall, with the head reaching out from it
  const at = {
    w: [-W / 2 + 0.03, 0, -W / 2 + 0.2, 0], e: [W / 2 - 0.03, 0, W / 2 - 0.2, 0],
    n: [0, -D / 2 + 0.03, 0, -D / 2 + 0.2], s: [0, D / 2 - 0.03, 0, D / 2 - 0.2],
  }[riserSide] || [W / 2 - 0.05, -D / 2 + 0.05, W / 2 - 0.2, -D / 2 + 0.2];
  cyl(g, 0.012, 0.012, 2.0, M.brass(), at[0], 0, at[1], 8);
  cyl(g, 0.13, 0.13, 0.015, M.brass(), at[2], 2.0, at[3], 28);
  return g;
}

// ---------- plants ----------
let leafGeo = null;
function leafGeometry() {
  if (leafGeo) return leafGeo;
  const s = new THREE.Shape();
  s.moveTo(0, 0);
  s.quadraticCurveTo(0.5, 0.35, 0, 1);
  s.quadraticCurveTo(-0.5, 0.35, 0, 0);
  leafGeo = new THREE.ShapeGeometry(s, 4);
  return leafGeo;
}

// instanced leaves scattered in ellipsoids
export function foliage(parent, blobs, { count = 400, size = 0.12, seed = 1, colors = [0, 1, 2, 3] } = {}) {
  const rnd = seeded(seed);
  const per = Math.ceil(count / colors.length);
  const dummy = new THREE.Object3D();
  for (const ci of colors) {
    const inst = new THREE.InstancedMesh(leafGeometry(), M.leaf(ci), per);
    inst.castShadow = true;
    inst.receiveShadow = true;
    for (let i = 0; i < per; i++) {
      const b = blobs[Math.floor(rnd() * blobs.length)];
      let x, y, z;
      do { x = rnd() * 2 - 1; y = rnd() * 2 - 1; z = rnd() * 2 - 1; } while (x * x + y * y + z * z > 1);
      dummy.position.set(b[0] + x * b[3], b[1] + y * (b[4] ?? b[3]), b[2] + z * (b[5] ?? b[3]));
      dummy.rotation.set(rnd() * Math.PI * 2, rnd() * Math.PI * 2, rnd() * Math.PI * 2);
      const k = size * (0.7 + rnd() * 0.6);
      dummy.scale.set(k * 0.7, k, k);
      dummy.updateMatrix();
      inst.setMatrixAt(i, dummy.matrix);
    }
    parent.add(inst);
  }
}

export function plantTall(dia = 0.5, h = 1.8, seed = 3) {
  const g = new THREE.Group();
  cyl(g, dia / 2, dia * 0.4, 0.42, M.pot(), 0, 0, 0, 28);
  cyl(g, dia / 2 - 0.02, dia / 2 - 0.02, 0.01, M.soil(), 0, 0.41, 0, 28);
  for (let i = 0; i < 3; i++) {
    const s = cyl(g, 0.012, 0.016, h - 0.5, M.trunk(), (i - 1) * 0.05, 0.42, (i % 2) * 0.04, 6);
    s.rotation.z = (i - 1) * 0.12;
  }
  foliage(g, [[0, h * 0.72, 0, dia * 0.75, h * 0.28, dia * 0.75], [0.12, h * 0.5, 0.05, dia * 0.5]], { count: 520, size: 0.13, seed });
  return g;
}

export function plantSmall(seed = 9) {
  const g = new THREE.Group();
  cyl(g, 0.16, 0.13, 0.3, M.potDark(), 0, 0, 0, 24);
  foliage(g, [[0, 0.5, 0, 0.24, 0.2, 0.24]], { count: 160, size: 0.1, seed });
  return g;
}

export function tree(h = 2.6, seed = 4) {
  const g = new THREE.Group();
  for (let i = 0; i < 4; i++) {
    const a = (i / 4) * Math.PI * 2;
    const t = cyl(g, 0.02, 0.035, h * 0.62, M.trunk(), Math.cos(a) * 0.05, 0, Math.sin(a) * 0.05, 7);
    t.rotation.z = Math.cos(a) * 0.18;
    t.rotation.x = Math.sin(a) * 0.18;
  }
  foliage(g, [[0, h * 0.72, 0, h * 0.3, h * 0.24, h * 0.3], [h * 0.12, h * 0.55, 0, h * 0.2], [-h * 0.1, h * 0.6, h * 0.08, h * 0.2]], { count: 1500, size: 0.11, seed, colors: [0, 1, 2, 4] });
  return g;
}

export function shrub(h = 1.2, seed = 6) {
  const g = new THREE.Group();
  foliage(g, [[0, h * 0.45, 0, h * 0.45, h * 0.42, h * 0.45]], { count: 600, size: 0.1, seed, colors: [1, 2, 3, 4] });
  return g;
}

// ---------- lights seen in the interior photographs ----------
export function pendantLinear(w = 1.6) {
  const g = new THREE.Group();
  box(g, w, 0.05, 0.08, M.brass(), 0, 0, 0);
  box(g, w - 0.04, 0.012, 0.05, M.bulb(), 0, -0.01, 0, { cast: false });
  cyl(g, 0.004, 0.004, 0.9, M.charcoal(), -w / 2 + 0.1, 0.05, 0, 4);
  cyl(g, 0.004, 0.004, 0.9, M.charcoal(), w / 2 - 0.1, 0.05, 0, 4);
  return g;
}

export function pendantRound() {
  const g = new THREE.Group();
  const s = new THREE.Mesh(new THREE.SphereGeometry(0.24, 32, 16, 0, Math.PI * 2, 0, Math.PI / 2), M.shade());
  s.material.side = THREE.DoubleSide;
  g.add(s);
  cyl(g, 0.004, 0.004, 1.0, M.charcoal(), 0, 0.2, 0, 4);
  return g;
}

// framed canvas hung on a wall, front facing +Z, bottom edge at y = 0
export function art(w = 1.2, h = 0.9, tone = 0) {
  const g = new THREE.Group();
  box(g, w, h, 0.035, M.oakDark(), 0, 0, 0);
  const c = document.createElement('canvas');
  c.width = 512; c.height = Math.round((512 * h) / w);
  const x = c.getContext('2d');
  const tones = [['#e9e1d3', '#c9b49a', '#a86440', '#8f9c82'], ['#efe8de', '#d6c8b2', '#5d6b78', '#b8925a']][tone % 2];
  x.fillStyle = tones[0]; x.fillRect(0, 0, c.width, c.height);
  x.fillStyle = tones[1]; x.beginPath(); x.ellipse(c.width * 0.36, c.height * 0.58, c.width * 0.26, c.height * 0.3, 0.3, 0, Math.PI * 2); x.fill();
  x.fillStyle = tones[2]; x.beginPath(); x.ellipse(c.width * 0.66, c.height * 0.42, c.width * 0.15, c.height * 0.2, -0.4, 0, Math.PI * 2); x.fill();
  x.strokeStyle = tones[3]; x.lineWidth = 7; x.beginPath(); x.moveTo(c.width * 0.12, c.height * 0.8); x.bezierCurveTo(c.width * 0.4, c.height * 0.2, c.width * 0.7, c.height * 0.95, c.width * 0.9, c.height * 0.3); x.stroke();
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  const m = new THREE.Mesh(new THREE.PlaneGeometry(w - 0.06, h - 0.06), new THREE.MeshStandardMaterial({ map: t, roughness: 0.9 }));
  m.position.set(0, h / 2, 0.019);
  g.add(m);
  return g;
}

// closed front door in oak with a brass pull, front facing +Z
export function door(w = 0.95) {
  const g = new THREE.Group();
  box(g, w, 2.2, 0.06, M.oakDark(), 0, 0, 0);
  box(g, 0.025, 0.6, 0.03, M.brass(), w / 2 - 0.12, 0.8, 0.045);
  box(g, w + 0.12, 0.06, 0.08, M.bronze(), 0, 2.2, 0);
  return g;
}

export { PALETTE };
