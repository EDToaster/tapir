// Right-half layout XY (mm, +Y palm); Z=0 is the keyboard carrier top.
// This is an ALTERNATIVE layout. Do not attach these solids to the baseline
// XIAO or interpret an old shaft hole as a valid Plus solder land pattern.
import polyclip from 'polygon-clipping';
import {
  INITIAL,
  PRESETS,
  SPECS,
  clearance,
  layout,
  prismGap,
  rect,
  rotate,
} from './layout.js';

export const STACK_DEFAULTS = Object.freeze({
  orientation: 'palm',
  offsetX: 6,
  offsetY: -2,
  gap: 0.8,
  headAcross: 28,
  headShift: -2,
  sensorFlip: true,
});
export const STACK_SOURCES = Object.freeze({
  xiao: 'https://files.seeedstudio.com/wiki/XIAO-BLE/Seeed_Studio_XIAO_nRF52840_Plus.zip',
  seeed: 'https://wiki.seeedstudio.com/XIAO_BLE/',
  sensor: 'https://docs.holykeebs.com/datasheets/SK8707-01.pdf#page=6',
  mounting: 'https://docs.holykeebs.com/guides/trackpoint-module/',
  precedent: 'https://codeberg.org/humanplayer2/trackpoint_on_rp2040zero',
});
// Seeed Plus v1.1 Edge.Cuts bounding box and front antenna footprint origin.
// USB points toward local -Y; x is viewer's right in this top-side frame.
const X = { w: 17.78, h: 20.955, t: SPECS.controller.t, antenna: [-1.8, 9.41] };
const P = SPECS.pointer;
const angles = { keys: 0, outer: 90, palm: 180, inner: -90 };
const anglesOK = (s) => Object.hasOwn(angles, s);
const num = (v, d, min, max) =>
  Number.isFinite(v) ? Math.max(min, Math.min(max, v)) : d;
const box = (poly) => {
  const x = poly.map((p) => p[0]),
    y = poly.map((p) => p[1]);
  const x0 = Math.min(...x),
    x1 = Math.max(...x),
    y0 = Math.min(...y),
    y1 = Math.max(...y);
  return { x0, x1, y0, y1, w: x1 - x0, h: y1 - y0 };
};
const delta = (q, u, v) => {
  const [x, y] = rotate([u, v], q.a || 0);
  return { x: q.x + x, y: q.y + y, a: q.a || 0 };
};
const point = (q) => [q.x, q.y];
const mid = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
const ring = (c, r, n = 32) =>
  Array.from({ length: n }, (_, i) => [
    c.x + r * Math.cos((i * 2 * Math.PI) / n),
    c.y + r * Math.sin((i * 2 * Math.PI) / n),
  ]);
const inflateBox = (b, g) =>
  rect(
    { x: (b.x0 + b.x1) / 2, y: (b.y0 + b.y1) / 2 },
    b.w + 2 * g,
    b.h + 2 * g,
  );
const signedNum = (n) =>
  Math.abs(n) < 0.005 ? '0' : Number(n.toFixed(2)).toString().replace('-', '−');
const area = (poly) =>
  Math.abs(
    poly.reduce((t, [x, y], i) => {
      let p = poly[(i + 1) % poly.length];
      return t + x * p[1] - y * p[0];
    }, 0),
  ) / 2;
const near = (a, b, fn = prismGap) => {
  let val = Infinity,
    pair = [];
  for (const p of a)
    for (const q of b) {
      const d = fn(p, q);
      if (d < val) {
        val = d;
        pair = [p.label, q.label];
      }
    }
  return { val, pair };
};
const planar = (p, q) => clearance(p.polygon, q.polygon);
function rayToEdge(start, direction, poly) {
  // Ray from the USB mouth through the outer contour. Use the last crossing:
  // a concave carrier may exit and reenter before reaching free space.
  let far = 0;
  const cross = (a, b) => a[0] * b[1] - a[1] * b[0];
  for (let i = 0; i < poly.length; i++) {
    const a = poly[i],
      b = poly[(i + 1) % poly.length],
      e = [b[0] - a[0], b[1] - a[1]],
      v = [a[0] - start[0], a[1] - start[1]];
    const den = cross(direction, e);
    if (Math.abs(den) < 1e-9) continue;
    const u = cross(v, direction) / den,
      t = cross(v, e) / den;
    if (u >= 0 && u <= 1 && t > far) far = t;
  }
  return far;
}

