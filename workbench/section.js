import { SPECS, rect } from './layout.js';
import { sliceX, posePoint } from './projection.js';

const mm = (n) =>
  Math.abs(n) < 0.005 ? '0' : Number(n.toFixed(2)).toString().replace('-', '−');
const zval = (n) => (n > 0 ? '+' : '') + mm(n);
const num = (n, fallback) => (Number.isFinite(n) ? n : fallback);
const ink = '#304238',
  forest = '#345646',
  copper = '#9f8c64',
  red = '#c74e36';

export function baselineCut(model, state) {
  const h = model.halves.find((x) => x.pointer),
    p = h.pointer,
    s = SPECS.pointer,
    thumb = state.placement === 'thumb';
  const [at, along] = thumb ? [p.x, p.y] : [p.y, p.x],
    range = 27,
    solids = [];
  const cut = (poly) =>
    sliceX(thumb ? poly : poly.map(([x, y]) => [y, x]), at)
      .map(([a, b]) => [
        Math.max(-range, a - along),
        Math.min(range, b - along),
      ])
      .filter(([a, b]) => a < b);
  const add = (spans, bottom, top, role) => {
    for (const [a, b] of spans)
      if (top > bottom) solids.push({ a, b, bottom, top, role });
  };
  const sections = cut(h.outline),
    back = model.backBottom;
  add(sections, back, back + (model.coverT ?? 1), 'back');
  const holes = p.under
    ? cut(rect({ ...p, a: p.apertureA ?? p.a }, p.opening, p.opening))
    : [];
  let laminate = sections;
  for (const [lo, hi] of holes)
    laminate = laminate.flatMap(([a, b]) =>
      [
        [a, Math.min(b, lo)],
        [Math.max(a, hi), b],
      ].filter(([x, y]) => x < y),
    );
  add(laminate, -SPECS.pcbT, 0, 'carrier');
  const keyTop = model.cap.top - (state.pressed ? model.cap.travel : 0);
  for (const k of h.keys)
    add(
      cut(rect(k, model.cap.w, model.cap.h)),
      keyTop - (state.switchType === 'ulp' ? 1.3 : 4),
      keyTop,
      'key',
    );
  const [x, y] = posePoint(p, 0, s.axisToBoardCenter),
    boardTop = p.boardTop ?? s.t,
    boardBottom = p.boardBottom ?? 0;
  add(cut(rect({ x, y, a: p.a }, s.w, s.h)), boardBottom, boardTop, 'sensor');
  const rubberBottom =
    p.capTop - Math.min(1.9, Math.max(1.1, p.capTop - p.stemTop - 0.12));
  add(cut(rect(p, s.stem, s.stem)), boardTop, p.stemTop, 'post');
  add([[-1.12, 1.12]], p.stemTop, rubberBottom, 'hub');
  add([[-s.cap / 2, s.cap / 2]], rubberBottom, p.capTop, 'cap');
  return {
    range,
    solids,
    name: thumb ? 'Y–Z / toward palm →' : 'X–Z / across half →',
  };
}
export function sectionHTML(model, state) {
  const p = model?.halves?.[1]?.pointer;
  if (!p) return '';
  const carrier = SPECS.pcbT,
    sensor = SPECS.pointer;
  const under = Boolean(p.under);
  const thumb = state.placement === 'thumb';
  const location = thumb ? 'Thumb bay' : 'Between keys';
  const boardTop = num(p.boardTop, under ? -carrier : sensor.t);
  const boardBottom = num(p.boardBottom, boardTop - sensor.t);
  const stockTop = num(p.stemTop, boardTop + sensor.stem);
  const tip = p.capTop,
    keyTop = model.cap.top - (state.pressed ? model.cap.travel : 0);
  const coverT = num(model.coverT, 1);
  const coverBottom = num(model.backBottom, -carrier - 3.2);
  const coverTop = coverBottom + coverT;
  const faceLimit = boardTop + sensor.frontReserve,
    rearLimit = boardBottom - sensor.rearReserve;
  // Pick a vertical cut across the finger columns or towards the thumb row.
  // Rotate neither the model nor the key footprints a second time.
  const cut = baselineCut(model, state);
  const W = 416,
    H = 174,
    axis = 190;
  const high = Math.max(tip, keyTop),
    low = Math.min(coverBottom, boardBottom);
  const scale = Math.min(267 / (cut.range * 2), 125 / (high - low)),
    topY = 17 + (125 - (high - low) * scale) / 2;
  const X = (u) => axis + u * scale,
    Y = (z) => topY + (high - z) * scale;
  const edge = '#626f61',
    inkKey = '#e4dfd0';
  const segment = (a, b, z, t, fill, role) =>
    '<rect data-role="' +
    role +
    '" x="' +
    X(a) +
    '" y="' +
    Y(t) +
    '" width="' +
    (b - a) * scale +
    '" height="' +
    (t - z) * scale +
    '" fill="' +
    fill +
    '" stroke="' +
    edge +
    '" stroke-width=".55"/>';
  const line = (x, y, x2, y2, c, d = '') =>
    '<path d="M' +
    x +
    ' ' +
    y +
    'L' +
    x2 +
    ' ' +
    y2 +
    '" fill="none" stroke="' +
    c +
    '" stroke-width=".85" ' +
    (d ? 'stroke-dasharray="' + d + '"' : '') +
    '/>';
  const txt = (x, y, t, c = ink, anchor = 'start') =>
    '<text x="' +
    x +
    '" y="' +
    y +
    '" fill="' +
    c +
    '" text-anchor="' +
    anchor +
    '" font-family="ui-monospace,monospace" font-size="10">' +
    t +
    '</text>';
  const colors = {
    back: '#696e61',
    carrier: forest,
    key: inkKey,
    sensor: '#83a28a',
    post: '#968a73',
    hub: copper,
    cap: red,
  };
  let drawing =
    '<title>Right stick, section at ' +
    cut.name +
    '</title><desc>Only intersecting geometry is shown. Printed heights and lateral distances use the same scale. Keycap envelopes show their outer heights, not sculpted profiles.</desc>';
  drawing += txt(6, 12, 'Z / mm', '#657067');
  for (let z = Math.ceil(low / 5) * 5; z <= high; z += 5)
    drawing +=
      line(40, Y(z), 323, Y(z), '#b5bcae', '3 3') +
      txt(34, Y(z) + 3, zval(z), '#657067', 'end');
  for (const s of cut.solids) {
    if (s.role === 'sensor' && under)
      drawing +=
        '<rect x="' +
        X(s.a) +
        '" y="' +
        Y(faceLimit) +
        '" width="' +
        (s.b - s.a) * scale +
        '" height="' +
        (faceLimit - rearLimit) * scale +
        '" fill="#d3decd" stroke="#81937a" stroke-width=".7" stroke-dasharray="2 2"/>';
    drawing += segment(s.a, s.b, s.bottom, s.top, colors[s.role], s.role);
  }
  drawing += line(axis, 9, axis, 147, '#8c5a4d', '4 2 1 2');
  const targets = [
    ['cap', tip, '1', red],
    ['carrier', -carrier / 2, '2', forest],
    ['sensor', (boardTop + boardBottom) / 2, '3', '#577361'],
    ['back', coverBottom + coverT / 2, '4', '#696e61'],
  ];
  for (const [i, [role, z, n, color]] of targets.entries()) {
    const part = cut.solids.filter((s) => s.role === role).at(-1);
    if (!part) continue;
    const x = X(part.b),
      y = Y(z),
      ty = 23 + i * 34;
    drawing +=
      line(x, y, 330, y, color) +
      line(330, y, 354, ty, color) +
      line(354, ty, 365, ty, color) +
      '<circle cx="374" cy="' +
      ty +
      '" r="7.5" fill="' +
      color +
      '"/>' +
      txt(374, ty + 3.3, n, 'white', 'middle');
  }
  drawing += txt(axis, 164, cut.name + ' · shaft at 0 mm', '#657067', 'middle');
  const legend = (n, name, body, c) =>
    '<div style="min-width:0"><span style="display:block;font-size:11px;color:#74796d"><b style="color:' +
    c +
    '">' +
    n +
    '</b> · ' +
    name +
    '</span><span style="font-size:13px;color:' +
    ink +
    '">' +
    body +
    '</span></div>';
  const hole =
    typeof p.opening === 'number' && under
      ? mm(p.opening) + ' × ' + mm(p.opening) + ' mm square'
      : 'proposed square';
  return (
    '<div style="padding:clamp(12px,2vw,22px);min-width:0"><div style="display:flex;align-items:baseline;flex-wrap:wrap;gap:5px 12px;justify-content:space-between"><h3 style="margin:0;font-size:17px;color:' +
    ink +
    '">Pointing stick section</h3><span style="font:10px ui-monospace,monospace;letter-spacing:.07em;color:#667360">' +
    location.toUpperCase() +
    ' · ' +
    (under ? 'UNDERSIDE MOUNT' : 'TOP MOUNT') +
    '</span></div>' +
    '<svg viewBox="0 0 ' +
    W +
    ' ' +
    H +
    '" role="img" aria-label="Section through the right stick axis" style="display:block;width:100%;max-height:205px;background:#f8f8f0;border-radius:4px;margin:12px 0">' +
    drawing +
    '</svg>' +
    '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(min(124px,100%),1fr));gap:8px 14px">' +
    legend('1', 'Rubber cap', 'Z ' + zval(tip) + ' mm', red) +
    legend('2', 'Carrier PCB', 'Z 0 to ' + zval(-carrier) + ' mm', forest) +
    legend(
      '3',
      'Sensor card',
      'Z ' + zval(boardTop) + ' to ' + zval(boardBottom) + ' mm',
      '#577361',
    ) +
    legend('4', 'Cover bottom', 'Z ' + zval(coverBottom) + ' mm', '#696e61') +
    '</div>' +
    '<p style="font-size:12px;line-height:1.55;margin:12px 0 0;color:#485345">The stick cap is ' +
    (Math.abs(tip - keyTop) < 0.005
      ? 'level with the '
      : mm(Math.abs(tip - keyTop)) +
        (tip > keyTop ? ' mm above the ' : ' mm below the ')) +
    (state.pressed ? 'pressed' : 'resting') +
    ' reference key crown. Stock post ends at Z ' +
    zval(stockTop) +
    ' mm; the tan extension reaches the rubber cap.' +
    (under
      ? ' The proposed shaft assembly passes through a ' +
        hole +
        ' carrier opening; the bare post alone does not reach the cap.'
      : ' The sensor rests on the carrier; no post opening is needed.') +
    '</p>' +
    (under
      ? '<p style="font-size:12px;line-height:1.55;margin:5px 0 0;color:#485345">The sensor face is ' +
        mm(-carrier - boardTop) +
        ' mm below the carrier underside. Dashed regions reserve ' +
        mm(sensor.frontReserve) +
        ' mm above the sensor face and ' +
        mm(sensor.rearReserve) +
        ' mm behind the card, leaving ' +
        mm(rearLimit - coverTop) +
        ' mm to the cover after the rear allowance. These are design allowances, not measured component heights; support and retention remain open.</p>'
      : '') +
    '<p style="font-size:11px;line-height:1.45;margin:4px 0 0;color:#70766a">Z = 0 at the carrier top. This true-scale section passes through the shaft center. Only intersecting key envelopes appear; off-plane neighbors are omitted. Dashed centerline: shaft axis. The section shows the assembled stack, not verified lateral clearance or comfortable reach.</p></div>'
  );
}
