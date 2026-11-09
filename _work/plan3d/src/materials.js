// Material library for the Nest Battersea dollhouse.
// The palette is the one the interior photographs are generated from, so the 3D model
// and the photos share every colour: warm white walls, natural oak, travertine, oatmeal
// boucle, linen, sage and rust accents, dark bronze metalwork (the facade colour).
import * as THREE from 'three';

export const PALETTE = {
  wall: 0xefe8de,
  wallCap: 0xf6f1ea,
  oak: 0xc49a6c,
  oakDark: 0x9c7450,
  stone: 0xe2d6c4,
  tile: 0xd9cdbb,
  bronze: 0x3d3430,
  bronzeLight: 0x5a4c42,
  boucle: 0xe9e1d3,
  oat: 0xd6c8b2,
  sage: 0x8f9c82,
  rust: 0xa86440,
  linen: 0xf2eee7,
  charcoal: 0x2f2d2b,
  brass: 0xb8925a,
  ceramic: 0xf4f2ee,
  leaf: [0x46633a, 0x587a43, 0x6a8a4e, 0x3b5531, 0x7a9658],
  soil: 0x3a2f27,
};

const textureCache = new Map();
let maxAniso = 8;
export function setAnisotropy(n) { maxAniso = n; }

function canvasTexture(key, size, draw, { repeat = 1, srgb = true } = {}) {
  if (textureCache.has(key)) return textureCache.get(key);
  const c = document.createElement('canvas');
  c.width = c.height = size;
  const g = c.getContext('2d');
  draw(g, size);
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(repeat, repeat);
  t.anisotropy = maxAniso;
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  textureCache.set(key, t);
  return t;
}

