import * as T from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { layout, SPECS } from './layout.js';

// Local CAD frame: +X right, +Z toward the typist, +Y above PCB. All values in mm.
const RAD = Math.PI / 180;
const C = {
  ivory: '#eee9db',
  graphite: '#58594f',
  ink: '#34392f',
  lightInk: '#f3eee2',
  mask: '#20584c',
  underMask: '#1d5044',
  core: '#578075',
  silk: '#d3ded0',
  pad: '#c4a16c',
  trace: '#447468',
  plastic: '#323932',
  switch: '#696e62',
  steel: '#adb2a8',
  silver: '#c5c5b7',
  black: '#272c29',
  back: '#51564e',
  red: '#d24a32',
  ruby: '#ad3b2b',
  amber: '#c89440',
  fpc: '#bf8b42',
  blue: '#364e60',
};
const clamp = T.MathUtils.clamp;
const finite = (v, d) => (Number.isFinite(+v) && v != null ? +v : d);

const identity = new T.Matrix4();
const transform = (x = 0, h = 0, z = 0, a = 0) =>
  new T.Matrix4().makeRotationY(-a * RAD).setPosition(x, h, z);
const local = (p, h = 0) => transform(p.x, h, p.y, p.a || 0);
const compose = (a, b) => new T.Matrix4().multiplyMatrices(a, b);
const textureFrom = (canvas) => {
  const tex = new T.CanvasTexture(canvas);
  tex.colorSpace = T.SRGBColorSpace;
  tex.anisotropy = 4;
  return tex;
};
function canvas(w, h) {
  const el = document.createElement('canvas');
  el.width = w;
  el.height = h;
  return el;
}

function roundRing(w, d, r, n = 6) {
  r = Math.min(r, w * 0.49, d * 0.49);
  const out = [];
  for (const [cx, cz, angle] of [
    [w / 2 - r, -d / 2 + r, -90],
    [w / 2 - r, d / 2 - r, 0],
    [-w / 2 + r, d / 2 - r, 90],
    [-w / 2 + r, -d / 2 + r, 180],
  ]) {
    for (let i = 0; i <= n; i++) {
      const a = (angle + (90 * i) / n) * RAD;
      out.push([cx + r * Math.cos(a), cz + r * Math.sin(a)]);
    }
  }
  return out;
}

// Equal-length rings give the shell a true rounded shoulder and an inset, shallow-dished top.
// 'tile' can select an atlas cell for a specific legend, both retaining the same smooth geometry.
function shell(w, d, rings, tile, segments = 6) {
  const pos = [],
    uv = [],
    idx = [];
  let count = 0;
  for (const [h, sx, sz, r] of rings) {
    const ring = roundRing(w * sx, d * sz, r, segments);
    count = ring.length;
    for (const [x, z] of ring) {
      pos.push(x, h, z);
      const u = clamp(x / w + 0.5, 0, 1),
        v = clamp(0.5 - z / d, 0, 1);
      uv.push(
        tile ? (tile.x + u) / tile.cols : u,
        tile ? (tile.rows - 1 - tile.y + v) / tile.rows : v,
      );
    }
  }
  for (let j = 0; j < rings.length - 1; j++)
    for (let i = 0; i < count; i++) {
      const b = j * count + i,
        n = j * count + ((i + 1) % count);
      idx.push(b, b + count, n, b + count, n + count, n);
    }
  // Capped centre fans close the shell at each terminal ring.
  for (const [j, top] of [
    [0, false],
    [rings.length - 1, true],
  ]) {
    const mid = pos.length / 3,
      row = j * count;
    pos.push(0, rings[j][0], 0);
    uv.push(
      tile ? (tile.x + 0.5) / tile.cols : 0.5,
      tile ? (tile.rows - tile.y - 0.5) / tile.rows : 0.5,
    );
    for (let k = 0; k < count; k++) {
      const a = row + k,
        b = row + ((k + 1) % count);
      if (top) idx.push(mid, b, a);
      else idx.push(mid, a, b);
    }
  }
  const g = new T.BufferGeometry();
  g.setAttribute('position', new T.Float32BufferAttribute(pos, 3));
  g.setAttribute('uv', new T.Float32BufferAttribute(uv, 2));
  g.setIndex(idx);
  g.computeVertexNormals();
  return g;
}

function solid(w, d, h, r = 0.5) {
  const e = Math.min(0.23, h * 0.2, w * 0.035, d * 0.035),
    sx = Math.max(0.1, 1 - (2 * e) / w),
    sz = Math.max(0.1, 1 - (2 * e) / d);
  return shell(
    w,
    d,
    [
      [0, sx, sz, Math.max(0.06, r - e)],
      [e, 1, 1, r],
      [h - e, 1, 1, r],
      [h, sx, sz, Math.max(0.06, r - e)],
      [h, sx * 0.92, sz * 0.92, Math.max(0.04, r * 0.85)],
    ],
    null,
    3,
  );
}

function outlineShape(points, rounding = 0.9) {
  const sh = new T.Shape();
  const a = points.map((v) => new T.Vector2(v[0], -v[1]));
  const at = (i) => a[(i + a.length) % a.length];
  for (let i = 0; i < a.length; i++) {
    const mid = at(i),
      prev = at(i - 1),
      next = at(i + 1),
      d = Math.min(
        rounding,
        mid.distanceTo(prev) * 0.38,
        mid.distanceTo(next) * 0.38,
      );
    const before = mid
      .clone()
      .add(prev.clone().sub(mid).normalize().multiplyScalar(d));
    const after = mid
      .clone()
      .add(next.clone().sub(mid).normalize().multiplyScalar(d));
    if (i === 0) sh.moveTo(before.x, before.y);
    else sh.lineTo(before.x, before.y);
    sh.quadraticCurveTo(mid.x, mid.y, after.x, after.y);
  }
  sh.closePath();
  return sh;
}
function plate(shape, thick) {
  const g = new T.ExtrudeGeometry(shape, {
    depth: thick,
    bevelEnabled: false,
    curveSegments: 3,
  });
  g.rotateX(-Math.PI / 2);
  g.clearGroups();
  return g;
}
function panelDecal(shape, bounds, underside = false) {
  const g = new T.ShapeGeometry(shape, 3);
  g.rotateX(-Math.PI / 2);
  const p = g.attributes.position,
    u = g.attributes.uv;
  for (let i = 0; i < p.count; i++)
    u.setXY(
      i,
      (p.getX(i) - bounds.x) / bounds.w,
      1 - (p.getZ(i) - bounds.z) / bounds.d,
    );
  if (underside) {
    const ix = g.index;
    for (let i = 0; i < ix.count; i += 3) {
      const a = ix.getX(i);
      ix.setX(i, ix.getX(i + 2));
      ix.setX(i + 2, a);
    }
    g.computeVertexNormals();
  }
  return g;
}
function bounds2(points) {
  const xx = points.map((p) => p[0]),
    zz = points.map((p) => p[1]),
    x = Math.min(...xx),
    z = Math.min(...zz);
  return { x, z, w: Math.max(...xx) - x, d: Math.max(...zz) - z };
}

