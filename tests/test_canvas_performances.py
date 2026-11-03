"""Sample real production performances and object endpoints without browser rendering."""
import json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_new_performances_and_contact():
    js=r"""
const fs=require('fs'),vm=require('vm'),c={console,Math};vm.createContext(c);
for(const f of ['core','character','performance'])vm.runInContext(fs.readFileSync('engine/'+f+'.js','utf8'),c);
const result=vm.runInContext(`(()=>{
 let maxPenError=0,transition=[];
 for(const pose of ['write','read','show','think','talk','standup','sitdown']){
  for(let u=0;u<=4;u+=.05){
   const P=evalPose({pose,seed:1,facing:1,seated:true,artwork:'seedling'},u,5,{seat:62,desk:108,moving:false});
   const coords=[...P.pelvis,...P.feet.flat(),...P.hands.flat()];
   if(!coords.every(Number.isFinite))throw Error('Nonfinite '+pose);
   if(P.feet.some(f=>f[1]>0))throw Error('Foot below floor '+pose);
   if(pose==='write' && u>.6){
    const target=artworkPoint(P.artwork,P.drawProgress);
    const tip=[P.hands[P.penHand][0]-Math.sin(.6)*6.5,P.hands[P.penHand][1]+Math.cos(.6)*6.5];
    maxPenError=Math.max(maxPenError,Math.hypot(tip[0]-P.paperX-target[0],tip[1]-P.paperY-target[1]));
   }
   if(pose==='standup')transition.push(P.pelvis[1]);
  }
 }
 const seats=allocateSeatActors({actors:[{id:'a',pose:'sit',x:50},{id:'b',pose:'write',x:50}]},{seatAnchors:[19,31]});
 return {maxPenError,transition,seats:seats.map(a=>a._seat_anchor)};
})()`,c);console.log(JSON.stringify(result));
"""
    result=json.loads(subprocess.check_output(['node','-e',js],cwd=ROOT,text=True))
    assert result['maxPenError']<1e-8
    assert len(set(result['seats']))==2
    assert result['transition'][0]>result['transition'][-1]
    assert max(abs(a-b) for a,b in zip(result['transition'],result['transition'][1:]))<3

def test_pen_contact_uses_the_reachable_rendered_ik_endpoint():
    js=r"""
const fs=require('fs'),vm=require('vm'),c={console,Math};vm.createContext(c);
for(const f of ['core','character','performance'])vm.runInContext(fs.readFileSync('engine/'+f+'.js','utf8'),c);
const error=vm.runInContext(`(()=>{
let worst=0;
for(const facing of [-1,0,1])for(const desk of [0,108])for(let u=.65;u<4;u+=.05){
 const P=evalPose({pose:'write',seed:1,facing,artwork:'seedling'},u,5,{seat:62,desk,moving:false});
 const hand=P.penHand,side=hand?1:-1,sx=side*RIG.shoulderX*(P.sideSit?.55:1),sy=P.pelvis[1]+RIG.shoulderY+P.shoulderDy+(1-P.squash)*20;
 const k=ik(sx,sy,...P.hands[hand],RIG.upper,RIG.fore,1);
 const target=artworkPoint(P.artwork,P.drawProgress);
 worst=Math.max(worst,Math.hypot(k[2]-Math.sin(.6)*6.5-P.paperX-target[0],k[3]+Math.cos(.6)*6.5-P.paperY-target[1]));
}
return worst;})()`,c);console.log(JSON.stringify(error));
"""
    error=json.loads(subprocess.check_output(['node','-e',js],cwd=ROOT,text=True))
    assert error<1e-6
