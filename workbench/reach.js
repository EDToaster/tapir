import { layout, PRESETS, rect, SPECS } from './layout.js';

// A standalone A4 print document. A single viewBox unit is one millimeter.
// Only translations and rotations are used: neither diagram is scaled to fit.
const W = 210,
  H = 297;
const n = (v) => Number(v.toFixed(3));
const esc = (value) =>
  String(value).replace(
    /[&<>"']/g,
    (c) =>
      ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&apos;',
      })[c],
  );
const pts = (ring) => ring.map(([x, y]) => `${n(x)},${n(y)}`).join(' ');
const tag = (x, y, txt, cls, anchor = 'start') =>
  `<text x="${n(x)}" y="${n(y)}" class="${cls}" text-anchor="${anchor}">${esc(txt)}</text>`;

function rightSide(state) {
  const model = layout(state),
    hand = model.halves.find((h) => h.hand === 'right');
  const { keys, pointer } = hand,
    thumbs = keys.filter((k) => k.thumb);
  const nearest = thumbs.reduce((a, b) =>
    Math.hypot(pointer.x - a.x, pointer.y - a.y) <=
    Math.hypot(pointer.x - b.x, pointer.y - b.y)
      ? a
      : b,
  );
  const distance = Math.hypot(nearest.x - pointer.x, nearest.y - pointer.y);
  // Common horizontal registration at the right index home key makes the two studies comparable.
  const home =
    keys.find((k) => k.label === 'J') ??
    keys.find((k) => k.row === 1 && k.c === 1);
  const r = SPECS.pointer.cap / 2;
  const marks = [
    ...hand.outline,
    ...keys.flatMap((k) => rect(k, model.cap.w, model.cap.h)),
    [pointer.x - r, pointer.y - r],
    [pointer.x + r, pointer.y + r],
  ];
  const xs = marks.map(([x]) => x - home.x),
    ys = marks.map(([, y]) => y - home.y);
  return {
    hand,
    cap: model.cap,
    nearest,
    distance,
    home,
    r,
    x0: Math.min(...xs),
    x1: Math.max(...xs),
    y0: Math.min(...ys),
    y1: Math.max(...ys),
  };
}

function drawPanel(study, index, title, captionY, diagramX, diagramY) {
  const { hand, cap, nearest, distance, home, r } = study,
    p = hand.pointer;
  const dx = n(diagramX - home.x),
    dy = n(diagramY - home.y);
  const cells = hand.keys.map((k) => {
    const match = k === nearest,
      cl = match ? 'nearest' : k.thumb ? 'thumb' : 'alpha';
    // Preserve the nominal rectangular envelope, including the corners used by fit calculations.
    const poly = `<polygon class="${cl}" points="${pts(rect(k, cap.w, cap.h))}"/>`;
    const label = `<text x="0" y=".98" class="legend ${k.thumb ? 'thumb-label' : ''}" text-anchor="middle" transform="translate(${n(k.x)} ${n(k.y)}) rotate(${n(k.a ?? 0)})">${esc(k.label)}</text>`;
    return { poly, label };
  });
  const reach = `<line x1="${n(p.x)}" y1="${n(p.y)}" x2="${n(nearest.x)}" y2="${n(nearest.y)}" class="reach"/>`;
  const target = `<g data-feature="pointer" transform="translate(${n(p.x)} ${n(p.y)})"><title>Pointer cap, ${2 * r} mm diameter</title><circle r="${n(r)}" class="target"/><path d="M-1.4 0h2.8M0-1.4v2.8" class="cross"/></g>`;
  return `<g data-panel="${index}"><title>${esc(title)}</title>
    ${tag(12, captionY, `${index}  /  ${title}`, 'panel-title')}
    ${tag(198, captionY, `Nearest thumb key: ${nearest.label}`, 'metric', 'end')}
    ${tag(198, captionY + 4.3, `${distance.toFixed(1)} mm center to center`, 'detail', 'end')}
    <g data-feature="right-half" transform="translate(${dx} ${dy})">
      <polygon class="carrier" points="${pts(hand.outline)}"/>
      ${cells.map((c) => c.poly).join('')}${reach}${cells.map((c) => c.label).join('')}${target}
    </g></g>`;
}

