import json
from story.planning import plan_in_parts
class Writer:
    def __init__(self):self.calls=[]
    def json(self,system,user,check=None,**kwargs):
        self.calls.append(kwargs)
        if len(self.calls)==1:
            return check({'title':'Test','cast':[{'id':'hero','kind':'hero'}],
                'beats':[{'idea':str(i),'mode':'story','where':'park','what_happens':'A visible choice'} for i in range(12)]})
        payload=json.loads(user)
        if 'requested_indices' not in payload:
            return {'youtube_titles':['A thoughtful title'],'description':'A specific explanation.'}
        return check({'beats':[{'where':'park','who':['hero'],'what_happens':'He weighs the choice.',
            'narration':['A complete explanatory sentence, preserved exactly.']} for _ in payload['requested_indices']]})
def test_full_plan_uses_bounded_requests_and_still_runs_final_validation(tmp_path):
    writer=Writer();checked=[]
    def validate(sheet):checked.append(sheet);return sheet
    result=plan_in_parts(writer,'schema','topic',validate,4,tmp_path)
    assert len(result['beats'])==12
    assert len(checked)==1
    assert all(c['max_tokens']<=900 for c in writer.calls)
    assert all(b['narration']==['A complete explanatory sentence, preserved exactly.'] for b in result['beats'])

def test_each_outline_point_is_expanded_once(tmp_path):
    class PointWriter:
        def __init__(self):self.payloads=[]
        def json(self,system,user,check=None,**kw):
            if 'OUTLINE REQUEST' in system:
                return check({'title':'Test','cast':[{'id':'hero','kind':'hero'}],
                    'spine':[{'idea':str(i),'mode':'story','where':'park','what_happens':'He considers a different consequence.'} for i in range(7)]})
            payload=json.loads(user)
            if 'requested_indices' not in payload:return {}
            self.payloads.append(payload)
            return check({'beats':[{'who':['hero'],'where':'park','what_happens':'He thinks about the consequence.',
                'narration':['This is a complete explanatory sentence.']} ]})
    w=PointWriter()
    result=plan_in_parts(w,'schema','topic',lambda x:x,6,tmp_path)
    assert len(result['beats'])==7
    assert [p['spine_entries_to_advance'][0]['idea'] for p in w.payloads]==list(map(str,range(7)))
    assert len(w.payloads[-1]['previous_beats'])==6
