import test from 'node:test';
import assert from 'node:assert/strict';
import { INITIAL, SPECS, clearance, layout, rect } from './layout.js';

const build = (overrides) => layout({ ...INITIAL, ...overrides });
const near = (actual, expected) =>
  assert.ok(
    Math.abs(actual - expected) <= 1e-7,
    `expected ${actual} to be within 0.0000001 mm of ${expected}`,
  );
const half = (model, hand) => model.halves.find((h) => h.hand === hand);

test('each half has a mirrored 3×6 matrix and three thumbs, with the input devices on the requested hands', () => {
  const model = build(),
    left = half(model, 'left'),
    right = half(model, 'right');
  for (const hand of [left, right]) {
    assert.equal(hand.keys.length, 21);
    assert.equal(hand.keys.filter((k) => k.thumb).length, 3);
    for (let row = 0; row < 3; row++) {
      const columns = hand.keys
        .filter((k) => !k.thumb && k.row === row)
        .map((k) => k.c)
        .sort();
      assert.deepEqual(columns, [0, 1, 2, 3, 4, 5]);
    }
  }
  for (const k of left.keys) {
    const mirror = right.keys.find(
      (other) => other.row === k.row && other.c === k.c,
    );
    near(k.x, -mirror.x);
    near(k.y, mirror.y);
    near(k.a, -mirror.a);
    if (!k.thumb) near(mirror.a, k.c < 4 ? 0 : INITIAL.splay);
  }
  assert.equal(left.mouse.length, 3);
  assert.equal(right.mouse.length, 0);
  assert.equal(left.pointer, null);
  assert.ok(right.pointer && right.driver);
});

test('nominal clearances are positive, but the fit check distinguishes a clear nub from a colliding sensor board', () => {
  for (const switchType of ['choc', 'ulp']) {
    const { mins } = build({ switchType });
    for (const [name, distance] of Object.entries(mins)) {
      assert.ok(
        Number.isFinite(distance) && distance > 0,
        `${switchType}: ${name} should clear at nominal settings`,
      );
    }
  }
  const partial = build({ splay: 0, gap: 8 }).mins;
  assert.ok(
    partial.cap > 0 && partial.sensor < 0,
    'a visibly clear nub does not guarantee room below',
  );
  const crowded = build({ splay: 0, gap: 0 }).mins;
  assert.ok(
    crowded.cap < 0 && crowded.sensor < 0,
    'removing both splay and gap should collide',
  );
  assert.ok(
    crowded.keys > 0,
    'the problem is pointer interference, not neighboring keycaps',
  );
});

test('inner separation changes desk span, while a wider column gap actually makes room for the sensor', () => {
  const nominal = build(),
    delta = 12,
    apart = build({ separation: INITIAL.separation + delta });
  const innerEdges = apart.halves.map((h) =>
    h.outline.map(([x]) => x + h.origin.x),
  );
  near(
    Math.min(...innerEdges[1]) - Math.max(...innerEdges[0]),
    INITIAL.separation + delta,
  );
  near(apart.width - nominal.width, delta);
  near(apart.depth, nominal.depth);
  assert.deepEqual(
    apart.mins,
    nominal.mins,
    'moving a whole half must not alter its internal clearances',
  );
  const wider = build({ gap: INITIAL.gap + 4 });
  assert.ok(
    wider.width > nominal.width && wider.mins.sensor > nominal.mins.sensor,
  );
  near(wider.height, nominal.height);
});

test('pressing keys cannot shrink a fixed nub or controller; a thicker ULP pouch can become the tallest part', () => {
  for (const switchType of ['choc', 'ulp']) {
    const rest = build({ switchType }),
      pressed = build({ switchType, pressed: true });
    const nub = half(rest, 'right').pointer;
    assert.ok(nub.capTop > rest.cap.top && rest.cap.travel > 0);
    near(half(pressed, 'right').pointer.capTop, nub.capTop);
    near(pressed.height, rest.height);
    assert.deepEqual(
      pressed.mins,
      rest.mins,
      'vertical travel does not change the XY fit report',
    );
  }
  const low = build({ switchType: 'ulp' }),
    tall = build({ switchType: 'ulp', batteryT: 6 });
  const baselinePeak = Math.max(
    half(low, 'right').pointer.capTop,
    SPECS.controller.t,
    INITIAL.batteryT,
  );
  near(tall.height - low.height, 6 - baselinePeak);
  near(tall.width, low.width);
  near(tall.depth, low.depth);
});

test('signed clearance measures real face and corner distances, not axis-aligned envelope overlap', () => {
  const plate = (x, y, a = 0, w = 2, d = 2) => rect({ x, y, a }, w, d);
  // Two 10×2 plates turned 45 degrees: the axis-aligned envelopes overlap, but the long faces are 2 mm apart.
  const u = Math.SQRT1_2,
    a = plate(0, 0, 45, 10, 2),
    b = plate(-4 * u, 4 * u, 45, 10, 2);
  near(clearance(a, b), 2);
  near(clearance(b, a), 2);
  // Axis-aligned nearest corners form a 3–4–5 triangle. Touching is neither separation nor interference.
  near(clearance(plate(0, 0), plate(5, 6)), 5);
  near(clearance(plate(0, 0), plate(2, 0)), 0);
  // Small square fully inside a rotated 10×10 square requires 6 mm of translation to escape.
  near(clearance(plate(7, 9, 24, 10, 10), plate(7, 9, 24)), -6);
});
