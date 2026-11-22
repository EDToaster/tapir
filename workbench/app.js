import './style.css';
import { INITIAL, PRESETS, SPECS, layout, rect } from './layout.js';
import { sectionHTML } from './section.js';
import { comparisonSVG } from './reach.js';
import { mountStackStudy } from './stack-panel.js';
import { PARTS } from './parts.js';
import { createFallback } from './fallback.js';
import { createViewer } from './viewer.js';
const $ = (s) => document.querySelector(s),
  st = structuredClone(INITIAL);
const paths = {
  box: 'M12 3 21 8 12 13 3 8Z M3 8v9l9 5 9-5V8 M12 13v9',
  book: 'M4 4h6a3 3 0 0 1 2 1 3 3 0 0 1 2-1h6v15h-6a3 3 0 0 0-2 1 3 3 0 0 0-2-1H4Z M12 5v15',
  download: 'M12 3v12m-5-5 5 5 5-5M4 16v4h16v-4',
  orbit:
    'M5 18C1 16 4 10 10 6s11-4 11-1-3 8-9 12-9 4-10 2 M10 11a3 3 0 1 0 6 0a3 3 0 1 0-6 0',
  layers: 'M12 3 22 8 12 13 2 8ZM3 12l9 5 9-5M3 16l9 5 9-5',
  focus: 'M3 9V3h6m6 0h6v6m0 6v6h-6m-6 0H3v-6 M9 12h6m-3-3v6',
  sliders: 'M3 6h8m4 0h6M3 12h1m4 0h13M3 18h12m4 0h2M11 3v6M6 9v6m11 0v6',
  reset: 'M4 5v6h6M4 11a8 8 0 1 1 2 8',
  chev: 'm6 9 6 6 6-6',
  diagonal: 'M6 18 18 6M8 6h10v10',
  ruler: 'm3 15 12-12 6 6L9 21zM12 6l3 3m-6 0 2 2m-5 1 3 3',
  arrow: 'M3 12h17m-6-6 6 6-6 6',
  x: 'm5 5 14 14m0-14L5 19',
  explode: 'm2 7 10-4 10 4-10 4zM2 13l10 4 10-4M2 18l10 4 10-4',
  under: 'm2 12 10-5 10 5-10 5zM12 17v5m-3-3 3 3 3-3',
};
const ico = (k) =>
  '<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="' +
  (paths[k] || paths.box) +
  '"/></svg>';
function icons() {
  document
    .querySelectorAll('[data-i]')
    .forEach((x) => (x.outerHTML = ico(x.dataset.i)));
}
const ranges = {
  splay: ['Column 4–5 splay', 0, 28, 1, '°'],
  gap: ['Extra column gap', 0, 18, 0.5, ' mm'],
  nubY: ['Pointer fore / aft', -15, 8, 0.5, ' mm'],
  thumbX: ['Thumb offset · across', -4, 8, 0.5, ' mm'],
  thumbY: ['Thumb offset · toward palm', -4, 4, 0.5, ' mm'],
  separation: ['Half separation', 4, 95, 1, ' mm'],
  batteryT: ['Battery thickness', 2.5, 8, 0.1, ' mm'],
  standoff: ['Board-to-sensor spacing', 0.4, 4, 0.1, ' mm'],
};
function range(k) {
  let [label, min, max, step] = ranges[k];
  return (
    '<div class="param"><div class="paramhead"><label for="' +
    k +
    '">' +
    label +
    '</label><output class="readout" id="' +
    k +
    '-out" for="' +
    k +
    '"></output></div><div class="rangewrap"><input type="range" id="' +
    k +
    '" min="' +
    min +
    '" max="' +
    max +
    '" step="' +
    step +
    '"></div>' +
    (min < 0
      ? '<div class="range-ends" aria-hidden="true"><span>−' +
        Math.abs(min) +
        ' mm</span><span>+' +
        max +
        ' mm</span></div>'
      : '') +
    '</div>'
  );
}
$('#geometry-sliders').innerHTML = ['splay', 'gap', 'nubY'].map(range).join('');
$('#thumb-offsets').innerHTML = ['thumbX', 'thumbY'].map(range).join('');
$('#extra-sliders').innerHTML = ['separation', 'batteryT'].map(range).join('');
$('#mount-gap').innerHTML = range('standoff');
function group(el, values, field) {
  $(el).innerHTML = values
    .map(
      ([id, name, icon]) =>
        '<button data-field="' +
        field +
        '" data-value="' +
        id +
        '">' +
        (icon ? ico(icon) : '') +
        name +
        '</button>',
    )
    .join('');
}
group(
  '#views',
  [
    ['iso', '3D'],
    ['top', 'Top'],
    ['front', 'Front'],
  ],
  'view',
);
group(
  '#modes',
  [
    ['assembled', 'Assembled', 'box'],
    ['exploded', 'Exploded', 'explode'],
    ['underside', 'Underside', 'under'],
  ],
  'mode',
);
group(
  '#profiles',
  [
    ['choc', 'Choc v1'],
    ['ulp', 'PG1316S'],
  ],
  'switchType',
);
const layerLabels = {
  keycaps: 'Keycaps',
  switches: 'Switch bodies',
  pcb: 'Main PCBs',
  electronics: 'Electronics',
  back: 'Back covers',
};
group(
  '#mounts',
  [
    ['under', 'Under PCB'],
    ['top', 'On top'],
  ],
  'mount',
);
$('#layerpop').innerHTML =
  '<div class="eyebrow">VISIBLE PARTS</div>' +
  Object.entries(layerLabels)
    .map(
      ([k, v]) =>
        '<label><input type="checkbox" data-layer="' +
        k +
        '" checked>' +
        v +
        '</label>',
    )
    .join('');