function atlas(halves) {
  const keys = halves.flatMap((h) => h.keys),
    cols = 8,
    rows = Math.ceil(keys.length / cols),
    s = 128;
  const c = canvas(cols * s, rows * s),
    ctx = c.getContext('2d');
  const tiles = new Map();
  keys.forEach((k, i) => {
    const col = i % cols,
      row = Math.floor(i / cols),
      x = col * s,
      y = row * s;
    const label = String(k.label ?? '');
    const mod = k.thumb || (!/^[\p{L}\d]$/u.test(label) && label.length > 1);
    ctx.fillStyle = mod ? C.graphite : C.ivory;
    ctx.fillRect(x, y, s, s);
    ctx.fillStyle = mod ? C.lightInk : C.ink;
    let txt = label;
    // Abbreviated hardware legends, while the selection callback retains the layout's full label.
    const alias = {
      BACKSPACE: 'Bksp',
      SPACE: 'Space',
      ENTER: 'Enter',
      SHIFT: 'Shift',
      CONTROL: 'Ctrl',
      ESCAPE: 'Esc',
      DELETE: 'Del',
      TAB: 'Tab',
    };
    txt = alias[label.toUpperCase()] ?? label;
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    ctx.font = `${txt.length > 2 ? 500 : 550} ${txt.length > 4 ? 16 : txt.length > 2 ? 18 : 27}px Arial, sans-serif`;
    ctx.fillText(txt, x + 24, y + 42, s - 35);
    tiles.set(k, { x: col, y: row, cols, rows });
  });
  return { map: textureFrom(c), tiles };
}

function pcbPrint(half, b, under, cap) {
  const scale = Math.min(8, 1350 / Math.max(b.w, b.d)),
    c = canvas(Math.ceil(b.w * scale), Math.ceil(b.d * scale)),
    p = c.getContext('2d');
  p.scale(c.width / b.w, c.height / b.d);
  p.translate(-b.x, -b.z);
  p.fillStyle = under ? C.underMask : C.mask;
  p.fillRect(b.x, b.z, b.w, b.d);
  const drawPath = (pts, color, line) => {
    p.strokeStyle = color;
    p.lineWidth = line;
    p.beginPath();
    p.moveTo(...pts[0]);
    pts.slice(1).forEach((pt) => p.lineTo(...pt));
    p.stroke();
  };
  const spot = (x, z, rad, fill) => {
    p.beginPath();
    p.arc(x, z, rad, 0, Math.PI * 2);
    p.fillStyle = fill;
    p.fill();
  };
  const keys = half.keys;
  const nearest = keys.map((k) =>
    keys
      .filter((v) => v !== k)
      .sort(
        (a, b) =>
          Math.hypot(k.x - a.x, k.y - a.y) - Math.hypot(k.x - b.x, k.y - b.y),
      )
      .slice(0, 2),
  );
  keys.forEach((k, i) => {
    for (let j = 0; j < nearest[i].length; j++) {
      const o = nearest[i][j];
      if (keys.indexOf(o) < i) continue;
      for (let t = 0; t < 3; t++) {
        const dx = under ? -2.7 : 3.3,
          dz = 2.3 + t * 0.55,
          ax = k.x + dx,
          az = k.y + dz,
          bx = o.x + dx,
          bz = o.y + dz;
        const turn =
          Math.sign(bx - ax) *
          Math.min(Math.abs(bx - ax) * 0.4, Math.abs(bz - az) * 0.5 + 1.2);
        drawPath(
          [
            [ax, az],
            [ax + turn, az],
            [
              bx,
              bz - Math.sign(bz - az) * Math.min(2, Math.abs(bz - az) * 0.5),
            ],
            [bx, bz],
          ],
          under ? '#387061' : '#306758',
          0.2,
        );
      }
    }
    p.save();
    p.translate(k.x, k.y);
    p.rotate((k.a || 0) * RAD);
    p.strokeStyle = under ? '#81a698' : '#93aba0';
    p.lineWidth = 0.18;
    const ox = cap.swW / 2 - 0.16,
      oz = cap.swH / 2 - 0.16;
    for (const [sx, sz] of [
      [1, 1],
      [-1, 1],
      [-1, -1],
      [1, -1],
    ])
      drawPath(
        [
          [sx * (ox - 2.7), sz * oz],
          [sx * ox, sz * oz],
          [sx * ox, sz * (oz - 2.7)],
        ],
        under ? '#70988b' : '#a7bbb0',
        0.2,
      );
    p.font = '1.15px monospace';
    p.fillStyle = under ? '#a1b9a9' : '#c1cec3';
    p.fillText(`S${String(i + 1).padStart(2, '0')}`, -6.8, -5.6);
    [
      [-4.9, -2.1],
      [4.6, 2],
      [1.2, -5],
    ].forEach(([x, z], j) => {
      spot(x, z, 0.8 - j * 0.08, C.pad);
      spot(x, z, 0.35, '#202f29');
    });
    if (under) {
      p.fillStyle = '#a4aaa1';
      p.fillRect(-4.2, 2.6, 2.3, 1.05);
      p.fillRect(2.0, 2.6, 2.4, 1.05);
      p.fillStyle = '#2c332e';
      p.fillRect(-2.6, 2.1, 5.3, 2.1);
      spot(0, 0, 1.3, '#142c23');
    }
    p.restore();
  });
  // Pinhole witness marks follow each half's actual polygon, not a rectangular slab.
  const center = {
    x: keys.reduce((v, k) => v + k.x, 0) / keys.length,
    y: keys.reduce((v, k) => v + k.y, 0) / keys.length,
  };
  half.outline.forEach(([ax, az], i) => {
    const [bx, bz] = half.outline[(i + 1) % half.outline.length],
      l = Math.hypot(bx - ax, bz - az);
    if (l < 8) return;
    for (let d = 3.4; d < l - 2; d += 6.3) {
      const x = ax + ((bx - ax) * d) / l,
        z = az + ((bz - az) * d) / l,
        dist = Math.hypot(center.x - x, center.y - z) || 1;
      const px = x + (0.95 / dist) * (center.x - x),
        pz = z + (0.95 / dist) * (center.y - z);
      spot(px, pz, 0.34, '#aa9168');
      spot(px, pz, 0.14, C.mask);
    }
  });
  return textureFrom(c);
}

