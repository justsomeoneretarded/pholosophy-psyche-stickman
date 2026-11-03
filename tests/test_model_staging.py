import pytest
from story.staging import validate_staging,compile_staging
from story.director import direct_beat
from story.validate import VOCAB
CAST=[{'id':'alex','kind':'hero'},{'id':'jamie','kind':'friend'}]
def test_model_selects_verified_articulated_performances_directly():
    b={'where':'park','seconds':12,'who':['alex'],'staging':[{'actors':[{'id':'alex','pose':'walk','x':15,'to':42}]},{'actors':[{'id':'alex','pose':'sitdown','x':42}]}]}
    validate_staging(b,CAST)
    shots=direct_beat(b,VOCAB)
    assert [s['actors'][0]['pose'] for s in shots]==['walk','sitdown']
    assert all(s['_directed'] for s in shots)
def test_unknown_actions_and_missing_contact_targets_fail_clearly():
    with pytest.raises(ValueError,match='Unsupported rig pose'):
        validate_staging({'staging':[{'actors':[{'id':'alex','pose':'execute_code','x':50}]}]},CAST)
    with pytest.raises(ValueError,match='target must appear'):
        validate_staging({'staging':[{'actors':[{'id':'alex','pose':'hug','x':50,'target':'jamie'}]}]},CAST)
def test_nonfinite_coordinates_cannot_reach_the_renderer():
    with pytest.raises(ValueError,match='finite coordinate'):
        validate_staging({'staging':[{'actors':[{'id':'alex','pose':'walk','x':float('nan')}]}]},CAST)
