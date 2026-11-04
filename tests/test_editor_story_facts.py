import json
import pytest
from story.editor import review_concept
from story.staging import validate_scene

def test_repair_receives_earlier_spoken_relationship_facts(tmp_path):
    sheet={'beats':[{'what_happens':'A letter','narration':['He writes to his brother.']},
                    {'what_happens':'A book','narration':['The objection deserves an answer.']}]}
    class Writer:
        count=0
        def json(self,system,user,validate,**kwargs):
            self.count+=1
            if self.count==1:return validate({'issues':[{'severity':'major','beats':[2],'repair':'Answer objection','problem':'No answer'}]})
            if self.count==2:
                payload=json.loads(user)
                assert 'brother' in payload['story_map'][0]['narration'][0]
                assert 'scene' in payload['supported_physical_staging']
                return validate({'changes':{'narration':['The letter to his brother supplies a concrete example.']}})
            return validate({'issues':[]})
    review_concept(sheet,Writer(),lambda s,m:([],20),'Meaning',4,tmp_path)

def test_named_set_is_not_a_composed_scene_base():
    with pytest.raises(ValueError,match='Unsupported scene base: street'):
        validate_scene({'base':'street'})
    validate_scene({'base':'outside','elements':[{'type':'streetlamp','x':60}]})

def test_invented_scene_prop_and_nonfinite_placement_fail():
    with pytest.raises(ValueError,match='Unsupported scene element'):
        validate_scene({'base':'room','elements':[{'type':'magic_flag'}]})
    with pytest.raises(ValueError,match='finite'):
        validate_scene({'base':'room','elements':[{'type':'table','x':float('nan')}]})