// Batch by material within each movable layer. Per-triangle intervals preserve precise picking.
function batch(group, objects) {
  const byMaterial = new Map();
  for (const it of objects) {
    if (!byMaterial.has(it.mat)) byMaterial.set(it.mat, []);
    byMaterial.get(it.mat).push(it);
  }
  for (const [mat, items] of byMaterial) {
    const geoms = [],
      spans = [];
    let end = 0;
    for (const it of items) {
      let g = it.g.index ? it.g.toNonIndexed() : it.g.clone();
      g.applyMatrix4(it.m);
      g.clearGroups();
      if (!g.getAttribute('normal')) g.computeVertexNormals();
      if (!g.getAttribute('uv'))
        g.setAttribute(
          'uv',
          new T.Float32BufferAttribute(
            new Float32Array(g.getAttribute('position').count * 2),
            2,
          ),
        );
      end += g.getAttribute('position').count / 3;
      spans.push([end, it.tag]);
      geoms.push(g);
    }
    const merged = mergeGeometries(geoms);
    geoms.forEach((g) => g.dispose());
    if (!merged) continue;
    const mesh = new T.Mesh(merged, mat);
    mesh.userData.spans = spans;
    mesh.castShadow = !mat.userData.flat;
    mesh.receiveShadow = true;
    group.add(mesh);
  }
}

