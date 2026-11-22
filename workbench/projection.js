// CAD coordinates: +X across to the right, +Y towards the palm, +Z above
// the carrier. SVG has downward screen Y; Three uses +world Y for height.
export const radians = Math.PI / 180;
export const toThree = ([x, y, z]) => [x, z, y];
export function posePoint(p, x = 0, y = 0) {
  const a = (p.a || 0) * radians,
    c = Math.cos(a),
    s = Math.sin(a);
  return [p.x + x * c - y * s, p.y + x * s + y * c];
}
export const explodedOffsets = Object.freeze({
  keycaps: 35,
  switches: 16,
  pcb: 0,
  electronics: 12,
  underSensor: -7,
  back: -14,
});
export function viewAngles(view, under = false) {
  const a = {
    top: [0, 90],
    bottom: [0, -90],
    front: [0, 2],
    side: [90, 2],
    under: [17, -41],
    underside: [17, -41],
  }[view] || [17, 41];
  return [a[0] * radians, (under ? -Math.abs(a[1]) : a[1]) * radians];
}
export function projector(yaw, elevation) {
  const c = Math.cos(yaw),
    s = Math.sin(yaw),
    v = Math.sin(elevation),
    u = Math.cos(elevation);
  return ([x, y, z]) => [c * x - s * y, v * (s * x + c * y) - u * z];
}
export function bounds2(points) {
  let x0 = Infinity,
    x1 = -Infinity,
    y0 = Infinity,
    y1 = -Infinity;
  for (const [x, y] of points) {
    x0 = Math.min(x0, x);
    x1 = Math.max(x1, x);
    y0 = Math.min(y0, y);
    y1 = Math.max(y1, y);
  }
  return { x0, x1, y0, y1, w: x1 - x0, h: y1 - y0 };
}
// Return an isotropic world rectangle matching a viewport aspect ratio.
export function fitFrame(b, aspect, padX = 1.1, padY = 1.16) {
  const h = Math.max(1e-6, b.h * padY, (b.w * padX) / aspect),
    w = h * aspect;
  return { x: (b.x0 + b.x1 - w) / 2, y: (b.y0 + b.y1 - h) / 2, w, h };
}
export const solidVertices = (s) =>
  s.polygon.flatMap(([x, y]) => [
    [x, y, s.bottom],
    [x, y, s.top],
  ]);
// Same framing envelope for both baseline renderers. Deliberately include the
// complete design when layers are hidden, so layer toggles don't recenter it.
export function assemblyEnvelope(model, state, spec) {
  const e = state.mode === 'exploded' ? explodedOffsets : {},
    z = (name) => e[name] || 0;
  return model.halves.flatMap((h) => {
    const p = h.pointer,
      lo = Math.min(
        model.backBottom + z('back'),
        p?.under
          ? p.boardBottom - spec.pointer.rearReserve + z('underSensor')
          : 0,
      );
    const hi = Math.max(
      model.cap.top + z('keycaps'),
      Math.max(state.batteryT ?? 0, spec.controller.t) + z('electronics'),
      (p?.capTop ?? 0) + z('electronics'),
    );
    return h.outline.flatMap(([x, y]) => [
      [x + h.origin.x, y + h.origin.y, lo],
      [x + h.origin.x, y + h.origin.y, hi],
    ]);
  });
}
// Intersect polygon with a constant-X cut. Half-open crossing rule counts
// shared corners once and handles the disconnected spans of a concave board.
export function sliceX(poly, x) {
  const hits = [];
  for (let i = 0; i < poly.length; i++) {
    const a = poly[i],
      b = poly[(i + 1) % poly.length];
    if ((a[0] <= x && x < b[0]) || (b[0] <= x && x < a[0]))
      hits.push(a[1] + ((x - a[0]) * (b[1] - a[1])) / (b[0] - a[0]));
  }
  hits.sort((a, b) => a - b);
  return hits
    .filter((_, i) => i % 2 === 0)
    .map((lo, i) => [lo, hits[i * 2 + 1]])
    .filter(([lo, hi]) => hi > lo);
}
