import { STACK_DEFAULTS, stackModel, stackSVG } from './stack.js';
import { stackPrint } from './stack-print.js';
import { createStackOrbit } from './stack-orbit.js';
import './stack.css';

const $ = (selector) => document.querySelector(selector);
const controls = {
  headAcross: ['Move stick along thumb row', -18, 54, 0.5],
  headShift: ['Move stick toward palm', -18, 18, 0.5],
  offsetX: ['Move XIAO across the half', -16, 16, 0.5],
  offsetY: ['Move XIAO toward palm', -16, 16, 0.5],
  gap: ['Vertical clearance', 0, 4, 0.1],
};
const clean = (text) =>
  String(text).replace(
    /[&<>"']/g,
    (c) =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[
        c
      ],
  );
const mm = (n) =>
  n == null || !Number.isFinite(n)
    ? 'n/a'
    : new Intl.NumberFormat('en', { maximumFractionDigits: 2 }).format(n);

export function mountStackStudy(getState) {
  let view = 'iso',
    params = { ...STACK_DEFAULTS },
    active = false;
  let profile = 'choc',
    down = false;
  let orbit = null,
    noWebGL = false;
  if (import.meta.env.DEV) {
    $('#stack-step').href =
      'https://github.com/EDToaster/tapir/raw/refs/heads/main/mechanical/stack/tapir-stacked-thumb.step';
  }
  $('#stack-ranges').innerHTML = Object.entries(controls)
    .map(
      ([key, [name, min, max, step]]) =>
        '<div class="param"><div class="paramhead"><label for="stack-' +
        key +
        '">' +
        name +
        '</label><output class="readout" id="stack-out-' +
        key +
        '"></output></div><div class="rangewrap"><input type="range" id="stack-' +
        key +
        '" min="' +
        min +
        '" max="' +
        max +
        '" step="' +
        step +
        '"></div></div>',
    )
    .join('');
  function draw() {
    const state = { ...getState(), switchType: profile, pressed: down };
    const model = stackModel(params, state);
    const isOrbit = view === 'orbit' && !noWebGL;
    $('#stack-orbit-region').hidden = !isOrbit;
    $('#stack-canvas').hidden = isOrbit;
    if (isOrbit) {
      try {
        orbit ||= createStackOrbit($('#stack-orbit'));
        orbit.update(model);
      } catch {
        noWebGL = true;
        view = 'iso';
        $('#stack-views [data-stack-view=orbit]').disabled = true;
        return draw();
      }
    } else
      $('#stack-canvas').innerHTML = stackSVG(
        model,
        view === 'orbit' ? 'iso' : view,
      );
    $('#stack-direction').value = params.orientation;
    $('#stack-switch').value = profile;
    $('#stack-pressed').checked = down;
    for (const [k, [, min, max]] of Object.entries(controls)) {
      const el = $('#stack-' + k);
      el.value = params[k];
      el.style.setProperty(
        '--pct',
        ((params[k] - min) * 100) / (max - min) + '%',
      );
      $('#stack-out-' + k).textContent = mm(params[k]) + ' mm';
    }
    document.querySelectorAll('[data-stack-view]').forEach((el) => {
      const selected = el.dataset.stackView === view;
      el.classList.toggle('sel', selected);
      el.setAttribute('aria-pressed', String(selected));
    });
    report(model);
  }
  function preset(value) {
    params = { ...STACK_DEFAULTS };
    if (value === 'center')
      Object.assign(params, {
        headAcross: 0,
        headShift: 0,
        offsetX: 0,
        offsetY: 0,
      });
    if (value === 'inner')
      Object.assign(params, {
        orientation: 'inner',
        headAcross: 0,
        headShift: 5,
        offsetX: 4,
        offsetY: 4,
        gap: 2,
      });
    if (value === 'first')
      Object.assign(params, { headAcross: 0, headShift: 8 });
    $('#stack-preset').value = value;
    draw();
  }
  function show(on, scroll = true) {
    active = on;
    $('#assembly-study').hidden = on;
    $('#stack-study').hidden = !on;
    document
      .querySelector('.nav[data-action=assembly]')
      .classList.toggle('on', !on);
    document
      .querySelector('.nav[data-action=stack]')
      .classList.toggle('on', on);
    if (on) draw();
    else window.dispatchEvent(new Event('resize'));
    if (scroll) window.scrollTo(0, 0);
  }
  function nav(on) {
    if (active === on) return;
    const hash = on ? '#stack' : '#assembly';
    // Sandboxed embed hosts may not permit rewriting the iframe URL.
    if (location.hash !== hash) {
      try {
        history.replaceState(null, '', hash);
      } catch {
        /* view still switches */
      }
    }
    show(on);
  }
  document.addEventListener('click', (event) => {
    const button = event.target.closest('button');
    if (!button) return;
    if (button.dataset.action === 'stack') {
      profile = getState().switchType;
      down = getState().pressed;
      nav(true);
    }
    if (button.dataset.action === 'assembly') nav(false);
    if (button.dataset.stackView) {
      view = button.dataset.stackView;
      draw();
    }
    if (button.id === 'stack-focus') orbit?.center(false);
    if (button.id === 'stack-whole') orbit?.center(true);
    if (button.id === 'stack-reset') {
      view = 'iso';
      profile = 'choc';
      down = false;
      preset('compact');
    }
  });
  $('#stack-preset').onchange = (e) => preset(e.target.value);
  $('#stack-print').onclick = () => {
    const state = { ...getState(), switchType: profile, pressed: down };
    const text = stackPrint(stackModel(params, state), state);
    const url = URL.createObjectURL(
      new Blob([text], { type: 'image/svg+xml' }),
    );
    const a = document.createElement('a');
    a.href = url;
    a.download = 'tapir-stack-reach-and-usb-1to1.svg';
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 30000);
  };
  $('#stack-direction').onchange = (e) => {
    params.orientation = e.target.value;
    $('#stack-preset').value = 'custom';
    draw();
  };
  $('#stack-switch').onchange = (e) => {
    profile = e.target.value;
    draw();
  };
  $('#stack-pressed').onchange = (e) => {
    down = e.target.checked;
    draw();
  };
  for (const k of Object.keys(controls))
    $('#stack-' + k).oninput = (e) => {
      params[k] = Number(e.target.value);
      $('#stack-preset').value = 'custom';
      draw();
    };
  window.addEventListener('hashchange', () => show(location.hash === '#stack'));
  if (location.hash === '#stack') show(true, false);
}
function report(model) {
  // All displayed dimensions come from the geometry engine, not from the drawing.
  const m = model.metrics;
  const datumReach = Math.hypot(
    model.baseline.head.x - model.thumb.x,
    model.baseline.head.y - model.thumb.y,
  );
  const cards = [
    [
      'Nearest thumb · ' + m.nearestThumbLabel,
      m.nearestThumbDistance,
      datumReach,
    ],
    ['Assembled height', m.totalHeight, m.baselineHeight],
    ['Right-half depth', m.rightDepth, m.baselineDepth],
  ];
  $('#stack-numbers').innerHTML = cards
    .map(
      ([name, v, old], i) =>
        '<div class="metric"><sup>0' +
        (i + 1) +
        '</sup><span class="metric-label">' +
        name +
        '</span><strong>' +
        mm(v) +
        '</strong><small>mm</small><span class="stack-prior">Baseline: ' +
        mm(old) +
        ' mm</span></div>',
    )
    .join('');
  const status = {
    clash: 'Interference',
    screen: 'Clears model',
    open: 'Verify physically',
  };
  $('#stack-checks').innerHTML = model.checks
    .map(
      (c) =>
        '<div class="stack-check ' +
        clean(c.status) +
        '"><div><b>' +
        clean(c.label) +
        '</b><span>' +
        clean(c.detail) +
        '</span></div><strong>' +
        clean(status[c.status]) +
        (c.value == null ? '' : '<small>' + mm(c.value) + ' mm</small>') +
        '</strong></div>',
    )
    .join('');
  $('#stack-verdict').innerHTML =
    '<b>' +
    (m.screened
      ? 'No clash in the nominal screens.'
      : 'This configuration has a modeled clash.') +
    '</b> ' +
    mm(100 * m.overlapFraction) +
    '% of the sensor PCB overlaps the XIAO in plan. Including support and connector, the local package is ' +
    mm(m.localWidth) +
    ' × ' +
    mm(m.localDepth) +
    ' mm. Right-half width is ' +
    mm(m.rightWidth) +
    ' mm (' +
    mm(m.baselineWidth) +
    ' mm unstacked). The nub is ' +
    mm(Math.abs(m.capTop - m.keyTop)) +
    ' mm ' +
    (m.capTop >= m.keyTop ? 'above' : 'below') +
    ' a released keycap.';
  $('#stack-rehome').textContent =
    'The original controller center is ' +
    mm(
      Math.hypot(
        model.thumb.x - model.baseline.controller.x,
        model.thumb.y - model.baseline.controller.y,
      ),
    ) +
    ' mm from the innermost thumb key. This study moves the XIAO to the thumb, rather than asking the thumb to reach the old USB bay. The old perimeter is retained; no size reduction is credited until that perimeter is redesigned.';
}
