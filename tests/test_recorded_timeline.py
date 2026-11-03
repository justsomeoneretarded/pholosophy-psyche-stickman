import json
from audio.voice import reusable_takes,fit_recorded_timeline
def test_exact_same_voice_checkpoint_only(tmp_path):
    (tmp_path/'voice').mkdir();(tmp_path/'voice'/'a.wav').write_bytes(b'validated-artifact')
    film={'narrator_voice':'warguy','speech_verification':{'passed':True},'shots':[{'lines':[{'who':'narrator','text':'The uncertainty remains.','speech_verified':True,'voice_file':'a.wav'}]}]}
    (tmp_path/'film.json').write_text(json.dumps(film))
    assert 'The uncertainty remains.' in reusable_takes(tmp_path,'warguy')
    assert reusable_takes(tmp_path,'female')=={}
    assert 'A different sentence.' not in reusable_takes(tmp_path,'warguy')
def test_measured_speech_removes_padding_without_cutting_an_action():
    film={'shots':[{'dur':20,'actors':[{'pose':'think'}],'lines':[{'who':'narrator','at':.25,'voice_dur':5}]},
                   {'dur':20,'actors':[{'pose':'walk','x':10,'to':90}],'lines':[{'who':'narrator','at':.25,'voice_dur':2}]}]}
    fit_recorded_timeline(film)
    assert film['shots'][0]['dur']==6
    assert film['shots'][1]['dur']>9
    assert film['duration']<20

def test_deletion_finishes_before_the_shot_is_cut():
    film={'shots':[{'dur':20,'actors':[],'phone':{'typing':{'text':'x'*44,'at':.4,'action':'delete'}},'lines':[{'who':'narrator','at':.25,'voice_dur':1}]}]}
    fit_recorded_timeline(film)
    assert film['shots'][0]['dur']>7
