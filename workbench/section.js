import { SPECS } from './layout.js';

const mm = (n) =>
  Math.abs(n) < 0.005 ? '0' : Number(n.toFixed(2)).toString().replace('-', '−');
const zval = (n) => (n > 0 ? '+' : '') + mm(n);
const num = (n, fallback) => (Number.isFinite(n) ? n : fallback);
const ink = '#304238',
  forest = '#345646',
  copper = '#9f8c64',
  red = '#c74e36';

// Section through the stick axis. X spacing is deliberately schematic: the
// neighbouring keycaps do not necessarily intersect this exact cut plane.
export function sectionHTML(model, state) {
  const p = model?.halves?.[1]?.pointer;
  if (!p) return '';
  const carrier = SPECS.pcbT,
    sensor = SPECS.pointer;
  const under = Boolean(p.under);
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
  const keyT = state.switchType === 'ulp' ? 1.3 : 4;
  const rubberBottom =
    tip - Math.min(1.9, Math.max(1.1, tip - stockTop - 0.12));
  const low = Math.min(coverBottom, boardBottom, -carrier),
    high = Math.max(tip, keyTop);
  const px = Math.min(13, 143 / (high - low)),
    Y = (z) => +(19 + (high - z) * px).toFixed(2);
  const W = 416,
    H = Math.ceil(Y(low) + 16),
    axis = 204,
    left = 48,
    right = 366;
  const rect = (x, w, top, bottom, fill) =>
    '<rect x="' +
    x +
    '" y="' +
    Y(top) +
    '" width="' +
    w +
    '" height="' +
    Math.max(0, Y(bottom) - Y(top)).toFixed(2) +
    '" fill="' +
    fill +
    '"/>';
  const line = (x, y, xx, yy, stroke, width = 1, dashes = '') =>
    '<path d="M' +
    x +
    ' ' +
    y +
    'L' +
    xx +
    ' ' +
    yy +
    '" fill="none" stroke="' +
    stroke +
    '" stroke-width="' +
    width +
    '"' +
    (dashes ? ' stroke-dasharray="' + dashes + '"' : '') +
    '/>';
  const label = (x, y, t, color = ink, size = 10, anchor = 'start') =>
    '<text x="' +
    x +
    '" y="' +
    y +
    '" fill="' +
    color +
    '" font-family="ui-monospace,monospace" font-size="' +
    size +
    '" text-anchor="' +
    anchor +
    '">' +
    t +
    '</text>';
  const badge = (x, y, n, color) =>
    '<g><circle cx="' +
    x +
    '" cy="' +
    y +
    '" r="7.5" fill="' +
    color +
    '"/>' +
    label(x, y + 3.5, n, '#fff', 10, 'middle') +
    '</g>';
  let drawing =
    '<title>Right pointing stick section, ' +
    (under ? 'underside' : 'top') +
    ' mount</title>';
  drawing +=
    '<desc>Heights measured from the carrier PCB top. Lateral dimensions and nearby keycaps are schematic. See the dimensions following the drawing.</desc>';
  drawing += label(6, 12, 'Z / mm', '#657067', 9);
  for (let z = Math.ceil(low / 5) * 5; z <= high; z += 5) {
    drawing +=
      line(
        40,
        Y(z),
        right,
        Y(z),
        z === 0 ? '#849182' : '#dcdfd4',
        z === 0 ? 0.9 : 0.65,
        '3 4',
      ) + label(33, Y(z) + 3, zval(z), '#657067', 10, 'end');
  }
  // Indicate axis before hardware so it appears only in empty space.
  drawing += line(axis, 5, axis, H - 7, '#a4a99a', 0.7, '5 2 1 2');
  // Neighbouring keycap crowns and skirts; side positions are contextual only.
  const key = (x) => {
    const yt = Y(keyTop),
      yb = Y(keyTop - keyT),
      rim = Y(keyTop - keyT * 0.18);
    return (
      '<path d="M' +
      x +
      ' ' +
      yb +
      ' L' +
      (x + 4) +
      ' ' +
      rim +
      ' Q' +
      (x + 5) +
      ' ' +
      yt +
      ' ' +
      (x + 9) +
      ' ' +
      yt +
      ' H' +
      (x + 61) +
      ' Q' +
      (x + 65) +
      ' ' +
      yt +
      ' ' +
      (x + 66) +
      ' ' +
      rim +
      ' L' +
      (x + 70) +
      ' ' +
      yb +
      ' Z" fill="#e4dfd0" stroke="#948f80" stroke-width="1"/>'
    );
  };
  drawing += key(71) + key(267);
  if (under) {
    drawing +=
      rect(left, axis - 13 - left, 0, -carrier, forest) +
      rect(axis + 13, right - axis - 13, 0, -carrier, forest);
  } else drawing += rect(left, right - left, 0, -carrier, forest);
  drawing += rect(left, right - left, coverTop, coverBottom, '#696e61');
  if (under) {
    drawing +=
      '<rect x="' +
      (axis - 40) +
      '" y="' +
      Y(faceLimit) +
      '" width="80" height="' +
      (Y(rearLimit) - Y(faceLimit)) +
      '" fill="#adbd9d" fill-opacity=".3" stroke="#6c8368" stroke-width=".8" stroke-dasharray="3 2"/>';
  }
  drawing += rect(axis - 40, 80, boardTop, boardBottom, '#83a28a');
  drawing += line(
    axis - 40,
    Y(boardBottom),
    axis + 40,
    Y(boardBottom),
    '#4f6a57',
    0.6,
  );
  drawing +=
    rect(axis - 5, 10, stockTop, boardTop, '#968a73') +
    rect(axis - 4, 8, rubberBottom, stockTop, copper);
  const yt = Y(tip),
    yb = Y(rubberBottom),
    r = Math.min((yb - yt) * 0.38, 5);
  drawing +=
    '<path d="M' +
    (axis - 11) +
    ' ' +
    yb +
    ' V' +
    (yt + r) +
    ' Q' +
    (axis - 11) +
    ' ' +
    yt +
    ' ' +
    (axis - 7) +
    ' ' +
    yt +
    ' H' +
    (axis + 7) +
    ' Q' +
    (axis + 11) +
    ' ' +
    yt +
    ' ' +
    (axis + 11) +
    ' ' +
    (yt + r) +
    ' V' +
    yb +
    ' Z" fill="' +
    red +
    '"/>';
  drawing +=
    line(axis + 12, yt, axis + 29, yt, red) + badge(axis + 38, yt, '1', red);
  const pcbY = (Y(0) + Y(-carrier)) / 2;
  drawing +=
    badge(right + 13, pcbY, '2', forest) +
    line(right, pcbY, right + 6, pcbY, forest);
  const cardY = (Y(boardTop) + Y(boardBottom)) / 2,
    markerY = under ? Math.min(H - 13, cardY + 13) : Math.max(12, cardY - 14);
  const badgeX = under ? axis - 71 : axis + 64,
    edge = under ? axis - 40 : axis + 40;
  drawing +=
    line(edge, cardY, badgeX, markerY, '#526c58') +
    badge(badgeX, markerY, '3', '#577361');
  const coverY = (Y(coverTop) + Y(coverBottom)) / 2;
  drawing +=
    line(right, coverY, right + 25, coverY, '#696e61') +
    badge(right + 32, coverY, '4', '#696e61');
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
    (under ? 'UNDERSIDE MOUNT' : 'LEGACY TOP MOUNT') +
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
    '<p style="font-size:12px;line-height:1.55;margin:12px 0 0;color:#485345">Cap sits ' +
    mm(tip - keyTop) +
    ' mm above the ' +
    (state.pressed ? 'pressed' : 'resting') +
    ' key crown. Stock post ends at Z ' +
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
    '<p style="font-size:11px;line-height:1.45;margin:4px 0 0;color:#70766a">Z = 0 at the carrier top. Heights are to scale; widths and neighboring keycaps are schematic. The assembled stack is shown regardless of viewer layers.</p></div>'
  );
}
