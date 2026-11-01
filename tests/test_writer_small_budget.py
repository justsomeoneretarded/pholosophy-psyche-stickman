from pipeline.writing.llm import Writer
def test_small_stage_output_budget_is_not_raised_above_callers_limit():
    captured=[]
    class Client:
        def complete(self,system,user,**kwargs):
            captured.append(kwargs['max_tokens'])
            return '{"ok":true}'
    writer=Writer('groq:test')
    writer._client=lambda _:Client()
    assert writer.json('system','user',max_tokens=900)=={'ok':True}
    assert captured==[900]
