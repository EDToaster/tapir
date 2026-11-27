import {test} from 'node:test';
import assert from 'node:assert/strict';
import {pose} from './product-motion.js';
const paths=[{id:'pcb_into_tray',startZoffset_mm:24},{id:'bezel_onto_caseless_assembly',startZoffset_mm:24},{id:'usb_straight_insertion',travel_mm:36}];
test('board and bezel follow the normal without moving their respective fixed references',()=>{
  for(const [mode,role,fixed] of [['board','board','tray'],['lid','cover','board']]){
    for(const f of [0,.25,.5,1]){
      assert.deepEqual(pose(mode,role,f,paths,{}),{show:true,x:0,y:0,z:24*(1-f)});
      assert.deepEqual(pose(mode,fixed,f,paths,{}),{show:true,x:0,y:0,z:0});
      assert.equal(pose(mode,'cap',f,paths,{}).show,false);
    }
  }
});
test('left and right USB gauges approach opposed mouths and finish on the datum',()=>{
  for(const sy of [-1,1])for(const f of [0,.5,1]){
    const m=pose('plug','plug-gauge',f,paths,{direction:[0,sy]});
    assert.equal(m.show,true);assert.ok(Math.abs(m.y + 36*(1-f)*sy)<1e-10);assert.equal(m.x,0);assert.equal(m.z,0);
  }
  assert.equal(pose('free','plug-gauge',1,paths,{}).show,false);
  assert.equal(pose('plug','plug-gauge',.5,[],{}).show,false);
});
