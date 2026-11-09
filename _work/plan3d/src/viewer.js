// Interactive dollhouse viewer for one home.
// createViewer(container, { apt, onRoom, onHover, quality }) returns an API used by the site
// and by the render scripts that produce the guide images for the interior photographs.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { GTAOPass } from 'three/addons/postprocessing/GTAOPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { APARTMENTS } from './apartments.js';
import { buildApartment } from './build.js';
import { M, setAnisotropy } from './materials.js';

const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const easeOut = (t) => 1 - Math.pow(1 - t, 3);

function nightBackdrop() {
  // a soft night sky with a distant line of city lights, seen through the windows
  const c = document.createElement('canvas');
  c.width = 2048; c.height = 512;
  const g = c.getContext('2d');
  const sky = g.createLinearGradient(0, 0, 0, 512);
  sky.addColorStop(0, '#0e1a33');
  sky.addColorStop(0.55, '#24365a');
  sky.addColorStop(0.75, '#3d4d6b');
  sky.addColorStop(1, '#141820');
  g.fillStyle = sky;
  g.fillRect(0, 0, 2048, 512);
  let s = 3;
  const r = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < 160; i++) {
    const x = r() * 2048, w = 12 + r() * 60, h = 20 + r() * 110;
    g.fillStyle = `rgba(22,26,36,${0.85 + r() * 0.15})`;
    g.fillRect(x, 384 - h, w, h + 128);
    for (let k = 0; k < (w * h) / 90; k++) {
      g.fillStyle = r() < 0.7 ? `rgba(255,214,150,${0.5 + r() * 0.5})` : `rgba(190,215,255,${0.4 + r() * 0.4})`;
      g.fillRect(x + 2 + r() * (w - 4), 384 - h + 3 + r() * (h - 6), 1.6, 1.6);
    }
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

export function createViewer(container, opts = {}) {
  const quality = opts.quality || (matchMedia('(pointer: coarse)').matches ? 'low' : 'high');
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance', preserveDrawingBuffer: !!opts.capture });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, quality === 'low' ? 1.5 : 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFShadowMap;
  const clip = new THREE.Plane(new THREE.Vector3(0, -1, 0), 100);
  renderer.clippingPlanes = [clip];
  container.appendChild(renderer.domElement);
  setAnisotropy(renderer.capabilities.getMaxAnisotropy());

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.42;

  const camera = new THREE.PerspectiveCamera(30, 1, 0.05, 400);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.rotateSpeed = 0.55;
  controls.zoomSpeed = 0.7;
  controls.enablePan = false;
  controls.minPolarAngle = 0.32;
  controls.maxPolarAngle = 1.12;

  // lighting: warm key from the front left with soft shadows, cool fill, sky dome
  const hemi = new THREE.HemisphereLight(0xfff2e2, 0x2b2622, 1.15);
  scene.add(hemi);
  const key = new THREE.DirectionalLight(0xffe2c2, 2.7);
  key.castShadow = true;
  key.shadow.mapSize.set(quality === 'low' ? 2048 : 4096, quality === 'low' ? 2048 : 4096);
  key.shadow.bias = -0.0003;
  key.shadow.normalBias = 0.025;
  key.shadow.radius = 3;
  scene.add(key, key.target);
  const fill = new THREE.DirectionalLight(0xc8d6ff, 0.45);
  scene.add(fill);

  let composer = null, gtao = null;
  if (quality !== 'low') {
    composer = new EffectComposer(renderer);
    composer.addPass(new RenderPass(scene, camera));
    gtao = new GTAOPass(scene, camera, 2, 2);
    gtao.output = GTAOPass.OUTPUT.Default;
    gtao.blendIntensity = 0.85;
    gtao.updateGtaoMaterial({ radius: 0.32, distanceExponent: 1.4, thickness: 1.2, scale: 1.1, samples: 16 });
    gtao.updatePdMaterial({ lumaPhi: 10, depthPhi: 2, normalPhi: 3, radius: 6, rings: 2, samples: 16 });
    composer.addPass(gtao);
    composer.addPass(new OutputPass());
  }

  // model
  let model = null, apt = null, level = 0, overlays = [], labels = [], hovered = null;
  const labelLayer = document.createElement('div');
  labelLayer.className = 'p3-labels';
  container.appendChild(labelLayer);

  const fit = { center: new THREE.Vector3(), dist: 20 };
  let interiorMode = false;
  let pointLights = [];
  let backdrop = null;

  function load(id) {
    if (model) { scene.remove(model.root); labelLayer.innerHTML = ''; }
    apt = APARTMENTS[id];
    model = buildApartment(apt);
    scene.add(model.root);
    // hover overlays, one per room
    overlays = [];
    const hl = new THREE.MeshBasicMaterial({ color: 0x92b7ca, transparent: true, opacity: 0, depthWrite: false });
    for (const lv of model.levels) {
      for (const r of lv.rooms) {
        const shape = new THREE.Shape(r.polyM.map(([x, z]) => new THREE.Vector2(x, -z)));
        const m = new THREE.Mesh(new THREE.ShapeGeometry(shape), hl.clone());
        m.rotation.x = -Math.PI / 2;
        m.position.y = 0.025;
        m.renderOrder = 2;
        m.userData.room = r;
        lv.group.add(m);
        overlays.push(m);
        r.overlay = m;
      }
    }
    // labels for rooms that have a photograph
    labels = [];
    for (const lv of model.levels) {
      for (const r of lv.rooms) {
        if (!r.photo || !r.hotM) continue;
        const el = document.createElement('button');
        el.className = 'p3-hot';
        el.type = 'button';
        el.innerHTML = `<i></i><span>${r.name}</span>`;
        el.addEventListener('click', (e) => { e.stopPropagation(); opts.onRoom && opts.onRoom(r); });
        el.addEventListener('pointerenter', () => setHover(r));
        el.addEventListener('pointerleave', () => setHover(null));
        labelLayer.appendChild(el);
        labels.push({ el, room: r, pos: new THREE.Vector3(r.hotM[0], lv.base + 1.2, r.hotM[1]) });
      }
    }
    // shadow camera around the model
    const sz = model.size;
    const R = Math.max(sz.x, sz.z) * 0.75 + 2;
    Object.assign(key.shadow.camera, { left: -R, right: R, top: R, bottom: -R, near: 1, far: 80 });
    key.shadow.camera.updateProjectionMatrix();
    key.position.set(-R * 0.9, 18, R * 1.1);
    fill.position.set(R, 10, -R);
    setLevel(model.levels.length > 1 ? 0 : 0, false);
    frame(false);
  }

  function frame(animate = true, azimuth = -0.62, polar = 0.8) {
    const sz = model.size;
    const lvBase = model.levels[level].base;
    fit.center.set(0, lvBase + 0.6, 0);
    const radius = Math.hypot(sz.x, sz.z) / 2 + 1.0;
    const vfov = (camera.fov * Math.PI) / 180;
    const aspect = camera.aspect || 1.6;
    const hfov = 2 * Math.atan(Math.tan(vfov / 2) * aspect);
    const dist = Math.max(radius / Math.sin(vfov / 2), radius / Math.sin(hfov / 2)) * 0.8;
    fit.dist = dist;
    controls.minDistance = dist * 0.45;
    controls.maxDistance = dist * 1.5;
    const pos = new THREE.Vector3(
      fit.center.x + dist * Math.sin(polar) * Math.sin(azimuth),
      fit.center.y + dist * Math.cos(polar),
      fit.center.z + dist * Math.sin(polar) * Math.cos(azimuth),
    );
    if (animate) return flyTo(pos, fit.center.clone(), 30, 900);
    camera.position.copy(pos);
    controls.target.copy(fit.center);
    camera.fov = 30;
    camera.updateProjectionMatrix();
    controls.update();
    requestRender();
    return Promise.resolve();
  }

  // levels: the upper floor drops onto the lower one, landing exactly on it
  // the level below the active one reads as a darker base so the active floor stands out
  const baseWall = new THREE.MeshStandardMaterial({ color: 0xbdb5aa, roughness: 0.95 });
  function tintBase() {
    if (!model) return;
    const wall = M.wall();
    model.levels.forEach((lv, k) => {
      for (const u of lv.cuts) {
        u.traverse((o) => {
          if (!o.isMesh) return;
          if (k < level && !interiorMode && o.material === wall) o.material = baseWall;
          else if ((k >= level || interiorMode) && o.material === baseWall) o.material = wall;
        });
      }
    });
  }
  let levelAnim = 0;
  function setLevel(i, animate = true) {
    if (!model) return Promise.resolve();
    const n = model.levels.length;
    level = Math.max(0, Math.min(n - 1, i));
    tintBase();
    const my = ++levelAnim;
    const target = model.levels[level];
    const topY = target.base + apt.wallH + 0.01;
    model.levels.forEach((lv, k) => { lv.group.visible = k <= level || interiorMode; });
    if (!animate || n === 1) {
      model.levels.forEach((lv) => { lv.group.position.y = lv.base; });
      clip.constant = interiorMode ? 100 : topY;
      requestRender();
      return Promise.resolve();
    }
    const upper = model.levels[n - 1];
    const goingUp = level === n - 1;
    const fromClip = clip.constant;
    const toClip = topY;
    const fromY = goingUp ? upper.base + 7 : upper.group.position.y;
    const toY = goingUp ? upper.base : upper.base + 7;
    if (goingUp) { upper.group.visible = true; upper.group.position.y = fromY; }
    else upper.group.visible = true;
    const camFrom = controls.target.clone();
    const camTo = new THREE.Vector3(0, target.base + 0.6, 0);
    const posFrom = camera.position.clone();
    const posTo = posFrom.clone().add(camTo.clone().sub(camFrom));
    const t0 = performance.now(), dur = 1100;
    return new Promise((res) => {
      const step = (now) => {
        if (my !== levelAnim) return res();
        const t = Math.min(1, (now - t0) / dur);
        const k = goingUp ? easeOut(t) : ease(t);
        upper.group.position.y = fromY + (toY - fromY) * k;
        clip.constant = goingUp ? fromClip + (toClip - fromClip) * Math.min(1, t * 1.6) : (t > 0.7 ? toClip : fromClip);
        controls.target.lerpVectors(camFrom, camTo, ease(t));
        camera.position.lerpVectors(posFrom, posTo, ease(t));
        renderNow();
        if (t < 1) requestAnimationFrame(step);
        else {
          if (!goingUp) { upper.group.visible = false; upper.group.position.y = upper.base; }
          clip.constant = toClip;
          requestRender();
          res();
        }
      };
      requestAnimationFrame(step);
    });
  }

  // camera flights (dive into a room, back to the overview)
  // mode: 'orbit' lets OrbitControls run, 'fly' during a tween, 'pose' at an eye level viewpoint
  let flight = 0;
  let mode = 'orbit';
  function flyTo(pos, look, fov, dur = 1000, end = 'orbit') {
    const my = ++flight;
    const p0 = camera.position.clone(), t0v = controls.target.clone(), f0 = camera.fov;
    const start = performance.now();
    controls.enabled = false;
    mode = 'fly';
    return new Promise((res) => {
      const step = (now) => {
        if (my !== flight) return res();
        const t = Math.min(1, (now - start) / dur);
        const k = ease(t);
        camera.position.lerpVectors(p0, pos, k);
        controls.target.lerpVectors(t0v, look, k);
        camera.fov = f0 + (fov - f0) * k;
        camera.updateProjectionMatrix();
        camera.lookAt(controls.target);
        renderNow();
        if (t < 1) requestAnimationFrame(step);
        else {
          mode = end;
          if (end === 'orbit') { controls.enabled = true; controls.update(); }
          renderNow();
          res();
        }
      };
      requestAnimationFrame(step);
    });
  }

  function dive(photo, dur = 1150) {
    const p = model.poses[photo];
    if (!p) return Promise.resolve();
    if (p.level !== level && model.levels.length > 1) setLevel(p.level, false);
    // a vertical fov for the photo's 16:9 frame
    const vf = (2 * Math.atan(Math.tan((p.fov * Math.PI) / 360) / (16 / 9)) * 180) / Math.PI;
    return flyTo(p.eye.clone(), p.look.clone(), vf, dur, 'pose');
  }

  // interior mode: ceilings, lamps on, night outside (used for the guide renders)
  function setInterior(on, exterior = false) {
    interiorMode = on;
    for (const lv of model.levels) {
      lv.interior.visible = on;
      lv.group.visible = true;
      lv.group.position.y = lv.base;
      lv.interiorOnly.forEach((o) => (o.visible = on));
    }
    model.facade.visible = on && exterior;
    tintBase();
    clip.constant = on ? 100 : model.levels[level].base + apt.wallH + 0.01;
    overlays.forEach((o) => (o.visible = !on));
    labelLayer.style.display = on ? 'none' : '';
    pointLights.forEach((l) => scene.remove(l));
    pointLights = [];
    if (on) {
      for (const lv of model.levels) {
        for (const l of lv.lights) {
          const pl = new THREE.PointLight(0xffc98f, l.i, 7, 2);
          pl.position.set(l.pos[0], lv.base + l.y, l.pos[1]);
          scene.add(pl);
          pointLights.push(pl);
        }
      }
      if (!backdrop) {
        const tex = nightBackdrop();
        backdrop = new THREE.Mesh(new THREE.CylinderGeometry(60, 60, 40, 64, 1, true), new THREE.MeshBasicMaterial({ map: tex, side: THREE.BackSide, toneMapped: false }));
        backdrop.position.y = 6;
      }
      scene.add(backdrop);
      key.intensity = 0.25;
      hemi.intensity = 0.55;
      scene.environmentIntensity = 0.3;
    } else {
      if (backdrop) scene.remove(backdrop);
      key.intensity = 2.7;
      hemi.intensity = 1.15;
      scene.environmentIntensity = 0.42;
    }
    requestRender();
  }

  // picking
  const ray = new THREE.Raycaster();
  const ndc = new THREE.Vector2();
  function roomAt(clientX, clientY) {
    if (!model) return null;
    const rect = renderer.domElement.getBoundingClientRect();
    ndc.set(((clientX - rect.left) / rect.width) * 2 - 1, -((clientY - rect.top) / rect.height) * 2 + 1);
    ray.setFromCamera(ndc, camera);
    const lv = model.levels[level];
    // intersect the floor plane of the active level and test the room polygons
    const plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), -lv.base);
    const hit = new THREE.Vector3();
    if (!ray.ray.intersectPlane(plane, hit)) return null;
    for (const r of lv.rooms) {
      const pts = r.polyM;
      let c = false;
      for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
        const [xi, zi] = pts[i], [xj, zj] = pts[j];
        if ((zi > hit.z) !== (zj > hit.z) && hit.x < ((xj - xi) * (hit.z - zi)) / (zj - zi) + xi) c = !c;
      }
      if (c) return r;
    }
    return null;
  }
  function setHover(r) {
    if (r && !r.photo) r = null;
    if (hovered === r) return;
    hovered = r;
    for (const o of overlays) {
      const on = r && (o.userData.room === r || (r.join && o.userData.room.id === r.join && false));
      o.material.opacity = on ? 0.22 : 0;
    }
    labels.forEach((l) => l.el.classList.toggle('on', l.room === r));
    renderer.domElement.style.cursor = r ? 'pointer' : '';
    opts.onHover && opts.onHover(r);
    requestRender();
  }
  let downAt = null;
  renderer.domElement.addEventListener('pointermove', (e) => {
    if (interiorMode || e.pointerType === 'touch') return;
    setHover(roomAt(e.clientX, e.clientY));
  });
  renderer.domElement.addEventListener('pointerleave', () => setHover(null));
  renderer.domElement.addEventListener('pointerdown', (e) => { downAt = [e.clientX, e.clientY]; });
  renderer.domElement.addEventListener('pointerup', (e) => {
    if (!downAt || Math.hypot(e.clientX - downAt[0], e.clientY - downAt[1]) > 6) return;
    const r = roomAt(e.clientX, e.clientY);
    if (r && r.photo && opts.onRoom) opts.onRoom(r);
  });

  // render loop on demand
  let needs = true, running = true;
  function requestRender() { needs = true; }
  const v = new THREE.Vector3();
  function placeLabels() {
    const w = renderer.domElement.clientWidth, h = renderer.domElement.clientHeight;
    for (const l of labels) {
      const show = l.room.level === level && !interiorMode;
      if (!show) { l.el.style.display = 'none'; continue; }
      v.copy(l.pos);
      const lvGroup = model.levels[l.room.level].group;
      v.y += lvGroup.position.y - model.levels[l.room.level].base;
      v.project(camera);
      l.el.style.display = v.z < 1 ? '' : 'none';
      l.el.style.transform = `translate(${((v.x + 1) / 2) * w}px, ${((1 - v.y) / 2) * h}px)`;
    }
  }
  // cutaway: walls and glazing in front of the model centre drop to a low height.
  // A unit is one wall line with its doors (or one glazing run): it keeps a single cut height,
  // and every part of it (wall pieces, header, lining, leaf) shows up to that height, so a
  // header over a door disappears as soon as the wall drops below it.
  const camDir = new THREE.Vector3();
  const CUT = 0.95;
  function updateCuts(snap = false) {
    if (!model) return false;
    camDir.subVectors(camera.position, controls.target);
    const high = camDir.y;
    camDir.y = 0;
    camDir.normalize();
    // inside a room (dive) or in interior mode every wall stands full height
    const inside = interiorMode || camera.position.y - model.levels[level].base < 3.4 || high < 2.5;
    let moving = false;
    model.levels.forEach((lv, k) => {
      for (const u of lv.cuts) {
        const c = u.userData.cut;
        const d = c.cx * camDir.x + c.cz * camDir.z;
        const near = !inside && k === level && d > 0.55;
        const tgt = near ? CUT : c.full;
        const cur = c.top ?? c.full;
        const nxt = snap ? tgt : cur + (tgt - cur) * 0.22;
        if (Math.abs(nxt - tgt) > 0.002) moving = true;
        const top = Math.abs(nxt - tgt) <= 0.002 ? tgt : nxt;
        if (top === c.top) continue;
        c.top = top;
        for (const p of c.parts) {
          const s = (top - p.a) / (p.b - p.a);
          p.o.visible = s > 0.002;
          p.o.scale.y = Math.min(1, Math.max(0.002, s));
        }
      }
    });
    return moving;
  }

  function renderNow() {
    cutsMoving = updateCuts();
    if (composer) composer.render(); else renderer.render(scene, camera);
    placeLabels();
    if (!cutsMoving) needs = false;
  }
  let cutsMoving = false;
  controls.addEventListener('change', requestRender);
  function loop() {
    if (!running) return;
    const moved = mode === 'orbit' ? controls.update() : false;
    if (needs || moved) renderNow();
    requestAnimationFrame(loop);
  }

  function resize() {
    const w = container.clientWidth || 800, h = container.clientHeight || 500;
    renderer.setSize(w, h, false);
    renderer.domElement.style.width = w + 'px';
    renderer.domElement.style.height = h + 'px';
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    if (composer) composer.setSize(w, h);
    requestRender();
  }
  const ro = new ResizeObserver(resize);
  ro.observe(container);

  load(opts.apt || 'loft4');
  resize();
  frame(false);
  requestAnimationFrame(loop);

  return {
    load: (id) => { load(id); resize(); frame(false); },
    setLevel, frame, dive, flyTo, setInterior,
    get level() { return level; },
    get levels() { return model.levels.map((l) => ({ id: l.id, label: l.label })); },
    get model() { return model; },
    renderer, scene, camera, controls,
    renderNow, requestRender,
    setPose(photo) {
      const p = model.poses[photo];
      flight++;
      mode = 'pose';
      controls.enabled = false;
      const vf = (2 * Math.atan(Math.tan((p.fov * Math.PI) / 360) / (camera.aspect || 16 / 9)) * 180) / Math.PI;
      camera.position.copy(p.eye);
      controls.target.copy(p.look);
      camera.fov = vf;
      camera.updateProjectionMatrix();
      camera.lookAt(p.look);
      renderNow();
    },
    dispose() {
      running = false;
      ro.disconnect();
      controls.dispose();
      renderer.dispose();
      renderer.domElement.remove();
      labelLayer.remove();
    },
  };
}
export { APARTMENTS } from './apartments.js';
