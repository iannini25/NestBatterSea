// Builds a Three.js model of a home from the plan data in apartments.js.
// Floors and walls come straight from the plan rectangles, so the joints are exact:
// every wall sits on a floor, the upper floor plate covers the lower walls and the
// stair rises exactly one storey (3.2 m) to meet the upper landing.
// Doors are cut out of their wall line: the wall pieces, the header over the opening,
// the lining and the leaf form one cutaway unit, so they drop together.
import * as THREE from 'three';
import { PX_PER_M } from './apartments.js';
import { M } from './materials.js';
import * as F from './furniture.js';

const S = PX_PER_M;
const HEAD = 2.1;      // underside of the header over a door
const LINE = 0.03;     // door lining width
const LEAF = 0.04;     // door leaf thickness

function bbox(apt) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  const add = (p) => { x0 = Math.min(x0, p[0]); y0 = Math.min(y0, p[1]); x1 = Math.max(x1, p[0]); y1 = Math.max(y1, p[1]); };
  for (const lv of apt.levels) {
    for (const r of lv.rooms) r.poly.forEach(add);
    for (const w of lv.walls) { add([w[0], w[1]]); add([w[2], w[3]]); }
  }
  for (const p of apt.exterior.planting) p.forEach(add);
  return { x0, y0, x1, y1 };
}

function scaleUV(geo, k) {
  const uv = geo.attributes.uv;
  for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * k, uv.getY(i) * k);
}

// box geometry that stands on its origin (y from 0 to h), UVs in metres
const vgeo = (w, h, d, mat) => F.boxGeo(w, h, d, (mat && mat.userData.tile) || 1).translate(0, h / 2, 0);
function vbox(w, h, d, mat, x = 0, y = 0, z = 0) {
  const m = new THREE.Mesh(vgeo(w, h, d, mat), mat);
  m.position.set(x, y, z);
  m.castShadow = m.receiveShadow = true;
  return m;
}

// is an opening rectangle part of a wall rectangle (same direction, within its length and thickness)
function hosts(w, o) {
  const wh = w[2] - w[0] >= w[3] - w[1];
  const oh = o[2] - o[0] >= o[3] - o[1];
  if (wh !== oh) return false;
  const [wa0, wa1, wt0, wt1] = wh ? [w[0], w[2], w[1], w[3]] : [w[1], w[3], w[0], w[2]];
  const [oa0, oa1, ot0, ot1] = oh ? [o[0], o[2], o[1], o[3]] : [o[1], o[3], o[0], o[2]];
  const overlap = Math.min(wt1, ot1) - Math.max(wt0, ot0);
  return oa0 >= wa0 - 1.5 && oa1 <= wa1 + 1.5 && overlap >= 0.5 * Math.min(wt1 - wt0, ot1 - ot0);
}

