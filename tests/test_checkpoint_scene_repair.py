import copy
import pytest
from story.checkpoint import repair_checkpoint

def test_checkpoint_schema_repair_preserves_speech_and_adds_needed_extra(tmp_path):
    sheet={'cast':[{'id':'a','kind':'hero'}],'beats':[{'where':'scene','scene':{'base':'street'},'narration':['He notices a stranger.'],'dialogue':[],'staging':[]}]}
    class Writer:
        used='mock'
        def json(self,system,user,validate,**kwargs):
            b=copy.deepcopy(sheet['beats'][0]);b['where']='street';b.pop('scene')
            b['staging']=[{'actors':[{'id':'a','pose':'think','x':30},{'id':'stranger','pose':'stand','x':60}]}]
            bad=copy.deepcopy(b);bad['narration']=['Changed speech']
            with pytest.raises(ValueError,match='preserve exact narration'):
                validate({'beat':bad,'extra_cast':[]})
            return validate({'beat':b,'extra_cast':[{'id':'stranger','kind':'extra'}]})
    result=repair_checkpoint(sheet,Writer(),tmp_path)
    assert result['beats'][0]['narration']==sheet['beats'][0]['narration']
    assert result['cast'][-1]['id']=='stranger'
    assert sheet['beats'][0]['scene']['base']=='street'
