import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { STLLoader } from 'three/addons/loaders/STLLoader.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import {pose} from './product-motion.js';

const colors={keys:0xe9e6d8,thumb:0x414b43,switches:0x9daca0,pcb:0x375f4a,electronics:0x40665e,driver:0x6c526a,battery:0xb7b5a5,usb:0xb2bcb4,post:0xb7bcac,stick:0xc75536,feet:0xbaad91,case:0x4e5b51,cover:0x5f6b5e,copper:0xc39964,reserves:0xa1804b,leads:0xa43d2b,analog:0x466da1};
export const GROUPS={keys:['Keycaps','#dedaca'],switches:['Switches','#9daca0'],pcb:['PCB & copper','#375f4a'],electronics:['Installed components','#497267'],case:['Enclosure & bridge','#69766b'],wiring:['Proposed cable paths','#466da1'],reserves:['Clearance volumes','#bd9453']};
export const normalLayers={keys:true,switches:true,pcb:true,electronics:true,case:true,wiring:false,reserves:false};
const xy=(poly)=>poly.map(([x,y])=>[x,-y]);
const ring=(x,y,r,n=20)=>Array.from({length:n},(_,i)=>[x+r*Math.cos(i*2*Math.PI/n),y+r*Math.sin(i*2*Math.PI/n)]);
const boxPoints=(b)=>[...Array(8)].map((_,n)=>new THREE.Vector3(n&1?b.max.x:b.min.x,n&2?b.max.y:b.min.y,n&4?b.max.z:b.min.z));
function shapeOf(outline,holes=[]){
  const s=new THREE.Shape();xy(outline).forEach(([x,y],i)=>i?s.lineTo(x,y):s.moveTo(x,y));s.closePath();
  for (const h of holes){const path=new THREE.Path();const d=h.diameter??h.drill;if(!(d>0))continue;path.absarc(h.x,-h.y,d/2,0,2*Math.PI,true);s.holes.push(path);}return s;
}
function kind(s){
  const r=(s.role||'').toLowerCase(), id=(s.id||'').toLowerCase();
  if(/original|prior|former/.test(r+' '+id)||/^(back|carrier|key|switch|key-sweep|keycap|key-cap|choc|switch-body)$/.test(r))return null;
  if(/^(key|switch|sweep|cap|hole)-\d/.test(id))return null;
  if(s.kind==='clearance'||/sweep|clearance|keepout|rf-screen|reserve|approach|tool|usb-plug|travel|actuation|court|jst-mate|manufacturer-max|driver-electronics/.test(r+' '+id)||['plug','xiao'].includes(id))return ['reserves','reserves'];
  if(r==='switch-tail')return ['switches','switches'];
  if(r==='case-boss')return ['reserves','reserves'];
  if(r==='screw-head')return ['electronics','usb'];
  if(r==='button-paddle')return ['keys','thumb'];
  if(/foot|bridge/.test(r+' '+id))return ['case','feet'];
  return ['electronics',/usb/.test(r)?'usb':/driver/.test(r)?'driver':/battery|pouch/.test(r)?'battery':/stick-cap|nub|dome/.test(r+' '+id)?'stick':/post|shaft/.test(r)?'post':'electronics'];
}
export async function createProductScene(host, documentData, notify, assetsBase='./prototype/') {
  const geometry=documentData.geometry, native=documentData.native||{}, sourceMeshes=documentData.meshes||[];
  const renderer=new THREE.WebGLRenderer({antialias:true,alpha:false});
  renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,2));renderer.setClearColor(0xe7ece3);
  host.replaceChildren(renderer.domElement);
  const scene=new THREE.Scene(), camera=new THREE.OrthographicCamera(-1,1,1,-1,.1,2500);
  camera.up.set(0,0,1);const orbit=new OrbitControls(camera,renderer.domElement);orbit.minZoom=.22;orbit.maxZoom=7;orbit.enableDamping=false;
  const hemi=new THREE.HemisphereLight(0xfffff4,0xb2c2ae,2.25);scene.add(hemi);
  for(const [pos,inten] of [[[0,-100,180],2.3],[[-40,70,100],.8]]){const l=new THREE.DirectionalLight(0xfff5df,inten);l.position.set(...pos);scene.add(l);}
  const groups={},parts=[],layers={...normalLayers};let hand='both',explode=0,view='iso',raf=0,loadedCAD=0,motionMode='free',motionPos=1;
  const proved=Object.fromEntries((documentData.cadEvidence?.halves||[]).map(s=>[s.hand,s]));
  const loader=new STLLoader(),models=new Map();
  await Promise.allSettled(Object.entries(documentData.componentMeshes||{}).map(async([id,src])=>{
    const buf=await loader.loadAsync(assetsBase+src);buf.computeVertexNormals();models.set(id,buf);
  }));
  const midpointGap=24, centerL=Math.max(...geometry.halves.left.outline.map(p=>p[0])),centerR=Math.min(...geometry.halves.right.outline.map(p=>p[0]));
  const stage=(grp,k)=>({case:-15,pcb:0,electronics:16,keys:43,switches:24,reserves:0}[grp]||0)+(k==='cover'?27:0);
  const matcache=new Map();
  function material(k,alpha=1){
    const code=k+':'+alpha;if(matcache.has(code))return matcache.get(code);
    const m=new THREE.MeshStandardMaterial({color:colors[k]||colors.electronics,metalness:['usb','copper'].includes(k)?.38:.04,roughness:.78,transparent:alpha<1,opacity:alpha,depthWrite:alpha===1,side:THREE.DoubleSide});
    matcache.set(code,m);return m;
  }
  function register(obj,li,layer,k,delta=0){obj.userData={hand:li,layer,role:layer==='keys'?'cap':layer==='reserves'?'reserve':'board',bx:obj.position.x,by:obj.position.y,base:obj.position.z,offset:stage(layer,k)+delta};groups[li].add(obj);parts.push(obj);return obj;}
  function solid(li,poly,b,t,layer,k,holes=[],alpha=1){
    if(!Array.isArray(poly)||poly.length<3||!Number.isFinite(b)||!Number.isFinite(t)||t<=b)return;
    const geo=new THREE.ExtrudeGeometry(shapeOf(poly,holes),{depth:t-b,bevelEnabled:false,curveSegments:8});geo.translate(0,0,b);
    const obj=new THREE.Mesh(geo,material(k,alpha));register(obj,li,layer,k);return obj;
  }
  function label(li,key,label,z){
    const canvas=document.createElement('canvas');canvas.width=160;canvas.height=80;const c=canvas.getContext('2d');
    c.font='600 38px sans-serif';c.textAlign='center';c.textBaseline='middle';c.fillStyle=key.thumb?'#f4f2e2':'#48534a';c.fillText(label,80,40,145);
    const tex=new THREE.CanvasTexture(canvas);tex.colorSpace=THREE.SRGBColorSpace;
    const txt=new THREE.Mesh(new THREE.PlaneGeometry(11,5.5),new THREE.MeshBasicMaterial({map:tex,transparent:true,depthWrite:false,side:THREE.DoubleSide}));
    txt.position.set(key.x,-key.y,z+.015);txt.rotation.z=-(key.a||0)*Math.PI/180;register(txt,li,'keys','keys');
  }
  function wire(li,points,r,col){
    if(!Array.isArray(points)||points.length<2)return;
    const v=points.map(([x,y,z])=>new THREE.Vector3(x,-y,z)),geos=[];
    for(let i=1;i<v.length;i++){const a=v[i-1],b=v[i],d=b.clone().sub(a),len=d.length();if(!Number.isFinite(len)||len<1e-7)continue;
      const seg=new THREE.CylinderGeometry(r,r,len,7,1,false);seg.applyQuaternion(new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0,1,0),d.normalize()));
      const center=a.clone().lerp(b,.5);seg.translate(center.x,center.y,center.z);geos.push(seg);}
    if(!geos.length)return;const merged=mergeGeometries(geos);geos.forEach(o=>o.dispose());const obj=register(new THREE.Mesh(merged,material(col)),li,'wiring',col);
    obj.userData.role='loose';
  }
  function addTraces(li,data){
    if(!data)return;
    const lanes={front:[],back:[]};const h=geometry.halves[li];
    for(const t of data.tracks||[]){if(!lanes[t.side])continue;const z=t.side==='front'?h.pcb.top+.012:h.pcb.bottom-.012;lanes[t.side].push(t.x1,-t.y1,z,t.x2,-t.y2,z);}
    for(const pts of Object.values(lanes)){if(!pts.length)continue;const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(pts,3));register(new THREE.LineSegments(g,new THREE.LineBasicMaterial({color:0xadc18c,transparent:true,opacity:.6})),li,'pcb','copper');}
    // Pads are native copper polygons. Drills are cut from them, not painted on.
    const mark=parts.length;
    for(const p of data.pads||[]){if(!p.polygon?.length)continue;for(const side of p.sides||[]){const top=side==='front'?h.pcb.top+.032:h.pcb.bottom-.018;solid(li,p.polygon,top-.014,top,'pcb','copper',p.drill?[p.drill]:[]);}}
    for(const v of data.vias||[])for(const z of [h.pcb.top+.018,h.pcb.bottom-.018])solid(li,ring(v.x,v.y,v.diameter/2),z-.01,z,'pcb','copper',[{...v,diameter:v.drill}]);
    // All of these native copper pads move rigidly with one carrier. Their
    // vertices are already in the carrier frame: upload once, one draw call.
    const pads=parts.slice(mark);if(pads.length){
      const combined=mergeGeometries(pads.map(p=>p.geometry),false);
      if(combined){parts.splice(mark);for(const p of pads){groups[li].remove(p);p.geometry.dispose();}register(new THREE.Mesh(combined,material('copper')),li,'pcb','copper');}
    }
  }
  for(const li of ['left','right']){
    const h=geometry.halves[li],g=new THREE.Group();g.position.x=li==='left'?-midpointGap/2-centerL:midpointGap/2-centerR;scene.add(g);groups[li]=g;
    const allHoles=native[li]?.holes||h.holes.map(hole=>({...hole,diameter:hole.drill??hole.diameter}));
    solid(li,h.outline,h.pcb.bottom,h.pcb.top,'pcb','pcb',allHoles);addTraces(li,native[li]);
    wire(li,h.wiring?.sensorToDriver?.points,.55,'analog');
    const wired=proved[li]?.wire_plan;
    wire(li,wired?.full_three_dimensional_centerline?.centerlineXYZ_mm,.55,'leads');
    const hardware=proved[li];
    if(hardware?.case_screws_assembled_XY){
      const bolt=(x,y,outer)=>{
        const u=outer?2.5:0,len=outer?8:6,nutTop=outer?-3.72:-4.20,role=outer?'cover-bolt':'board-bolt';
        const shank=solid(li,ring(x,y,1),u-len,u,'electronics','usb');
        const head=solid(li,ring(x,y,1.75),u,u+1.30,'electronics','usb',[{x,y,diameter:1.30}]);
        for(const obj of [shank,head]){obj.userData.role=role;obj.userData.offset=outer?37:14;}
        const nut=solid(li,ring(x,y,4/Math.sqrt(3),6),nutTop-1.60,nutTop,'electronics','usb',[{x,y,diameter:2.04}]);
        nut.userData.role='nut';nut.userData.offset=-24;
      };
      for(const [x,y] of hardware.mounts_assembled_XY)bolt(x,y,false);
      for(const [x,y] of hardware.case_screws_assembled_XY)bolt(x,y,true);
    }
    const refs=new Set();
    for(const m of native[li]?.models||[]){
      const geometry=models.get(m.model);if(!geometry)continue;
      const cap=m.model.startsWith('MBK'),sw=m.model.includes('Kailh'),key=h.switches.find(s=>s.ref===m.ref);
      const layer=cap?'keys':sw?'switches':'electronics';
      const color=cap?(key?.thumb?'thumb':'keys'):sw?'switches':m.ref==='J1'?'keys':m.ref==='S1'?'usb':'electronics';
      const mesh=new THREE.Mesh(geometry,material(color));mesh.position.set(m.x,-m.y,0);mesh.rotation.z=m.a*Math.PI/180;
      register(mesh,li,layer,color);refs.add(m.ref+':'+layer);
    }
    for(const sw of h.switches){
      if(!refs.has(sw.ref+':switches'))solid(li,sw.bodyPolygon,...sw.bodyZ,'switches','switches');
      const z=sw.capAtRestZ[1];if(!refs.has(sw.ref+':keys'))solid(li,sw.capPolygon,...sw.capAtRestZ,'keys',sw.thumb?'thumb':'keys');label(li,sw,sw.label,z);
    }
    const coverCAD=sourceMeshes.some(p=>p.hand===li&&p.role==='cover');
    for(const s of h.solids){const tag=kind(s);if(!tag)continue;
      if(s.role==='screw-head'&&hardware?.case_screws_assembled_XY)continue;
      const ref=({'xiao-board':'U1','usb-shell':'U1','power-switch':'S1','power-lever':'S1'})[s.id]||s.id.split('-')[0];
      if((tag[0]==='electronics'&&refs.has(ref+':electronics'))||(s.role==='switch-tail'&&(refs.has(ref+':switches')||refs.has(ref+':electronics'))))continue;
      if(s.role==='button-paddle'&&coverCAD)continue;
      if(tag[0]==='case' && sourceMeshes.some(p=>p.hand===li&&/bridge/.test(p.role||'')))continue;
      const obj=solid(li,s.polygon,s.bottom,s.top,...tag,[],tag[0]==='reserves'?.17:1);
      if(obj&&/^(sensor|driver|post|stick-cap|battery|screw-head|support|bridge)$/.test(s.role))obj.userData.role=s.role==='stick-cap'?'cap':'loose';
    }
    for(const button of h.buttons)if(!coverCAD)label(li,{...button,thumb:true},button.label,button.paddle.top);
    if(proved[li]?.paths?.some(p=>p.id==='usb_straight_insertion')){
      // Qualtek 3021091-01M: original drawing for shoulder length, shell
      // projection and jacket. Envelope W/H per the CAD qualification.
      const m=h.usbMouth,[dx,dy]=m.direction;
      for(const [d0,d1,w,b,t,color] of [[0,36,12.35,0,6.50,'stick'],[-6.85,0,8.50,3.25-2.43/2,3.25+2.43/2,'usb'],[36,56,3.70,3.25-1.85,3.25+1.85,'case']]){
        const half=w/2,poly=[[d0,-half],[d1,-half],[d1,half],[d0,half]].map(([d,w])=>[m.x+dx*d-dy*w,m.y+dy*d+dx*w]);
        const gauge=solid(li,poly,b,t,'electronics',color);gauge.userData.role='plug-gauge';
      }
    }
  }
  function refresh(){for(const p of parts){const u=p.userData,s=pose(motionMode,u.role,motionPos,proved[u.hand]?.paths,geometry.halves[u.hand].usbMouth);
    p.visible=(hand==='both'||hand===u.hand)&&layers[u.layer]&&s.show;
    p.position.set(u.bx+s.x,u.by+s.y,u.base+s.z+(motionMode==='free'?explode*u.offset:0));
  }schedule();}
  function schedule(){if(!raf)raf=requestAnimationFrame(()=>{raf=0;if(host.clientWidth&&host.clientHeight)renderer.render(scene,camera);});}
  function fit(keepView=false){
    const w=host.clientWidth,h=host.clientHeight;if(!w||!h)return;
    const target=new THREE.Vector3(),b=new THREE.Box3();
    scene.updateMatrixWorld(true);const boxes=[];
    for(const p of parts){if(!p.visible||p.userData.layer==='reserves')continue;if(!p.geometry.boundingBox)p.geometry.computeBoundingBox();const a=p.geometry.boundingBox.clone().applyMatrix4(p.matrixWorld);b.union(a);boxes.push(a);}
    if(b.isEmpty())return;b.getCenter(target);
    let dir= new THREE.Vector3().subVectors(camera.position,orbit.target).normalize();
    if(!keepView||!dir.length())dir=new THREE.Vector3(...({iso:[-.24,-.88,.88],top:[0,0,1],front:[0,-1,.01]}[view])).normalize();
    camera.up.set(...(Math.abs(dir.z)>.999?[0,1,0]:[0,0,1]));camera.position.copy(target).addScaledVector(dir,630);camera.lookAt(target);camera.updateMatrixWorld(true);
    // Fit the union of the visible component bounds in camera space. Use both
    // axes and the active viewport ratio; anchoring to world XY crops tall views.
    const screen=new THREE.Box3();for(const box of boxes)for(const p of boxPoints(box))screen.expandByPoint(p.applyMatrix4(camera.matrixWorldInverse));
    const cx=(screen.min.x+screen.max.x)/2,cy=(screen.min.y+screen.max.y)/2;
    const right=new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld,0),up=new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld,1);
    target.addScaledVector(right,cx).addScaledVector(up,cy);camera.position.addScaledVector(right,cx).addScaledVector(up,cy);
    const size=Math.max((screen.max.y-screen.min.y)/2,(screen.max.x-screen.min.x)*h/(2*w),6)*1.10;
    camera.zoom=1;camera.left=-size*w/h;camera.right=size*w/h;camera.top=size;camera.bottom=-size;camera.updateProjectionMatrix();orbit.target.copy(target);orbit.update();
    renderer.setSize(w,h,false);schedule();
  }
  const loaded=await Promise.allSettled(sourceMeshes.map(async meta=>{
    const buf=await loader.loadAsync(assetsBase+meta.stl);buf.computeVertexNormals();
    const type=meta.role==='cover'?'cover':meta.role==='bridge'?'feet':'case';
    const obj=new THREE.Mesh(buf,material(type));register(obj,meta.hand,'case',type);obj.userData.role=meta.role;loadedCAD++;
  }));
  refresh();fit();new ResizeObserver(()=>fit(true)).observe(host);orbit.addEventListener('change',schedule);
  notify({loadedCAD,componentFiles:models.size,failedCAD:loaded.filter(t=>t.status==='rejected').length});
  return {setHand(v){hand=v;refresh();fit();},setCamera(v){view=v;fit();},setLayer(k,b){layers[k]=b;refresh();fit(true);},setExplode(p){explode=p;refresh();fit(true);},setMotion(mode,p){motionMode=mode;motionPos=p;refresh();fit(true);},fit:()=>fit(true)};
}