export function buildApartment(apt) {
  const bb = bbox(apt);
  const cx = (bb.x0 + bb.x1) / 2, cy = (bb.y0 + bb.y1) / 2;
  const P = ([x, y]) => [(x - cx) / S, (y - cy) / S];
  const root = new THREE.Group();
  root.name = apt.id;
  const levels = [];

  // a horizontal slab from a polygon: top at y = 0, thickness t downwards
  const slab = (poly, t, topMat, sideMat, tile, bottomMat = sideMat) => {
    const shape = new THREE.Shape(poly.map((p) => { const [x, z] = P(p); return new THREE.Vector2(x, -z); }));
    const geo = new THREE.ExtrudeGeometry(shape, { depth: t, bevelEnabled: false });
    scaleUV(geo, 1 / tile);
    // ExtrudeGeometry puts both lids in group 0: the first half is the bottom lid
    const g0 = geo.groups[0];
    const half = g0.count / 2;
    geo.groups.splice(0, 1, { start: g0.start, count: half, materialIndex: 2 }, { start: g0.start + half, count: half, materialIndex: 0 });
    const m = new THREE.Mesh(geo, [topMat, sideMat, bottomMat]);
    m.rotation.x = -Math.PI / 2;
    m.position.y = -t;
    m.receiveShadow = true;
    m.castShadow = true;
    return m;
  };

  // cutaway units: everything of one wall line drops together when it faces the camera.
  // Each part spans heights a..b above its floor; its geometry stands on its own origin,
  // so the viewer shows the part up to the current cut height by scaling it.
  const cutList = [];
  const unit = (parent, cxw, czw, full) => {
    const u = new THREE.Group();
    u.userData.cut = { cx: cxw, cz: czw, full, parts: [] };
    parent.add(u);
    cutList.push(u);
    return u;
  };
  const part = (u, obj, a, b) => {
    obj.position.y = a;
    u.add(obj);
    u.userData.cut.parts.push({ o: obj, a, b });
    return obj;
  };

  const place = (parent, obj, at, r = 0, y = 0) => {
    const [x, z] = P(at);
    obj.position.set(x, y, z);
    obj.rotation.y = (r * Math.PI) / 180;
    parent.add(obj);
    return obj;
  };

  apt.levels.forEach((lv, li) => {
    const base = li * apt.floorToFloor;
    const g = new THREE.Group();
    g.name = lv.id;
    g.position.y = base;
    const interior = new THREE.Group();
    interior.name = 'interior';
    interior.visible = false;
    g.add(interior);
    const lights = [];
    const H = apt.wallH;
    const upper = li > 0;
    const slabT = upper ? apt.floorToFloor - apt.wallH : 0.3;
    const sideMat = upper ? M.wall() : M.slab();
    const bottomMat = upper ? M.ceiling() : M.slab();
    const doors = (lv.doors || []).map((d) => ({ ...d, k: d.k || 'swing' }));

    // floors (one mesh per room so rooms can be picked and lit)
    const rooms = [];
    for (const room of lv.rooms) {
      if (room.floor === 'none') {
        rooms.push({ ...room, level: li, mesh: null, polyM: room.poly.map(P), hotM: room.hot ? P(room.hot) : null });
        continue;
      }
      const mat = room.floor === 'stone' ? M.tiles() : M.oakFloor();
      const tile = room.floor === 'stone' ? 1.2 : 4;
      const m = slab(room.poly, slabT, mat, sideMat, tile, bottomMat);
      m.userData.room = room.id;
      g.add(m);
      rooms.push({ ...room, level: li, mesh: m, polyM: room.poly.map(P), hotM: room.hot ? P(room.hot) : null });
      // ceiling for the interior photographs
      const ch = room.double ? apt.floorToFloor + H : H;
      const c = slab(room.poly, 0.02, M.ceiling(), M.ceiling(), 4);
      c.position.y = ch;
      c.castShadow = false;
      interior.add(c);
      // recessed downlights on a 1.6 m grid
      const pts = room.poly.map(P);
      let mnx = Infinity, mxx = -Infinity, mnz = Infinity, mxz = -Infinity;
      pts.forEach(([x, z]) => { mnx = Math.min(mnx, x); mxx = Math.max(mxx, x); mnz = Math.min(mnz, z); mxz = Math.max(mxz, z); });
      const nx = Math.max(1, Math.round((mxx - mnx) / 1.6)), nz = Math.max(1, Math.round((mxz - mnz) / 1.6));
      for (let i = 0; i < nx; i++) for (let k = 0; k < nz; k++) {
        const dl = new THREE.Mesh(new THREE.CircleGeometry(0.045, 20), M.bulb());
        dl.rotation.x = Math.PI / 2;
        dl.position.set(mnx + ((i + 0.5) * (mxx - mnx)) / nx, ch - 0.005, mnz + ((k + 0.5) * (mxz - mnz)) / nz);
        interior.add(dl);
      }
    }
    // floor that belongs to no room (under the stair), and a threshold under every opening
    const fillMat = (f) => (f === 'stone' ? M.tiles() : f === 'sill' ? M.paving() : M.oakFloor());
    for (const f of lv.fills || []) g.add(slab(f.poly, slabT, fillMat(f.floor), f.floor === 'sill' ? M.slab() : sideMat, f.floor === 'oak' || !f.floor ? 4 : 1.2, bottomMat));

    // wet rooms: large format stone on the walls, wherever the room edge meets a wall
    const inPoly = (px, py, poly) => {
      let c = false;
      for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
        const [xi, yi] = poly[i], [xj, yj] = poly[j];
        if ((yi > py) !== (yj > py) && px < ((xj - xi) * (py - yi)) / (yj - yi) + xi) c = !c;
      }
      return c;
    };
    const inOpening = (px, py) => doors.some((d) => px >= d.o[0] - 0.5 && px <= d.o[2] + 0.5 && py >= d.o[1] - 0.5 && py <= d.o[3] + 0.5);
    const inWall = (px, py) => !inOpening(px, py) && (lv.walls.some((w) => px >= w[0] - 0.5 && px <= w[2] + 0.5 && py >= w[1] - 0.5 && py <= w[3] + 0.5)
      || (lv.solids || []).some((s) => inPoly(px, py, s.poly)));
    for (const room of lv.rooms) {
      if (room.floor !== 'stone') continue;
      const poly = room.poly;
      for (let i = 0; i < poly.length; i++) {
        const a = poly[i], b = poly[(i + 1) % poly.length];
        const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
        if (len < 2) continue;
        const ux = (b[0] - a[0]) / len, uy = (b[1] - a[1]) / len;
        let nx = -uy, ny = ux;
        const mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2;
        // the normal points into the room (tested on the polygon, rooms can be L shaped)
        if (!inPoly(mx + nx * 0.6, my + ny * 0.6, poly)) { nx = -nx; ny = -ny; }
        // walk the edge in 2 px steps and collect runs that are backed by a wall
        let run = null;
        const flush = (t1) => {
          if (run === null) return;
          const t0 = run;
          run = null;
          if (t1 - t0 < 4) return;
          const pa = [a[0] + ux * t0 + nx * 0.4, a[1] + uy * t0 + ny * 0.4];
          const pb = [a[0] + ux * t1 + nx * 0.4, a[1] + uy * t1 + ny * 0.4];
          const [qax, qaz] = P(pa), [qbx, qbz] = P(pb);
          const L = Math.hypot(qbx - qax, qbz - qaz);
          const grp = new THREE.Group();
          grp.position.set(qax, 0, qaz);
          grp.rotation.y = Math.atan2(-(qbz - qaz), qbx - qax);
          F.box(grp, L, 2.4, 0.012, M.tiles(), L / 2, 0, 0, { cast: false });
          interior.add(grp);
        };
        for (let t = 0; t <= len; t += 2) {
          const backed = inWall(a[0] + ux * t - nx * 2, a[1] + uy * t - ny * 2);
          if (backed && run === null) run = t;
          if (!backed && run !== null) flush(t);
        }
        flush(len);
      }
    }

    // ---------- doors ----------
    // a door assembly in its own frame: x along the wall (from the 'a' end to the 'b' end),
    // z across it, y up from the floor; the header stays with the wall pieces
    const doorGroup = (d, W, T, horiz) => {
      const dg = new THREE.Group();
      const front = d.k === 'front';
      const liningMat = front ? M.bronze() : M.oak();
      // which local z the plan side '+' points to (east or south)
      const zPlus = horiz ? 1 : -1;
      const sideSign = (d.side === '-' ? -1 : 1) * zPlus;
      // lining: two jambs and the head, slightly proud of both faces
      const ld = T + 0.012;
      dg.add(vbox(LINE, HEAD, ld, liningMat, -W / 2 + LINE / 2, 0, 0));
      dg.add(vbox(LINE, HEAD, ld, liningMat, W / 2 - LINE / 2, 0, 0));
      dg.add(vbox(W, LINE, ld, liningMat, 0, HEAD - LINE, 0));
      if (d.k === 'open') return dg;
      const lw = W - 2 * LINE - 0.006;
      const lh = HEAD - LINE - 0.012;
      if (d.k === 'pocket') {
        // the leaf rests in the wall at the pocket end, its edge showing at the mouth
        const dir = d.pocket === 'a' ? -1 : 1;
        const edge = dir * (W / 2 - LINE - 0.11);
        const leaf = vbox(lw, lh, LEAF, M.oak(), edge + (dir * lw) / 2, 0.006, 0);
        dg.add(leaf);
        dg.add(vbox(0.012, 0.3, LEAF + 0.008, M.brass(), edge + dir * 0.01, 0.9, 0));
        return dg;
      }
      const thick = front ? 0.055 : LEAF;
      const hingeA = d.hinge !== 'b';
      const dirX = hingeA ? 1 : -1;
      const pivot = new THREE.Group();
      pivot.position.set(hingeA ? -W / 2 + LINE : W / 2 - LINE, 0, (sideSign * T) / 2);
      const leafMat = front ? M.oakDark() : M.oak();
      pivot.add(vbox(lw, lh, thick, leafMat, (dirX * lw) / 2, 0.006, (-sideSign * thick) / 2));
      // handles on both faces at the free edge (a long pull on the front door)
      const hx = dirX * (lw - 0.075);
      if (front) {
        pivot.add(vbox(0.025, 0.75, 0.03, M.brass(), hx, 0.75, sideSign * 0.015));
      } else if (d.k === 'cupboard') {
        pivot.add(vbox(0.018, 0.22, 0.02, M.brass(), hx, 0.95, sideSign * 0.01));
      } else {
        for (const s of [1, -1]) {
          const zf = (-sideSign * thick) / 2 + (s * (thick / 2 + 0.012));
          pivot.add(vbox(0.13, 0.018, 0.018, M.brass(), hx - (dirX * 0.05), 0.98, zf));
          pivot.add(vbox(0.05, 0.05, 0.008, M.brass(), hx, 0.965, (-sideSign * thick) / 2 + s * (thick / 2 + 0.004)));
        }
      }
      const ang = d.k === 'swing' ? ((d.ang ?? 90) * Math.PI) / 180 : 0;
      pivot.rotation.y = -dirX * sideSign * ang;
      dg.add(pivot);
      return dg;
    };

    // build one opening into a cut unit: lining and leaf, header, threshold
    const buildOpening = (u, d, host) => {
      const o = d.o;
      const horiz = o[2] - o[0] >= o[3] - o[1];
      const t0 = host ? (horiz ? host[1] : host[0]) : (horiz ? o[1] : o[0]);
      const t1 = host ? (horiz ? host[3] : host[2]) : (horiz ? o[3] : o[2]);
      const rect = horiz ? [o[0], t0, o[2], t1] : [t0, o[1], t1, o[3]];
      const [ax, az] = P([rect[0], rect[1]]), [bx, bz] = P([rect[2], rect[3]]);
      const W = horiz ? bx - ax : bz - az;
      const T = horiz ? bz - az : bx - ax;
      const mx = (ax + bx) / 2, mz = (az + bz) / 2;
      // header from the door head to the top of the wall
      part(u, vbox(bx - ax, H - HEAD, bz - az, M.wall(), mx, 0, mz), HEAD, H);
      const dg = doorGroup(d, W, T, horiz);
      dg.position.set(mx, 0, mz);
      dg.rotation.y = horiz ? 0 : -Math.PI / 2;
      part(u, dg, 0, HEAD);
      // threshold: the floor runs through the opening
      const fm = d.floor === 'stone' ? M.tiles() : M.oakFloor();
      g.add(slab([[rect[0], rect[1]], [rect[2], rect[1]], [rect[2], rect[3]], [rect[0], rect[3]]], slabT, fm, sideMat, d.floor === 'stone' ? 1.2 : 4, bottomMat));
    };

    // L and T junctions: a wall end that butts against another wall runs 0.6 px into it,
    // so the two boxes overlap instead of meeting on a hairline
    const EXT = 0.6;
    const rects = lv.walls.map((w) => w.slice());
    rects.forEach((w, i) => {
      const horiz = w[2] - w[0] >= w[3] - w[1];
      const [a0, a1, t0, t1] = horiz ? [0, 2, 1, 3] : [1, 3, 0, 2];
      const others = lv.walls.filter((_, j) => j !== i);
      const across = (r) => r[t0] < w[t1] - 0.01 && r[t1] > w[t0] + 0.01;
      if (others.some((r) => across(r) && r[a0] < w[a0] - 0.01 && r[a1] >= w[a0] - 0.5)) w[a0] -= EXT;
      if (others.some((r) => across(r) && r[a1] > w[a1] + 0.01 && r[a0] <= w[a1] + 0.5)) w[a1] += EXT;
    });

    // walls rise from the underside of the floor slab to the ceiling; door openings are cut out
    const used = new Set();
    for (const w of rects) {
      const [ax, az] = P([w[0], w[1]]), [bx, bz] = P([w[2], w[3]]);
      const u = unit(g, (ax + bx) / 2, (az + bz) / 2, H);
      const horiz = w[2] - w[0] >= w[3] - w[1];
      const mine = doors.filter((d, i) => !used.has(i) && hosts(w, d.o) && used.add(i));
      // pieces along the wall between the openings
      const cuts = mine.map((d) => (horiz ? [d.o[0], d.o[2]] : [d.o[1], d.o[3]])).sort((p, q) => p[0] - q[0]);
      const pieces = [];
      let s = horiz ? w[0] : w[1];
      const end = horiz ? w[2] : w[3];
      for (const [c0, c1] of cuts) {
        if (c0 - s > 0.05) pieces.push([s, c0]);
        s = Math.max(s, c1);
      }
      if (end - s > 0.05) pieces.push([s, end]);
      for (const [p0, p1] of pieces) {
        const r = horiz ? [p0, w[1], p1, w[3]] : [w[0], p0, w[2], p1];
        const [qx0, qz0] = P([r[0], r[1]]), [qx1, qz1] = P([r[2], r[3]]);
        part(u, vbox(Math.max(0.02, qx1 - qx0), H + slabT, Math.max(0.02, qz1 - qz0), M.wall(), (qx0 + qx1) / 2, 0, (qz0 + qz1) / 2), -slabT, H);
      }
      for (const d of mine) buildOpening(u, d, w);
    }
    // openings with no wall around them (a door that fills the whole gap between two walls)
    doors.forEach((d, i) => {
      if (used.has(i)) return;
      const [ax, az] = P([d.o[0], d.o[1]]), [bx, bz] = P([d.o[2], d.o[3]]);
      buildOpening(unit(g, (ax + bx) / 2, (az + bz) / 2, H), d, null);
    });

    // wall prisms with a polygon footprint
    for (const so of lv.solids || []) {
      const pts = so.poly.map(P);
      const shape = new THREE.Shape(pts.map(([x, z]) => new THREE.Vector2(x, -z)));
      const geo = new THREE.ExtrudeGeometry(shape, { depth: H + slabT, bevelEnabled: false });
      geo.rotateX(-Math.PI / 2);
      const m = new THREE.Mesh(geo, M.wall());
      m.castShadow = m.receiveShadow = true;
      const c = pts.reduce((acc, p) => [acc[0] + p[0] / pts.length, acc[1] + p[1] / pts.length], [0, 0]);
      part(unit(g, c[0], c[1], H), m, -slabT, H);
    }

    // frameless glass shower screens with a slim brass edge, a hinged door at the 'a' end
    for (const sc of lv.screens || []) {
      const [ax, az] = P(sc.a), [bx, bz] = P(sc.b);
      const L = Math.hypot(bx - ax, bz - az);
      const h = sc.h || 2.0;
      const grp = new THREE.Group();
      grp.position.set(ax, 0, az);
      grp.rotation.y = Math.atan2(-(bz - az), bx - ax);
      grp.add(vbox(L, h, 0.01, M.glass(), L / 2, 0.03, 0));
      grp.add(vbox(0.015, h, 0.02, M.brass(), 0.008, 0.03, 0));
      grp.add(vbox(0.015, h, 0.02, M.brass(), L - 0.008, 0.03, 0));
      grp.add(vbox(L, 0.015, 0.02, M.brass(), L / 2, 0.03 + h - 0.015, 0));
      if (sc.door) {
        const dw = Math.min(0.75, L * 0.6);
        grp.add(vbox(0.015, h - 0.05, 0.022, M.brass(), dw, 0.05, 0));
        grp.add(vbox(0.02, 0.25, 0.04, M.brass(), dw - 0.06, 0.95, 0));
      }
      part(unit(g, (ax + bx) / 2, (az + bz) / 2, h + 0.03), grp, 0, h + 0.03);
      grp.children.forEach((c) => { c.castShadow = false; });
    }

    // glazing with slim bronze frames
    for (const gl of lv.glass || []) {
      const [ax, az] = P(gl.a), [bx, bz] = P(gl.b);
      const L = Math.hypot(bx - ax, bz - az);
      const ang = Math.atan2(-(bz - az), bx - ax);
      const u = unit(g, (ax + bx) / 2, (az + bz) / 2, gl.h);
      const grp = new THREE.Group();
      grp.position.set(ax, 0, az);
      grp.rotation.y = ang;
      u.add(grp);
      u.userData.cut.parts.push({ o: grp, a: 0, b: gl.h });
      const h = gl.h;
      const fr = M.bronze();
      F.box(grp, L, 0.05, 0.09, fr, L / 2, 0, 0);
      F.box(grp, L, 0.06, 0.09, fr, L / 2, h - 0.06, 0);
      if (gl.double) F.box(grp, L, 0.09, 0.1, fr, L / 2, apt.floorToFloor - 0.2, 0);
      const n = Math.max(1, Math.round(L / 1.25));
      const step = L / n;
      const openA = gl.open ? gl.open.from * L : -1, openB = gl.open ? gl.open.to * L : -1;
      for (let i = 0; i <= n; i++) F.box(grp, 0.05, h, 0.09, fr, i * step, 0, 0);
      // panes, skipping the open sliding door
      const panes = [];
      if (gl.open) {
        if (openA > 0.02) panes.push([0, openA]);
        if (L - openB > 0.02) panes.push([openB, L]);
        // the slid panel parks outside the next fixed pane
        const pw = openB - openA;
        const sp = new THREE.Group();
        F.box(sp, pw, 2.7, 0.03, M.glass(), pw / 2, 0.05, 0, { cast: false });
        F.box(sp, pw, 0.05, 0.05, fr, pw / 2, 0.05, 0);
        F.box(sp, pw, 0.05, 0.05, fr, pw / 2, 2.7, 0);
        F.box(sp, 0.05, 2.7, 0.05, fr, 0, 0.05, 0);
        F.box(sp, 0.05, 2.7, 0.05, fr, pw, 0.05, 0);
        sp.position.set(openB, 0, -0.09);
        grp.add(sp);
        F.box(grp, 0.06, 2.75, 0.1, fr, openA, 0, 0);
        F.box(grp, 0.06, 2.75, 0.1, fr, openB, 0, 0);
        if (h > 2.9) F.box(grp, pw, h - 2.75, 0.02, M.glass(), (openA + openB) / 2, 2.75, 0, { cast: false });
        if (h > 2.9) F.box(grp, pw, 0.06, 0.09, fr, (openA + openB) / 2, 2.72, 0);
      } else panes.push([0, L]);
      for (const [p0, p1] of panes) F.box(grp, p1 - p0, h - 0.11, 0.02, M.glass(), (p0 + p1) / 2, 0.05, 0, { cast: false });
      if (gl.slider) {
        // a second sliding door, closed, drawn with its frame
        const s0 = gl.slider.from * L, s1 = gl.slider.to * L;
        F.box(grp, 0.06, h, 0.1, fr, s0, 0, 0);
        F.box(grp, 0.06, h, 0.1, fr, s1, 0, 0);
      }
    }

    // glass balustrades
    const railLine = (parent, a, b, y0 = 0, h = 1.1) => {
      const [ax, az] = P(a), [bx, bz] = P(b);
      const L = Math.hypot(bx - ax, bz - az);
      const grp = new THREE.Group();
      grp.position.set(ax, y0, az);
      grp.rotation.y = Math.atan2(-(bz - az), bx - ax);
      F.box(grp, L, h, 0.015, M.glass(), L / 2, 0, 0, { cast: false });
      F.box(grp, L, 0.04, 0.05, M.bronze(), L / 2, h, 0);
      F.box(grp, L, 0.06, 0.06, M.bronze(), L / 2, 0, 0);
      parent.add(grp);
    };
    for (const r of lv.rails || []) railLine(g, r.a, r.b);

    // timber fins between bedroom three and the double height living room
    if (lv.fins) {
      const { x, y0, y1, n } = lv.fins;
      for (let i = 0; i < n; i++) {
        const y = y0 + ((y1 - y0) * (i + 0.5)) / n;
        const [fx, fz] = P([x, y]);
        F.box(g, 0.045, H, 0.34, M.oak(), fx, 0, fz, { ry: 0.6 });
      }
    }

    // stair: U shape with winders, 17 risers of 0.188 m reaching the upper landing at 3.2 m.
    // The flights follow the plan: the upper flight runs along the living room wall (with the
    // cupboard under it, its door on the hall), the lower flight along the lobby, and the well
    // between them is open to the hall.
    if (lv.stair) {
      const [x0p, y0p, x1p, y1p] = lv.stair.box;
      const [sx0, sz0] = P([x0p, y0p]);
      const [sx1, sz1] = P([x1p, y1p]);
      const rise = apt.floorToFloor / 17;
      const st = new THREE.Group();
      st.name = 'stair';
      const inner = sx0 + 1.1;           // end of the straight flights
      const upperLane = [sz0 + 0.09, sz0 + 0.97];
      const lowerLane = [sz1 - 1.0, sz1 - 0.09];
      const tread = (poly, k) => {
        const top = k * rise;
        const shape = new THREE.Shape(poly.map(([x, z]) => new THREE.Vector2(x, -z)));
        const body = new THREE.Mesh(new THREE.ExtrudeGeometry(shape, { depth: top - 0.04, bevelEnabled: false }), M.wall());
        body.rotation.x = -Math.PI / 2;
        body.castShadow = body.receiveShadow = true;
        st.add(body);
        const capGeo = new THREE.ExtrudeGeometry(shape, { depth: 0.04, bevelEnabled: false });
        scaleUV(capGeo, 1);
        const cap = new THREE.Mesh(capGeo, M.oak());
        cap.rotation.x = -Math.PI / 2;
        cap.position.y = top - 0.04;
        cap.castShadow = cap.receiveShadow = true;
        st.add(cap);
      };
      const go = 0.22;
      for (let k = 1; k <= 5; k++) {
        const xa = sx0 + (k - 1) * go, xb = sx0 + k * go;
        tread([[xa, lowerLane[0]], [xb, lowerLane[0]], [xb, lowerLane[1]], [xa, lowerLane[1]]], k);
      }
      // winders around the centre of the turn
      const c = [inner, (upperLane[1] + lowerLane[0]) / 2];
      // the winders run 5 mm into the east wall so no hairline shows between them
      const rect = [inner, upperLane[0], sx1 + 0.005, lowerLane[1]];
      const hit = (th) => {
        const dx = Math.sin(th), dz = Math.cos(th);
        let t = Infinity;
        if (dx > 1e-6) t = Math.min(t, (rect[2] - c[0]) / dx);
        if (dz > 1e-6) t = Math.min(t, (rect[3] - c[1]) / dz);
        if (dz < -1e-6) t = Math.min(t, (rect[1] - c[1]) / dz);
        return [c[0] + dx * t, c[1] + dz * t];
      };
      const corners = [[rect[2], rect[3]], [rect[2], rect[1]]];
      const nW = 7;
      for (let i = 0; i < nW; i++) {
        const a0 = (i / nW) * Math.PI, a1 = ((i + 1) / nW) * Math.PI;
        const pts = [c, hit(a0)];
        for (const cr of corners) {
          const ca = Math.atan2(cr[0] - c[0], cr[1] - c[1]);
          const aa = ca < 0 ? ca + Math.PI * 2 : ca;
          if (aa > a0 && aa < a1) pts.push(cr);
        }
        pts.push(hit(a1));
        // the first winder also covers the gap to the lower lane, the last to the upper lane
        if (i === 0) pts.splice(1, 0, [inner, lowerLane[1]]);
        if (i === nW - 1) pts.push([inner, upperLane[0]]);
        tread(pts, 6 + i);
      }
      for (let k = 13; k <= 17; k++) {
        const j = k - 13;
        // the top tread stops a hair short of the cupboard front so their faces never fight
        const xb = inner - j * go, xa = Math.max(inner - (j + 1) * go, sx0 + 0.006);
        tread([[xa, upperLane[0]], [xb, upperLane[0]], [xb, upperLane[1]], [xa, upperLane[1]]], k);
      }
      // glass balustrades with a bronze handrail along the open sides of the well:
      // the lower flight, the turn and the upper flight
      const pitch = rise / go;
      const guard = (x0, z0, y0, x1, z1, y1) => {
        const L = Math.hypot(x1 - x0, z1 - z0);
        const grp = new THREE.Group();
        grp.position.set(x0, 0, z0);
        grp.rotation.y = Math.atan2(-(z1 - z0), x1 - x0);
        const shear = new THREE.Matrix4().makeShear((y1 - y0) / L, 0, 0, 0, 0, 0);
        const pane = new THREE.Mesh(new THREE.BoxGeometry(L, 1.15, 0.012).translate(L / 2, 1.15 / 2, 0).applyMatrix4(shear), M.glass());
        pane.position.y = y0 - 0.25;
        grp.add(pane);
        const railM = new THREE.Mesh(new THREE.BoxGeometry(L, 0.045, 0.05).translate(L / 2, 0, 0).applyMatrix4(shear), M.bronze());
        railM.position.y = y0 + 0.92;
        railM.castShadow = true;
        grp.add(railM);
        st.add(grp);
      };
      const zl = lowerLane[0] - 0.012, zu = upperLane[1] + 0.012;
      guard(sx0, zl, rise, inner, zl, rise + (inner - sx0) * pitch);
      guard(inner - 0.012, zl, 6 * rise, inner - 0.012, zu, 13 * rise);
      guard(inner, zu, 13 * rise, sx0 + go, zu, 17 * rise);
      guard(sx0 + go, zu, 17 * rise, sx0, zu, 17 * rise);
      // newel posts at the turn
      for (const [z, y] of [[zl, 6 * rise], [zu, 13 * rise]]) st.add(vbox(0.05, y + 0.95, 0.05, M.bronze(), inner - 0.012, 0, z));
      g.add(st);
    }

    // furniture
    for (const f of lv.furniture) {
      const tgt = f.interior ? interior : g;
      let o = null;
      switch (f.t) {
        case 'rug': o = F.rug(f.w, f.d, f.jute ? M.rugJute() : M.rugWool()); break;
        case 'sofa': o = F.sofa(f.w, f.d); break;
        case 'armchair': o = F.armchair(); break;
        case 'coffeeRound': o = F.coffeeRound(f.dia); break;
        case 'bench': o = F.bench(f.w, f.d); break;
        case 'console': o = F.console_(f.w, f.d); break;
        case 'plantTall': o = F.plantTall(f.dia, f.h, Math.round(f.at[0] + f.at[1])); break;
        case 'plantSmall': o = F.plantSmall(Math.round(f.at[0])); break;
        case 'floorLamp': o = F.floorLamp(); lights.push({ at: f.at, y: 1.5, i: 6 }); break;
        case 'diningTable': o = F.diningTable(f.w, f.d); break;
        case 'chair': o = F.chair(); break;
        case 'stool': o = F.stool(); break;
        case 'island': o = F.island(f.w, f.d); break;
        case 'bed': o = F.bed(f.w, f.d, f.single, f.throw); break;
        case 'nightstand': o = F.nightstand(); lights.push({ at: f.at, y: 0.75, i: 2.5 }); break;
        case 'wardrobe': o = F.wardrobe(f.w, f.d); break;
        case 'desk': o = F.desk(f.w, f.d); break;
        case 'deskChair': o = F.deskChair(); break;
        case 'utility': o = F.utility(f.w, f.d); break;
        case 'washer': o = F.washer(); break;
        case 'wc': o = F.wc(); break;
        case 'vanity': o = F.vanity(f.w, f.d); break;
        case 'bath': o = F.bath(f.w, f.d); break;
        case 'pendantLinear': o = F.pendantLinear(f.w); o.position.y = 1.95; lights.push({ at: f.at, y: 1.9, i: 10 }); break;
        case 'pendantRound': o = F.pendantRound(); o.position.y = 1.85; lights.push({ at: f.at, y: 1.8, i: 8 }); break;
        case 'art': o = F.art(f.w, f.h, f.tone); o.position.y = f.y || 0.9; break;
        case 'door': o = F.door(f.w); break;
        case 'kitchenRun': {
          // a is the plan corner where the run starts; its back sits on the wall
          const run = F.kitchenRun({ ...f, flip: f.r === 90 });
          const cxp = f.r === 90 ? f.a[0] + (f.depth * S) / 2 : f.a[0] - (f.depth * S) / 2;
          place(tgt, run, [cxp, f.a[1] + (f.len * S) / 2], f.r);
          break;
        }
        case 'dressing': case 'shelves': case 'shower': case 'boxing': {
          const [ax, az] = P([f.box[0], f.box[1]]), [bx, bz] = P([f.box[2], f.box[3]]);
          const W = bx - ax, D = bz - az;
          let obj;
          if (f.t === 'dressing') {
            // partial runs are given in plan px along their wall; the builder wants metres from the room edge
            const sides = f.sides.map((s) => (typeof s === 'string' ? s : { s: s.s, a: (s.a - (s.s === 'w' || s.s === 'e' ? f.box[1] : f.box[0])) / S, b: (s.b - (s.s === 'w' || s.s === 'e' ? f.box[1] : f.box[0])) / S }));
            obj = F.dressing(W, D, sides);
          } else if (f.t === 'shelves') obj = F.shelves(W, D, f.side);
          else if (f.t === 'boxing') obj = F.boxing(W, D, f.h || 1.1, f.mat === 'oak' ? M.oak() : M.stone());
          else obj = F.showerTray(W, D, f.screen, f.riser);
          obj.position.set((ax + bx) / 2, 0, (az + bz) / 2);
          tgt.add(obj);
          break;
        }
        default: break;
      }
      if (o) place(tgt, o, f.at, f.r || 0, o.position.y);
    }

    levels.push({ id: lv.id, label: lv.label, group: g, interior, base, rooms, cuts: cutList.splice(0), lights: lights.map((l) => ({ ...l, pos: P(l.at) })) });
    root.add(g);
  });

  // exterior: planted beds, paving, balustrade, trees (on the entrance level)
  const ext = new THREE.Group();
  ext.name = 'exterior';
  const ex = apt.exterior;
  for (const poly of ex.paving) ext.add(slab(poly, 0.3, M.paving(), M.slab(), 1.2));
  for (const poly of ex.planting) {
    const bed = slab(poly, 0.3, M.soil(), M.slab(), 1);
    ext.add(bed);
    const lip = slab(poly, 0.38, M.soil(), M.bronze(), 1);
    lip.position.y = 0.08;
    lip.scale.set(1, 1, 1);
    ext.add(lip);
    // shrubs on a jittered grid inside the polygon
    const pts = poly.map(P);
    let minx = Infinity, minz = Infinity, maxx = -Infinity, maxz = -Infinity;
    pts.forEach(([x, z]) => { minx = Math.min(minx, x); maxx = Math.max(maxx, x); minz = Math.min(minz, z); maxz = Math.max(maxz, z); });
    const inside = (x, z) => {
      let c = false;
      for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
        const [xi, zi] = pts[i], [xj, zj] = pts[j];
        if ((zi > z) !== (zj > z) && x < ((xj - xi) * (z - zi)) / (zj - zi) + xi) c = !c;
      }
      return c;
    };
    const blobs = [];
    let seed = 1;
    for (let x = minx + 0.15; x < maxx; x += 0.3) {
      for (let z = minz + 0.15; z < maxz; z += 0.3) {
        seed = (seed * 16807) % 2147483647;
        const jx = ((seed % 1000) / 1000 - 0.5) * 0.2, jz = (((seed / 1000) % 1000) / 1000 - 0.5) * 0.2;
        if (inside(x + jx, z + jz)) blobs.push([x + jx, 0.32 + (seed % 9) * 0.035, z + jz, 0.24, 0.26, 0.24]);
      }
    }
    if (blobs.length) F.foliage(ext, blobs, { count: Math.min(12000, blobs.length * 150), size: 0.095, seed: blobs.length, colors: [0, 1, 2, 3, 4] });
  }
  const railPoly = (line) => {
    for (let i = 0; i < line.length - 1; i++) {
      const [ax, az] = P(line[i]), [bx, bz] = P(line[i + 1]);
      const L = Math.hypot(bx - ax, bz - az);
      const grp = new THREE.Group();
      grp.position.set(ax, 0.08, az);
      grp.rotation.y = Math.atan2(-(bz - az), bx - ax);
      F.box(grp, L, 1.1, 0.015, M.glass(), L / 2, 0, 0, { cast: false });
      F.box(grp, L, 0.04, 0.05, M.bronze(), L / 2, 1.1, 0);
      ext.add(grp);
    }
  };
  if (ex.rail) railPoly(ex.rail);
  if (ex.rail2) railPoly(ex.rail2);
  for (const t of ex.trees || []) {
    const o = t.shrub ? F.shrub(t.h, Math.round(t.at[0])) : F.tree(t.h, Math.round(t.at[0]));
    const [x, z] = P(t.at);
    o.position.set(x, 0.08, z);
    ext.add(o);
  }
  levels[0].group.add(ext);

  // meshes that only belong in the eye level views (mirrors)
  levels.forEach((lv) => {
    lv.interiorOnly = [];
    lv.group.traverse((o) => { if (o.userData.interiorOnly) { lv.interiorOnly.push(o); o.visible = false; } });
  });

  // facade context for the exterior arrival frame: the slab above the home with its
  // dark bronze edge and warm timber soffit, as on the official render
  const facade = new THREE.Group();
  facade.name = 'facade';
  facade.visible = false;
  const topY = apt.levels.length * apt.floorToFloor;
  const all = [];
  apt.levels.forEach((lv) => lv.rooms.forEach((r) => all.push(r.poly)));
  ex.planting.forEach((p) => all.push(p));
  ex.paving.forEach((p) => all.push(p));
  for (const poly of all) {
    const sl = slab(poly, 0.42, M.slab(), M.bronze(), 1, M.soffit());
    sl.position.y = topY;
    facade.add(sl);
  }
  for (const e of apt.facadeEdge || []) {
    const [ax, az] = P(e[0]), [bx, bz] = P(e[1]);
    const L = Math.hypot(bx - ax, bz - az);
    const grp = new THREE.Group();
    grp.position.set(ax, topY, az);
    grp.rotation.y = Math.atan2(-(bz - az), bx - ax);
    F.box(grp, L, 1.1, 0.015, M.glass(), L / 2, 0.42, 0, { cast: false });
    F.box(grp, L, 0.04, 0.05, M.bronze(), L / 2, 1.52, 0);
    facade.add(grp);
  }
  // dark bronze cladding on the solid parts of the facade (exterior views only)
  for (const c of apt.cladding || []) {
    const [ax, az] = P([c[0], c[1]]), [bx, bz] = P([c[2], c[3]]);
    const h = c[4] || topY;
    F.box(facade, Math.max(0.03, bx - ax), h, Math.max(0.03, bz - az), M.cladding(), (ax + bx) / 2, -0.3, (az + bz) / 2);
  }
  root.add(facade);

  // poses in world metres
  const poses = {};
  for (const [k, p] of Object.entries(apt.poses || {})) {
    const li = apt.levels.findIndex((l) => l.id === p.level);
    const base = li * apt.floorToFloor;
    const [ex_, ez] = P(p.eye), [lx, lz] = P(p.look);
    poses[k] = { level: li, eye: new THREE.Vector3(ex_, base + p.eye[2], ez), look: new THREE.Vector3(lx, base + p.look[2], lz), fov: p.fov };
  }

  const size = new THREE.Vector3((bb.x1 - bb.x0) / S, apt.levels.length * apt.floorToFloor, (bb.y1 - bb.y0) / S);
  return { root, levels, poses, size, P, facade };
}
