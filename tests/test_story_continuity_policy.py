from story.essay import check_concept
def test_a_coherent_single_location_is_not_rejected_for_an_arbitrary_set_quota():
    line='The next decision changes what the character can learn from the situation.'
    beats=[{'where':'park','mode':'story','who':['hero'],'seconds':18,
            'what_happens':'He walks toward another person.','narration':[line,line]} for _ in range(12)]
    sheet={'_title':'A conversation','beats':beats}
    problems,_=check_concept(sheet,4)
    assert not any('different places' in p or 'at least 3 different ways' in p for p in problems)
    assert sheet['_visual_review_notes']
