import { INITIAL, PRESETS, layout, rect } from './layout.js';

const points = (a) =>
  a.map((p) => p.map((x) => x.toFixed(3)).join(',')).join(' ');
const e = (s) =>
  String(s)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;');

// Stamp the same coordinates as the 3D experiment. Never auto-fit or distort a 1:1 print.
export function stackPrint(model, state) {
  const base = layout({
    ...INITIAL,
    ...state,
    ...PRESETS.thumb,
    thumbX: state.thumbX ?? 0,
    thumbY: state.thumbY ?? 0,
  });
  const hand = base.halves[1];
  const visible = new Set([
    'xiao',
    'sensor',
    'usb-shell',
    'rf-screen',
    'plug',
    'bridge',
    'driver',
  ]);
  const chosen = model.solids.filter(
    (s) => visible.has(s.id) && s.polygon?.length,
  );
  const polygon = (p, css) =>
    '<polygon class="' + css + '" points="' + points(p) + '"/>';
  const circles = (p, r, css) =>
    '<circle class="' +
    css +
    '" cx="' +
    p.x +
    '" cy="' +
    p.y +
    '" r="' +
    r +
    '"/>';
  const outline = hand.outline;
  const limits = [
    ...outline,
    ...chosen.flatMap((s) => s.polygon),
    [model.head.x, model.head.y],
  ];
  const minX = Math.min(...limits.map((p) => p[0])),
    maxX = Math.max(...limits.map((p) => p[0])),
    minY = Math.min(...limits.map((p) => p[1]));
  const tx = (210 - maxX + minX) / 2 - minX,
    ty = 52 - minY;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">
  <title>Tapir / controller stack reach and cable check</title>
  <style>@page{size:A4 portrait;margin:0}text{font-family:Arial,Helvetica,sans-serif;fill:#27362d}.outline{stroke:#60705f;stroke-width:.38;fill:#edf0e8}.key{fill:white;stroke:#778474;stroke-width:.3}.xiao{fill:#82bba7;fill-opacity:.5;stroke:#356459;stroke-width:.4}.sensor{fill:#ecac91;fill-opacity:.55;stroke:#995238;stroke-width:.4}.extra{fill:none;stroke:#6d7065;stroke-width:.25;stroke-dasharray:1 .65}.plug{fill:#b4c5da;fill-opacity:.5;stroke:#536782;stroke-width:.32;stroke-dasharray:1 .6}.old{fill:none;stroke:#424b40;stroke-width:.34;stroke-dasharray:1 .6}.target{fill:#aa482d;stroke:#623623;stroke-width:.3}</style>
  <rect width="210" height="297" fill="white"/><text x="13" y="14" font-size="3">TAPIR   /   PACKAGING STUDY 004</text>
  <text x="13" y="24" font-size="6.5" font-weight="bold">Right-thumb controller stack</text>
  <text x="13" y="32" font-size="3.4">Right half, true size. Print at 100%, not “fit to page”. Verify the 50 mm line first.</text>
  <text x="13" y="38" font-size="3">USB exit: ${e(model.options.orientation)} · ${state.switchType === 'ulp' ? 'PG1316S' : 'Choc v1 + MBK'} · layout in mm · space reservation, not a fabrication outline</text>
  <g transform="translate(${tx} ${ty})">
  ${polygon(outline, 'outline')}${hand.keys.map((k) => polygon(rect(k, base.cap.w, base.cap.h), 'key') + '<text x="' + k.x + '" y="' + (k.y + 1) + '" font-size="3" text-anchor="middle">' + e(k.label) + '</text>').join('')}
  ${chosen.map((s) => polygon(s.polygon, /plug/i.test(s.id) ? 'plug' : /^xiao$/i.test(s.id) || /xiao.*board/i.test(s.id) ? 'xiao' : /sensor.*pcb|^sensor$/i.test(s.id) ? 'sensor' : 'extra')).join('')}
  ${circles(hand.pointer, 2.5, 'old')}${circles(model.head, 2.5, 'target')}<path d="M${model.head.x - 1.3},${model.head.y}h2.6m-1.3,-1.3v2.6" fill="none" stroke="white" stroke-width=".35"/>
  </g>
  <text x="13" y="218" font-size="4.5" font-weight="bold">Try the reach before making the stack</text>
  <text x="13" y="226" font-size="3.3">1. Set your index finger on J. Touch the crossed disk without lifting your palm.</text>
  <text x="13" y="233" font-size="3.3">2. Tap Bksp and the other thumb keys. Note any accidental contact with the nub.</text>
  <text x="13" y="240" font-size="3.3">3. Lay your actual USB cable on the dashed plug area. Does it touch the palm?</text>
  <text x="13" y="250" font-size="3">Dashed circle: under-mounted baseline nub. Filled disk: selected stacked nub.</text>
  <text x="13" y="256" font-size="3">Light outline: original carrier for reference, not a finished case. Plan does not verify Z or RF.</text>
  <path d="M13 274h50m-50 -2v4m50 -4v4" stroke="#27362d" stroke-width=".38" fill="none"/>
  <text x="13" y="284" font-size="3.2">50 mm between ticks</text></svg>`;
}
