import './product.css';
import {createProductScene,GROUPS,normalLayers} from './product-scene.js';
const $=s=>document.querySelector(s), esc=s=>String(s).replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const base='./prototype/', fmt=x=>Number(x).toLocaleString('en',{maximumFractionDigits:2});
const layerState={...normalLayers};let viewer,viewState={hand:'both',cam:'iso',exploded:0};
const pathNotes={board:'The capless carrier descends 24 mm into the fixed tray. The cell and bridge are not installed.',lid:'The bezel descends 24 mm over the seated parts with keycaps and rubber nub off. Slide to 100% for closed.',plug:'Qualtek 3021091-01M: a 36 mm approach, with the metal tip, 12.35 × 6.50 mm maximum overmold gauge and cable jacket. Tests case access, not USB contact engagement.'};
function pathUpdate(){const mode=$('#path-kind').value,v=Number($('#path-progress').value);$('#path-label').textContent=v+'%';
  $('#travel-panel').hidden=mode==='free';$('#explode').disabled=mode!=='free';$('#path-note').textContent=pathNotes[mode]||'';
  const state=$('#model-state');state.textContent=mode==='free'?(state.dataset.default||'CAD + envelopes'):{board:'Lower the carrier',lid:'Close the bezel',plug:'Insert the Qualtek gauge'}[mode]+' · '+v+'%';
  viewer?.setMotion?.(mode,v/100);}
