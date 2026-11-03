from story.editor import review_concept
def test_unfounded_major_finding_does_not_rewrite_valid_narration(tmp_path):
    class Critic:
        used='critic'
        def json(self,system,user,validate,**kwargs):
            return validate({'issues':[{'severity':'major','beats':[1],'problem':'Checking a schedule means knowing what Jamie intended.','repair':'Remove the clarifying question.'}]})
    class Checker:
        used='checker'
        def json(self,system,user,validate,**kwargs):
            return validate({'judgments':[{'index':0,'confirmed':False,'reason':'The schedule establishes task status, not another person intention.'}]})
    class Patcher:
        def json(self,*args,**kwargs):raise AssertionError('An unconfirmed preference must not trigger rewriting')
    source={'beats':[{'narration':['He checks the schedule, then asks what Jamie meant.']}]}
    result=review_concept(source,Patcher(),lambda s,m:([],10),'Test',6,tmp_path,reviewer=Critic(),adjudicator=Checker())
    assert result==source