const fmt = (x, n = 1) => Number(x).toFixed(n).replace(/\.0$/, '');
const sg = (x) => (x >= 0 ? '+' : '−') + Math.abs(x).toFixed(2);
const host = $('#scene');
let view,
  fallback = false;
try {
  view = createViewer(host, selectPart);
} catch (e) {
  console.warn('WebGL unavailable; using vector projection.', e.message);
  host.replaceChildren();
  view = createFallback(host, selectPart);
  fallback = true;
}
const dialog = $('#dialog');
let model,
  queued = false;
let restoreBack = false;
function openUnderside() {
  if (st.layers.back) restoreBack = true;
  st.mode = 'underside';
  st.view = 'iso';
  st.layers.back = false;
}
function leaveUnderside() {
  if (restoreBack) st.layers.back = true;
  restoreBack = false;
}
function sync() {
  queued = false;
  model = layout(st);
  const under = st.mount === 'under';
  const atThumb = st.placement === 'thumb';
  $('#nubY').closest('.param').hidden = atThumb;
  $('#thumb-offsets').hidden = !atThumb;
  const h = model.halves[1],
    t = h.keys.find((k) => k.thumb && k.c === 0);
  $('#site-note').textContent = atThumb
    ? 'Center-to-center reach: ' +
      fmt(Math.hypot(t.x - h.pointer.x, t.y - h.pointer.y)) +
      ' mm from the innermost thumb key. Zero offset is the preset position, not the key center.'
    : 'Comparison layout: the stick sits between finger columns 4 and 5.';
  $('#mount-gap').hidden = !under;
  $('#mount-note').textContent = under
    ? 'Spacing is from the carrier underside to the sensor PCB’s top face. Direct-solder switches only.'
    : 'The whole sensor board shares the switch-housing plane. Switch mount without changing splay to compare.';
  $('#section-panel').innerHTML = sectionHTML(model, st);
  view.update(st);
  Object.keys(ranges).forEach((k) => {
    const el = $('#' + k),
      [, lo, hi, , unit] = ranges[k];
    el.value = st[k];
    el.style.setProperty('--pct', ((st[k] - lo) / (hi - lo)) * 100 + '%');
    $('#' + k + '-out').textContent = fmt(st[k]) + unit;
  });
  document.querySelectorAll('[data-field]').forEach((el) => {
    const on = st[el.dataset.field] === el.dataset.value;
    el.classList.toggle('sel', on);
    el.setAttribute('aria-pressed', String(on));
  });
  $('#pressed').checked = st.pressed;
  document
    .querySelectorAll('[data-layer]')
    .forEach((x) => (x.checked = st.layers[x.dataset.layer]));
  $('#switch-note').textContent =
    st.switchType === 'choc'
      ? 'MBK 1U · 17.5 × 16.5 mm · 3 mm travel'
      : 'Butterfly 1U · 16 × 16 mm · 1.8 mm travel';
  const info = [
    ['Overall span', fmt(model.width), 'mm'],
    ['Assembled height', fmt(model.height), 'mm'],
    [
      under ? 'Sensor to underside parts' : 'Sensor to switch',
      sg(model.mins.sensor),
      'mm',
    ],
  ];
  $('#metrics').innerHTML = info
    .map(
      ([l, v, u], i) =>
        '<div class="metric ' +
        (i === 2 && model.mins.sensor < 0 ? 'warn' : '') +
        '"><sup>0' +
        (i + 1) +
        '</sup><span class="metric-label">' +
        l +
        '</span><strong>' +
        v +
        '</strong><small>' +
        u +
        '</small></div>',
    )
    .join('');
  $('#gesture').textContent =
    (fallback ? 'Vector view · ' : '') +
    'Drag to orbit · Scroll to zoom · Click to inspect';
}
function changed() {
  if (!queued) {
    queued = true;
    requestAnimationFrame(sync);
  }
}
Object.keys(ranges).forEach((k) =>
  $('#' + k).addEventListener('input', (e) => {
    st[k] = +e.target.value;
    if (['splay', 'gap', 'nubY', 'thumbX', 'thumbY', 'standoff'].includes(k))
      $('#preset').value = 'custom';
    changed();
  }),
);
$('#preset').onchange = (e) => {
  Object.assign(st, PRESETS[e.target.value]);
  changed();
};
$('#pressed').onchange = (e) => {
  st.pressed = e.target.checked;
  changed();
};
function show(k, title, html) {
  $('#dkicker').textContent = k;
  $('#dtitle').textContent = title;
  $('#dbody').innerHTML = html;
  if (!dialog.open) dialog.showModal();
}
function partBlock(p) {
  return (
    '<div class="part"><header><b>' +
    p.name +
    '</b><span class="badge ' +
    (p.tag === 'Allowance' ? 'est' : '') +
    '">' +
    p.tag +
    '</span></header><p>' +
    p.desc +
    '</p></div>'
  );
}
function selectPart(o) {
  let type = o?.type;
  if (!type) return;
  let key = { keycap: st.switchType, switch: st.switchType }[type] || type,
    p = PARTS[key];
  if (!p) return;
  show(
    'COMPONENT INSPECTOR  /  ' + (o.hand || 'ASSEMBLY').toUpperCase(),
    p.name,
    partBlock(p) +
      '<p class="callout">' +
      (o.label ? 'Selected: <b>' + esc(o.label) + '</b>. ' : '') +
      'Dimensions are nominal mechanical envelopes. Use the part drawing for production tolerances.</p><button class="secondary" data-action="sources">All parts &amp; sources ' +
      ico('arrow') +
      '</button>',
  );
}
function fit() {
  const r = model,
    check = (key, title, sub) =>
      '<div class="check"><span>' +
      title +
      '<small>' +
      sub +
      ' · closest: ' +
      esc(r.nearest[key]) +
      '</small></span><strong class="' +
      (r.mins[key] < 0 ? 'bad' : 'good') +
      '">' +
      sg(r.mins[key]) +
      ' mm</strong></div>';
  show(
    'DESIGN CHECK / MILLIMETRES',
    'Fit & clearances',
    '<p class="callout"><b>' +
      (Object.values(r.mins).some((n) => n < 0)
        ? 'Interference in the current geometry.'
        : 'No overlap among the tested envelopes.') +
      '</b> Positive means separation; negative means interference. These are nominal envelope checks, not tolerance or assembly approval.</p>' +
      check(
        'sensor',
        st.mount === 'under'
          ? 'Sensor to underside parts'
          : 'Sensor PCB to switch housing',
        st.mount === 'under'
          ? '3D: reserved sensor volume vs. nearby switch backs'
          : 'Plan: rotated rectangular envelopes',
      ) +
      (st.mount === 'under'
        ? check(
            'aperture',
            'Carrier opening to switch housing',
            'Plan: proposed square cutout and switch flanges',
          ) +
          check(
            'shaft',
            'Post to aperture wall',
            'Per side with a centered 2.4 mm shaft envelope; no movement',
          ) +
          check(
            'face',
            'Sensor face reserve to carrier',
            'Excludes the shaft, which passes through the cutout',
          ) +
          check(
            'cover',
            'Rear hardware reserve to cover',
            'Inside the cover, with the assumed mounting/wire reserve',
          )
        : '') +
      check(
        'cap',
        'Pointer cap to keycap skirt',
        'Ø5 mm cap, no finger allowance',
      ) +
      check('keys', 'Keycap to keycap', 'All 42 cap footprints') +
      check(
        'pointerBay',
        'Pointer to top-side electronics',
        st.mount === 'under'
          ? 'Carrier opening vs. component footprints'
          : 'Sensor card vs. component footprints',
      ) +
      (st.mount === 'under'
        ? check(
            'support',
            'Sensor reserve to support',
            '3D: provisional back-cover spacers',
          )
        : '') +
      check('bay', 'Electronics bay', 'Boards, pouch and switch housings') +
      '<p><b>Assembly box:</b> ' +
      fmt(r.width) +
      ' × ' +
      fmt(r.depth) +
      ' × ' +
      fmt(r.height) +
      ' mm, at this split separation; exploded offsets are excluded.</p>' +
      (st.mount === 'under'
        ? '<p><b>What the underside check assumes:</b> Direct solder, not hot-swap. Choc terminals allow 1.4 mm below this 1.6 mm carrier plus 0.4 mm for solder; the ULP alternative instead reserves a provisional 0.6 mm process zone. Sensor front and rear hardware have 0.5 and 0.8 mm reserves. The cover lowers automatically; its clearance is a design allowance, not a measurement. The rubber top is ' +
          fmt(r.halves[1].pointer.capTop - r.halves[1].pointer.stemTop) +
          ' mm above the stock post tip, including rubber. The detached driver stays on top.</p>'
        : '') +
      '<p><b>Not verified:</b> actual solder, routed copper, milled corners, sensor retention/adapter, flex and wobble of the longer shaft, fasteners, wire bends, hot-swap sockets, USB plug and battery swelling. Moving a key changes Z but not its conservative skirt footprint; hiding parts never changes the report.</p>',
  );
}
function sources() {
  show(
    'REFERENCE LIBRARY / MECHANICAL',
    'Parts & sources',
    '<p>Supplier dimensions, measured reference builds and proposed allowances are kept separate. W × D are in the PCB plane; heights are measured from the PCB top unless noted.</p>' +
      Object.values(PARTS).map(partBlock).join(''),
  );
}
function esc(x) {
  return String(x)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}
