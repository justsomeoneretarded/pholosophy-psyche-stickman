from story.continuity import carry_counters
def film(mode,reset=False):
    return {'hud':{'items':[{'label':'EDITS','mode':mode}]},'shots':[{'hud':{'values':[3]}},{'hud':{'values':[0],'reset':reset}},{'hud':{'values':[[1,4]]}}]}
def test_cumulative_totals_do_not_reset_between_shots():
    f=film('cumulative');notes=[];carry_counters(f,notes)
    assert f['shots'][1]['hud']['values']==[3]
    assert f['shots'][2]['hud']['values']==[[3,4]]
    assert notes
def test_normal_values_can_decrease():
    f=film('value');carry_counters(f,[])
    assert f['shots'][1]['hud']['values']==[0]
def test_explicit_story_reset_is_allowed():
    f=film('cumulative',True);carry_counters(f,[])
    assert f['shots'][1]['hud']['values']==[0]
