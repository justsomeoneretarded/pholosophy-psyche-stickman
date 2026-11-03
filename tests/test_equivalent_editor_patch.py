from story.editor import review_concept
def test_equivalent_bare_field_patch_is_validated_on_the_fixed_requested_beat(tmp_path):
    class Model:
        n=0
        def json(self,system,user,validate,**kwargs):
            self.n+=1
            if self.n==1:return validate({'issues':[{'severity':'major','beats':[1],'problem':'A contradiction','repair':'Retain uncertainty.'}]})
            if self.n==2:return validate({'narration':['The uncertainty remains.']})
            return validate({'issues':[]})
    result=review_concept({'beats':[{'narration':['Everything is certain.']}]},Model(),lambda s,m:([],10),'Test',6,tmp_path)
    assert result['beats'][0]['narration']==['The uncertainty remains.']
