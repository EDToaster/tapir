import test from 'node:test';
import assert from 'node:assert/strict';
import { INITIAL, PRESETS, layout } from './layout.js';
import { STACK_DEFAULTS, stackModel } from './stack.js';
import { stackPrint } from './stack-print.js';

const near = (a, b) => assert.ok(Math.abs(a - b) < 1e-6, `${a} != ${b}`);
test('the compact candidate preserves both outside spans, the three thumb keys and a free USB approach', () => {
  const m = stackModel(),
    base = layout(INITIAL).halves[1];
  near(m.metrics.baselineWidth, m.metrics.rightWidth);
  near(m.metrics.baselineDepth, m.metrics.rightDepth);
  assert.deepEqual(
    m.baseline.keys.filter((k) => k.thumb),
    base.keys.filter((k) => k.thumb),
  );
  assert.equal(m.nearestThumb.label, 'Lower');
  assert.ok(m.metrics.nearestThumbDistance < m.metrics.headDistance);
  assert.ok(
    m.metrics.keyGap >= 1 && m.metrics.plugGap >= 1 && m.metrics.rfGap > 0,
  );
  assert.ok(m.metrics.screened && m.metrics.addedCarrierArea > 0);
  assert.ok(
    m.checks.some((c) => c.status === 'open'),
    'nominal feasibility is not prototype validation',
  );
});
const center = () =>
  stackModel({ headShift: 0, headAcross: 0, offsetX: 0, offsetY: 0 });
test('full head/controller overlap is not a passing fit: original centered thumb site hits the swept typing envelope', () => {
  const m = center();
  assert.ok(m.metrics.overlapFraction > 0.95);
  assert.equal(m.checks.find((c) => c.id === 'keys').status, 'clash');
  assert.equal(m.metrics.screened, false);
  assert.deepEqual(
    m.baseline.keys,
    layout({ ...INITIAL, ...PRESETS.thumb }).halves[1].keys,
  );
});
test('raising the bridge moves the stick in Z, not its XY or the unmoved controller', () => {
  const a = stackModel({ gap: 0.8 }),
    b = stackModel({ gap: 2.3 });
  near(b.metrics.capTop - a.metrics.capTop, 1.5);
  near(b.refs.deck.bottom - a.refs.deck.bottom, 1.5);
  assert.deepEqual(a.head, b.head);
  assert.deepEqual(a.refs.usb, b.refs.usb);
});
test('simulating a keypress moves the pictured thumb key but cannot waive a collision during its full stroke', () => {
  const opts = {
    ...STACK_DEFAULTS,
    headShift: 0,
    headAcross: 0,
    offsetX: 0,
    offsetY: 0,
  };
  const a = stackModel(opts, { pressed: false }),
    b = stackModel(opts, { pressed: true });
  near(a.metrics.keyGap, b.metrics.keyGap);
  near(a.refs.movingCaps.at(-3).top - b.refs.movingCaps.at(-3).top, 3);
});
test('print uses true A4 units, a 50 mm ruler, and separate target and baseline nubs at model coordinates', () => {
  const m = stackModel(),
    svg = stackPrint(m, INITIAL);
  assert.match(svg, /width="210mm" height="297mm" viewBox="0 0 210 297"/);
  assert.match(svg, /M13 274h50/);
  assert.ok(svg.includes(`class="target" cx="${m.head.x}" cy="${m.head.y}"`));
  assert.ok(
    svg.includes(
      `class="old" cx="${m.baseline.head.x}" cy="${m.baseline.head.y}"`,
    ),
  );
});
