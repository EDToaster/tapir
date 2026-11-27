import test from 'node:test';
import assert from 'node:assert/strict';
import { Vector3, OrthographicCamera } from 'three';
import { layout, INITIAL, PRESETS, SPECS } from './layout.js';
import { createFallback } from './fallback.js';
import { baselineCut, sectionHTML } from './section.js';
import { stackModel, stackSVG } from './stack.js';
import { stackPrint } from './stack-print.js';
import { comparisonSVG } from './reach.js';
import {
  bounds2,
  fitFrame,
  toThree,
  viewAngles,
  projector,
  assemblyEnvelope,
} from './projection.js';

const near = (a, b, tol = 0.00001) =>
  assert.ok(Math.abs(a - b) < tol, `${a} ≠ ${b}`);
const polyPoints = (s) =>
  [...s.matchAll(/<polygon\b[^>]*\bpoints="([^"]+)"/g)].flatMap((m) =>
    m[1]
      .trim()
      .split(/\s+/)
      .map((p) => p.split(',').map(Number)),
  );
const widthModes = [
  [320, 900],
  [375, 275],
  [1440, 540],
  [2000, 180],
];
const presets = Object.values(PRESETS).map((p, i) => ({
  ...INITIAL,
  ...p,
  pressed: i % 2 === 1,
  switchType: i % 2 ? 'ulp' : 'choc',
  separation: i % 2 ? 4 : 95,
  batteryT: 8,
  standoff: i % 2 ? 0.4 : 4,
}));
presets.push({
  ...INITIAL,
  thumbX: 8,
  thumbY: 4,
  splay: 28,
  gap: 18,
  separation: 95,
  batteryT: 8,
  standoff: 4,
});
const candidates = [
  {},
  { headAcross: 0, headShift: 0, offsetX: 0, offsetY: 0, orientation: 'keys' },
  {
    headAcross: -18,
    headShift: 18,
    offsetX: -16,
    offsetY: 16,
    orientation: 'inner',
    gap: 4,
  },
  {
    headAcross: 54,
    headShift: -18,
    offsetX: 16,
    offsetY: -16,
    orientation: 'outer',
    gap: 0,
  },
];

test('SVG and Three project the same real PCB landmarks into the same fitted viewport', () => {
  for (const s of presets) {
    const model = layout(s);
    for (const mode of ['assembled', 'underside', 'exploded'])
      for (const view of ['iso', 'top', 'front']) {
        const [yaw, el] = viewAngles(view, mode === 'underside'),
          proj = projector(yaw, el);
        const points = assemblyEnvelope(model, { ...s, mode }, SPECS);
        const b = bounds2(points.map(proj)),
          dir = new Vector3(
            Math.sin(yaw) * Math.cos(el),
            Math.sin(el),
            Math.cos(yaw) * Math.cos(el),
          );
        for (const [w, h] of widthModes) {
          const f = fitFrame(b, w / h),
            cam = new OrthographicCamera(
              f.x,
              f.x + f.w,
              -f.y,
              -f.y - f.h,
              0.1,
              2000,
            );
          cam.position.copy(dir).multiplyScalar(500);
          // At an exact pole the preset basis is the limit approaching from the palm.
          if (view === 'top') cam.up.set(0, 0, -Math.sign(el));
          cam.lookAt(0, 0, 0);
          cam.updateMatrixWorld();
          for (const p of points) {
            const [x, y] = proj(p),
              v = new Vector3(...toThree(p)).project(cam);
            near((v.x + 1) / 2, (x - f.x) / f.w);
            near((1 - v.y) / 2, (y - f.y) / f.h);
            assert.ok(Math.abs(v.x) < 1 && Math.abs(v.y) < 1);
          }
        }
      }
  }
});

test('actual vector fallback never clips a visible part after resize or preset change at fit zoom', () => {
  let queued;
  const svg = {
    style: {},
    attrs: {},
    setAttribute(k, v) {
      this.attrs[k] = v;
    },
    addEventListener() {},
    remove() {},
  };
  const host = { appendChild() {}, clientWidth: 1, clientHeight: 1 };
  globalThis.document = {
    createElementNS() {
      return svg;
    },
  };
  globalThis.requestAnimationFrame = (f) => ((queued = f), 1);
  globalThis.cancelAnimationFrame = () => {};
  const f = createFallback(host, () => {});
  try {
    for (const [i, s] of presets.entries())
      for (const [j, view] of ['top', 'iso', 'front'].entries()) {
        [host.clientWidth, host.clientHeight] =
          widthModes[(i + j) % widthModes.length];
        f.update({
          ...s,
          view,
          mode: ['assembled', 'exploded', 'underside'][(i + j) % 3],
        });
        queued();
        const [x, y, w, h] = svg.attrs.viewBox.split(' ').map(Number);
        const parts = polyPoints(
          svg.innerHTML.slice(svg.innerHTML.indexOf('<g data-part=')),
        );
        assert.ok(parts.length > 300);
        for (const [px, py] of parts)
          assert.ok(
            px >= x - 0.02 &&
              px <= x + w + 0.02 &&
              py >= y - 0.02 &&
              py <= y + h + 0.02,
            `${view} part ${px},${py} outside ${svg.attrs.viewBox}`,
          );
      }
  } finally {
    f.destroy();
    delete globalThis.document;
    delete globalThis.requestAnimationFrame;
    delete globalThis.cancelAnimationFrame;
  }
});

