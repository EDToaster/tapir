import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

// Interactive inspection of the exact prisms used by stackModel and build123d.
// Reflect layout Y into drawing Y so +Z points up and the palm is in front.
export function createStackOrbit(div) {
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setClearColor(0xedf0e8, 1);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  div.replaceChildren(renderer.domElement);
  const scene = new THREE.Scene(),
    camera = new THREE.OrthographicCamera(-38, 38, 28, -28, 0.1, 1000);
  camera.up.set(0, 0, 1);
  const ctl = new OrbitControls(camera, renderer.domElement);
  ctl.minZoom = 0.25;
  ctl.maxZoom = 8;
  ctl.enableDamping = false;
  scene.add(new THREE.HemisphereLight(0xfffcf0, 0x8f998b, 2.15));
  const light = new THREE.DirectionalLight(0xfff5d9, 2.15);
  light.position.set(-80, -100, 140);
  scene.add(light);
  const fill = new THREE.DirectionalLight(0xd7e8ee, 1.15);
  fill.position.set(90, 55, 80);
  scene.add(fill);
  let group = new THREE.Group(),
    model,
    frame = 0;
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
    camera.left = (-28 * w) / h;
    camera.right = (28 * w) / h;
    camera.top = 28;
    camera.bottom = -28;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h, false);
    render();
  });
  ro.observe(div);
  ctl.addEventListener('change', render);
  function center(whole = false) {
    if (!model) return;
    const box = new THREE.Box3().setFromPoints(
      model.outline.map(([x, y]) => new THREE.Vector3(x, -y, 0)),
    );
    const target = whole
      ? box.getCenter(new THREE.Vector3())
      : new THREE.Vector3(model.head.x, -model.head.y, 4);
    camera.zoom = whole ? 0.36 : 1.2;
    camera.position.copy(target).add(new THREE.Vector3(-46, -75, 56));
    camera.updateProjectionMatrix();
    ctl.target.copy(target);
    ctl.update();
    render();
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
    render();
  }
  return { update, center };
}