function svgTemplate() {
  const d = model;
  const sheet = [];
  let row = 36;
  for (const h of d.halves) {
    const xs = h.outline.map((p) => p[0]),
      ys = h.outline.map((p) => p[1]),
      minx = Math.min(...xs),
      maxx = Math.max(...xs),
      miny = Math.min(...ys);
    let tx = (210 - (maxx - minx)) / 2 - minx,
      ty = row - miny;
    const pol = (pts, fill, stroke) =>
      '<polygon points="' +
      pts.map((p) => p.map((v) => v.toFixed(3)).join(',')).join(' ') +
      '" fill="' +
      fill +
      '" stroke="' +
      stroke +
      '" stroke-width=".26"/>';
    sheet.push(
      '<text x="10" y="' +
        (row - 3) +
        '" font-size="3.3">' +
        h.hand.toUpperCase() +
        ' HALF</text><g transform="translate(' +
        tx +
        ' ' +
        ty +
        ')">' +
        pol(h.outline, '#f2f4ec', '#556256') +
        h.keys
          .map(
            (k) =>
              pol(rect(k, d.cap.w, d.cap.h), 'white', '#555') +
              '<text x="' +
              k.x +
              '" y="' +
              (k.y + 1) +
              '" text-anchor="middle" font-size="3">' +
              esc(k.label) +
              '</text>',
          )
          .join('') +
        h.mouse.map((k) => pol(rect(k, 8, 5), '#d6dccf', '#777')).join('') +
        (h.pointer
          ? '<circle cx="' +
            h.pointer.x +
            '" cy="' +
            h.pointer.y +
            '" r="2.5" fill="#b64d34"/>'
          : '') +
        '</g>',
    );
    row += Math.max(...ys) - miny + 10;
  }
  return (
    '<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297"><g font-family="sans-serif" fill="#28352d"><text x="10" y="11" font-size="5.5">Tapir / 1:1 reach template</text><text x="10" y="18" font-size="3.2">' +
    (st.placement === 'thumb' ? 'Thumb cluster' : 'Between columns') +
    ' · ' +
    st.splay +
    '° splay · ' +
    st.gap +
    ' mm extra gap · ' +
    (st.mount === 'under' ? 'under PCB' : 'top mount') +
    ' · ' +
    st.switchType +
    ' · print at 100%, no fit-to-page</text>' +
    sheet.join('') +
    '<path d="M10 277h50m-50 -2v4m50 -4v4" stroke="#263028" fill="none" stroke-width=".35"/><text x="10" y="285" font-size="3.2">Calibration: this line must measure 50 mm. Cut the halves apart to position them independently.</text></g></svg>'
  );
}
function download(compare = false) {
  const a = document.createElement('a'),
    ur = URL.createObjectURL(
      new Blob([compare ? comparisonSVG(st) : svgTemplate()], {
        type: 'image/svg+xml',
      }),
    );
  a.href = ur;
  a.download = compare ? 'tapir-thumb-reach-1to1.svg' : 'tapir-1to1-layout.svg';
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(ur), 30000);
}
document.addEventListener('click', (e) => {
  const b = e.target.closest('button');
  if (!b) return;
  if (b.dataset.field) {
    let f = b.dataset.field;
    if (
      st.mode === 'underside' &&
      ((f === 'mode' && b.dataset.value !== 'underside') || f === 'view')
    )
      leaveUnderside();
    st[f] = b.dataset.value;
    if (f === 'mount') $('#preset').value = 'custom';
    if (f === 'mode' && st.mode === 'underside' && st.mount === 'under')
      openUnderside();
    if (f === 'view' && st.mode === 'underside') {
      st.mode = 'assembled';
    }
    changed();
    if (f === 'view') view.setView(st.view);
    return;
  }
  switch (b.dataset.action) {
    case 'compare':
      download(true);
      break;
    case 'sourcing':
      show(
        'COMPONENT SELECTION / POINTER',
        'Sensor & donor options',
        '<p>The 3D geometry and fit numbers use the Sprintek reference only. A salvaged ThinkPad assembly is a valid alternative, not a drop-in replacement.</p>' +
          [
            PARTS.pointer,
            ...Object.values(PARTS).filter((p) => p.name.includes('T440')),
          ]
            .map(partBlock)
            .join(''),
      );
      break;
    case 'reveal':
      openUnderside();
      st.layers.electronics = true;
      st.layers.pcb = true;
      st.layers.switches = true;
      changed();
      document.querySelector('.viewport').scrollIntoView({ block: 'center' });
      break;
    case 'assembly':
      if (dialog.open) dialog.close();
      break;
    case 'sources':
      sources();
      break;
    case 'fit':
      fit();
      break;
    case 'export':
      download();
      break;
    case 'layers':
      $('#layerpop').hidden = !$('#layerpop').hidden;
      break;
    case 'home':
      view.setView(st.view);
      break;
    case 'reset':
      restoreBack = false;
      Object.assign(st, structuredClone(INITIAL));
      $('#preset').value = 'thumb';
      $('#layerpop').hidden = true;
      changed();
      view.setView('iso');
      break;
    case 'close':
      dialog.close();
      break;
  }
});
document.querySelectorAll('[data-layer]').forEach(
  (x) =>
    (x.onchange = () => {
      if (x.dataset.layer === 'back') restoreBack = false;
      st.layers[x.dataset.layer] = x.checked;
      changed();
    }),
);
dialog.addEventListener('click', (e) => {
  if (e.target === dialog) {
    let r = dialog.getBoundingClientRect();
    if (
      e.clientX < r.left ||
      e.clientX > r.right ||
      e.clientY < r.top ||
      e.clientY > r.bottom
    )
      dialog.close();
  }
});
document.addEventListener('pointerdown', (e) => {
  if (!e.target.closest('#layerpop,[data-action="layers"]'))
    $('#layerpop').hidden = true;
});
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') $('#layerpop').hidden = true;
});
icons();
sync();
mountStackStudy(() => st);
