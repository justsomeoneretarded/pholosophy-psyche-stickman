from story.validate import repair
def test_cta_actor_does_not_type_on_a_floating_desk_or_cover_centered_buttons():
    f,_=repair({'shots':[{'dur':3,'card':{'style':'cta','lines':['A question']},'actors':[{'id':'hero','pose':'type','x':50,'seated':True}]}]})
    a=f['shots'][0]['actors'][0]
    assert a['pose']=='wave' and a['x']==18 and a['scale']==.6 and not a['seated']
