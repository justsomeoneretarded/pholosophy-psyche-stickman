from story.editor import review_concept

def test_editor_repairs_specific_issue_without_discarding_other_story_elements(tmp_path):
    sheet={'title':'A decision','beats':[{'name':'Opening','narration':['A concrete situation.'],'what_happens':'A character checks a message.'},
                                       {'name':'Turn','narration':['Every doubt disappears forever.'],'what_happens':'The character sends a message.'}],
           'logo':['A decision','A useful distinction']}
    class Writer:
        count=0
        def json(self,system,user,validate,**kwargs):
            self.count+=1
            if self.count==1:
                return validate({'issues':[{'severity':'major','beats':[2],'problem':'Promises a universal cure','repair':'Show uncertainty remaining while the conversation begins.'}],'strengths':['Keep the concrete message story']})
            if self.count==2:
                return validate({'edits':[{'beat':2,'narration':['The doubt remains, but another person can finally reply.']}],'metadata':{}})
            return validate({'issues':[],'strengths':['The ending now follows the argument']})
    result=review_concept(sheet,Writer(),lambda s,m:([],40),'A decision',4,tmp_path)
    assert result['beats'][0]==sheet['beats'][0]
    assert result['beats'][1]['what_happens']==sheet['beats'][1]['what_happens']
    assert 'doubt remains' in result['beats'][1]['narration'][0]
    assert (tmp_path/'editorial-review.json').exists()
    assert sheet['beats'][1]['narration']==['Every doubt disappears forever.']
