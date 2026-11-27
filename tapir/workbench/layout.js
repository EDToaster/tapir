import polyclip from 'polygon-clipping';
export const SPECS = {
  pcbT: 1.6,
  controller: { w: 17.8, h: 21, t: 5 },
  battery: { w: 11.5, h: 32, t: 3.3 },
  pointer: {
    w: 13.2,
    h: 18.29,
    t: 0.8,
    stem: 2.4,
    axisToBoardCenter: 1.695,
    cap: 5,
    opening: 4, // proposed square aperture for the 2.4 mm post/coupler envelope
    frontReserve: 0.5, // unmapped sensor face hardware outside the post, provisional
    rearReserve: 0.8, // fastening/wiring reserve below the daughterboard
    coverGap: 0.4,
  },
  mouse: { w: 4.2, h: 3.2, t: 2.5 },
};
export const PRESETS = {
  thumb: {
    placement: 'thumb',
    mount: 'under',
    splay: 0,
    gap: 0,
    nubY: -6,
    thumbX: 0,
    thumbY: 0,
    standoff: 1.4,
  },
  straight: {
    placement: 'columns',
    mount: 'under',
    splay: 0,
    gap: 6.5,
    nubY: -6,
    standoff: 2.8,
  },
  gentle: {
    placement: 'columns',
    mount: 'under',
    splay: 4,
    gap: 4.5,
    nubY: -6,
    standoff: 2.8,
  },
  balanced: {
    placement: 'columns',
    mount: 'top',
    splay: 16,
    gap: 8,
    nubY: -6,
    standoff: 2.8,
  },
};
export const INITIAL = {
  mode: 'assembled',
  view: 'iso',
  switchType: 'choc',
  ...PRESETS.thumb,
  separation: 24,
  batteryT: 3.3,
  pressed: false,
  layers: {
    keycaps: true,
    switches: true,
    pcb: true,
    electronics: true,
    back: true,
  },
};
export const profile = (id) =>
  id === 'ulp'
    ? { w: 16, h: 16, top: 4.2, travel: 1.8, swW: 13.5, swH: 13 }
    : { w: 17.5, h: 16.5, top: 10.6, travel: 3, swW: 15, swH: 15 };
export const rotate = ([x, y], a) => {
  let c = Math.cos((a * Math.PI) / 180),
    s = Math.sin((a * Math.PI) / 180);
  return [x * c - y * s, x * s + y * c];
};
export const rect = (p, w, h) =>
  [
    [-1, -1],
    [1, -1],
    [1, 1],
    [-1, 1],
  ].map(([x, y]) => {
    let [u, v] = rotate([(x * w) / 2, (y * h) / 2], p.a || 0);
    return [u + p.x, v + p.y];
  });
