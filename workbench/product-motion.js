// All motions are relative to the fully seated component. Local CAD +Y is
// minus the carrier drawing Y. A sequence is an inspection, not physical signoff.
export const motionIds={board:'pcb_into_tray',lid:'bezel_onto_caseless_assembly',plug:'usb_straight_insertion'};
export function pose(mode,role,f,paths,mouth){
  const answer={show:true,x:0,y:0,z:0};
  if(mode==='free'){answer.show=role!=='plug-gauge';return answer;}
  const p=paths?.find(s=>s.id===motionIds[mode]);
  if(!p){answer.show=false;return answer;}
  const remain=1-Math.min(1,Math.max(0,f));
  if(mode==='board'){answer.show=['board','tray','nut'].includes(role);if(role==='board')answer.z=remain*p.startZoffset_mm;}
  if(mode==='lid'){answer.show=!['cap','plug-gauge','reserve','cover-bolt'].includes(role);if(role==='cover')answer.z=remain*p.startZoffset_mm;}
  if(mode==='plug'){
    answer.show=role!=='reserve';
    if(role==='plug-gauge'){answer.x=remain*p.travel_mm*mouth.direction[0];answer.y=-remain*p.travel_mm*mouth.direction[1];}
  }
  return answer;
}
