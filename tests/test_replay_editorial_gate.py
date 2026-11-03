import json,pytest
from scripts.replay_plan import replay
def test_failed_editorial_checkpoint_cannot_bypass_the_review_gate(tmp_path):
    w=tmp_path/'writing';w.mkdir()
    (w/'beats.json').write_text(json.dumps({'title':'Test','beats':[]}))
    (w/'shots.json').write_text('{}')
    (w/'editorial-review.json').write_text(json.dumps([{'review':{'issues':[{'severity':'major','problem':'Contradictory message ownership'}]}}]))
    with pytest.raises(ValueError,match='unresolved major'):
        replay(tmp_path,'Test','6')