function makeAssembly(state) {
  const data = layout(state),
    root = new T.Group(),
    groups = {},
    materials = new Map(),
    textures = [],
    cache = new Map(),
    sources = new Set();
  const std = (color, roughness = 0.7, metalness = 0) => {
    const id = `${color}/${roughness}/${metalness}`;
    if (!materials.has(id))
      materials.set(
        id,
        new T.MeshStandardMaterial({ color, roughness, metalness }),
      );
    return materials.get(id);
  };
  function mapped(map, flat = false) {
    const mat = new T.MeshStandardMaterial({
      map,
      roughness: 0.77,
      metalness: 0.04,
      polygonOffset: flat,
      polygonOffsetFactor: flat ? -1 : 0,
      polygonOffsetUnits: flat ? -2 : 0,
    });
    mat.userData.flat = flat;
    materials.set(mat.uuid, mat);
    textures.push(map);
    return mat;
  }
  const use = (key, fn) => {
    if (!cache.has(key)) cache.set(key, fn());
    return cache.get(key);
  };
  const box = (w, d, h, r = 0.5) =>
    use(`b:${[w, d, h, r]}`, () => solid(w, d, h, r));
  const rect = (w, d, h) =>
    use(`r:${[w, d, h]}`, () =>
      new T.BoxGeometry(w, h, d).translate(0, h / 2, 0),
    );
  const cyl = (rt, rb, h, n = 20) =>
    use(`c:${[rt, rb, h, n]}`, () =>
      new T.CylinderGeometry(rt, rb, h, n).translate(0, h / 2, 0),
    );
  const pipe = (pts, r) =>
    new T.TubeGeometry(
      new T.CatmullRomCurve3(pts.map((v) => new T.Vector3(...v))),
      18,
      r,
      6,
      false,
    );
  const keysAtlas = atlas(data.halves),
    capMat = mapped(keysAtlas.map);
  const pT = finite(SPECS.pcbT, 1.6),
    cap = data.cap,
    ulp = state.switchType === 'ulp';
  const capH = ulp ? 1.3 : 4.0;
  const contents = {};
  for (const name of ['pcb', 'keycaps', 'switches', 'electronics', 'back']) {
    groups[name] = new T.Group();
    root.add(groups[name]);
    contents[name] = [];
  }
  for (const half of data.halves) {
    const origin = transform(half.origin.x, 0, half.origin.y),
      hand = half.hand;
    let frame = origin,
      tag = { type: 'pcb', hand, label: 'Main PCB' };
    const part = (p, type, label) => {
      frame = p ? compose(origin, local(p)) : origin;
      tag = { type, hand, label };
    };
    const add = (layer, g, mat, x = 0, h = 0, z = 0, a = 0) => {
      sources.add(g);
      contents[layer].push({
        g,
        mat,
        m: compose(frame, transform(x, h, z, a)),
        tag,
      });
    };
    const bowl = outlineShape(half.outline),
      bounds = bounds2(half.outline);
    const covering = plate(bowl, pT),
      bottom = -pT;
    add('pcb', covering, std(C.core, 0.63), 0, bottom);
    for (const under of [false, true])
      add(
        'pcb',
        panelDecal(bowl, bounds, under),
        mapped(pcbPrint(half, bounds, under, cap), true),
        0,
        under ? bottom : 0,
      );
    part(null, 'back', 'Optional back cover');
    add('back', plate(bowl, 1), std(C.back, 0.67, 0.14), 0, -pT - 3.2);

    // Physical standoffs and screws follow known holes if supplied; no invented mounting drill spec.
    const holes = half.mounts || half.holes || [];
    if (!holes.length) {
      // Conceptual bonded spacer pucks only, not production hole locations or drill instructions.
      const support = half.keys
        .filter(
          (k) =>
            !k.thumb &&
            ((k.row === 0 && (k.c === 0 || k.c === 5)) ||
              (k.row === 2 && k.c === 4)),
        )
        .concat(half.keys.filter((k) => k.thumb && k.c === 0));
      for (const k of support)
        add(
          'back',
          cyl(2.05, 2.18, 2.2),
          std('#4b5048', 0.88),
          k.x,
          -pT - 2.2,
          k.y,
        );
      const cw = 24,
        ch = 9;
      const basePrint = chipText(
        cw,
        ch,
        [`TAPIR / ${hand === 'left' ? 'L' : 'R'}`, 'BASE    01'],
        C.back,
        '#b2b4a5',
        1.29,
        true,
      );
      const mark =
        half.keys.find((k) => !k.thumb && k.c === 2 && k.row === 1) ||
        half.keys[0];
      add('back', basePrint.g, basePrint.mat, mark.x, -pT - 3.2, mark.y);
    }
    for (const h of holes) {
      const x = Array.isArray(h) ? h[0] : h.x,
        z = Array.isArray(h) ? h[1] : h.y;
      if (!Number.isFinite(x) || !Number.isFinite(z)) continue;
      part(null, 'back', 'Back cover standoff');
      add(
        'back',
        cyl(1.55, 1.55, 2.2, 6),
        std(C.pad, 0.54, 0.42),
        x,
        -pT - 2.2,
        z,
      );
      add(
        'back',
        cyl(1.65, 1.45, 0.27),
        std(C.steel, 0.5, 0.48),
        x,
        -pT - 3.46,
        z,
      );
      part(null, 'pcb', 'PCB fastener');
      add('pcb', cyl(1.55, 1.7, 0.38), std(C.steel, 0.48, 0.48), x, 0.025, z);
      add('pcb', rect(1.7, 0.31, 0.03), std(C.black), x, 0.412, z, 22);
    }

    for (const k of half.keys) {
      part(k, 'switch', `${k.label} switch`);
      const sw = 'switches',
        S = (g, m, x = 0, h = 0, z = 0, a = 0) => add(sw, g, m, x, h, z, a);
      if (!ulp) {
        // Choc V1 + seated MBK: housing 5.0, stock post 8.0 at rest/5.0 bottomed out.
        S(box(cap.swW, cap.swH, 2.1, 1), std(C.black));
        S(box(13.45, 13.45, 2.47, 0.8), std(C.switch, 0.6), 0, 2.05);
        S(box(11.7, 10.25, 0.49, 0.62), std('#444b43'), 0, 4.51);
        for (const x of [-5.75, 5.75])
          S(rect(0.8, 7.6, 0.32), std('#999c8c'), x, 4.53);
        const stemEnd = 8.0 - (state.pressed ? cap.travel : 0);
        S(
          box(6.85, 4.55, Math.max(0.12, stemEnd - 4.78), 0.5),
          std('#d1cab3', 0.65),
          0,
          4.78,
        );
        for (const x of [-2.68, 2.68])
          S(rect(1.15, 2, 0.09), std(C.black), x, stemEnd - 0.09);
      } else {
        // The package drawing, not its larger solder-land pattern, defines the physical body.
        S(box(cap.swW, cap.swH, 0.53, 0.85), std(C.black));
        S(
          box(cap.swW - 0.64, cap.swH - 0.66, 0.55, 0.7),
          std('#999e90', 0.55, 0.38),
          0,
          0.5,
        );
        S(
          box(9.9, 9.9, state.pressed ? 0.21 : 0.55, 0.9),
          std('#464f47'),
          0,
          0.75,
        );
        for (const a of [-35, 35])
          S(
            box(12, 1.2, state.pressed ? 0.24 : 0.68, 0.3),
            std('#c5c7b9', 0.53, 0.4),
            0,
            state.pressed ? 0.86 : 1.5,
            0,
            a,
          );
        S(
          box(7.5, 5.2, state.pressed ? 0.2 : 0.48, 0.65),
          std('#c7c8b9'),
          0,
          state.pressed ? 0.92 : 2.02,
        );
      }
      part(k, 'keycap', k.label);
      const w = cap.w,
        h = cap.h,
        R = Math.min(2.0, w * 0.11),
        H = capH,
        top = cap.top - (state.pressed ? cap.travel : 0);
      const rings = [
        // Inner roof and sidewall let the skirt pass around the stock switch housing on a press.
        [H * 0.73, 0.2, 0.2, 0.47],
        [H * 0.73, 0.74, 0.74, 1.43],
        [H * 0.6, 0.84, 0.845, 1.63],
        [0.18, 0.87, 0.875, 1.69],
        [0, 0.87, 0.875, 1.72],
        [0, 0.93, 0.94, R],
        [0.19, 0.98, 0.985, R + 0.15],
        [0.42, 1, 1, R + 0.27],
        [H * 0.64, 0.957, 0.96, R + 0.19],
        [H * 0.88, 0.918, 0.925, R + 0.15],
        [H * 0.99, 0.883, 0.895, R + 0.12],
        [H, 0.836, 0.851, R + 0.04],
        [H - 0.08, 0.72, 0.73, 1.57],
        [H - 0.19, 0.42, 0.42, 1.12],
        [H - 0.25, 0.125, 0.13, 0.34],
      ];
      add(
        'keycaps',
        shell(w, h, rings, keysAtlas.tiles.get(k)),
        capMat,
        0,
        top - H,
      );
      if (k.label === 'F' || k.label === 'J')
        add(
          'keycaps',
          box(2.25, 0.48, 0.12, 0.19),
          std('#ded8c9', 0.8),
          0,
          top - 0.12,
          h * 0.3,
        );
      if (!ulp) {
        for (const x of [-2.68, 2.68])
          add(
            'keycaps',
            box(1.1, 1.85, 1.45, 0.15),
            std('#c7c4b6', 0.71),
            x,
            top - 2.51,
          );
      }
    }

    function chipText(w, d, lines, base, ink, size = 1.1, under = false) {
      const c = canvas(320, Math.max(85, Math.round((320 * d) / w))),
        p = c.getContext('2d');
      p.fillStyle = base;
      p.fillRect(0, 0, c.width, c.height);
      p.fillStyle = ink;
      p.textAlign = 'center';
      p.textBaseline = 'middle';
      p.font = `500 ${(size * c.width) / w}px monospace`;
      lines.forEach((line, i) =>
        p.fillText(
          line,
          c.width / 2,
          c.height * (0.5 + ((i - (lines.length - 1) / 2) * size * 1.3) / d),
          c.width * 0.91,
        ),
      );
      const g = new T.PlaneGeometry(w, d).rotateX(
        under ? Math.PI / 2 : -Math.PI / 2,
      );
      return { g, mat: mapped(textureFrom(c), true) };
    }
    function E(g, m, x = 0, h = 0, z = 0, a = 0) {
      add('electronics', g, m, x, h, z, a);
    }
    if (half.controller) {
      const cs = SPECS.controller,
        w = cs.w,
        d = cs.h,
        pcbH = Math.min(0.95, finite(cs.t, 0.85));
      part(half.controller, 'controller', 'XIAO nRF52840 Plus');
      // Castellated carrier and recessed USB-C mouth, port facing the rear of the half.
      E(box(w, d, pcbH, 0.85), std('#273e36', 0.7, 0.15), 0, 0.14);
      for (let j = 0; j < 7; j++)
        for (const s of [-1, 1]) {
          const z = -d / 2 + 2.6 + (j * (d - 5.2)) / 6;
          E(
            box(2.15, 1.53, 0.17, 0.34),
            std(C.pad, 0.43, 0.5),
            s * (w / 2 - 1),
            0.15 + pcbH,
            z,
          );
          E(
            cyl(0.39, 0.39, 0.055, 12),
            std('#294035'),
            s * (w / 2 - 0.77),
            0.331 + pcbH,
            z,
          );
        }
      const chipY = 0.15 + pcbH;
      E(box(7.3, 7.05, 1.13, 0.45), std('#aeb1a5', 0.45, 0.55), 0, chipY, 0.35);
      const rf = chipText(
        6.65,
        5.8,
        ['nRF52840', 'XIAO +'],
        '#b8bcb0',
        '#455048',
        0.78,
      );
      E(rf.g, rf.mat, 0, chipY + 1.145, 0.4);
      for (let j = 0; j < 4; j++) {
        E(
          rect(1.18, 0.65, 0.44),
          std(j % 2 ? C.silver : '#af9568', 0.57, 0.18),
          -4.8,
          chipY,
          -3.1 + j * 1.63,
        );
      }
      E(box(5.2, 1.7, 0.69, 0.16), std('#d1cbb7'), 0.9, chipY, d / 2 - 1.8);
      E(
        box(3, 2, 0.59, 0.16),
        std('#a8b0a2', 0.5, 0.28),
        -3.3,
        chipY,
        d / 2 - 3.1,
      );
      E(
        box(1.25, 1.2, 0.25, 0.22),
        std('#464e45'),
        -3.3,
        chipY + 0.6,
        d / 2 - 3.1,
      );
      const portW = Math.min(w * 0.57, 9.0),
        portD = 6.6,
        portY = chipY + 0.07,
        portH = Math.max(2.4, finite(cs.t, 4.8) - portY),
        portZ = -d / 2 + portD / 2 + 0.12;
      E(
        box(portW, portD, portH, 0.69),
        std(C.steel, 0.36, 0.67),
        0,
        portY,
        portZ,
      );
      const faceZ = portZ - portD / 2 - 0.045; // Face toward outside: opening is not painted on the top.
      E(
        box(portW - 1.15, 0.14, portH - 1.03, 0.06),
        std('#272c28', 0.63),
        0,
        portY + 0.43,
        faceZ,
      );
      E(
        rect(portW - 3.05, 0.14, 0.39),
        std('#738070', 0.54, 0.22),
        0,
        portY + 1.08,
        faceZ - 0.082,
      );
      for (let s of [-1, 1])
        E(
          rect(0.65, 1.55, 0.07),
          std('#737c70', 0.5, 0.28),
          s * 2.6,
          portY + portH - 0.07,
          -d / 2 + 2.2,
        );
      E(
        box(0.68, 0.85, 0.34, 0.16),
        std('#ddbf76'),
        w / 2 - 3.1,
        chipY,
        -d / 2 + 2.8,
      );
    }
    if (half.battery) {
      part(half.battery, 'battery', 'LiPo pouch');
      const bs = SPECS.battery,
        w = half.battery.w ?? bs.w,
        d = half.battery.h ?? bs.h,
        t = finite(state.batteryT, bs.t),
        y = 0;
      const wr = w - 1,
        dr = d - 1;
      E(box(w, d, 0.31, 0.7), std('#aea99b', 0.53, 0.4), 0, y);
      E(
        shell(wr, dr, [
          [0, 0.96, 0.96, 1.05],
          [0.23, 1, 0.99, 1.13],
          [t * 0.4, 1, 1, 1.4],
          [t * 0.78, 0.99, 0.99, 1.52],
          [t - 0.14, 0.962, 0.96, 1.5],
          [t, 0.91, 0.91, 1.36],
          [t, 0.7, 0.71, 1.1],
        ]),
        std('#caccc1', 0.46, 0.47),
        0,
        y,
      );
      const bandD = Math.min(3.2, d * 0.22);
      E(
        box(wr * 0.985, bandD, 0.4, 0.34),
        std('#c19a4d', 0.5, 0.28),
        0,
        y + t - 0.4,
        -d / 2 + bandD * 0.62,
      );
      const label = chipText(
        w * 0.73,
        d * 0.54,
        ['Li-POLY', '3.7 V'],
        '#c8c9bd',
        '#666d61',
        Math.min(1.13, w * 0.063),
      );
      E(label.g, label.mat, 0, y + t, 0.5);
    }
    if (half.pointer) {
      const pointer = half.pointer,
        ps = SPECS.pointer,
        { w, h: d, t } = ps;
      part(pointer, 'pointer', 'TrackPoint');
      const stemTop = pointer.stemTop,
        rubberTop = pointer.capTop,
        rad = ps.cap / 2,
        offset = ps.axisToBoardCenter;
      E(box(w, d, t, 0.48), std('#60856c', 0.67), 0, 0, offset);
      E(
        box(Math.min(4.4, w * 0.65), Math.min(4.15, d * 0.6), 0.55, 0.3),
        std('#c2b799', 0.6, 0.3),
        0,
        t + 0.04,
        0.12,
      );
      // Bare sensor package, stock stem, and a separate length-compensating hub.
      E(
        box(ps.stem, ps.stem, ps.stem, 0.18),
        std('#b3a78c', 0.6, 0.18),
        0,
        t,
        0,
      );
      const rubberH = Math.min(1.9, Math.max(1.1, rubberTop - stemTop - 0.12));
      const hubT = Math.max(0.12, rubberTop - rubberH - stemTop);
      E(cyl(0.99, 1.12, hubT, 16), std('#9d7964', 0.45, 0.38), 0, stemTop);
      E(
        cyl(rad * 0.86, rad * 0.71, 0.32, 36),
        std(C.ruby, 0.85),
        0,
        rubberTop - rubberH,
      );
      E(
        cyl(rad, rad * 0.88, rubberH - 0.64, 36),
        std(C.red, 0.91),
        0,
        rubberTop - rubberH + 0.3,
      );
      E(cyl(rad * 0.9, rad, 0.27, 36), std(C.red, 0.92), 0, rubberTop - 0.36);
      for (let j = -3; j <= 3; j++)
        for (let i = -3; i <= 3; i++) {
          const x = (i + Math.abs(j % 2) * 0.5) * 0.54,
            z = j * 0.49;
          if (x * x + z * z > (rad * 0.81) ** 2) continue;
          E(
            cyl(0.13, 0.18, 0.1, 7),
            std('#d45238', 0.94),
            x,
            rubberTop - 0.1,
            z,
          );
        }
    }
    if (half.driver) {
      part(half.driver, 'driver', 'Pointing module driver reserve');
      const d = half.driver,
        w = finite(d.w, 13),
        h = finite(d.h, 16),
        t = finite(d.t, 0.8);
      E(box(w, h, t, 0.68), std('#858476', 0.68), 0, 0);
      const c = canvas(360, 240),
        p = c.getContext('2d');
      p.scale(360 / w, 240 / h);
      p.fillStyle = '#858476';
      p.fillRect(0, 0, w, h);
      p.strokeStyle = '#979687';
      p.lineWidth = 0.18;
      for (let x = -h; x < w + h; x += 1.5) {
        p.beginPath();
        p.moveTo(x, 0);
        p.lineTo(x + h, h);
        p.stroke();
      }
      p.fillStyle = '#77796d';
      p.fillRect(w * 0.11, h * 0.22, w * 0.78, h * 0.56);
      p.fillStyle = '#eeeada';
      p.font = '600 2.0px monospace';
      p.textBaseline = 'middle';
      p.textAlign = 'center';
      p.fillText('DRIVER', w * 0.5, h * 0.43);
      p.font = '1.15px monospace';
      p.fillText('KEEP-OUT', w * 0.5, h * 0.64);
      E(
        new T.PlaneGeometry(w * 0.94, h * 0.92).rotateX(-Math.PI / 2),
        mapped(textureFrom(c), true),
        0,
        t,
        0,
      );
    }
    if (half.battery && half.controller) {
      // Paired, insulated conductors; route only through the service bay between both bodies.
      part(null, 'battery', 'LiPo pouch leads');
      const b = half.battery,
        q = half.controller,
        bt = finite(state.batteryT, 3);
      const vb = new T.Vector2(q.x - b.x, q.y - b.y),
        dist = vb.length();
      if (dist > 1) {
        vb.normalize();
        const bW = finite(b.w, SPECS.battery.w),
          bD = finite(b.h, SPECS.battery.h),
          cW = SPECS.controller.w,
          cD = SPECS.controller.h;
        const reach = (w, d, p, v) => {
          const a = -(p.a || 0) * RAD,
            x = v.x * Math.cos(a) - v.y * Math.sin(a),
            z = v.x * Math.sin(a) + v.y * Math.cos(a);
          return Math.min(
            (w * 0.49) / (Math.abs(x) || 1e-6),
            (d * 0.49) / (Math.abs(z) || 1e-6),
          );
        };
        const br = reach(bW, bD, b, vb),
          cr = reach(cW, cD, q, vb);
        const sx = b.x + vb.x * br,
          sz = b.y + vb.y * br,
          ex = q.x - vb.x * (cr - 0.55),
          ez = q.y - vb.y * (cr - 0.55);
        if ((ex - sx) * vb.x + (ez - sz) * vb.y > -0.5)
          for (let i = 0; i < 2; i++) {
            const shift = (i - 0.5) * 0.65,
              nx = -vb.y,
              nz = vb.x;
            E(
              pipe(
                [
                  [sx + nx * shift, Math.max(0.7, bt - 0.65), sz + nz * shift],
                  [
                    (sx + ex) / 2 + nx * (1.7 + shift),
                    Math.max(1.3, bt - 0.7),
                    (sz + ez) / 2 + nz * (1.7 + shift),
                  ],
                  [ex + nx * shift, 1.02, ez + nz * shift],
                ],
                0.22,
              ),
              std(i ? '#46483f' : '#ab5944', 0.75),
            );
          }
      }
    }
    for (const [i, m] of (half.mouse || []).entries()) {
      part(
        m,
        'mouse',
        m.label || ['Left click', 'Middle click', 'Right click'][i],
      );
      const w = 4.2,
        d = 3.2,
        pw = finite(m.w, 8),
        pd = finite(m.h, 5);
      E(box(w, d, 1.12, 0.39), std(C.black), 0, 0.02);
      E(
        box(w * 0.98, d * 0.94, 0.55, 0.32),
        std('#a6a99c', 0.55, 0.33),
        0,
        1.14,
      );
      E(cyl(1.03, 1.11, 0.81), std('#575e52'), 0, 1.69);
      E(box(pw, pd, 0.82, 1.05), std('#686b5e'), 0, 2.5);
      for (let j = 0; j <= i; j++)
        E(
          box(0.28, 1.45, 0.08, 0.12),
          std('#c6c7ba'),
          (j - i * 0.5) * 0.75,
          3.325,
        );
    }
  }
  for (const [key, arr] of Object.entries(contents)) batch(groups[key], arr);
  sources.forEach((g) => g.dispose());
  return {
    root,
    groups,
    data,
    dispose() {
      root.traverse((o) => {
        if (o.geometry) o.geometry.dispose();
      });
      textures.forEach((t) => t.dispose());
      materials.forEach((m) => m.dispose());
    },
  };
}