/**
 * stackModel(options?, layoutState?) creates an independent top-mounted study;
 * offsets are from the sensor PCB CENTER, not the displaced shaft. headAcross
 * is additional +X travel; headShift is +Y travel from the current thumb layout. sensorFlip reverses
 * the contact edge while preserving the shaft. gap is the free Z clearance
 * from the 5 mm XIAO mounting envelope to the proposed bridging daughterboard.
 * Solids: {id,role,label,kind,polygon:[[x,y],...],bottom,top}; kind='rigid'
 * means conceptual material, NOT measured CAD; 'envelope' is a swept/reserved
 * volume, 'reference' is not part of the proposed assembly. All units mm.
 * Checks: {id,label,status:'clash'|'screen'|'open',value:number|null,detail}.
 * No output from this function is permission to declare production fit.
 */
export function stackModel(options = {}, layoutState = {}) {
  const d = STACK_DEFAULTS;
  const o = {
    orientation: anglesOK(options.orientation)
      ? options.orientation
      : d.orientation,
    offsetX: num(options.offsetX, d.offsetX, -18, 18),
    offsetY: num(options.offsetY, d.offsetY, -18, 18),
    gap: num(options.gap, d.gap, 0, 6),
    headShift: num(options.headShift, d.headShift, -18, 18),
    headAcross: num(options.headAcross, d.headAcross, -18, 54),
    sensorFlip:
      typeof options.sensorFlip === 'boolean'
        ? options.sensorFlip
        : d.sensorFlip,
  };
  const state = {
    ...INITIAL,
    ...layoutState,
    ...PRESETS.thumb,
    thumbX: layoutState.thumbX ?? 0,
    thumbY: layoutState.thumbY ?? 0,
  };
  const base = layout(state),
    h = base.halves[1],
    p = h.pointer;
  const head = {
    x: p.x + o.headAcross,
    y: p.y + o.headShift,
    a: o.sensorFlip ? 270 : 90,
  };
  const sensor = delta(head, 0, P.axisToBoardCenter);
  const controller = {
    x: sensor.x + o.offsetX,
    y: sensor.y + o.offsetY,
    a: angles[o.orientation],
  };
  const solids = [];
  function put(id, role, label, kind, polygon, bottom, top) {
    let s = { id, role, label, kind, polygon, bottom, top };
    solids.push(s);
    return s;
  }
  const cub = (id, role, label, kind, q, w, l, z0, z1) =>
    put(id, role, label, kind, rect(q, w, l), z0, z1);
  const controllerSolid = cub(
    'xiao',
    'controller',
    'XIAO assembled allowance',
    'envelope',
    controller,
    X.w,
    X.h,
    0,
    X.t,
  );
  const boardSolid = cub(
    'xiao-board',
    'controller-board',
    'XIAO PCB, 1.6 mm nominal',
    'rigid',
    controller,
    X.w,
    X.h,
    0.15,
    1.75,
  );
  // Plus USB1 F.Fab: X ±4.50, Y −11.99…−4.64. This establishes shell plan,
  // NOT connector mating datum nor shell Z (the latter remains an allowance).
  const usb = cub(
    'usb-shell',
    'usb-shell',
    'USB-C shell, fab plan / assumed Z',
    'rigid',
    delta(controller, 0, (-11.99 - 4.64) / 2),
    9,
    7.35,
    1.75,
    5,
  );
  const antenna = delta(controller, ...X.antenna);
  const rf = cub(
    'rf-screen',
    'rf-screen',
    'Antenna neighborhood (6 × 6 assumption)',
    'envelope',
    antenna,
    6,
    6,
    -2,
    18,
  );
  const mouth = delta(controller, 0, -11.99),
    exit = rotate([0, -1], controller.a);
  const sensorPoly = rect(sensor, P.w, P.h);
  // Four proposed dielectric support feet flank the module rather than bearing
  // on it. Constrain their longitudinal position while following the head.
  const local = rotate(
    [sensor.x - controller.x, sensor.y - controller.y],
    -controller.a,
  );
  const railV = mid(local[1], -X.h / 2 + 4.5, X.h / 2 - 4.5),
    deckZ = X.t + o.gap;
  const feet = [];
  for (const s of [-1, 1])
    for (const t of [-1, 1]) {
      const q = delta(controller, s * (X.w / 2 + 0.6 + 0.9), railV + t * 3);
      feet.push(
        cub(
          'foot-' + feet.length,
          'support',
          'Bridge foot ' + (feet.length + 1),
          'rigid',
          q,
          1.8,
          2.2,
          0,
          deckZ,
        ),
      );
    }
  // Bounding stock around the actual feet + sensor (0.35 mm per edge). It is
  // not a purchased bracket; holes, fasteners, pads and copper remain open.
  const deckPoly = inflateBox(
    box([...sensorPoly, ...feet.flatMap((f) => f.polygon)]),
    0.35,
  );
  const deck = put(
    'bridge',
    'bridge',
    'Independent bridge PCB',
    'rigid',
    deckPoly,
    deckZ,
    deckZ + 0.8,
  );
  const sensorZ = deck.top + 0.15,
    sensorCard = put(
      'sensor',
      'sensor',
      'Detached sensor PCB envelope',
      'rigid',
      sensorPoly,
      sensorZ,
      sensorZ + P.t,
    );
  const post = cub(
    'post',
    'post',
    'Stock square post',
    'rigid',
    head,
    P.stem,
    P.stem,
    sensorCard.top,
    sensorCard.top + P.stem,
  );
  const cap = put(
    'stick-cap',
    'stick-cap',
    'Rubber cap allowance',
    'envelope',
    ring(head, P.cap / 2),
    post.top - 0.6,
    post.top + 1.1,
  );
  const face = put(
    'sensor-face',
    'face-reserve',
    'Unmapped sensor face',
    'envelope',
    sensorPoly,
    sensorCard.top,
    sensorCard.top + P.frontReserve,
  );
  const oldCarrier = put(
    'original-carrier',
    'original-carrier',
    'Existing right-half perimeter',
    'reference',
    h.outline,
    -SPECS.pcbT,
    0,
  );
  const oldXiao = cub(
    'original-xiao',
    'original-controller',
    'Former XIAO site',
    'reference',
    h.controller,
    SPECS.controller.w,
    SPECS.controller.h,
    0,
    X.t,
  );
  // Preserve the old board perimeter; no speculative shrink of the rear bay.
  // Add 1.5 mm around the board and bridge as a local carrier margin.
  const extra = inflateBox(box([...controllerSolid.polygon, ...deckPoly]), 1.5);
  const merged = polyclip.union([h.outline], [extra]);
  // Remote test coordinates can disconnect the candidate from the carrier.
  // Bridge the old thumb-palm datum and the candidate with a simple rectangle
  // if disconnected (a concept, not a routed neck).
  let outline = merged[0][0].slice(0, -1);
  if (merged.length > 1) {
    const path = rect(
      {
        x: (h.keys.at(-3).x + sensor.x) / 2,
        y: (h.keys.at(-3).y + sensor.y) / 2,
        a: 0,
      },
      Math.abs(h.keys.at(-3).x - sensor.x) + 3,
      Math.abs(h.keys.at(-3).y - sensor.y) + 3,
    );
    outline = polyclip.union([h.outline], [extra], [path])[0][0].slice(0, -1);
  }
  const carrier = put(
    'carrier',
    'carrier',
    'Proposed continuous carrier',
    'rigid',
    outline,
    -SPECS.pcbT,
    0,
  );
  const back = put(
    'back',
    'back',
    '1 mm back-sheet allowance',
    'rigid',
    outline,
    -4.8,
    -3.8,
  );
  const driver = cub(
    'driver',
    'driver',
    'Separate pointer driver',
    'envelope',
    h.driver,
    h.driver.w,
    h.driver.h,
    0,
    h.driver.t,
  );
  const battery = cub(
    'battery',
    'battery',
    'Protected pouch allowance',
    'envelope',
    h.battery,
    SPECS.battery.w,
    SPECS.battery.h,
    0,
    state.batteryT,
  );
  const caps = [],
    switches = [],
    movingCaps = [];
  const skirt = state.switchType === 'ulp' ? 1.3 : 4,
    swTop = state.switchType === 'ulp' ? 3 : 8;
  h.keys.forEach((k, i) => {
    const top = base.cap.top - (state.pressed ? base.cap.travel : 0);
    switches.push(
      cub(
        'switch-' + i,
        'switch',
        k.label + ' switch reserve',
        'envelope',
        k,
        base.cap.swW,
        base.cap.swH,
        0,
        swTop,
      ),
    );
    caps.push(
      cub(
        'sweep-' + i,
        'key-sweep',
        k.label + ' swept cap',
        'envelope',
        k,
        base.cap.w,
        base.cap.h,
        base.cap.top - base.cap.travel - skirt,
        base.cap.top,
      ),
    );
    movingCaps.push(
      cub(
        'key-' + i,
        'key',
        k.label + ' keycap',
        'reference',
        k,
        base.cap.w,
        base.cap.h,
        top - skirt,
        top,
      ),
    );
  });
  const setback = rayToEdge(point(mouth), exit, outline);
  // Test all the way to outside the carrier, not just a short box at the mouth.
  const pathDepth = Math.max(18, setback + 5);
  const plug = cub(
    'plug',
    'plug',
    'USB mating + straight approach reserve',
    'envelope',
    delta(mouth, 0, -pathDepth / 2),
    12,
    pathDepth,
    0.25,
    6.25,
  );
  const pads = delta(sensor, 0, P.h / 2);
  const db = box(driver.polygon),
    driverNear = [mid(pads.x, db.x0, db.x1), mid(pads.y, db.y0, db.y1)];
  const leadMin = Math.hypot(driverNear[0] - pads.x, driverNear[1] - pads.y);
  const keys = [...caps, ...switches],
    bridgeSolids = [
      deck,
      sensorCard,
      face,
      post,
      cap,
      ...feet,
      controllerSolid,
      usb,
    ],
    kGap = near(bridgeSolids, keys),
    sensorKey = near([sensorCard], caps, planar),
    plugGap = near(
      [plug],
      [deck, sensorCard, ...feet, ...keys, driver, battery],
    ),
    rfGap = near([rf], [sensorCard, deck], planar),
    elecGap = near(bridgeSolids, [battery, driver]),
    accessGap = near(feet, [controllerSolid], planar);
  const oldBounds = box(oldCarrier.polygon),
    newBounds = box(carrier.polygon),
    pack = box([...controllerSolid.polygon, ...sensorPoly]),
    localPack = box([
      ...deckPoly,
      ...controllerSolid.polygon,
      ...usb.polygon,
      ...feet.flatMap((f) => f.polygon),
    ]),
    sharedPolys = polyclip.intersection(
      [controllerSolid.polygon],
      [sensorPoly],
    ),
    overlapArea = sharedPolys.reduce((n, p) => n + area(p[0]), 0),
    headDistance = Math.hypot(
      head.x - h.keys.at(-3).x,
      head.y - h.keys.at(-3).y,
    );
  const checks = [],
    check = (id, label, hit, description, limit = 0) => {
      const v = hit.val;
      checks.push({
        id,
        label,
        value: v,
        status: v > limit + 1e-6 ? 'screen' : 'clash',
        detail:
          description +
          (hit.pair.length ? ' Closest: ' + hit.pair.join(' / ') + '.' : ''),
      });
    };
  check(
    'keys',
    'Moving keys and switch bodies',
    kGap,
    'Signed 3D gap to conservative full cap stroke and switch envelopes.',
  );
  check(
    'plug',
    'USB insertion corridor',
    plugGap,
    '12 mm wide × 6 mm high straight approach from an estimated mouth to outside perimeter; actual cable not fitted.',
  );
  check(
    'rf',
    'Antenna projection',
    rfGap,
    'Signed XY separation to conductive bridge / sensor from a provisional 6 × 6 mm screen centered on the Plus antenna origin. Not an RF keep-out specification.',
  );
  check(
    'feet',
    'Feet to controller',
    accessGap,
    'Nominal plastic-to-board side gap; no drill, fillet, tool, socket or fabrication tolerance.',
  );
  check(
    'deck',
    'Bridge above XIAO',
    { val: o.gap, pair: [deck.label, controllerSolid.label] },
    'Gap to the provisional 5 mm mounted-module envelope; 0 mm is uninsulated contact, not a support.',
  );
  check(
    'remote',
    'Pouch and detached driver',
    elecGap,
    'Nominal intact component envelopes; wiring, insulation, pouch swelling and strain relief not tested.',
  );
  checks.push({
    id: 'wall',
    label: 'USB mouth to outer contour',
    value: setback,
    status: 'open',
    detail:
      'Centerline setback to last perimeter crossing. A case cutout or inset tunnel must pass the plug body and seat its connector; carrier material below a plug is not a wall.',
  });
  checks.push({
    id: 'build',
    label: 'Attachment, wiring and RF test',
    value: null,
    status: 'open',
    detail:
      'No mounting-hole registration, solder-land accessibility, reset probe, harness route, loaded deflection or closed-case radio result has been verified.',
  });
  const distance = (k) => Math.hypot(k.x - head.x, k.y - head.y);
  const nearestThumb = h.keys
    .filter((k) => k.thumb)
    .reduce((a, b) => (distance(a) <= distance(b) ? a : b));
  const metrics = {
    boardWidth: pack.w,
    boardDepth: pack.h,
    boardArea: pack.w * pack.h,
    overlapArea,
    overlapFraction: overlapArea / (P.w * P.h),
    localWidth: localPack.w,
    localDepth: localPack.h,
    sideBySideWidth: X.w + P.w,
    sideBySideDepth: Math.max(X.h, P.h),
    stackedMinWidth: X.w,
    stackedMinDepth: X.h,
    capTop: cap.top,
    stockTip: post.top,
    keyTop: base.cap.top,
    pressedKeyTop: base.cap.top - base.cap.travel,
    keyGap: kGap.val,
    sensorKeyPlanGap: sensorKey.val,
    plugGap: plugGap.val,
    rfGap: rfGap.val,
    plugSetback: setback,
    wireLowerBound: leadMin,
    headDistance,
    nearestThumbDistance: distance(nearestThumb),
    nearestThumbLabel: nearestThumb.label,
    baselineWidth: oldBounds.w,
    baselineDepth: oldBounds.h,
    rightWidth: newBounds.w,
    rightDepth: newBounds.h,
    widthDelta: newBounds.w - oldBounds.w,
    depthDelta: newBounds.h - oldBounds.h,
    addedCarrierArea: area(outline) - area(h.outline),
    totalHeight:
      Math.max(base.cap.top, cap.top, X.t, state.batteryT, h.driver.t) -
      back.bottom,
    baselineHeight: base.height,
    controllerShift: Math.hypot(
      controller.x - h.controller.x,
      controller.y - h.controller.y,
    ),
    screened: checks.every((t) => t.status !== 'clash'),
  };
  return {
    options: o,
    state,
    solids,
    head,
    controller,
    sensor,
    antenna,
    mouth,
    checks,
    metrics,
    baseline: {
      head: p,
      controller: h.controller,
      outline: h.outline,
      driver: h.driver,
      keys: h.keys,
      bounds: oldBounds,
    },
    outline,
    thumb: h.keys.at(-3),
    nearestThumb,
    wire: [point(pads), driverNear],
    plugExit: exit,
    sensorHoles: [-1, 1].flatMap((u) =>
      [-1, 1].map((v) => point(delta(head, 4.75 * u, 4.75 * v))),
    ),
    refs: {
      controllerSolid,
      boardSolid,
      usb,
      rf,
      deck,
      sensorCard,
      post,
      cap,
      face,
      carrier,
      back,
      driver,
      battery,
      plug,
      oldXiao,
      feet,
      caps,
      switches,
      movingCaps,
    },
  };
}

