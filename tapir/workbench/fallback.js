import { layout, rect as footprint, SPECS } from './layout.js';
import {
  posePoint as pos,
  bounds2,
  fitFrame,
  projector,
  viewAngles,
  explodedOffsets as E,
  assemblyEnvelope,
} from './projection.js';

const RAD = Math.PI / 180;
const round = (n) => Number(n.toFixed(2));
const esc = (s) =>
  String(s).replace(
    /[&<>"']/g,
    (c) =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[
        c
      ],
  );
const clamp = (n, min, max) => Math.min(max, Math.max(min, n));
const box = (p, w, h, r = 0.6) => {
  const radius = Math.min(r, w / 2, h / 2),
    out = [];
  for (let i = 0; i < 4; i++)
    for (let j = 0; j < 4; j++) {
      const a = (90 * i + 30 * j) * RAD,
        cx = (i === 0 || i === 3 ? 1 : -1) * (w / 2 - radius),
        cy = (i < 2 ? 1 : -1) * (h / 2 - radius);
      out.push(pos(p, cx + radius * Math.cos(a), cy + radius * Math.sin(a)));
    }
  return out;
};
const circ = (p, r, n = 16) =>
  Array.from({ length: n }, (_, i) =>
    pos(
      p,
      r * Math.cos((i * 2 * Math.PI) / n),
      r * Math.sin((i * 2 * Math.PI) / n),
    ),
  );
const colors = {
  pcb: ['#20483c', '#3b6351', '#152d29'],
  back: ['#444944', '#625f54', '#323731'],
  cap: ['#f1eddf', '#d4cfc0', '#aaa89d'],
  dark: ['#4c5652', '#3a4641', '#2a3430'],
  housing: ['#65746c', '#46564e', '#33413b'],
  metal: ['#c8cfcd', '#a2adab', '#737f7b'],
  chip: ['#333b36', '#505650', '#202822'],
  gold: ['#e0ba75', '#a58b56', '#886c3d'],
  orange: ['#e66137', '#be4525', '#96351f'],
  silver: ['#dad9ce', '#b3b4a9', '#92968b'],
};
let instance = 0;

export function createFallback(host, onPick) {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg'),
    uid = 'tapirProjection' + ++instance;
  svg.setAttribute('width', '100%');
  svg.setAttribute('height', '100%');
  svg.setAttribute('tabindex', '0');
  svg.setAttribute('role', 'group');
  svg.setAttribute(
    'aria-label',
    'Interactive keyboard model. Drag to orbit, scroll to zoom. Use arrow keys to rotate and plus or minus to zoom.',
  );
  svg.style.cssText =
    'display:block;width:100%;height:100%;overflow:hidden;touch-action:none;cursor:grab;user-select:none';
  host.appendChild(svg);
  let state,
    model,
    yaw = 12 * RAD,
    elev = 42 * RAD,
    zoom = 1,
    drag = null,
    frame = 0,
    lastView = '',
    lastMode = '',
    picks = [],
    dead = false;
  const queue = () => {
    if (!dead && !frame)
      frame = requestAnimationFrame(() => {
        frame = 0;
        draw();
      });
  };
  function setView(view) {
    lastView = view;
    [yaw, elev] = viewAngles(
      view,
      state?.mode === 'underside' || state?.mode === 'under',
    );
    zoom = 1;
    queue();
  }
  function update(s) {
    const changed = s.view !== lastView,
      modeChanged = s.mode !== lastMode;
    state = s;
    model = layout(s);
    if (changed || modeChanged) {
      setView(s.view || 'iso');
      if ((s.mode === 'under' || s.mode === 'underside') && s.view !== 'front')
        elev = -Math.abs(elev);
      lastMode = s.mode;
    }
    queue();
  }
  function draw() {
    if (!state || !model || dead) return;
    const { halves, cap } = model,
      L = state.layers || {},
      explode = state.mode === 'exploded' ? 1 : 0,
      under = elev < 0;
    const ex = {
      back: E.back * explode,
      pcb: 0,
      sw: E.switches * explode,
      key: E.keycaps * explode,
      parts: E.electronics * explode,
      underSensor: E.underSensor * explode,
    };
    const cy = Math.cos(yaw),
      sy = Math.sin(yaw),
      ce = Math.cos(elev),
      se = Math.sin(elev);
    const project3 = projector(yaw, elev);
    const project = ([x, y], z = 0) => project3([x, y, z]);
    const coords = (ps) => ps.map((p) => p.map(round).join(',')).join(' ');
    let fragments = [],
      extraDefs = '',
      bounds = assemblyEnvelope(model, state, SPECS).map(project3),
      shadows = '',
      offset = 0;
    picks = [];
    const world = (p) => [p[0] + offset, p[1]];
    const plane = (p, z) => project(world(p), z);
    const polygon = (points, fill, stroke = 'none', width = 0.16) =>
      '<polygon points="' +
      coords(points) +
      '" fill="' +
      fill +
      '" stroke="' +
      stroke +
      '" stroke-width="' +
      width +
      '" stroke-linejoin="round"/>';
    const contour = (pts) =>
      'M' + pts.map((p) => p.map(round).join(',')).join('L') + 'Z';
    const solid = (
      lower,
      upper,
      z0,
      z1,
      palette,
      stroke = palette[2],
      aperture = null,
    ) => {
      const a = lower.map((p) => plane(p, z0)),
        b = upper.map((p) => plane(p, z1)),
        faces = [];
      for (let i = 0; i < lower.length; i++) {
        const j = (i + 1) % lower.length,
          dx = lower[j][0] - lower[i][0],
          dy = lower[j][1] - lower[i][1];
        // Convex component sides are single-sided; omit reversed or edge-on faces.
        if (
          (a[j][0] - a[i][0]) * (b[j][1] - a[i][1]) -
            (a[j][1] - a[i][1]) * (b[j][0] - a[i][0]) <=
          0.0002
        )
          continue;
        const y =
          (lower[i][0] + lower[j][0]) * sy + (lower[i][1] + lower[j][1]) * cy;
        faces.push([
          y,
          polygon(
            [a[i], a[j], b[j], b[i]],
            dy * cy - dx * sy > 0.1 ? palette[1] : palette[2],
          ),
        ]);
      }
      let face = polygon(
        under ? a : b,
        under ? palette[1] : palette[0],
        stroke,
      );
      if (aperture) {
        const lo = aperture.map((p) => plane(p, z0)),
          hi = aperture.map((p) => plane(p, z1));
        const walls = lo
          .map((pt, i) => {
            const j = (i + 1) % lo.length;
            return polygon([pt, lo[j], hi[j], hi[i]], palette[i % 2 ? 1 : 2]);
          })
          .join('');
        face =
          walls +
          '<path fill-rule="evenodd" d="' +
          contour(under ? a : b) +
          contour(under ? lo : hi) +
          '" fill="' +
          (under ? palette[1] : palette[0]) +
          '" stroke="' +
          stroke +
          '" stroke-width=".16"/>';
      }
      return (
        faces
          .sort((a, b) => a[0] - b[0])
          .map((f) => f[1])
          .join('') + face
      );
    };
    const prism = (p, w, h, z, t, c, r = 0.6) => {
      let q = box(p, w, h, r);
      return solid(q, q, z, z + t, c);
    };
    const disk = (p, r, z, t, c) => {
      let q = circ(p, r);
      return solid(q, q, z, z + t, c);
    };
    const path = (points, z, color, w = 0.24) =>
      '<polyline points="' +
      coords(points.map((p) => plane(p, z))) +
      '" fill="none" stroke="' +
      color +
      '" stroke-width="' +
      w +
      '" stroke-linecap="round" stroke-linejoin="round"/>';
    const center = (p, x, y) => {
      let a = pos(p, x, y);
      return { x: a[0], y: a[1], a: p.a };
    };
    const wireCage = (ps, lo, hi, ink) => {
      let lines =
        path([...ps, ps[0]], lo, ink, 0.16) +
        path([...ps, ps[0]], hi, ink, 0.13);
      for (const p of ps)
        lines +=
          '<polyline points="' +
          coords([plane(p, lo), plane(p, hi)]) +
          '" fill="none" stroke="' +
          ink +
          '" stroke-width=".14"/>';
      return lines;
    };
    const text = (p, z, str, size, ink, undersideInk = false) => {
      let o = plane([p.x, p.y], z),
        u = plane(pos(p, 1, 0), z),
        v = plane(pos(p, 0, undersideInk ? -1 : 1), z);
      let matrix = [u[0] - o[0], u[1] - o[1], v[0] - o[0], v[1] - o[1], ...o];
      return (
        '<text transform="matrix(' +
        matrix.map((n) => n.toFixed(4)).join(' ') +
        ')" text-anchor="middle" dominant-baseline="central" font-family="Arial, sans-serif" font-size="' +
        size +
        '" font-weight="550" pointer-events="none" fill="' +
        ink +
        '">' +
        esc(str) +
        '</text>'
      );
    };
    const emit = (rank, p, info, body) => {
      let id = picks.push(info) - 1,
        depth = (p.x + offset) * sy + p.y * cy;
      fragments.push([
        rank * (under ? -1 : 1),
        depth,
        '<g data-part="' +
          id +
          '" aria-label="' +
          esc(info.hand + ' ' + info.label) +
          '"><title>' +
          esc(info.hand + ' · ' + info.label) +
          '</title>' +
          body +
          '</g>',
      ]);
    };
    for (const h of halves) {
      offset = h.origin.x;
      const part = (type, label) => ({ type, hand: h.hand, label }),
        zero = { x: 0, y: 0 };
      const backZ = (model.backBottom ?? -SPECS.pcbT - 3.2) + ex.back;
      const aperture =
        h.pointer?.under && h.pointer.opening > 0
          ? footprint(
              { ...h.pointer, a: h.pointer.apertureA ?? h.pointer.a },
              h.pointer.opening,
              h.pointer.opening,
            )
          : null;
      if (!under && Object.values(L).some(Boolean)) {
        let ps = h.outline.map((p) => {
          let [x, y] = plane(p, backZ);
          return [x + 1.2, y + 2];
        });
        shadows += polygon(ps, '#604e39');
      }
      if (L.back !== false) {
        let back = solid(h.outline, h.outline, backZ, backZ + 1, colors.back);
        emit(0, zero, part('back', 'Backplate'), back);
      }
      if (L.pcb !== false) {
        let pcb = solid(
          h.outline,
          h.outline,
          -SPECS.pcbT,
          0,
          colors.pcb,
          colors.pcb[2],
          aperture,
        );
        const z = under ? -SPECS.pcbT - 0.04 : 0.04;
        if (aperture) {
          const inkClip = uid + 'ink' + h.hand,
            faceZ = under ? -SPECS.pcbT : 0;
          extraDefs +=
            '<clipPath id="' +
            inkClip +
            '"><path clip-rule="evenodd" d="' +
            contour(h.outline.map((p) => plane(p, faceZ))) +
            contour(aperture.map((p) => plane(p, faceZ))) +
            '"/></clipPath>';
          pcb += '<g clip-path="url(#' + inkClip + ')">';
        }
        for (const k of h.keys) {
          let p = pos(k, 0, 0),
            q = pos(k, 2.7, 4.5),
            r = pos(k, 7.4, 4.5);
          pcb += path([p, q, r], z, '#658366', 0.24);
          for (const dx of [-5, 5])
            pcb += polygon(
              circ(center(k, dx, 3), 0.72, 8).map((pt) => plane(pt, z)),
              '#ae975c',
            );
        }
        if (aperture) {
          const p = h.pointer,
            mark = footprint(
              { ...p, a: p.apertureA ?? p.a },
              p.opening + 0.9,
              p.opening + 0.9,
            );
          pcb += path([...mark, mark[0]], z, '#cfb889', 0.24) + '</g>';
        }
        emit(1, zero, part('pcb', 'PCB'), pcb);
      }
      if (L.switches !== false)
        for (const body of h.underbody || []) {
          const ps = body.polygon;
          if (!ps?.length || !(body.top > body.bottom)) continue;
          const cage = wireCage(
            ps,
            body.bottom + ex.sw,
            body.top + ex.sw,
            '#a38351',
          );
          emit(
            explode ? 2.8 : 0.73,
            { x: ps[0][0], y: ps[0][1] },
            part('switch', body.label + ' · underside keep-out envelope'),
            cage,
          );
        }
      for (const k of h.keys) {
        if (L.switches !== false) {
          const z = ex.sw,
            w = cap.swW,
            housingDepth = cap.swH,
            ulp = state.switchType === 'ulp';
          // Use the package outline from the active profile, not a common switch plate or solder-land envelope.
          let body;
          if (ulp) {
            body = prism(k, w, housingDepth, z, 0.53, colors.chip, 0.85);
            body += prism(
              k,
              w - 0.64,
              housingDepth - 0.66,
              z + 0.5,
              0.55,
              colors.metal,
              0.7,
            );
            body += prism(
              k,
              7.5,
              5.2,
              z + (state.pressed ? 0.92 : 2.02),
              state.pressed ? 0.2 : 0.48,
              colors.housing,
              0.65,
            );
          } else {
            body = prism(k, w, housingDepth, z, 2.1, colors.chip, 1.0);
            body += prism(
              k,
              w - 1.55,
              housingDepth - 1.55,
              z + 2.05,
              2.95,
              colors.housing,
              0.8,
            );
            body += prism(
              k,
              6.85,
              4.55,
              z + 4.78,
              8 - (state.pressed ? cap.travel : 0) - 4.78,
              colors.metal,
              0.5,
            );
          }
          emit(3, k, part('switch', k.label), body);
        }
        if (L.keycaps !== false) {
          const z = cap.top + ex.key - (state.pressed ? cap.travel : 0),
            dark = k.thumb || k.label.length > 1,
            p = dark ? colors.dark : colors.cap,
            thick = state.switchType === 'ulp' ? 1.3 : 4;
          let base = box(k, cap.w, cap.h, 1.1),
            top = box(k, cap.w - 1.7, cap.h - 1.6, 1.8),
            body = solid(base, top, z - thick, z, p);
          if (!under)
            body += text(
              k,
              z + 0.02,
              k.label,
              k.label.length > 2 ? 2.45 : 3.35,
              dark ? '#f0ede2' : '#454a40',
            );
          emit(4, k, part('keycap', k.label), body);
        }
      }
      if (L.electronics !== false) {
        const z = ex.parts,
          c = h.controller,
          b = h.battery;
        let body = prism(
          c,
          SPECS.controller.w,
          SPECS.controller.h,
          z,
          1,
          colors.pcb,
          1.1,
        );
        for (const side of [-1, 1])
          for (let i = 0; i < 7; i++)
            body += prism(
              center(c, side * 8, (i - 3) * 2.5),
              1.35,
              1.4,
              z + 1,
              0.1,
              colors.gold,
              0.24,
            );
        body +=
          prism(center(c, 0, 2.4), 8, 8, z + 1, 1, colors.chip, 0.45) +
          prism(center(c, 0, -8), 8.8, 6.8, z + 1, 2.5, colors.metal, 0.9);
        if (!under)
          body += text(center(c, 0, 2.4), z + 2.05, 'XIAO', 1.75, '#c3c9b9');
        emit(2, c, part('controller', 'XIAO controller'), body);
        body = prism(
          b,
          SPECS.battery.w,
          SPECS.battery.h,
          z,
          state.batteryT,
          colors.silver,
          1.25,
        );
        body += prism(
          center(b, 0, -13.6),
          SPECS.battery.w,
          4.1,
          z + state.batteryT,
          0.12,
          colors.gold,
          0.4,
        );
        for (let n = 0; n < 3; n++)
          body += path(
            [pos(b, -3.6, 8 + n * 0.65), pos(b, 2.2, 8 + n * 0.65)],
            z + state.batteryT + 0.03,
            '#999b8e',
            0.16,
          );
        emit(2, b, part('battery', 'LiPo pouch'), body);
        for (const m of h.mouse) {
          body =
            prism(m, SPECS.mouse.w, SPECS.mouse.h, z, 1.8, colors.metal, 0.45) +
            prism(m, 4.3, 2.8, z + 1.8, SPECS.mouse.t - 1.8, colors.chip, 0.8);
          emit(2, m, part('mouse', m.label), body);
        }
        if (h.driver) {
          let d = h.driver;
          body = prism(
            d,
            d.w,
            d.h,
            z,
            d.t,
            ['#929487', '#797d72', '#696c64'],
            0.8,
          );
          if (!under)
            body +=
              text(center(d, 0, -1.25), z + d.t, 'DRIVER', 2.15, '#f6f3e8') +
              text(center(d, 0, 1.6), z + d.t, 'KEEP-OUT', 1.25, '#eeece0');
          emit(2, d, part('driver', 'Pointing module driver reserve'), body);
        }
        if (h.pointer) {
          let p = h.pointer,
            ps = SPECS.pointer,
            sensor = center(p, 0, ps.axisToBoardCenter),
            top = p.capTop + ex.parts,
            sensorOffset = p.under ? ex.underSensor : ex.parts,
            boardBottom = (p.boardBottom ?? 0) + sensorOffset,
            boardTop = (p.boardTop ?? ps.t) + sensorOffset;
          body = prism(
            sensor,
            ps.w,
            ps.h,
            boardBottom,
            boardTop - boardBottom,
            colors.pcb,
            0.48,
          );
          if (under && p.under)
            body += text(sensor, boardBottom, 'SENSOR', 1.6, '#ccd9c6', true);
          if (p.under)
            emit(
              under ? 0.43 : 0.46,
              p,
              part('pointer', 'Sensor face / rear clearance allowance'),
              wireCage(
                footprint(sensor, ps.w, ps.h),
                boardBottom - (ps.rearReserve ?? 0),
                boardTop + (ps.frontReserve ?? 0),
                '#839e91',
              ),
            );
          emit(
            p.under ? 0.45 : 2,
            p,
            part(
              'pointer',
              p.under
                ? 'TrackPoint underside sensor card'
                : 'TrackPoint sensor card',
            ),
            body,
          );
          // Split at both carrier faces. The portion inside the board is seen only through its aperture.
          const shaft = (label, from, to, draw, aboveRank) => {
            for (const [low, high, rank] of [
              [-Infinity, -SPECS.pcbT, 0.74],
              [-SPECS.pcbT, 0, under ? 1.02 : 0.98],
              [0, Infinity, aboveRank],
            ]) {
              const a = Math.max(low, from),
                b = Math.min(high, to);
              if (b - a > 0.0001)
                emit(rank, p, part('pointer', label), draw(a, b - a));
            }
          };
          shaft(
            'TrackPoint stock stem',
            boardTop,
            p.stemTop + sensorOffset,
            (lo, t) => prism(p, ps.stem, ps.stem, lo, t, colors.metal, 0.18),
            2.15,
          );
          shaft(
            'TrackPoint extension',
            p.stemTop + ex.parts,
            top - 1.75,
            (lo, t) => disk(p, 1.12, lo, t, colors.chip),
            4.75,
          );
          body = disk(p, ps.cap / 2, top - 1.75, 1.75, colors.orange);
          if (!under)
            for (let i = -1; i <= 1; i++)
              for (let j = -1; j <= 1; j++)
                body += polygon(
                  circ(center(p, i * 0.8, j * 0.8), 0.135, 6).map((pt) =>
                    plane(pt, top + 0.03),
                  ),
                  '#a84626',
                );
          emit(5, p, part('pointer', 'Pointing stick'), body);
        }
      }
    }
    const aspect = (host.clientWidth || 800) / (host.clientHeight || 430),
      f = fitFrame(bounds2(bounds), aspect),
      h = f.h;
    const vh = h / zoom,
      vw = vh * aspect;
    svg.setAttribute(
      'viewBox',
      [f.x + (f.w - vw) / 2, f.y + (f.h - vh) / 2, vw, vh].map(round).join(' '),
    );
    svg.innerHTML =
      '<defs>' +
      extraDefs +
      '<filter id="' +
      uid +
      '" x="-20%" y="-40%" width="140%" height="180%"><feGaussianBlur stdDeviation="2.3"/></filter></defs><g pointer-events="none" opacity=".22" filter="url(#' +
      uid +
      ')">' +
      shadows +
      '</g>' +
      fragments
        .sort((a, b) => a[0] - b[0] || a[1] - b[1])
        .map((f) => f[2])
        .join('');
  }
  function start(e) {
    if (e.button !== 0 || drag) return;
    const g = e.target.closest?.('[data-part]');
    drag = {
      id: e.pointerId,
      x: e.clientX,
      y: e.clientY,
      yaw,
      elev,
      pick: g ? picks[Number(g.getAttribute('data-part'))] : null,
      moved: false,
    };
    svg.setPointerCapture?.(e.pointerId);
    svg.style.cursor = 'grabbing';
  }
  function move(e) {
    if (!drag || drag.id !== e.pointerId) return;
    const dx = e.clientX - drag.x,
      dy = e.clientY - drag.y;
    if (Math.hypot(dx, dy) > 3) drag.moved = true;
    if (drag.moved) {
      yaw = drag.yaw + dx * 0.008;
      elev = clamp(drag.elev + dy * 0.008, -Math.PI / 2, Math.PI / 2);
      queue();
    }
  }
  function end(e) {
    if (!drag || drag.id !== e.pointerId) return;
    const d = drag;
    drag = null;
    svg.style.cursor = 'grab';
    if (e.type === 'pointerup' && !d.moved && d.pick) onPick?.(d.pick);
  }
  function scale(f) {
    zoom = clamp(zoom * f, 0.55, 3.5);
    queue();
  }
  svg.addEventListener('pointerdown', start);
  svg.addEventListener('pointermove', move);
  svg.addEventListener('pointerup', end);
  svg.addEventListener('pointercancel', end);
  svg.addEventListener(
    'wheel',
    (e) => {
      e.preventDefault();
      scale(Math.exp(-clamp(e.deltaY, -150, 150) * 0.0017));
    },
    { passive: false },
  );
  svg.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft') yaw -= 0.12;
    else if (e.key === 'ArrowRight') yaw += 0.12;
    else if (e.key === 'ArrowUp')
      elev = clamp(elev + 0.12, -Math.PI / 2, Math.PI / 2);
    else if (e.key === 'ArrowDown')
      elev = clamp(elev - 0.12, -Math.PI / 2, Math.PI / 2);
    else if (e.key === '+' || e.key === '=') scale(1.12);
    else if (e.key === '-') scale(1 / 1.12);
    else return;
    e.preventDefault();
    queue();
  });
  const ro =
    typeof ResizeObserver !== 'undefined' ? new ResizeObserver(queue) : null;
  ro?.observe(host);
  return {
    update,
    setView,
    resize: queue,
    destroy() {
      dead = true;
      cancelAnimationFrame(frame);
      ro?.disconnect();
      svg.remove();
      picks = [];
      drag = null;
    },
  };
}
