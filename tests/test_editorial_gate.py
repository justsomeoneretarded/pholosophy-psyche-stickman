import json,pytest
from story.editor import review_concept
def test_unresolved_major_findings_block_production_and_preserve_the_draft(tmp_path):
    class Reviewer:
        used='test'
        def json(self,system,user,validate,**kwargs):
            return validate({'issues':[{'severity':'major','beats':[1],'problem':'The same invitation restarts after acceptance.','repair':'Keep the accepted invitation complete.'}]})
    sheet={'title':'Test','beats':[{'narration':['An invitation is accepted.']}]}
    with pytest.raises(ValueError,match='major continuity/content issues'):
        review_concept(sheet,Reviewer(),lambda s,m:([],10),'Test',6,tmp_path,rounds=0)
    assert (tmp_path/'editorial-review.json').exists()
    assert json.loads((tmp_path/'concept-after-editor.json').read_text())==sheet