const cross = (a, b, c) =>
  (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
function hull(points) {
  let p = points.slice().sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  let l = [],
    u = [];
  for (let a of p) {
    while (l.length > 1 && cross(l.at(-2), l.at(-1), a) <= 0) l.pop();
    l.push(a);
  }
  for (let a of p.reverse()) {
    while (u.length > 1 && cross(u.at(-2), u.at(-1), a) <= 0) u.pop();
    u.push(a);
  }
  return l.slice(0, -1).concat(u.slice(0, -1));
}
const dst = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);
function ptseg(p, a, b) {
  let x = b[0] - a[0],
    y = b[1] - a[1],
    t = Math.max(
      0,
      Math.min(
        1,
        ((p[0] - a[0]) * x + (p[1] - a[1]) * y) / (x * x + y * y || 1),
      ),
    );
  return dst(p, [a[0] + x * t, a[1] + y * t]);
}
export function clearance(A, B) {
  let pen = Infinity,
    apart = false;
  for (const p of [A, B])
    for (let i = 0; i < p.length; i++) {
      let a = p[i],
        b = p[(i + 1) % p.length],
        x = b[1] - a[1],
        y = a[0] - b[0],
        d = Math.hypot(x, y);
      const proj = (q) => q.map(([u, v]) => (u * x + v * y) / d),
        pa = proj(A),
        pb = proj(B);
      let depth = Math.min(
        Math.max(...pa) - Math.min(...pb),
        Math.max(...pb) - Math.min(...pa),
      );
      if (depth < 0) apart = true;
      pen = Math.min(pen, depth);
    }
  if (!apart) return -pen;
  let best = Infinity;
  for (let [a, b] of [
    [A, B],
    [B, A],
  ])
    for (let p of a)
      for (let i = 0; i < b.length; i++)
        best = Math.min(best, ptseg(p, b[i], b[(i + 1) % b.length]));
  return best;
}
function circleRect(p, r, k, w, h) {
  let [u, v] = rotate([p.x - k.x, p.y - k.y], -k.a),
    dx = Math.abs(u) - w / 2,
    dy = Math.abs(v) - h / 2;
  return (
    Math.hypot(Math.max(0, dx), Math.max(0, dy)) +
    Math.min(0, Math.max(dx, dy)) -
    r
  );
}
const legends = {
  right: [
    ['Y', 'U', 'I', 'O', 'P', '\\'],
    ['H', 'J', 'K', 'L', ';', "'"],
    ['N', 'M', ',', '.', '/', 'Enter'],
  ],
  left: [
    ['T', 'R', 'E', 'W', 'Q', 'Esc'],
    ['G', 'F', 'D', 'S', 'A', 'Shift'],
    ['B', 'V', 'C', 'X', 'Z', 'Ctrl'],
  ],
};
const capsuleOutline = (pts) => hull(pts);

