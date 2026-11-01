import json,subprocess
from pathlib import Path
from story.validate import repair
ROOT=Path(__file__).resolve().parents[1]
def test_seated_actor_resolves_real_seat_and_compensates_for_scale():
    js=r"""
const fs=require('fs'),vm=require('vm');
const c={console,Math,setFor:()=>({ground:()=>880,seatAnchors:[19,31],seat:()=>62,desk:()=>108})};
vm.createContext(c);vm.runInContext(fs.readFileSync('engine/core.js','utf8'),c);
vm.runInContext(fs.readFileSync('engine/main.js','utf8'),c);
const result=vm.runInContext("FILM={cast:{}};actorState({},{id:'hero',x:50,pose:'sit',scale:.7},1)",c);
console.log(JSON.stringify(result));
"""
    value=json.loads(subprocess.check_output(['node','-e',js],cwd=ROOT,text=True))
    assert abs(value['st']['wx']-1920*.31)<1e-8
    assert abs(value['w']['seat']*.7-62)<1e-8
def test_narration_is_not_silently_cut_at_character_limit():
    text='The narrator explains this concrete situation carefully, '+('including its consequences and uncertainties. '*7)
    film,_=repair({'shots':[{'set':'park','dur':8,'actors':[{'id':'hero','x':50,'pose':'stand'}],
        'lines':[{'who':'narrator','text':text}]}]})
    assert film['shots'][0]['lines'][0]['text']==text.strip()