test('cutouts, post, hub and rubber share the physical shaft; a top-mounted card has continuous laminate', () => {
  for (const s of presets) {
    const m = layout(s),
      cut = baselineCut(m, s),
      by = (k) => cut.solids.filter((t) => t.role === k);
    for (const k of ['cap', 'post', 'hub']) near(by(k)[0].a + by(k)[0].b, 0);
    near(by('cap')[0].top, m.halves[1].pointer.capTop);
    assert.equal(
      by('carrier').some((t) => t.a < 0 && t.b > 0),
      s.mount !== 'under',
    );
    const p = m.halves[1].pointer;
    near(by('sensor')[0].bottom, p.boardBottom);
    near(by('sensor')[0].top, p.boardTop);
    assert.ok(sectionHTML(m, s).includes('data-role="post"'));
  }
});

test('selected plan, shaft section and A4 export stay registered when the head, controller and port move', () => {
  for (const opts of candidates)
    for (const switchType of ['choc', 'ulp']) {
      const m = stackModel(opts, { switchType, pressed: true }),
        svg = stackPrint(m, { switchType });
      const expected = m.refs.carrier.polygon
        .map((p) => p.map((x) => x.toFixed(3)).join(','))
        .join(' ');
      assert.ok(
        svg.includes('<polygon class="outline" points="' + expected + '"'),
      );
      const tr = svg
        .match(/<g transform="translate\(([^ ]+) ([^)]+)\)"/)
        .slice(1)
        .map(Number);
      for (const [x, y] of polyPoints(svg))
        assert.ok(
          x + tr[0] > 5 && x + tr[0] < 205 && y + tr[1] > 42 && y + tr[1] < 211,
        );
      for (const view of ['iso', 'plan', 'section']) {
        const drawing = stackSVG(m, view, true),
          focus = drawing.split('<g data-solid=')[1];
        assert.ok(focus);
        const polys = [
          ...drawing.matchAll(/<g data-solid="[^"]+">([\s\S]*?)<\/g>/g),
        ].flatMap((t) => polyPoints(t[1]));
        for (const [x, y] of polys)
          assert.ok(
            x >= 18.9 && x <= 466.1 && y >= 33.9 && y <= 254.1,
            `${view}: ${x},${y}`,
          );
        if (view === 'section') {
          const cut = drawing.match(
            /d="M([\d.]+) [\d.]+L([\d.]+) [\d.]+"[^>]*data-datum="shaft-axis"/,
          );
          assert.ok(cut);
          near(+cut[1], +cut[2]);
          for (const part of ['post', 'stick-cap']) {
            const b = bounds2(
              polyPoints(
                drawing.match(
                  new RegExp('<g data-solid="' + part + '">([\\s\\S]*?)</g>'),
                )[1],
              ),
            );
            near((b.x0 + b.x1) / 2, +cut[1], 0.015);
          }
        }
      }
    }
});

test('A4 comparison keeps homes on the same X datum and both 1:1 outlines between their panel captions and ruler', () => {
  for (const s of presets) {
    const svg = comparisonSVG(s),
      panels = [
        ...svg.matchAll(
          /<g data-panel="([AB])">([\s\S]*?)(?=<g data-panel=|<line x1="12" x2="198" y1="275")/g,
        ),
      ],
      xs = [];
    for (const [, name, content] of panels) {
      const [, x, y] = content.match(
          /data-feature="right-half" transform="translate\(([^ ]+) ([^)]+)\)/,
        ),
        b = bounds2(polyPoints(content));
      assert.ok(b.x0 + +x > 5 && b.x1 + +x < 205);
      assert.ok(
        b.y0 + +y > 30 && b.y1 + +y < 274,
        `${name} crosses header/footer`,
      );
      const home = content.match(
        /transform="translate\(([^ ]+) ([^)]+)\) rotate\([^"]+\)">J</,
      );
      xs.push(+home[1] + +x);
    }
    assert.equal(xs.length, 2);
    near(xs[0], xs[1], 0.002);
  }
});