const OFFSETS = {
  assembled: { keycaps: 0, switches: 0, pcb: 0, electronics: 0, back: 0 },
  exploded: { keycaps: 35, switches: 16, pcb: 0, electronics: 12, back: -14 },
};
const asV = (v) => new T.Vector3(...v);
const dirFor = (view, mode) => {
  const under = mode === 'underside';
  if (view === 'top') return asV([0, under ? -1 : 1, 0.0001]).normalize();
  if (view === 'front') return asV([0, under ? -0.032 : 0.032, 1]).normalize();
  return asV([0.33, under ? -0.97 : 0.96, 1.06]).normalize();
};

/** A transparent, orthographic WebGL model viewport. update() accepts a complete layout state. */
export function createViewer(host, onPick) {
  const renderer = new T.WebGLRenderer({
    alpha: true,
    antialias: true,
    powerPreference: 'high-performance',
    preserveDrawingBuffer: true,
  });
  renderer.setClearColor(0x000000, 0);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));
  renderer.outputColorSpace = T.SRGBColorSpace;
  renderer.toneMapping = T.NoToneMapping;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = T.PCFSoftShadowMap;
  const el = renderer.domElement;
  el.style.cssText =
    'display:block;width:100%;height:100%;touch-action:none;cursor:grab;';
  el.setAttribute('aria-label', '3D assembly of the Tapir split keyboard');
  host.appendChild(el);
  const scene = new T.Scene(),
    cam = new T.OrthographicCamera(-150, 150, 100, -100, 0.1, 3500);
  cam.position.set(65, 220, 230);
  const controls = new OrbitControls(cam, el);
  controls.enableDamping = false;
  controls.screenSpacePanning = true;
  controls.rotateSpeed = 0.65;
  controls.zoomSpeed = 0.97;
  controls.panSpeed = 0.74;
  controls.minZoom = 0.35;
  controls.maxZoom = 12;
  controls.minPolarAngle = 0.00001;
  controls.maxPolarAngle = Math.PI - 0.00001;

  const hemi = new T.HemisphereLight(0xfffaf0, 0xc7c9b7, 1.62);
  scene.add(hemi);
  const key = new T.DirectionalLight(0xfff9f0, 2.1);
  key.position.set(-125, 260, 110);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  key.shadow.camera.left = -225;
  key.shadow.camera.right = 225;
  key.shadow.camera.top = 170;
  key.shadow.camera.bottom = -170;
  key.shadow.camera.near = 1;
  key.shadow.camera.far = 650;
  key.shadow.bias = -0.00016;
  key.shadow.normalBias = 0.045;
  scene.add(key, key.target);
  const rim = new T.DirectionalLight(0xf3f6f8, 0.68);
  rim.position.set(100, 80, -115);
  scene.add(rim);
  const groundGeo = new T.PlaneGeometry(1800, 1550).rotateX(-Math.PI / 2),
    groundMat = new T.ShadowMaterial({
      color: '#333629',
      opacity: 0.19,
      depthWrite: false,
    });
  const ground = new T.Mesh(groundGeo, groundMat);
  ground.receiveShadow = true;
  ground.renderOrder = -2;
  scene.add(ground);

  let model = null,
    state = null,
    signature = '',
    width = 1,
    height = 1,
    span = 130,
    disposed = false,
    reflow = null,
    raf = 0,
    transition = null;
  let currentView = 'iso',
    currentMode = 'assembled',
    ready = false,
    manual = false;
  const reduced =
    window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
  const ray = new T.Raycaster();
  let start = null;
  function frustum() {
    const aspect = width / height;
    cam.left = -span * aspect * 0.5;
    cam.right = -cam.left;
    cam.top = span * 0.5;
    cam.bottom = -cam.top;
    cam.updateProjectionMatrix();
  }
  function draw() {
    if (disposed) return;
    ground.visible = cam.position.y > ground.position.y + 3 && model != null;
    renderer.render(scene, cam);
  }
  function schedule() {
    if (!raf && !disposed) {
      raf = requestAnimationFrame((now) => {
        raf = 0;
        if (transition) {
          const t = clamp((now - transition.begin) / 300, 0, 1),
            e = 1 - (1 - t) ** 3;
          controls.target.lerpVectors(transition.t0, transition.t1, e);
          cam.position.lerpVectors(transition.c0, transition.c1, e);
          span = T.MathUtils.lerp(transition.s0, transition.s1, e);
          cam.zoom = T.MathUtils.lerp(transition.z0, 1, e);
          frustum();
          controls.update();
          if (t === 1) transition = null;
          else schedule();
        }
        draw();
      });
    }
  }
  controls.addEventListener('change', schedule);
  controls.addEventListener('start', () => {
    transition = null;
    manual = true;
    el.style.cursor = 'grabbing';
  });
  controls.addEventListener('end', () => {
    el.style.cursor = 'grab';
    schedule();
  });

  function fit(view) {
    if (!model) return null;
    const direction = dirFor(view, currentMode),
      right = new T.Vector3()
        .crossVectors(new T.Vector3(0, 1, 0), direction)
        .normalize(),
      up = new T.Vector3().crossVectors(direction, right).normalize();
    const coords = model.data.halves.flatMap((h) =>
      h.outline.map(([x, z]) => [x + h.origin.x, z + h.origin.y]),
    );
    const heights =
      currentMode === 'exploded'
        ? [-19, 48]
        : [
            -5,
            Math.max(model.data.cap.top + 1.2, finite(state?.batteryT, 3.3)),
          ];
    let minX = Infinity,
      maxX = -Infinity,
      minY = Infinity,
      maxY = -Infinity,
      minD = Infinity,
      maxD = -Infinity;
    for (const [x, z] of coords)
      for (const y of heights) {
        const p = new T.Vector3(x, y, z),
          px = p.dot(right),
          py = p.dot(up),
          pd = p.dot(direction);
        minX = Math.min(minX, px);
        maxX = Math.max(maxX, px);
        minY = Math.min(minY, py);
        maxY = Math.max(maxY, py);
        minD = Math.min(minD, pd);
        maxD = Math.max(maxD, pd);
      }
    const target = right
      .clone()
      .multiplyScalar((minX + maxX) / 2)
      .addScaledVector(up, (minY + maxY) / 2)
      .addScaledVector(direction, (minD + maxD) / 2);
    const viewSpan = Math.max(
      ((maxX - minX) / (width / height)) * 1.093,
      (maxY - minY) * 1.24,
      54,
    );
    return {
      target,
      pos: target.clone().addScaledVector(direction, 520),
      span: viewSpan,
    };
  }
  function setView(view = currentView, immediate = false) {
    currentView = view;
    const f = fit(view);
    if (!f) return;
    manual = false;
    if (immediate || reduced || !ready) {
      transition = null;
      controls.target.copy(f.target);
      cam.position.copy(f.pos);
      span = f.span;
      cam.zoom = 1;
      frustum();
      controls.update();
      draw();
    } else {
      transition = {
        begin: performance.now(),
        t0: controls.target.clone(),
        t1: f.target,
        c0: cam.position.clone(),
        c1: f.pos,
        s0: span,
        s1: f.span,
        z0: cam.zoom,
      };
      schedule();
    }
    ready = true;
  }
  function resize() {
    const rect = host.getBoundingClientRect();
    const w = Math.max(1, Math.round(rect.width)),
      h = Math.max(1, Math.round(rect.height));
    if (w === width && h === height) return;
    width = w;
    height = h;
    renderer.setSize(width, height, false);
    if (model && !manual) setView(currentView, true);
    else {
      frustum();
      schedule();
    }
  }
  function update(next) {
    if (disposed || !next) return;
    const first = !model,
      oldMode = currentMode,
      oldView = state?.view;
    const geom = JSON.stringify([
      next.switchType,
      next.splay,
      next.gap,
      next.nubY,
      next.separation,
      next.batteryT,
      next.pressed,
      next.mouseButtons,
    ]);
    if (geom !== signature || !model) {
      const nextAssembly = makeAssembly(next);
      if (model) {
        scene.remove(model.root);
        model.dispose();
      }
      model = nextAssembly;
      signature = geom;
      scene.add(model.root);
    }
    state = { ...next, layers: { ...next.layers } };
    currentMode = next.mode || 'assembled';
    const offs = OFFSETS[currentMode] || OFFSETS.assembled;
    for (const [name, g] of Object.entries(model.groups)) {
      g.visible = next.layers?.[name] !== false;
      g.position.y = offs[name] || 0;
    }
    ground.position.y =
      (next.layers?.back === false
        ? -finite(SPECS.pcbT, 1.6)
        : -(finite(SPECS.pcbT, 1.6) + 3.2)) +
      (next.layers?.back === false ? 0 : offs.back) -
      0.13;
    if (
      first ||
      next.view !== oldView ||
      (oldMode === 'underside') !== (currentMode === 'underside')
    )
      setView(next.view || 'iso', first);
    else if (oldMode !== currentMode && !manual) setView(currentView);
    else schedule();
    model.root.updateMatrixWorld(true);
  }
  function down(ev) {
    if (ev.button === 0) start = [ev.clientX, ev.clientY, ev.pointerId];
  }
  function up(ev) {
    if (!start || start[2] !== ev.pointerId || !model || !onPick) return;
    const [x, y] = start;
    start = null;
    if (Math.hypot(x - ev.clientX, y - ev.clientY) > 5) return;
    const r = el.getBoundingClientRect(),
      px = ((ev.clientX - r.left) / r.width) * 2 - 1,
      py = 1 - ((ev.clientY - r.top) / r.height) * 2;
    cam.updateMatrixWorld();
    ray.setFromCamera(new T.Vector2(px, py), cam);
    const meshes = Object.values(model.groups)
        .filter((g) => g.visible)
        .flatMap((g) => g.children),
      hit = ray.intersectObjects(meshes, false)[0];
    if (hit) {
      const mark = hit.object.userData.spans?.find(
        ([end]) => hit.faceIndex < end,
      )?.[1];
      if (mark) onPick({ ...mark });
    }
  }
  function cancel() {
    start = null;
  }
  el.addEventListener('pointerdown', down);
  el.addEventListener('pointerup', up);
  el.addEventListener('pointercancel', cancel);
  reflow = new ResizeObserver(resize);
  reflow.observe(host);
  resize();
  function destroy() {
    disposed = true;
    if (raf) cancelAnimationFrame(raf);
    reflow?.disconnect();
    controls.dispose();
    el.removeEventListener('pointerdown', down);
    el.removeEventListener('pointerup', up);
    el.removeEventListener('pointercancel', cancel);
    model?.dispose();
    groundGeo.dispose();
    groundMat.dispose();
    key.shadow.map?.dispose();
    renderer.dispose();
    el.remove();
  }
  return { update, setView, resize, destroy };
}
