import json,subprocess
def test_stopped_walk_has_both_feet_on_the_floor():
    js=r"""
const fs=require('fs'),vm=require('vm'),c={console,Math};vm.createContext(c);
for(const f of ['core','character'])vm.runInContext(fs.readFileSync('engine/'+f+'.js','utf8'),c);
const P=vm.runInContext("evalPose({pose:'walk',seed:1},3,4,{walked:147,moving:false,dir:1})",c);
console.log(JSON.stringify(P.feet));"""
    feet=json.loads(subprocess.check_output(['node','-e',js],text=True))
    assert feet==[[-24,0],[24,0]]
