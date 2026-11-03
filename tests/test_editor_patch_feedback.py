from story.editor import review_concept
import pytest
def test_editor_rejection_names_unknown_fields_for_an_actionable_retry(tmp_path):
    sheet={'beats':[{'narration':['A complete explanation.'],'what_happens':'He considers the situation.'}]}
    class Writer:
        count=0
        def json(self,system,user,validate,**kwargs):
            self.count+=1
            if self.count==1:return validate({'issues':[{'severity':'major','beats':[1],'problem':'Needs a distinction','repair':'Add a specific distinction'}]})
            if self.count==2:
                assert 'Allowed beat fields:' in system
                with pytest.raises(ValueError,match='unknown_field'):
                    validate({'changes':{'unknown_field':'A revision'}})
                return validate({'changes':{'narration':['A specific distinction now advances the explanation.']}})
            return validate({'issues':[]})
    result=review_concept(sheet,Writer(),lambda s,m:([],20),'A topic',4,tmp_path)
    assert 'specific distinction' in result['beats'][0]['narration'][0]
    assert 'unknown_field' in (tmp_path/'editorial-review.json').read_text()