// Three views below share the same extrusions. Only the nearby piece of the
// carrier is shown in the large view; the inset retains the uncut outline.
const colors = {
  back: '#888a80',
  carrier: '#abc2a6',
  switch: '#8d9387',
  key: '#e4dece',
  'controller-board': '#406955',
  'usb-shell': '#a7b2ae',
  support: '#b79772',
  bridge: '#d2b187',
  sensor: '#6b9978',
  post: '#ad996e',
  'stick-cap': '#bd4e37',
  'rf-screen': '#b88735',
  plug: '#568b9b',
  controller: '#537762',
};
const f2 = (n) => Number(n.toFixed(2));
const xyText = (points) => points.map((p) => p.map(f2).join(',')).join(' ');
const escape = (s) =>
  String(s).replace(
    /[&<>"]/g,
    (k) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[k],
  );
const pg = (p, fill, extra = '') =>
  '<polygon points="' + xyText(p) + '" fill="' + fill + '" ' + extra + '/>';
const line = (a, b, color, extra = '') =>
  '<path d="M' +
  a.map(f2).join(' ') +
  'L' +
  b.map(f2).join(' ') +
  '" fill="none" stroke="' +
  color +
  '" ' +
  extra +
  '/>';
const txt = (x, y, t, size = 12, extra = '') =>
  '<text x="' +
  f2(x) +
  '" y="' +
  f2(y) +
  '" font-size="' +
  size +
  '" ' +
  extra +
  '>' +
  escape(t) +
  '</text>';
const pt = (x, y, r, fill, extra = '') =>
  '<circle cx="' +
  f2(x) +
  '" cy="' +
  f2(y) +
  '" r="' +
  r +
  '" fill="' +
  fill +
  '" ' +
  extra +
  '/>';
const shade = (color, k) =>
  '#' +
  [1, 3, 5]
    .map((i) =>
      Math.min(255, Math.round(parseInt(color.slice(i, i + 2), 16) * k))
        .toString(16)
        .padStart(2, '0'),
    )
    .join('');
const fit = (b, x, y, w, h) => {
  const k = Math.min(w / (b.w || 1), h / (b.h || 1));
  return (p) => [
    x + w / 2 + (p[0] - (b.x0 + b.x1) / 2) * k,
    y + h / 2 + (p[1] - (b.y0 + b.y1) / 2) * k,
  ];
};
function localCrop(m) {
  const r = m.refs,
    b = box([
      ...r.deck.polygon,
      ...r.boardSolid.polygon,
      ...r.usb.polygon,
      ...rect(m.nearestThumb, 18, 17),
      point(m.head),
    ]);
  return rect(
    { x: (b.x0 + b.x1) / 2, y: (b.y0 + b.y1) / 2 },
    b.w + 10,
    b.h + 9,
  );
}
function clip(poly, window) {
  return polyclip.intersection([poly], [window]).map((c) => c[0].slice(0, -1));
}
function sliceX(poly, x) {
  const hits = [];
  for (let i = 0; i < poly.length; i++) {
    const a = poly[i],
      b = poly[(i + 1) % poly.length];
    if ((a[0] <= x && b[0] > x) || (b[0] <= x && a[0] > x))
      hits.push(a[1] + ((x - a[0]) * (b[1] - a[1])) / (b[0] - a[0]));
  }
  hits.sort((a, b) => a - b);
  let spans = [];
  for (let i = 1; i < hits.length; i += 2) spans.push([hits[i - 1], hits[i]]);
  return spans;
}
function inset(m) {
  const fitInset = fit(box(m.outline), 495, 55, 165, 128);
  const plot = (p, c, ext = '') => pg(p.map(fitInset), c, ext);
  const mark = (p, color, rad) => pt(...fitInset(p), rad, color);
  return (
    '<g><title>Whole right half: original and proposed thumb lobe, former controller, remote driver and candidate</title>' +
    plot(m.outline, '#c4d2bb', 'stroke="#6d826b" stroke-width="1.15"') +
    plot(
      m.baseline.outline,
      '#e2e7da',
      'stroke="#768670" stroke-dasharray="2 2" stroke-width=".8"',
    ) +
    m.refs.movingCaps
      .map((k) =>
        plot(k.polygon, '#f1eee3', 'stroke="#8b9182" stroke-width=".7"'),
      )
      .join('') +
    plot(
      m.refs.oldXiao.polygon,
      'none',
      'stroke="#41664f" stroke-width="1.2" stroke-dasharray="3 2"',
    ) +
    plot(
      m.refs.battery.polygon,
      '#c1c3ae',
      'stroke="#8c947d" stroke-width=".6"',
    ) +
    plot(
      m.refs.driver.polygon,
      '#b9a1b5',
      'stroke="#826e83" stroke-width=".8"',
    ) +
    line(
      fitInset(m.wire[0]),
      fitInset(m.wire[1]),
      '#845b79',
      'stroke-dasharray="3 2"',
    ) +
    plot(
      m.refs.boardSolid.polygon,
      '#598269',
      'stroke="#3b5c48" stroke-width=".8"',
    ) +
    plot(
      m.refs.sensorCard.polygon,
      '#acbd97',
      'stroke="#58715a" stroke-width=".6"',
    ) +
    mark(point(m.head), '#bc5138', 3.2) +
    '</g>'
  );
}
function projView(m, view) {
  const r = m.refs,
    window = localCrop(m),
    low = r.back.bottom,
    high = Math.max(m.metrics.capTop, m.metrics.keyTop);
  const proj = (p, z) =>
    view === 'plan'
      ? [p[0], p[1]]
      : view === 'section'
        ? [p[1], -2 * z]
        : [0.84 * p[0] - 0.68 * p[1], 0.34 * p[0] + 0.42 * p[1] - 0.91 * z];
  const b = box(window.flatMap((p) => [proj(p, low), proj(p, high)])),
    map = fit(b, 19, 34, 447, 220);
  const Q = (p, z) => map(proj(p, z)),
    paint = (ps, c, extra = '') => pg(ps, c, extra);
  const trace = (poly, z, c, extra = '') =>
    paint(
      poly.map((p) => Q(p, z)),
      'none',
      'stroke="' + c + '" ' + extra,
    );
  const shape = (o, poly) => {
    const c = colors[o.role] || '#a7b4a4',
      edge = 'stroke="#4d5c4e" stroke-width=".9" stroke-linejoin="round"';
    const ghost =
      o.role === 'plug' || o.role === 'rf-screen' || o.role === 'controller';
    if (view === 'section') {
      let spans = sliceX(poly, m.head.x);
      return spans
        .map(([a, b]) => {
          const q = [
            [a, o.bottom],
            [b, o.bottom],
            [b, o.top],
            [a, o.top],
          ].map(([y, z]) => Q([m.head.x, y], z));
          return paint(
            q,
            ghost ? 'none' : c,
            ghost
              ? 'stroke="' + c + '" stroke-width="1.5" stroke-dasharray="4 3"'
              : edge,
          );
        })
        .join('');
    }
    if (ghost) {
      const z = o.role === 'rf-screen' ? 1.8 : o.role === 'plug' ? 2.8 : o.top;
      return paint(
        poly.map((p) => Q(p, z)),
        c,
        'fill-opacity=".12" stroke="' +
          c +
          '" stroke-width="1.4" stroke-dasharray="4 3"',
      );
    }
    let faces = '';
    if (view === 'iso') {
      // Paint the distant sides first, then the front sides and top. Sorting
      // the extruded edges independently also handles the circular cap prism.
      const sides = poly
        .map((p, i) => {
          const q = poly[(i + 1) % poly.length];
          return { p, q, front: p[0] + p[1] + q[0] + q[1] };
        })
        .sort((a, b) => a.front - b.front);
      for (const { p, q } of sides) {
        let cs = shade(
          c,
          Math.abs(p[0] - q[0]) > Math.abs(p[1] - q[1]) ? 0.77 : 0.88,
        );
        faces += paint(
          [Q(p, o.bottom), Q(q, o.bottom), Q(q, o.top), Q(p, o.top)],
          cs,
          o.role === 'stick-cap'
            ? 'stroke="' + cs + '" stroke-width=".45"'
            : edge,
        );
      }
    }
    return (
      faces +
      paint(
        poly.map((p) => Q(p, o.top)),
        c,
        edge +
          (o.role === 'bridge' && view === 'plan' ? ' fill-opacity=".70"' : ''),
      )
    );
  };
  const items = [
    r.back,
    r.carrier,
    ...r.switches,
    ...r.movingCaps,
    r.boardSolid,
    r.usb,
    r.controllerSolid,
    r.plug,
    r.rf,
    ...r.feet,
    r.deck,
    r.sensorCard,
    r.post,
    r.cap,
  ];
  let out = '';
  if (view === 'section') {
    const ys = box(window);
    for (const z of [-4, 0, 5, 10, 15])
      if (z <= high + 1) {
        const a = Q([m.head.x, ys.y0], z),
          b = Q([m.head.x, ys.y1], z);
        out +=
          line(a, b, '#afbaab', 'stroke-width=".75" stroke-dasharray="3 4"') +
          txt(a[0] + 1, a[1] - 3, z + '', 9, 'fill="#697b6c"');
      }
  }
  for (const o of items) {
    // RF is a projected copper screen, not a fictitious tall component.
    if (view === 'section' && o === r.rf) continue;
    let slices = clip(o.polygon, window);
    for (const poly of slices) {
      out +=
        '<g><title>' + escape(o.label) + '</title>' + shape(o, poly) + '</g>';
    }
    if (o === r.sensorCard && view !== 'section') {
      for (const [x, y] of m.sensorHoles) {
        const hole = ring({ x, y }, 0.9, 14);
        out += paint(
          hole.map((p) => Q(p, o.top)),
          '#d6daae',
          'stroke="#4f6a50" stroke-width=".9"',
        );
      }
    }
  }
  // Re-mark hidden items with outlines only in the engineering plan.
  if (view === 'plan') {
    out += trace(
      r.boardSolid.polygon,
      r.boardSolid.top,
      '#365d45',
      'stroke-width="1.5" stroke-dasharray="4 3"',
    );
    out += trace(
      r.rf.polygon,
      2,
      '#a27725',
      'stroke-width="1.8" stroke-dasharray="3 2"',
    );
    const wb = box(window);
    out += line(
      Q([m.head.x, wb.y0], 0),
      Q([m.head.x, wb.y1], 0),
      '#526a62',
      'stroke-width=".7" stroke-dasharray="6 2 1 2"',
    );
  }
  if (view !== 'section') {
    const s = Q(point(m.nearestThumb), m.refs.movingCaps.at(-3).top);
    out += txt(
      s[0],
      s[1] + 3,
      m.nearestThumb.label,
      11,
      'text-anchor="middle" fill="#514f41" font-weight="650"',
    );
  }
  return out;
}

/** A dependency-free, standalone SVG string for plan | section | iso.
 * Section is a true YZ vertical cut through the current shaft, not the USB
 * centerline: off-cut feet/connectors are intentionally absent. */
export function stackSVG(m, view = 'iso') {
  if (!['iso', 'plan', 'section'].includes(view)) view = 'iso';
  const key = {
    iso: 'AXONOMETRIC',
    plan: 'TOP PLAN',
    section: 'SHAFT SECTION',
  }[view];
  const notes =
    view === 'iso'
      ? ['Cropped right-thumb bay.', 'Assembled envelopes; not vendor 3D CAD.']
      : view === 'plan'
        ? [
            'Across-half X →  /  palm Y ↓',
            'Broken green outline: XIAO underneath.',
          ]
        : [
            'True Y–Z cut: shaft X = ' + signedNum(m.head.x) + ' mm.',
            'Y increases right; Z enlarged 2×. Off-cut parts omitted.',
          ];
  const legend = [
    ['#bd4e37', 'Pointing cap'],
    ['#6b9978', 'Sensor PCB'],
    ['#d2b187', 'Bridge + feet'],
    ['#406955', 'XIAO Plus'],
    ['#568b9b', 'Plug sweep'],
    ['#b88735', 'RF screen'],
  ];
  let leg = '';
  legend.forEach(([c, l], i) => {
    const x = 25 + (i % 3) * 148,
      y = 321 + Math.floor(i / 3) * 24;
    leg +=
      pt(x, y - 4, 4, c, 'stroke="#536458" stroke-width=".5"') +
      txt(x + 10, y, l, 12);
  });
  const tag = (x, y, t) =>
    txt(
      x,
      y,
      t,
      10,
      'font-family="ui-monospace,monospace" letter-spacing="1.1" font-weight="600" fill="#637563"',
    );
  const colorsNote = m.metrics.screened ? '#49674c' : '#aa4b38';
  return (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 680 373" role="img" aria-label="' +
    key +
    ' of the thumb pointing stick over the XIAO nRF52840 Plus, plus whole-half plan" style="font-family:Manrope,system-ui,sans-serif;color:#33483b">' +
    '<title>Tapir controller stack: ' +
    key +
    '</title><desc>Engineering envelope study, not verified fit. The bridge is supported by four proposed feet outside the XIAO. The original remote pointer driver is retained. ' +
    escape(notes.join(' ')) +
    '</desc>' +
    '<rect width="680" height="373" fill="#edf0e8"/><g fill="#33483b">' +
    tag(20, 22, key + '   /   RIGHT THUMB') +
    tag(490, 22, 'WHOLE RIGHT HALF') +
    '<path stroke="#ced7c9" d="M478 12v346M18 288h444"/>' +
    '<g>' +
    projView(m, view) +
    '</g>' +
    inset(m) +
    txt(493, 203, 'Dashed: former XIAO', 12) +
    txt(493, 222, 'Purple: separate driver', 12) +
    txt(493, 241, 'Dashed lead: direct span', 11) +
    '<path stroke="#ced7c9" d="M491 255h170"/>' +
    tag(493, 278, 'CARRIER CHANGE') +
    txt(
      493,
      306,
      (m.metrics.depthDelta >= 0 ? '+' : '') +
        signedNum(m.metrics.depthDelta) +
        ' mm depth',
      17,
      'font-weight="650"',
    ) +
    txt(493, 328, 'Width Δ ' + signedNum(m.metrics.widthDelta) + ' mm', 12) +
    txt(
      493,
      351,
      m.metrics.screened ? 'No nominal clash' : 'Nominal interference',
      11,
      'fill="' + colorsNote + '" font-weight="650"',
    ) +
    leg +
    txt(19, 274, notes[0], 11, 'fill="#627265"') +
    txt(20, 365, notes[1], 11, 'fill="#627265"') +
    '</g></svg>'
  );
}