$('#path-kind').onchange=()=>{$('#path-progress').value='0';pathUpdate();};
$('#path-progress').oninput=pathUpdate;
function selections(){for(const [field,selector] of [['hand','[data-hand]'],['cam','[data-cam]']])document.querySelectorAll(selector).forEach(el=>el.setAttribute('aria-pressed',String(el.dataset[field]===viewState[field])));$('#explode').value=viewState.exploded;$('#exploded-label').textContent=viewState.exploded+'%';}
$('#layer-set').innerHTML=Object.entries(GROUPS).map(([id,[name,color]])=>'<label class="plabel"><input type="checkbox" data-pl="'+id+'" '+(layerState[id]?'checked':'')+'/><span class="chip" style="background:'+color+'"></span>'+name+'</label>').join('');
document.addEventListener('click',ev=>{const b=ev.target.closest('button');if(!b||!viewer)return;
  if(b.dataset.hand){viewState.hand=b.dataset.hand;viewer.setHand(viewState.hand);}
  if(b.dataset.cam){viewState.cam=b.dataset.cam;viewer.setCamera(viewState.cam);}
  if(b.id==='pfit')viewer.fit();
  if(b.id==='preset-reset'){if(!$('#path-panel').hidden){$('#path-kind').value='free';pathUpdate();}for(const k of Object.keys(GROUPS)){layerState[k]=normalLayers[k];document.querySelector('[data-pl="'+k+'"]').checked=layerState[k];viewer.setLayer(k,layerState[k]);}viewState={hand:'both',cam:$('#cameras [data-cam=iso]').disabled?'top':'iso',exploded:0};viewer.setHand('both');viewer.setCamera(viewState.cam);viewer.setExplode(0);}
  selections();
});
$('#explode').oninput=e=>{viewState.exploded=Number(e.target.value);viewer?.setExplode(viewState.exploded/100);selections();};
$('#layer-set').onchange=e=>{if(!e.target.dataset.pl)return;const k=e.target.dataset.pl;layerState[k]=e.target.checked;viewer?.setLayer(k,layerState[k]);};
function fallback(data){
  const host=$('#pview');let hand='both';
  function draw(){const g=data.geometry.halves;
    const halves=(hand==='both'?['left','right']:[hand]).map(s=>{const h=g[s],x=hand==='both'?(s==='left'?-12-h.bounds.x1:12-h.bounds.x0):0;return {h,x};});
    const x0=Math.min(...halves.map(({h,x})=>h.bounds.x0+x)),x1=Math.max(...halves.map(({h,x})=>h.bounds.x1+x)),y0=Math.min(...halves.map(({h})=>h.bounds.y0)),y1=Math.max(...halves.map(({h})=>h.bounds.y1));
    const pad=7,pol=(a,fill,stroke='#485443')=>'<polygon points="'+a.map(p=>p.join(',')).join(' ')+'" fill="'+fill+'" stroke="'+stroke+'" stroke-width=".25"/>';
    host.innerHTML='<svg role="img" aria-label="Mathematically registered plan view, no WebGL" viewBox="'+[x0-pad,y0-pad,x1-x0+2*pad,y1-y0+2*pad].join(' ')+'" preserveAspectRatio="xMidYMid meet">'+halves.map(({h,x})=>'<g transform="translate('+x+' 0)">'+(layerState.pcb?pol(h.outline,'#365b48'):'')+h.solids.filter(s=>layerState.electronics&&['controller-board','sensor','usb-shell','driver','battery','stick-cap','mouse-switch'].includes(s.role)).map(s=>pol(s.polygon,s.role==='stick-cap'?'#c85532':'#aab2a1')).join('')+h.switches.map(s=>(layerState.switches?pol(s.bodyPolygon,'#8e9d91'):'')+(layerState.keys?pol(s.capPolygon,s.thumb?'#4c574b':'#eeeadd')+'<text x="'+s.x+'" y="'+(s.y+1)+'" fill="'+(s.thumb?'white':'#344136')+'" font-size="3" text-anchor="middle">'+esc(s.label)+'</text>':'')).join('')+'</g>').join('')+'</svg>';
  }
  draw();viewState.cam='top';document.querySelectorAll('[data-cam]:not([data-cam=top]),#explode,[data-pl=case],[data-pl=wiring],[data-pl=reserves]').forEach(el=>el.disabled=true);
  $('#interaction').textContent='Plan only · WebGL is required for CAD and assembly motion';$('#view-extent').textContent='This browser is displaying the shared XY outlines and component envelopes. The native case, copper and motion inspection require WebGL; their source files and test results are still available in the download.';$('#model-state').textContent='Registered plan';selections();
  return {setHand(v){hand=v;draw();},setLayer:()=>draw(),setCamera:()=>draw(),setExplode:()=>{},fit:()=>draw()};
}
function showProof(data){
  const g=data.geometry.halves, dims=h=>fmt(h.bounds.w)+' × '+fmt(h.bounds.h);
  const c=data.cadEvidence?.halves||[], bounding=hand=>{const b=c.find(h=>h.hand===hand)?.assembled_physical_bounds;return b?.length===6?[b[3]-b[0],b[4]-b[1],b[5]-b[2]]:null;};
  const left=bounding('left'),right=bounding('right');
  const specs=left&&right?[
    [fmt(left[0])+' × '+fmt(left[1]),'Left assembled · PCB '+dims(g.left)],
    [fmt(right[0])+' × '+fmt(right[1]),'Right assembled · PCB '+dims(g.right)],
    [fmt(Math.max(left[2],right[2]))+' mm','Assembled height · cable and optional feet excluded']
  ]:[[dims(g.left),'Left carrier / mm'],[dims(g.right),'Right carrier / mm'],[data.meshes.length+' meshes','Generated enclosure parts']];
  $('#product-specs').innerHTML=specs.map(([v,n])=>'<div class="pspec"><b>'+v+'</b><span>'+n+'</span></div>').join('');
  const rows=data.validation.rows||[], grid=$('#verification-grid');
  const countStatus=vals=>Object.entries(vals.reduce((obj,item)=>{let k=item.status||'UNKNOWN';obj[k]=(obj[k]||0)+1;return obj;},{})).map(([k,v])=>v+' '+k.replace(/_/g,' ').toLowerCase()).join(' · ');
  const buckets=new Map();for(const r of rows){const k=r.scope||'System';if(!buckets.has(k))buckets.set(k,[]);buckets.get(k).push(r);}
  function card(name,marker,detail,style='',items=[]){return '<article class="proofcard '+style+'"><span>'+esc(marker)+'</span><h3>'+esc(name)+'</h3><p>'+esc(detail)+'</p>'+(items.length?'<details><summary>Inspect '+items.length+' result'+(items.length===1?'':'s')+'</summary><ul>'+items.map(r=>'<li><b>'+esc(r.id)+'</b><br>'+esc(r.status.replaceAll('_',' '))+': '+esc(r.observed)+'</li>').join('')+'</ul></details>':'')+'</article>';}
  const out=[];
  out.push(card('Carrier geometry','DIMENSIONAL CHECKS',data.geometryChecks.passing+' of '+data.geometryChecks.count+' checks pass in the shared carrier model. These are nominal clearances.',data.geometryChecks.passing===data.geometryChecks.count?'good':'bad'));
  for(const [k,vs] of buckets){
    const failures=vs.filter(r=>/fail|block|missing|hold|partial/i.test(r.status));const conclusion=failures[0]?.observed;
    out.push(card(k.charAt(0).toUpperCase()+k.slice(1),countStatus(vs),conclusion?String(conclusion).slice(0,220):k==='physical'?'These tests require real parts and a built keyboard. No physical acceptance is claimed.':vs.length+' recorded test'+(vs.length===1?'':'s')+'.', failures.length?'bad':vs.every(r=>/pass/i.test(r.status))?'good':'',vs));
  }
  if(!rows.length)out.push(card('System release gate','NO RECORDED RUN','No release verification results were supplied for this preview. Do not infer clearance from the render.'));
  grid.innerHTML=out.join('');
}
async function start(){try{
  const response=await fetch(base+'scene.json');if(!response.ok)throw Error('Missing versioned scene');
  const data=await response.json();showProof(data);
  try{viewer=await createProductScene($('#pview'),data,({loadedCAD,failedCAD,componentFiles})=>{
      $('#model-state').textContent=failedCAD?'Mesh loading incomplete':loadedCAD?'CAD + envelopes':'Carrier envelopes';
      $('#model-state').dataset.default=$('#model-state').textContent;
      const active=Object.values(data.native).filter(n=>n.tracks?.length);
      $('#view-extent').textContent=loadedCAD+' build123d print-part meshes. '+(active.length===2?'Trace centerlines, pads and vias come from both routed boards; copper pours and mask are omitted for clarity. ':'Missing or unrouted native copper is not drawn. ')+(componentFiles&&active.length?'Top-side packages use the local STEP library, including independently drawn cap, XIAO and JST shapes.':'Keys and modules are shown as envelopes.')+' Fit models are not measured samples.';
    },base);
    $('#path-panel').hidden=!(data.cadEvidence?.halves?.length===2 && data.meshes?.some(s=>s.role==='cover'));
  }catch(error){console.warn('WebGL inspector unavailable; vector plan provided.',error);viewer=fallback(data);}
  selections();
}catch(error){$('#model-state').textContent='Geometry unavailable';$('#pview').innerHTML='<p>The product geometry could not be read. Use the native project sources or rerun the release preparation script.</p>';console.error(error);}}
start();