/** Downloadable 1:1 paper test: right thumb target vs. the earlier straight inter-column target. */
export function comparisonSVG(state) {
  const custom = state.placement === 'thumb';
  const candidate = {
    ...state,
    ...PRESETS.thumb,
    thumbX: custom
      ? (state.thumbX ?? PRESETS.thumb.thumbX ?? 0)
      : (PRESETS.thumb.thumbX ?? 0),
    thumbY: custom
      ? (state.thumbY ?? PRESETS.thumb.thumbY ?? 0)
      : (PRESETS.thumb.thumbY ?? 0),
  };
  const reference = { ...state, ...PRESETS.straight };
  const a = rightSide(candidate),
    b = rightSide(reference),
    left = Math.min(a.x0, b.x0),
    right = Math.max(a.x1, b.x1);
  const diagramX = (W - left - right) / 2;
  const firstTop = 39,
    secondCaption = firstTop + (a.y1 - a.y0) + 9,
    secondTop = secondCaption + 7;
  const firstCaption = firstTop - 7;
  const switchName =
    state.switchType === 'ulp' ? 'PG1316S / 16 mm caps' : 'Choc v1 / MBK caps';
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 ${W} ${H}" role="img" aria-labelledby="title desc" lang="en">
  <title id="title">Tapir right-thumb reach comparison, actual size</title>
  <desc id="desc">Two right-half keyboard outlines at 1:1. The crossed disk is the pointer cap. The dashed line joins its center to the nearest outlined thumb key. Print on A4 at 100 percent and verify the 50 millimeter scale.</desc>
  <style>
    @page { size: A4 portrait; margin: 0; }
    svg { print-color-adjust: exact; -webkit-print-color-adjust: exact; }
    text { font-family: Arial, Helvetica, sans-serif; fill: #252e29; }
    .kicker { font-size: 2.6px; font-weight: 700; letter-spacing: .42px; }
    .title { font-size: 6.1px; font-weight: 700; letter-spacing: -.19px; }
    .instruction, .metric { font-size: 3.1px; }
    .panel-title { font-size: 3.8px; font-weight: 700; }
    .detail { font-size: 2.75px; fill: #48534b; }
    .carrier { fill: #f3f3ee; stroke: #667267; stroke-width: .35; stroke-linejoin: round; }
    .alpha, .thumb, .nearest { stroke-linejoin: round; }
    .alpha { fill: white; stroke: #71776e; stroke-width: .29; }
    .thumb { fill: #e6e9df; stroke: #4c594f; stroke-width: .35; }
    .nearest { fill: #e1e8dc; stroke: #273d32; stroke-width: .76; }
    .legend { font-size: 3.05px; paint-order: stroke; stroke: white; stroke-width: 1.05; stroke-linejoin: round; }
    .thumb-label { font-weight: 700; stroke: #e6e9df; }
    .reach { stroke: #525a4c; stroke-width: .35; stroke-dasharray: 1.1 1.05; }
    .target { fill: #be492d; stroke: #342b23; stroke-width: .25; }
    .cross { fill: none; stroke: white; stroke-width: .48; stroke-linecap: round; }
    .rule { stroke: #a1aaa0; stroke-width: .20; }
  </style>
  <rect width="210" height="297" fill="white"/>
  ${tag(12, 9.5, 'TAPIR  /  ERGONOMICS STUDY', 'kicker')}
  ${tag(198, 9.5, `${switchName}   /   1:1`, 'detail', 'end')}
  ${tag(12, 17.5, 'Right-thumb reach comparison', 'title')}
  ${tag(12, 23, 'Rest your index finger on J. Can your thumb reach the crossed disk without shifting your hand?', 'instruction')}
  <line x1="12" x2="198" y1="26" y2="26" class="rule"/>
  ${drawPanel(a, 'A', 'Thumb pointer', firstCaption, diagramX, firstTop - a.y0)}
  ${drawPanel(b, 'B', 'Inter-column pointer', secondCaption, diagramX, secondTop - b.y0)}
  <line x1="12" x2="198" y1="275" y2="275" class="rule"/>
  <g data-feature="calibration"><title>Calibration bar, 50 mm between tick centers</title>
    <path d="M12 282H62 M12 279.7v4.6 M62 279.7v4.6" stroke="#263029" stroke-width=".4" fill="none"/>
    ${tag(37, 288, '50 mm between ticks', 'detail', 'middle')}
  </g>
  ${tag(75, 282, 'A4 portrait. Print at 100% / Actual size.', 'metric')}
  ${tag(75, 288, 'Do not fit to page. Verify the bar with a ruler before testing.', 'detail')}
</svg>`;
}
