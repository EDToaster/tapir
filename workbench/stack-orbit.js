import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import {
  toThree,
  viewAngles,
  bounds2,
  fitFrame,
  solidVertices,
} from './projection.js';

// Interactive inspection of the exact prisms used by stackModel and build123d.
// Construct in the extrusion plane, then rotate into the baseline Three
// frame: CAD (across, palm, height) maps to world (across, height, palm).
export function createStackOrbit(div) {
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setClearColor(0xedf0e8, 1);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  div.replaceChildren(renderer.domElement);
  const scene = new THREE.Scene(),
    camera = new THREE.OrthographicCamera(-38, 38, 28, -28, 0.1, 1000);
  camera.up.set(0, 1, 0);
  const ctl = new OrbitControls(camera, renderer.domElement);
  ctl.minZoom = 0.25;
  ctl.maxZoom = 8;
  ctl.enableDamping = false;
  scene.add(new THREE.HemisphereLight(0xfffcf0, 0x8f998b, 2.15));
  const light = new THREE.DirectionalLight(0xfff5d9, 2.15);
  light.position.set(-80, 140, 100);
  scene.add(light);
  const fill = new THREE.DirectionalLight(0xd7e8ee, 1.15);
  fill.position.set(90, 80, -55);
  scene.add(fill);
  let group = new THREE.Group(),
    model,
    frame = 0,
    showWhole = false;
  scene.add(group);
  const tint = {
    carrier: '#325249',
    back: '#303831',
    'controller-board': '#2d645a',
    'usb-shell': '#b7c5be',
    bridge: '#918060',
    support: '#cecfbe',
    sensor: '#486662',
    post: '#c1c5ba',
    'stick-cap': '#d85530',
    battery: '#b0b2a2',
    driver: '#52635d',
    key: '#e9e6d8',
    switch: '#879385',
    plug: '#6386a2',
    'rf-screen': '#dc9b45',
  };
  function render() {
    if (!frame)
      frame = requestAnimationFrame(() => {
        frame = 0;
        if (!div.clientWidth || !div.clientHeight) return;
        renderer.render(scene, camera);
      });
  }
  const ro = new ResizeObserver(() => {
    let w = div.clientWidth,
      h = div.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    if (model) reframe(false);
    render();
  });
  ro.observe(div);
  ctl.addEventListener('change', render);
  function reframe(reset) {
    if (!model || !div.clientHeight || !div.clientWidth) return;
    const [yaw, el] = viewAngles('iso'),
      dir = reset
        ? new THREE.Vector3(
            Math.sin(yaw) * Math.cos(el),
            Math.sin(el),
            Math.cos(yaw) * Math.cos(el),
          )
        : camera.position.clone().sub(ctl.target).normalize();
    const r = camera.up.clone().cross(dir).normalize(),
      u = dir.clone().cross(r).normalize();
    const solids = showWhole
      ? model.solids.filter((s) => Object.hasOwn(tint, s.role))
      : [
          model.refs.deck,
          ...model.refs.feet,
          model.refs.usb,
          model.refs.sensorCard,
          model.refs.cap,
          model.refs.post,
          model.refs.plug,
          model.refs.rf,
          model.refs.boardSolid,
          model.refs.movingCaps.find(
            (s) => s.label === model.nearestThumb.label,
          ),
        ].filter(Boolean);
    const xyz = solids
      .flatMap(solidVertices)
      .map((p) => new THREE.Vector3(...toThree(p)));
    const b = bounds2(xyz.map((p) => [p.dot(r), p.dot(u)])),
      depth = xyz.map((p) => p.dot(dir));
    const t = r
      .clone()
      .multiplyScalar((b.x0 + b.x1) / 2)
      .addScaledVector(u, (b.y0 + b.y1) / 2)
      .addScaledVector(dir, (Math.min(...depth) + Math.max(...depth)) / 2);
    const f = fitFrame(b, div.clientWidth / div.clientHeight, 1.15, 1.18);
    camera.left = -f.w / 2;
    camera.right = f.w / 2;
    camera.top = f.h / 2;
    camera.bottom = -f.h / 2;
    if (reset) camera.zoom = 1;
    camera.position.copy(t).addScaledVector(dir, 300);
    ctl.target.copy(t);
    camera.updateProjectionMatrix();
    ctl.update();
    render();
  }
  function center(whole = false) {
    showWhole = whole;
    reframe(true);
  }
  function update(next) {
    const first = !model;
    model = next;
    for (const item of group.children) {
      item.geometry.dispose();
      item.material.dispose();
    }
    group.clear();
    for (const s of model.solids) {
      if (!Object.hasOwn(tint, s.role)) continue;
      const shape = new THREE.Shape();
      s.polygon.forEach(([x, y], i) => {
        if (!i) shape.moveTo(x, -y);
        else shape.lineTo(x, -y);
      });
      shape.closePath();
      const geom = new THREE.ExtrudeGeometry(shape, {
        depth: s.top - s.bottom,
        bevelEnabled: false,
        curveSegments: 8,
      });
      geom.translate(0, 0, s.bottom);
      geom.rotateX(-Math.PI / 2);
      const alpha =
        s.role === 'plug'
          ? 0.18
          : s.role === 'rf-screen'
            ? 0.24
            : s.role === 'switch'
              ? 0.72
              : 1;
      const material = new THREE.MeshStandardMaterial({
        color: tint[s.role],
        roughness: 0.82,
        metalness: s.role === 'usb-shell' ? 0.46 : 0.05,
        transparent: alpha < 1,
        opacity: alpha,
        depthWrite: alpha === 1,
      });
      const mesh = new THREE.Mesh(geom, material);
      group.add(mesh);
      const edge = new THREE.LineSegments(
        new THREE.EdgesGeometry(geom, 24),
        new THREE.LineBasicMaterial({
          color: alpha < 0.5 ? tint[s.role] : '#334138',
          transparent: true,
          opacity: alpha < 0.5 ? 0.55 : 0.43,
        }),
      );
      group.add(edge);
    }
    if (first) center();
    else reframe(false);
    render();
  }
  return { update, center };
}