// deterministic random so the model is identical on every visit
function rng(seed) {
  let s = seed >>> 0;
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

function hex(c, k = 1, dr = 0, dg = 0, db = 0) {
  const r = Math.max(0, Math.min(255, ((c >> 16) & 255) * k + dr));
  const g = Math.max(0, Math.min(255, ((c >> 8) & 255) * k + dg));
  const b = Math.max(0, Math.min(255, (c & 255) * k + db));
  return `rgb(${r | 0},${g | 0},${b | 0})`;
}

// Oak floor: 1024 px = 4 m, planks 0.19 m wide, random lengths, soft grain, hairline joints
export function oakFloorTexture() {
  return canvasTexture('oakFloor', 1024, (g, S) => {
    const r = rng(7);
    const pxm = S / 4;
    const pw = 0.19 * pxm;
    const rows = Math.ceil(S / pw);
    for (let i = 0; i < rows; i++) {
      let x = -r() * 2 * pxm;
      while (x < S) {
        const len = (1.2 + r() * 1.3) * pxm;
        const k = 0.9 + r() * 0.17;
        const y = i * pw;
        g.fillStyle = hex(PALETTE.oak, k, r() * 6 - 3, 0, -r() * 6);
        g.fillRect(x, y, len, pw);
        // grain
        for (let j = 0; j < 14; j++) {
          const gy = y + r() * pw;
          g.strokeStyle = `rgba(110,72,40,${0.04 + r() * 0.07})`;
          g.lineWidth = 0.6 + r() * 1.2;
          g.beginPath();
          g.moveTo(x, gy);
          const segs = 6;
          for (let s = 1; s <= segs; s++) g.lineTo(x + (len * s) / segs, gy + (r() - 0.5) * 3);
          g.stroke();
        }
        if (r() < 0.12) {
          g.fillStyle = 'rgba(95,60,32,0.25)';
          g.beginPath();
          g.ellipse(x + r() * len, y + pw / 2, 3 + r() * 4, 1.5 + r() * 2, 0, 0, Math.PI * 2);
          g.fill();
        }
        // joints, drawn wrapped so the texture tiles
        g.fillStyle = 'rgba(70,45,25,0.35)';
        g.fillRect(x, y, 1.2, pw);
        x += len;
      }
      g.fillStyle = 'rgba(70,45,25,0.30)';
      g.fillRect(0, i * pw, S, 1);
    }
  });
}

// Oak veneer for joinery, 512 px = 1 m, vertical grain
export function oakVeneerTexture(dark = false) {
  return canvasTexture(dark ? 'oakDark' : 'oakVeneer', 512, (g, S) => {
    const r = rng(dark ? 21 : 11);
    g.fillStyle = hex(dark ? PALETTE.oakDark : PALETTE.oak, 1.0);
    g.fillRect(0, 0, S, S);
    for (let i = 0; i < 220; i++) {
      const x = r() * S;
      g.strokeStyle = `rgba(100,66,38,${0.03 + r() * 0.08})`;
      g.lineWidth = 0.5 + r() * 1.8;
      g.beginPath();
      g.moveTo(x, 0);
      for (let y = 0; y <= S; y += S / 8) g.lineTo(x + Math.sin(y * 0.02 + i) * 2 + (r() - 0.5) * 2, y);
      g.stroke();
    }
  });
}

// Travertine / limestone, 512 px = 1.2 m, soft clouds and pores
export function stoneTexture(tiles = false) {
  return canvasTexture(tiles ? 'stoneTiles' : 'stone', 512, (g, S) => {
    const r = rng(tiles ? 33 : 31);
    g.fillStyle = hex(tiles ? PALETTE.tile : PALETTE.stone);
    g.fillRect(0, 0, S, S);
    for (let i = 0; i < 160; i++) {
      const x = r() * S, y = r() * S, rad = 20 + r() * 90;
      const grd = g.createRadialGradient(x, y, 0, x, y, rad);
      const a = 0.025 + r() * 0.04;
      grd.addColorStop(0, r() < 0.5 ? `rgba(255,250,240,${a})` : `rgba(150,125,95,${a})`);
      grd.addColorStop(1, 'rgba(0,0,0,0)');
      g.fillStyle = grd;
      g.fillRect(x - rad, y - rad, rad * 2, rad * 2);
    }
    for (let i = 0; i < 700; i++) {
      g.fillStyle = `rgba(120,95,70,${0.05 + r() * 0.12})`;
      g.fillRect(r() * S, r() * S, 1 + r() * 2.5, 0.6 + r());
    }
    if (tiles) {
      // 0.6 x 1.2 m tiles with 2 mm joints
      g.fillStyle = 'rgba(160,145,125,0.55)';
      const cell = S / 2;
      for (let k = 0; k <= 2; k++) {
        g.fillRect(0, k * cell - 1, S, 2);
      }
      g.fillRect(-1, 0, 2, S);
      g.fillRect(S - 1, 0, 2, S);
    }
  });
}

// Soft fabric (boucle / linen) colour noise, tiles every 0.5 m
export function fabricTexture(base, key, coarse = 1) {
  return canvasTexture('fab' + key, 256, (g, S) => {
    const r = rng(base & 0xffff);
    g.fillStyle = hex(base);
    g.fillRect(0, 0, S, S);
    for (let i = 0; i < 2600 * coarse; i++) {
      const k = 0.92 + r() * 0.14;
      g.fillStyle = hex(base, k);
      const s = 1 + r() * 2.2 * coarse;
      g.beginPath();
      g.arc(r() * S, r() * S, s, 0, Math.PI * 2);
      g.fill();
    }
  });
}

// Wool / jute rug, woven look
export function rugTexture(base, key) {
  return canvasTexture('rug' + key, 256, (g, S) => {
    const r = rng(base & 0xfff);
    g.fillStyle = hex(base);
    g.fillRect(0, 0, S, S);
    for (let y = 0; y < S; y += 4) {
      for (let x = 0; x < S; x += 4) {
        g.fillStyle = hex(base, 0.93 + r() * 0.12);
        g.fillRect(x + ((y / 4) % 2) * 2, y, 3, 3);
      }
    }
  });
}

const matCache = new Map();
// metres covered by one repeat of each material's texture (used by the UV helpers)
const TILES = { oak: 1, oakDarkM: 1, stoneM: 1.2, tilesM: 1.2, paving: 1.2, boucle: 0.5, oat: 0.5, sage: 0.5, rust: 0.5, linen: 0.5, rugWool: 0.6, rugJute: 0.6 };
function cached(key, make) {
  if (!matCache.has(key)) {
    const m = make();
    m.userData.tile = TILES[key] || 1;
    m.userData.key = key;
    matCache.set(key, m);
  }
  return matCache.get(key);
}
export function allMaterials() { return [...matCache.values()]; }

export const M = {
  wall: () => cached('wall', () => new THREE.MeshStandardMaterial({ color: PALETTE.wall, roughness: 0.92 })),
  ceiling: () => cached('ceiling', () => new THREE.MeshStandardMaterial({ color: 0xf4f0ea, roughness: 0.95 })),
  oakFloor: () => cached('oakFloor', () => new THREE.MeshStandardMaterial({ map: oakFloorTexture(), roughness: 0.58 })),
  oak: () => cached('oak', () => new THREE.MeshStandardMaterial({ map: oakVeneerTexture(), roughness: 0.62 })),
  oakDark: () => cached('oakDarkM', () => new THREE.MeshStandardMaterial({ map: oakVeneerTexture(true), roughness: 0.6 })),
  stone: () => cached('stoneM', () => new THREE.MeshStandardMaterial({ map: stoneTexture(), roughness: 0.48 })),
  tiles: () => cached('tilesM', () => new THREE.MeshStandardMaterial({ map: stoneTexture(true), roughness: 0.5 })),
  bronze: () => cached('bronze', () => new THREE.MeshStandardMaterial({ color: PALETTE.bronze, roughness: 0.42, metalness: 0.55 })),
  slab: () => cached('slab', () => new THREE.MeshStandardMaterial({ color: 0x4a3f38, roughness: 0.7, metalness: 0.15 })),
  glass: () => cached('glass', () => new THREE.MeshStandardMaterial({ color: 0xcfdde0, roughness: 0.04, metalness: 0.1, transparent: true, opacity: 0.16, depthWrite: false, envMapIntensity: 1.6 })),
  boucle: () => cached('boucle', () => new THREE.MeshStandardMaterial({ map: fabricTexture(PALETTE.boucle, 'boucle', 1.2), roughness: 0.98 })),
  oat: () => cached('oat', () => new THREE.MeshStandardMaterial({ map: fabricTexture(PALETTE.oat, 'oat'), roughness: 0.97 })),
  sage: () => cached('sage', () => new THREE.MeshStandardMaterial({ map: fabricTexture(PALETTE.sage, 'sage'), roughness: 0.96 })),
  rust: () => cached('rust', () => new THREE.MeshStandardMaterial({ map: fabricTexture(PALETTE.rust, 'rust'), roughness: 0.9 })),
  linen: () => cached('linen', () => new THREE.MeshStandardMaterial({ map: fabricTexture(PALETTE.linen, 'linen', 0.6), roughness: 0.97 })),
  rugWool: () => cached('rugWool', () => new THREE.MeshStandardMaterial({ map: rugTexture(0xdcd0bd, 'wool'), roughness: 1 })),
  rugJute: () => cached('rugJute', () => new THREE.MeshStandardMaterial({ map: rugTexture(0xc8b28e, 'jute'), roughness: 1 })),
  leather: () => cached('leather', () => new THREE.MeshStandardMaterial({ color: 0x8b5b3b, roughness: 0.55 })),
  charcoal: () => cached('charcoal', () => new THREE.MeshStandardMaterial({ color: PALETTE.charcoal, roughness: 0.6 })),
  blackGlass: () => cached('blackGlass', () => new THREE.MeshStandardMaterial({ color: 0x111111, roughness: 0.15, metalness: 0.3 })),
  brass: () => cached('brass', () => new THREE.MeshStandardMaterial({ color: PALETTE.brass, roughness: 0.32, metalness: 1 })),
  steel: () => cached('steel', () => new THREE.MeshStandardMaterial({ color: 0xb9bcbd, roughness: 0.3, metalness: 1 })),
  ceramic: () => cached('ceramic', () => new THREE.MeshStandardMaterial({ color: PALETTE.ceramic, roughness: 0.22 })),
  mirror: () => cached('mirror', () => new THREE.MeshStandardMaterial({ color: 0xdfe3e4, roughness: 0.02, metalness: 1 })),
  shade: () => cached('shade', () => new THREE.MeshStandardMaterial({ color: 0xf6efe2, roughness: 0.9, emissive: 0xffd7a0, emissiveIntensity: 0.35 })),
  bulb: () => cached('bulb', () => new THREE.MeshStandardMaterial({ color: 0xfff1d6, emissive: 0xffd9a8, emissiveIntensity: 2.2 })),
  soil: () => cached('soil', () => new THREE.MeshStandardMaterial({ color: PALETTE.soil, roughness: 1 })),
  pot: () => cached('pot', () => new THREE.MeshStandardMaterial({ color: 0xcdbfa8, roughness: 0.85 })),
  potDark: () => cached('potDark', () => new THREE.MeshStandardMaterial({ color: 0x3a3532, roughness: 0.8 })),
  trunk: () => cached('trunk', () => new THREE.MeshStandardMaterial({ color: 0x6d563f, roughness: 0.9 })),
  leaf: (i) => cached('leaf' + i, () => new THREE.MeshStandardMaterial({ color: PALETTE.leaf[i % PALETTE.leaf.length], roughness: 0.8, side: THREE.DoubleSide })),
  paving: () => cached('paving', () => new THREE.MeshStandardMaterial({ map: stoneTexture(true), color: 0xd8d2c8, roughness: 0.75 })),
  clothes: (i) => cached('clothes' + i, () => new THREE.MeshStandardMaterial({ color: [0xe8e2d8, 0xa9b0a0, 0x4a4e57, 0xcdbba3, 0xb08a6e, 0xf3f0ea][i % 6], roughness: 0.95 })),
  soffit: () => cached('soffit', () => new THREE.MeshStandardMaterial({ map: oakVeneerTexture(), color: 0xb79a7c, roughness: 0.6 })),
  cladding: () => cached('cladding', () => new THREE.MeshStandardMaterial({ color: 0x3e3530, roughness: 0.55, metalness: 0.35 })),
};
