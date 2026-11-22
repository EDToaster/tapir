// Node >=20; from the root: (cd workbench && npm ci); node product/design/generate-geometry.mjs
// --check compares the checked-in contract. No timestamp, network or randomness.
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
import {INITIAL,SPECS,layout,rect,rotate,prismGap,clearance} from '../../workbench/layout.js';
import {stackModel,STACK_DEFAULTS,STACK_SOURCES} from '../../workbench/stack.js';

const model=stackModel(), base=layout(INITIAL), zPCB=-SPECS.pcbT;
const scalar=n=>Number(n.toFixed(6));
const clean=o=>JSON.parse(JSON.stringify(o,(_k,v)=>typeof v==='number'?scalar(v):v));
const at=(q,u,v)=>{const [dx,dy]=rotate([u,v],q.a||0);return {x:q.x+dx,y:q.y+dy,a:q.a||0}};
const pose=(x,y,a=0)=>({x,y,a});
const center=p=>({x:p.reduce((s,q)=>s+q[0],0)/p.length,y:p.reduce((s,q)=>s+q[1],0)/p.length,a:0});
const bounds=p=>{const x=p.map(q=>q[0]),y=p.map(q=>q[1]),x0=Math.min(...x),x1=Math.max(...x),y0=Math.min(...y),y1=Math.max(...y);return{x0,x1,y0,y1,w:x1-x0,h:y1-y0}};
const disk=(x,y,r,n=32)=>Array.from({length:n},(_,i)=>[x+r*Math.cos(i*2*Math.PI/n),y+r*Math.sin(i*2*Math.PI/n)]);
const circleBounds=(q,r,n=32)=>disk(q.x,q.y,r/Math.cos(Math.PI/n),n); // circumscribed collision polygon
const solid=(id,role,label,kind,p,bottom,top,extra={})=>({id,role,label,kind,polygon:p,bottom,top,...extra});
const cub=(id,role,label,kind,q,w,h,bottom,top,extra={})=>solid(id,role,label,kind,rect(q,w,h),bottom,top,{...q,...extra});
function edgeDistance(q,poly){
  let inside=false,d=Infinity;
  for(let i=0,j=poly.length-1;i<poly.length;j=i++){
    const a=poly[j],b=poly[i],dx=b[0]-a[0],dy=b[1]-a[1],t=Math.max(0,Math.min(1,((q.x-a[0])*dx+(q.y-a[1])*dy)/(dx*dx+dy*dy)));
    d=Math.min(d,Math.hypot(q.x-a[0]-t*dx,q.y-a[1]-t*dy));
    if((a[1]>q.y)!==(b[1]>q.y)&&q.x<(b[0]-a[0])*(q.y-a[1])/(b[1]-a[1])+a[0])inside=!inside;
  }
  return inside?d:-d;
}
const minimum=(a,b,fn=prismGap)=>{
  let value=Infinity,pair=[]; for(const x of a)for(const y of b){const v=fn(x,y);if(v<value){value=v;pair=[x.id,y.id]}}return{value,pair};
};
const xyGap=(x,y)=>clearance(x.polygon,y.polygon);
const holesByHand={left:[[-83,-19.5],[10.5,-2.5],[14.5,62],[-79,31.5]],right:[[83,-19.5],[-10.5,-2.5],[-14.5,62],[79,31.5]]};
function half(h){
  const right=h.hand==='right', outline=right?model.outline:h.outline, components={},solids=[],holes=[],checks=[];
  const add=(s)=>{solids.push(s);return s};
  const part=(k,s)=>{components[k]=add(s);return s};
  const reserve=(id,label,q,w,ht,z0,z1)=>cub(id,id,label,'envelope',q,w,ht,z0,z1);
  function compare(id,a,b,explanation,fn=prismGap){const v=minimum(a,b,fn);checks.push({id,status:v.value>0?'pass':'clash',gap:v.value,pair:v.pair,explanation});return v.value}
  const switches=[],buttons=[],caps=[],bodies=[],tails=[],diodes=[],keyHoles=[];
  for(const k of h.keys){
    const col=5-k.c, row=k.row, ref='SW'+(row===3?16+col:1+6*row+col),id=ref;
    const body=add(cub(id+'-body','switch',k.label+' switch','envelope',k,15,15,0,8)),
          cap=add(cub(id+'-cap','keycap',k.label+' rest','material-envelope',k,17.5,16.5,6.6,10.6)),
          sweep=add(cub(id+'-stroke','key-sweep',k.label+' full cap stroke','clearance',k,17.5,16.5,3.6,10.6));
    caps.push(sweep);bodies.push(body);
    const pins=[];
    for(const [idLocal,u,v,drill,diameter,type,depth,rad] of [
      ['1',5,-3.8,1.27,2.032,'PTH',1.8,1.2],['2',0,-5.9,1.27,2.032,'PTH',1.8,1.2],
      ['stem',0,0,3.429,3.429,'NPTH',1.05,1.72],['locator-left',-5.5,0,1.7018,1.7018,'NPTH',1.05,.95],
      ['locator-right',5.5,0,1.7018,1.7018,'NPTH',1.05,.95],['asym-locator',-5.22,4.2,.9906,.9906,'NPTH',1.05,.55],
    ]){
      const q=at(k,u,v),p={id:idLocal,ref,...q,diameter,drill,type,local:[u,v],bottom:zPCB-depth,top:0};
      pins.push(p);holes.push({...p,id:ref+'-'+idLocal,owner:ref});keyHoles.push(p);
      tails.push(add(solid(ref+'-tail-'+idLocal,'switch-tail',k.label+' '+idLocal,'envelope',circleBounds(q,rad),p.bottom,zPCB,q)));
    }
    const dq=at(k,-3,-5.9), diode=add(cub('D'+ref.slice(2),'matrix-diode',ref+' B-side diode reserve','envelope',dq,2.8,1.6,-2.65,zPCB));
    diodes.push(diode);
    switches.push({id,ref,label:k.label,x:k.x,y:k.y,a:k.a,thumb:k.thumb,row,col,
      bodyPolygon:body.polygon,capPolygon:cap.polygon,bodyZ:[0,8],capAtRestZ:[6.6,10.6],capSweptZ:[3.6,10.6],travel:3,pins,diode});
  }
  for(const [i,k] of h.mouse.entries()){
    const ref='SW'+(22+i),body=add(cub(ref+'-body','mouse-switch',k.label+' PTS810','envelope',k,4.2,3.2,0,2.5)),
      paddle=add(cub(ref+'-paddle','button-paddle',k.label+' test paddle','envelope',k,8,5,2.35,3.65));
    const pads=[-1,1].flatMap(u=>[-1,1].map(v=>({...at(k,u*2.075,v*1.075),pin:v<0?'1':'2',size:[1.05,.65]})));
    const dq=at(k,0,-3.8),diode=add(cub('D'+ref.slice(2),'matrix-diode',ref+' B-side diode reserve','envelope',dq,2.8,1.6,-2.65,zPCB));
    diodes.push(diode);buttons.push({id:ref,ref,label:k.label,x:k.x,y:k.y,a:k.a,row:3,col:i,polygon:body.polygon,paddle,pads,diode});bodies.push(body,paddle);
  }
  const xq=right?model.controller:h.controller, ref=model.refs, xiao=part('xiao',cub('xiao','controller','Seeed XIAO nRF52840 Plus','envelope',xq,17.78,20.955,0,5,{ref:'U1'}));
  part('xiaoBoard',cub('xiao-board','controller-board','XIAO substrate','material-envelope',xq,17.78,20.955,.15,1.75));
  part('usbShell',cub('usb-shell','usb-shell','USB1 F.Fab plan; Z allowance','material-envelope',at(xq,0,(-11.99-4.64)/2),9,7.35,1.75,5));
  const mouth=at(xq,0,-11.99),rf=part('antennaScreen',reserve('rf-screen','6 × 6 mm provisional RF neighborhood',at(xq,-1.8,9.41),6,6,-2,18));
  const plug=part('usbPlug',reserve('usb-plug','Assumed straight USB plug approach',at(mouth,0,-9),12,18,.25,6.25));
  const bq=h.battery, battery=part('battery',cub('battery','battery','Adafruit 1570 nominal pouch','material-envelope',bq,11.5,31,0,3.8));
  const maxPack=part('batteryMaximum',reserve('battery-manufacturer-max','PKCELL 1570 drawing p. 5 as-made maximum, before service growth',bq,12.3,32,0,4.3));
  const batteryReserve=part('batteryReserve',reserve('battery-reserve','Pouch isolation + growth allowance',bq,13.5,33,0,4.8));
  const j=right?pose(-20,-18):pose(-39.5,38.8,90);
  const jBody=part('batteryConnector',cub('J1','battery-connector','JST S2B-PH-SM4-TB(LF)(SN)','material-envelope',at(j,0,.6),7.9,7.6,0,6.4,{...j,ref:'J1',landOrigin:[j.x,j.y],
    pads:[['1',-1,-2.85,'CELL+',[1,3.5]],['2',1,-2.85,'GND',[1,3.5]],['MP',-3.35,2.9,null,[1.5,3.4]],['MP',3.35,2.9,null,[1.5,3.4]]].map(([pin,x,y,net,size])=>({pin,net,size,...at(j,x,y)}))}));
  const jCourt=part('batteryConnectorCourt',reserve('jst-court','JST footprint and solder courtyard',j,9.2,10.2,0,6.4));
  const jPlug=part('batteryPlug',reserve('jst-mate','JST housing / withdrawal proxy',at(j,0,10.4),8,12,0,6.4));
  const sq=right?pose(-22,73.75):pose(-6,61.85,4.7);
  const locators=[-1,1].map((s,i)=>({...at(sq,s*1.5,.33),id:'S1-L'+(i+1),owner:'S1',drill:.9,diameter:.9,type:'NPTH'}));
  holes.push(...locators);
  for(const l of locators)tails.push(add(solid(l.id+'-tail','switch-tail','Slide-switch locating feature '+l.id,'envelope',circleBounds(l,.5),zPCB-.4,zPCB,pose(l.x,l.y))));
  const sw=part('powerSwitch',cub('power-switch','power-switch','C&K PCM12SMTR','material-envelope',sq,6.7,2.6,0,2.1,{ref:'S1',landOrigin:[sq.x,sq.y],locators,
    pads:[[-2.25,-1.43,'1',.7,1.5],[.75,-1.43,'2',.7,1.5],[2.25,-1.43,'3',.7,1.5],...[-1,1].flatMap(s=>[-.78,1.43].map(y=>[s*3.65,y,'MP',1,.8]))].map(([u,v,pin,w,h])=>({...at(sq,u,v),pin,size:[w,h]}))}));
  const swCourt=part('powerSwitchCourt',reserve('power-switch-court','Slide switch land reserve',at(sq,0,-.1),8.6,4.4,0,2.1));
  const lever=part('powerLever',reserve('power-lever','Slide actuator / travel reserve',at(sq,0,2.16),3.6,1.72,.35,2.25));
  let stackObstacles=[];
  if(right){
    const save=(k,s,q=center(s.polygon))=>part(k,{...s,...q});
    save('driver',ref.driver,h.driver);save('sensor',ref.sensorCard,model.sensor);save('bridge',ref.deck);
    save('shaft',ref.post,model.head);save('rubberCap',ref.cap,model.head);
    components.feet=ref.feet.map(s=>add({...s,...center(s.polygon)}));
    components.sensorHoles=model.sensorHoles.map(([x,y],i)=>({id:'TP-M'+(i+1),x,y,a:0,diameter:1.8,drill:1.8,
      owner:'sensor PCB ONLY',carrierDrill:false,top:ref.sensorCard.top,bottom:ref.sensorCard.bottom}));
    components.sensorPadEdge={x:model.wire[0][0],y:model.wire[0][1],z:ref.sensorCard.bottom};
    components.originalShaftHoleRemoved=true;
    const ju=pose(50,49),jp=Array.from({length:5},(_,i)=>({id:String(i+1),...at(ju,(i-2)*1.8,0),net:['GND','DATA','CLK','RST','VOUT'][i],drill:.8,diameter:1.55,type:'PTH'}));
    part('driverHeader',cub('J2','driver-wire-pads','5-wire remote driver termination','envelope',ju,8.75,1.55,0,1.2,{ref:'J2',pads:jp}));
    holes.push(...jp.map(p=>({...p,id:'J2-'+p.id,owner:'J2'})));
    for(const p of jp)tails.push(add(solid('J2-'+p.id+'-solder','wire-tail','J2 direct-solder tail','envelope',circleBounds(p,.95),zPCB-1.2,zPCB,pose(p.x,p.y))));
    part('driverElectronics',reserve('driver-electronics','Switched-power electronics placement budget',pose(37,39),12,8,0,3));
    components.driverDiscrete=[
      ['U2',-.75,0,0,3,3.1,1.55],['C1',-4,0,-90,1.8,1,1.1],['C2',2.7,0,-90,1.8,1,1.1],
      ['R1',2.5,-2.9,0,1.8,1,.7],['R2',2.5,2.9,0,1.8,1,.7],['R3',-2.8,2.9,0,1.8,1,.7],
    ].map(([ref,x,y,a,w,h,ht])=>add(cub(ref,'driver-discrete',ref+' package allowance','envelope',pose(37+x,39+y,a),w,h,0,ht,{ref})));
    stackObstacles=[components.driver,components.sensor,components.bridge,components.shaft,components.rubberCap,...components.feet,components.driverHeader,components.driverElectronics];
  }
  const others=[xiao,batteryReserve,jCourt,jPlug,swCourt,rf,plug,...stackObstacles];
  const mountingHoles=holesByHand[h.hand].map(([x,y],i)=>{
    const id='H'+(i+1),q=pose(x,y),head=solid(id+'-head','screw-head',id+' M2 head','envelope',circleBounds(q,2),0,1.6,q),
      boss=solid(id+'-boss','case-boss',id+' underside boss design allowance','envelope',circleBounds(q,2.7),-3.8,zPCB,q),
      tool=solid(id+'-tool','screwdriver',id+' access with keycaps removed','clearance',circleBounds(q,2.2),0,15,q);
    add(head);add(boss);add(tool);
    const edge=edgeDistance(q,outline)-2.7,
      hv=minimum([head],[...caps,...bodies,...others]),bv=minimum([boss],[...tails,...diodes]),tv=minimum([tool],[...bodies,...others]),
      worst=Math.min(edge,hv.value,bv.value,tv.value);
    const mh={id,ref:id,x,y,diameter:2.2,drill:2.2,type:'NPTH',headDiameter:4,headHeight:1.6,bossDiameter:5.4,toolDiameter:4.4,
      clearance:{edge,bossToTailsAndDiodes:bv,headToPopulatedParts:hv,toolWithCapsOff:tv,worst},top:0,bottom:zPCB};
    holes.push({...q,id,owner:'carrier',diameter:2.2,drill:2.2,type:'NPTH'});checks.push({id:id+'-fit',status:worst>.25?'pass':'clash',gap:worst,pair:[id,'edge/head/boss/tool'],explanation:'Minimum of four independent screw installation checks; keycaps removed for tool only.'});return mh;
  });
  const occupied=[...caps,...bodies,xiao,rf,batteryReserve,swCourt,...stackObstacles];
  const pairwise=(id,parts,explanation)=>{let best={value:Infinity,pair:[]};for(let i=1;i<parts.length;i++){const s=minimum([parts[i]],parts.slice(0,i));if(s.value<best.value)best=s}
    checks.push({id,status:best.value>0?'pass':'clash',gap:best.value,pair:best.pair,explanation})};
  pairwise('all-key-sweeps',caps,'Every distinct pair of 21 full-stroke cap envelopes on this half.');
  compare('moldings-vs-diodes',diodes,tails,'Every backside diode reserve vs every switch locator, pin and solder envelope including its own switch; direct solder only.');
  compare('controller-vs-keys',[xiao,components.usbShell],[...caps,...bodies],'Populated module and overhanging shell vs full key sweep and switch bodies.');
  compare('as-made-cell-vs-hard-parts',[maxPack],[...caps,...bodies,xiao,jCourt,jPlug,swCourt,...stackObstacles],'PKCELL maximum as-made pack, separately from individual cell nominal and unqualified additional service allowance.');
  compare('jst-court', [jCourt],occupied,'Connector courtyard, all facing obstacles; nominal Z envelope.');
  compare('jst-approach',[jPlug],occupied,'12 mm plug housing / withdrawal corridor; wires, fingers and case not inherently validated.');
  compare('power-switch',[swCourt,lever],[...caps,...bodies,xiao,rf,batteryReserve,jCourt,...stackObstacles],'Switch body/land/lever reserves vs fitted front parts.');
  compare('battery',[batteryReserve],[...caps,...bodies,xiao,jCourt,...stackObstacles],'Battery +1 mm lateral and 1 mm height allowance; foam/age expansion must be measured.');
  compare('usb-approach',[plug],[...caps,...bodies,jCourt,batteryReserve,swCourt,...stackObstacles],'USB surrogate plug vs hardware; physical insertion through enclosure remains untested.');
  if(right){
    pairwise('driver-discrete-parts',components.driverDiscrete,'Placed native electronics centers with package/lead allowances, distinct parts only.');
    compare('driver-electronics-package',[components.driverElectronics],[...caps,...bodies,components.driver,components.driverHeader,...components.feet,components.bridge,xiao],'Power/level isolation block reserved vs surrounding components.');
    compare('driver-header',[components.driverHeader],[...caps,...bodies,components.driver,components.driverElectronics],'Remote driver wire solder pads and ends; no header body assumed.');
    compare('stack-motion',[components.bridge,components.sensor,components.shaft,components.rubberCap,...components.feet,xiao,components.usbShell],[...caps,...bodies],'Every stack part against each switch and moving cap; includes the upright center column of the sensor.');
    compare('antenna-projection',[rf],[components.bridge,components.sensor,components.driver,components.driverElectronics,swCourt,jCourt,batteryReserve],'Provisional 6×6 mm copper/metal screen vs hardware, independent of empty-space Z; carrier copper, hand loading and radio performance unproven.',xyGap);
  }
  const wiring=right?{
    sensorToDriver:{evidence:'Proposed four insulated analog leads; loft over bridge before descending on its key-side (−Y) edge. Top-edge solder exit and driver contact point are provisional. NOT a supplied flex, measured bundle, selected connector or verified solder map.',
      points:[[18.84,66,7.55],[21.5,66,7.85],[25.5,62.5,7.85],[26,56.7,7.85],[30.7,54.4,2],[34,51.5,1.5],[41.7,46.5,1.5],[43.5,46.25,1.5]],
      minimumEndpointDistance:model.metrics.wireLowerBound,actualTerminalAndBend:'sample gate',bundleAllowance:{width:2.8,height:.8},endpointNote:'Launch on the top edge of the castellated sensor. Electrical pin order and driver solder landing must be verified on the exact assembly; the last point is an envelope corner, not an electrical pad claim.'},
  }:{};
  if(right){
    const w=wiring.sensorToDriver,obs=[...caps,...bodies,xiao,components.usbShell,components.bridge,...components.feet,components.rubberCap,components.shaft,rf,batteryReserve,jCourt,jPlug,swCourt,
      components.driverHeader,components.driverElectronics,...solids.filter(s=>s.role==='screw-head')];
    // Every short AABB encloses its entire centerline segment expanded by the
    // rectangular-bundle circumscribed lateral radius and vertical half-height;
    // this is conservative between samples, not a samples-only interference test.
    const prisms=[];let length=0,edge=Infinity;
    for(let i=1;i<w.points.length;i++){
      const a=w.points[i-1],b=w.points[i],v=b.map((x,j)=>x-a[j]),len=Math.hypot(...v);
      const n=Math.ceil(len/.4);length+=len;
      for(let j=0;j<n;j++){
        const q=a.map((x,k)=>x+v[k]*(j+.5)/n),dx=Math.abs(v[0])/n,dy=Math.abs(v[1])/n,dz=Math.abs(v[2])/n,mid=pose(q[0],q[1]);
        prisms.push(cub('lead-span-'+i+'-'+j,'analog-sweep','Analog bundle guard','clearance',mid,w.bundleAllowance.width+dx,w.bundleAllowance.width+dy,q[2]-(w.bundleAllowance.height+dz)/2,q[2]+(w.bundleAllowance.height+dz)/2));
        edge=Math.min(edge,edgeDistance(mid,outline)-w.bundleAllowance.width/2-Math.hypot(dx,dy)/2);
      }
    }
    w.polylineLength=length;w.guardSegmentCount=prisms.length;
    compare('analog-bundle-to-carrier-parts',prisms,obs,'Entire swept 2.8 mm wide × 0.8 mm high conservative surrogate against bridge, feet, all switches/caps and hardware. Sensor and detached driver intentionally excluded as termination bodies; real solder/pin access and bend radii are not established.');
    checks.push({id:'analog-bundle-to-board-edge',status:edge>0?'pass':'clash',gap:edge,pair:['analog bundle','carrier edge'],explanation:'Signed lower bound for the full lateral 1.4 mm radius around every guide segment to the actual concave perimeter; rails and case cover still require MCAD.'});
  }
  const be=at(bq,0,right?-16:16), ce=at(j,0,4.4); // reference on as-built maximum end face, not the molded cable crimp
  wiring.battery={cellLeadLength:105,connector:'J1',cellExit:[be.x,be.y,1],connectorMouth:[ce.x,ce.y,2.5],
    exitOrientation:right?'−Y toward rear':'+Y toward palm',endpointEvidence:'Design reference on maximum pack end face only: measure actual tab point, pin lead length and installed plug wire exit.',
    selectedEnvelope:{width:2.2,height:1.1,serviceReserve:{pouchTopMax:4.3,organizerShelfBottom:5.4,organizerShelfTop:6.65}},
    routeOwner:'../mechanical (single source for actual lead centerline and organizer geometry; do NOT treat a straight segment between these points as a harness).',
    route:right?'Retained rear bay, then factory JST housing. Isolate stored slack from cell, connector and radio.':
    'Open interrow/upper-palm gap to outer palm connector; isolate slack above protected pouch. Verify both leads with actual sample.'};
  return {hand:h.hand,outline,bounds:bounds(outline),pcb:{top:0,bottom:zPCB,thickness:SPECS.pcbT},switches,buttons,components,mountingHoles,
    holes,solids,checks,wiring,usbMouth:{...mouth,direction:rotate([0,-1],xq.a||0)},powerActuator:at(sq,0,3.02),
    checkCoverage:{validated:'Nominal rectangles/prisms/circular drill envelopes, switch travel, screws/driver, PCB edge, battery and USB/JST equipment. No physical fixture.',
      open:['actual mating plug/cable and overmolds','routing and occupied volume of 105 mm lead, actual pouch tab exit/bend radius','sensor attachment/loaded deflection and actual wire egress','enclosure tolerance/assembly','exposed power actuator tool/fingertip reach','RF and charge qualification','individual incidental passive placements and positions of electrical pads not explicitly present here are owned by ECAD']}}
}
const result=clean({version:'tapir-rev-a-1',units:'mm',datum:{xy:'Independent local top view of each populated hand; originating B/G or N/H column x=0, never re-mirror. X increases toward viewer right; Y increases toward palm.',z:'Carrier top is 0; positive Z toward keycaps.',angles:'a is clockwise degrees on top-view XY, local vector (0,−1) points to nominal USB on controller at a=0. x/y are footprint origins unless specified.',outline:'Counterclockwise or clockwise simple polygon in XY with implicit closing segment. Same outline in PCB and case.',upperSwitch:'Direct-solder Choc v1; product footprint terminal side rotated 180° relative to historical web workbench. Body/cap unchanged; underside solids regenerated from ECAD-agreed physical pins.'},
  source:{layout:'../../workbench/layout.js',stack:'../../workbench/stack.js',stackOptions:STACK_DEFAULTS,
    switch:'https://raw.githubusercontent.com/daprice/keyswitches.pretty/master/SW_PG1350.kicad_mod',xiao:STACK_SOURCES.xiao,sensor:STACK_SOURCES.sensor,
    battery:'https://www.adafruit.com/product/1570',batteryMaximum:'https://cdn-shop.adafruit.com/product-files/1570/1570datasheet.pdf#page=5'},
  halves:Object.fromEntries(base.halves.map(h=>[h.hand,half(h)]))});
const path=fileURLToPath(new URL('./geometry.json',import.meta.url));
const output=JSON.stringify(result,null,2)+'\n';
if(process.argv.includes('--check'))assert.equal(fs.readFileSync(path,'utf8'),output,'geometry.json differs: regenerate it');
else fs.writeFileSync(path,output);
for(const [hand,h] of Object.entries(result.halves)){
  assert.equal(h.switches.length,21);assert.equal(h.buttons.length,hand==='left'?3:0);assert.equal(new Set(h.switches.map(k=>k.row+'-'+k.col)).size,21);
  assert.equal(new Set(h.solids.map(s=>s.id)).size,h.solids.length,'All solids must have unique IDs within a half');
  assert.equal(new Set(h.holes.map(s=>s.id)).size,h.holes.length,'All drills must have unique IDs within a half');
  console.log(hand,h.bounds,'drills',h.holes.length,'solids',h.solids.length);
  for(const c of h.checks) console.log(c.status,c.id,c.gap,c.pair?.join(' / '));
}
if(Object.values(result.halves).flatMap(h=>h.checks).some(c=>c.status==='clash'))process.exitCode=2;
