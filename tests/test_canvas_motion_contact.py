"""Numerical checks against the production canvas rig and trajectory."""
import json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def node(source):
    return json.loads(subprocess.check_output(['node','-e',source],cwd=ROOT,text=True))
def test_walk_and_run_contact_stays_planted_at_different_scales():
    result=node(r"""
const fs=require('fs'),vm=require('vm');
const c={console,Math,clamp:(x,a,b)=>Math.max(a,Math.min(b,x)),
lerp:(a,b,t)=>a+(b-a)*t,easeInOut:t=>t*t*(3-2*t),noise1:()=>0};
vm.createContext(c);vm.runInContext(fs.readFileSync('engine/character.js','utf8'),c);
const errors=[];
for(const scale of [.6,1,1.4])for(const run of [false,true])for(const dir of [-1,1]){
 const stride=run?190:120,stance=run?.48:.6, xs=[];
 for(const f of [.1,.2,.3,.4]){
  const distance=stride*f;
  const P=vm.runInContext('basePose()',c);
  c.P=P;c.w={walked:distance,moving:true,dir};c.run=run;
  vm.runInContext('POSES.walk(P,{seed:1},1,4,w,run)',c);
  xs.push(dir*distance*scale+P.feet[0][0]*scale);
  if(P.feet[0][1]!==0)throw Error('stance foot left floor');
 }
 errors.push(Math.max(...xs)-Math.min(...xs));
}
console.log(JSON.stringify(errors));
""")
    assert max(result)<1e-8
def test_trajectory_has_no_acceleration_boundary_jump():
    result=node(r"""
const fs=require('fs'),vm=require('vm');
const c={console,Math,FILM:{cast:{}},setFor:()=>({ground:()=>900}),
flatGround:()=>900,pct:x=>x*19.2,clamp:(x,a,b)=>Math.max(a,Math.min(b,x)),
lerp:(a,b,t)=>a+(b-a)*t,strHash:()=>1};
vm.createContext(c);vm.runInContext(fs.readFileSync('engine/main.js','utf8'),c);
vm.runInContext('FILM={cast:{}}',c);
const values=[];
for(const q of [.1,.9]){
 c.q=q;
 values.push(vm.runInContext(`(()=>{let a={id:'hero',x:10,to:90,pose:'walk'};let T=1536/170;return Math.abs(actorState({},a,(q+1e-7)*T).st.wx-actorState({},a,(q-1e-7)*T).st.wx)})()`,c));
}
console.log(JSON.stringify(values));
""")
    assert max(result)<.001
