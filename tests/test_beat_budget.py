from story.essay import place_narration
def test_additional_narration_angles_share_the_existing_beat_duration():
    b={'seconds':60,'who':['alex'],'narration':['One complete sentence with useful explanatory content.' for _ in range(6)]}
    shots=[{'dur':30,'actors':[{'id':'alex','pose':'think','x':50}],'camera':{'frame':'wide'}},{'dur':30,'actors':[{'id':'alex','pose':'think','x':50}],'camera':{'frame':'medium'}}]
    result=place_narration(b,shots)
    assert len(result)==6
    assert abs(sum(s['dur'] for s in result)-60)<.01