// Signed distance between extruded convex envelopes. When their footprints
// overlap, an actual vertical separation still counts as clearance (not a clash).
export function prismGap(a, b) {
  const xy = clearance(a.polygon, b.polygon);
  const z = Math.max(b.bottom - a.top, a.bottom - b.top);
  return xy > 0 || z > 0
    ? Math.hypot(Math.max(xy, 0), Math.max(z, 0))
    : Math.max(xy, z);
}
// Square bounding boxes enclose the round pegs, pad/fillet regions, etc.
// This is a direct-solder concept with a chosen footprint rotation, not hotswap.
function undersideEnvelopes(keys, switchType) {
  const underside = -SPECS.pcbT;
  const features =
    switchType === 'choc'
      ? [
          [0, 0, 3.4, 3.4, 1.05, 'center boss'],
          [-5.5, 0, 1.9, 1.9, 1.05, 'locator'],
          [5.5, 0, 1.9, 1.9, 1.05, 'locator'],
          [-5, 3.8, 2.4, 2.4, 1.8, 'terminal / solder'],
          [0, 5.9, 2.4, 2.4, 1.8, 'terminal / solder'],
        ]
      : [[0, 0, 13.5, 13, 0.6, 'ULP backside reserve (assumed)']];
  return keys.flatMap((k) =>
    features.map(([x, y, w, h, depth, name]) => {
      const [dx, dy] = rotate([x, y], k.a);
      return {
        polygon: rect({ x: k.x + dx, y: k.y + dy, a: k.a }, w, h),
        top: underside,
        bottom: underside - depth,
        label: k.label + ' / ' + name,
      };
    }),
  );
}
function sensorPose(pointer) {
  const [dx, dy] = rotate([0, SPECS.pointer.axisToBoardCenter], pointer.a);
  return { x: pointer.x + dx, y: pointer.y + dy, a: pointer.a };
}
export function layout(s) {
  const under = s.mount === 'under',
    thumbSite = s.placement === 'thumb',
    ps = SPECS.pointer,
    baseBottom = -SPECS.pcbT - 3.2;
  const boardTop = under ? -SPECS.pcbT - s.standoff : ps.t;
  const boardBottom = boardTop - ps.t;
  const backBottom = under
    ? Math.min(baseBottom, boardBottom - ps.rearReserve - ps.coverGap - 1)
    : baseBottom;
  const cap = profile(s.switchType),
    pitch = { x: 18, y: 17 },
    halves = [];
  for (const hand of ['left', 'right']) {
    const mirror = hand === 'right' ? 1 : -1,
      keys = [],
      mouse = [],
      put = (x, y, a = 0) => ({ x: x * mirror, y, a: a * mirror });
    for (let row = 0; row < 3; row++)
      for (let c = 0; c < 6; c++) {
        let x = c * pitch.x,
          y = (row - 1) * pitch.y + [1.5, 0, -3, 0, 4, 8][c],
          a = c >= 4 ? s.splay : 0;
        if (c >= 4) {
          let [u, v] = rotate([x - 72, y - 26], a);
          x = 72 + u + s.gap;
          y = 26 + v;
        }
        keys.push({
          ...put(x, y, a),
          label: legends[hand][row][c],
          thumb: false,
          c,
          row,
        });
      }
    for (let [i, [x, y, a]] of [
      [-20, 53, -25],
      [0.6, 45, -15],
      [21, 41, -6],
    ].entries())
      keys.push({
        ...put(x, y, a),
        label: (hand === 'right'
          ? ['Bksp', 'Lower', 'Tab']
          : ['Space', 'Raise', 'Alt'])[i],
        thumb: true,
        c: i,
        row: 3,
      });
    if (hand === 'left')
      for (let [i, x] of [22, 33, 44].entries())
        mouse.push({ ...put(x, 57, -6), label: ['L', 'Scroll', 'R'][i] });
    const controller = put(-21.8, -15.5),
      battery = put(-22.8, 15.5);
    const y = s.nubY ?? -6;
    const [uo, vo] = rotate([0, y - 26], s.splay);
    const xc = 72 + uo + s.gap; // locate right bank at the same y as the nub
    const xbank = xc + (26 + vo - y) * Math.tan((s.splay * Math.PI) / 180);
    const pointer =
      hand === 'right'
        ? {
            ...(thumbSite
              ? put(-20 + (s.thumbX ?? 0), 68 + (s.thumbY ?? 0), 90)
              : put((54 + xbank) / 2, y, s.splay * 0.5)),
            capTop: cap.top + 0.6,
            stemTop: boardTop + ps.stem,
            boardTop,
            boardBottom,
            under,
            opening: ps.opening,
          }
        : null;
    const driver =
      hand === 'right' ? { ...put(55, 39, 0), w: 23, h: 14.5, t: 3 } : null;
    const bank = capsuleOutline([
      ...keys
        .filter((k) => !k.thumb)
        .flatMap((k) => rect(k, cap.w + 4, cap.h + 4)),
      ...rect(controller, 21.8, 22),
      ...rect(battery, 16.5, 37),
    ]);
    const palm = capsuleOutline([
      ...keys
        .filter((k) => k.thumb)
        .flatMap((k) => rect(k, cap.w + 4, cap.h + 4)),
      ...keys
        .filter((k) => !k.thumb && k.row === 2 && k.c < 4)
        .flatMap((k) => rect(k, cap.w + 3, cap.h + 3)),
      ...mouse.flatMap((k) => rect(k, 9, 8)),
      ...(driver ? rect(driver, driver.w + 4, driver.h + 4) : []),
      // Extend only the right thumb lobe; allow 1.5 mm of carrier/cover
      // around this provisional sensor envelope. This is not a drill pattern.
      ...(thumbSite && pointer
        ? rect(sensorPose(pointer), ps.w + 3, ps.h + 3)
        : []),
    ]);
    const outline = polyclip.union([bank], [palm])[0][0].slice(0, -1),
      inner =
        hand === 'right'
          ? Math.min(...outline.map((p) => p[0]))
          : -Math.max(...outline.map((p) => p[0]));
    const origin = { x: mirror * (s.separation / 2 - inner), y: 0 };
    halves.push({
      hand,
      keys,
      mouse,
      controller,
      battery,
      driver,
      pointer,
      underbody: pointer && under ? undersideEnvelopes(keys, s.switchType) : [],
      outline,
      origin,
    });
  }
  const right = halves[1],
    p = right.pointer;
  const sensor = rect(sensorPose(p), ps.w, ps.h);
  let mins = { cap: Infinity, sensor: Infinity, keys: Infinity, bay: Infinity },
    nearest = {};
  function hit(n, val, label) {
    if (val < (mins[n] ?? Infinity)) {
      mins[n] = val;
      nearest[n] = label;
    }
  }
  if (under) {
    const envelope = {
      polygon: sensor,
      top: boardTop + ps.frontReserve,
      bottom: boardBottom - ps.rearReserve,
    };
    for (const tail of right.underbody)
      hit('sensor', prismGap(envelope, tail), tail.label);
    // The viewer represents bonded support pucks as round. Use a bounding
    // square here; no assumed fastener can make this clearance look better.
    for (const k of right.keys.filter(
      (k) =>
        (k.thumb && k.c === 0) ||
        (!k.thumb &&
          ((k.row === 0 && (k.c === 0 || k.c === 5)) ||
            (k.row === 2 && k.c === 4))),
    )) {
      hit(
        'support',
        prismGap(envelope, {
          polygon: rect({ ...k, a: 0 }, 4.36, 4.36),
          top: -SPECS.pcbT,
          bottom: backBottom + 1,
        }),
        k.label + ' / provisional spacer',
      );
    }
    hit('cover', envelope.bottom - (backBottom + 1), 'inside of back cover');
    hit('face', -SPECS.pcbT - envelope.top, 'carrier underside');
    hit('shaft', (ps.opening - ps.stem) / 2, 'one side, centered');
  }
  for (let h of halves) {
    for (let i = 0; i < h.keys.length; i++) {
      let k = h.keys[i];
      for (let j = i + 1; j < h.keys.length; j++)
        hit(
          'keys',
          clearance(rect(k, cap.w, cap.h), rect(h.keys[j], cap.w, cap.h)),
          k.label + ' / ' + h.keys[j].label,
        );
      if (h.pointer) {
        hit('cap', circleRect(p, ps.cap / 2, k, cap.w, cap.h), k.label);
        if (!under)
          hit('sensor', clearance(sensor, rect(k, cap.swW, cap.swH)), k.label);
        else
          hit(
            'aperture',
            clearance(
              rect(p, ps.opening, ps.opening),
              rect(k, cap.swW, cap.swH),
            ),
            k.label,
          );
      }
    }
    let components = [
      [h.controller, SPECS.controller.w, SPECS.controller.h, 'XIAO'],
      [h.battery, SPECS.battery.w, SPECS.battery.h, 'Pouch'],
      ...(h.driver ? [[h.driver, h.driver.w, h.driver.h, 'Driver']] : []),
    ];
    for (let i = 0; i < components.length; i++) {
      let [a, w, d, n] = components[i];
      if (h.pointer) {
        const moving = under ? rect(p, ps.opening, ps.opening) : sensor;
        hit('pointerBay', clearance(moving, rect(a, w, d)), n);
      }
      for (let k of h.keys) {
        hit(
          'bay',
          clearance(rect(a, w, d), rect(k, cap.swW, cap.swH)),
          n + ' / ' + k.label,
        );
      }
      for (let [b, w2, d2, n2] of components.slice(i + 1))
        hit('bay', clearance(rect(a, w, d), rect(b, w2, d2)), n + ' / ' + n2);
    }
  }
  let all = halves.flatMap((h) =>
      h.outline.map(([x, y]) => [x + h.origin.x, y]),
    ),
    xs = all.map((p) => p[0]),
    ys = all.map((p) => p[1]);
  return {
    halves,
    cap,
    pitch,
    mins,
    nearest,
    backBottom,
    width: Math.max(...xs) - Math.min(...xs),
    depth: Math.max(...ys) - Math.min(...ys),
    height:
      Math.max(
        p.capTop,
        s.pressed ? cap.top - cap.travel : cap.top,
        s.batteryT,
        SPECS.controller.t,
      ) - backBottom,
  };
}
